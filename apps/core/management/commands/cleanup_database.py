import logging
from collections import Counter

from activity.models import UserActivity
from allauth.account.models import EmailAddress, EmailConfirmation
from annotations.models import Annotation
from deployment.models import FooterImage, SiteLogo
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic
from django_celery_results.models import TaskResult
from django_otp.plugins.otp_email.models import EmailDevice
from events.models import Event
from export.models import FlexibleDataExport
from impersonate.models import ImpersonationLog
from knowledgebase.models import PlatformImportAttempt, RouterSyncAttempt
from logs.models import (
    Dimension,
    DimensionText,
    FlexibleReport,
    ImportBatch,
    ImportBatchSyncLog,
    LastAction,
    ManualDataUpload,
)
from necronomicon.models import Batch, Candidate
from organizations.models import Organization, UserOrganization
from publications.models import Platform, Title
from recache.models import CachedQuery
from rest_framework.authtoken.models import Token
from reversion.models import Revision, Version
from scheduler.models import FetchIntentionQueue, Harvest, Scheduler
from sushi.models import SushiFetchAttempt
from tags.models import Tag, TagClass, TaggingBatch

from core.logic.util import this_celus_domain
from core.models import DataSource, User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Cleanup all the organizations and their data from the database. Used when you copy an "
        "existing db into a new install and want to clean it up."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--bootstrap",
            action="store_true",
            help="Do extra cleaning for creating a database bootstrap",
        )
        parser.add_argument("--do-it", dest="doit", action="store_true")

    @classmethod
    def update_stats(cls, stats, details):
        for key, value in details.items():
            stats[key] += value

    def handle(self, *args, **options):
        if not options["doit"]:
            # when pretending, we need to run in a transaction to be able to rollback
            with atomic():
                self.cleanup_database(options)
            self.stderr.write(
                self.style.SUCCESS("Pretend run completed, use --do-it to really do it")
            )
        else:
            self.cleanup_database(options)
            self.stderr.write(self.style.SUCCESS("Database cleaned up"))

    def cleanup_database(self, options):
        # at first truncate the largest tables to make the cleanup faster
        to_truncate = (
            "logs_accesslog",
            "logs_importbatch",
            "publications_platformtitle",
            "publications_title",
            "sushi_sushifetchattempt",
        )
        with connection.cursor() as cursor:
            for table in to_truncate:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                self.stderr.write(self.style.SUCCESS(f"{table} table truncated"))

        # remove unused data
        stats = Counter()
        for model in (
            ImportBatch,
            Organization,
            Annotation,
            FlexibleDataExport,
            CachedQuery,
            Harvest,
            Scheduler,
            Title,
            UserActivity,
            RouterSyncAttempt,
            TaskResult,
            PlatformImportAttempt,
            EmailConfirmation,
            Token,
            FooterImage,
            SiteLogo,
            ImpersonationLog,
            FlexibleReport,
            ManualDataUpload,
            LogEntry,
            ImportBatchSyncLog,
            Version,
            FetchIntentionQueue,
            Revision,
            Tag,
            TagClass,
            TaggingBatch,
            SushiFetchAttempt,
            Candidate,
            Batch,
            LastAction,
            Session,
            Token,
            Event,
            EmailDevice,
        ):
            self.stderr.write(self.style.WARNING(f"Deleting {model.__name__}"))
            count, details = model.objects.all().delete()
            self.update_stats(stats, details)
            self.stderr.write(self.style.WARNING(f"  - deleted: {count} objects"))
        # remove some dimension texts
        for dim_name in ("Publisher", "Success", "Platform", "YOP"):
            try:
                dim = Dimension.objects.get(short_name=dim_name)
            except Dimension.DoesNotExist:
                pass
            else:
                count, details = DimensionText.objects.filter(dimension=dim).delete()
                self.update_stats(stats, details)
                self.stderr.write(
                    self.style.WARNING(f'Deleted {count} DimensionTexts for dim "{dim_name}"')
                )
        self.stderr.write(self.style.WARNING("Delete stats: "))
        for key, value in sorted(stats.items()):
            self.stderr.write(self.style.WARNING(f"  {key}: {value}"))
        # fix other things
        site = Site.objects.get(pk=settings.SITE_ID)
        host_name = this_celus_domain()
        if site.name != host_name or site.domain != host_name:
            site.name = host_name
            site.domain = host_name
            self.stderr.write(
                self.style.SUCCESS(f'Updating site object to host name "{host_name}"')
            )
            site.save()
        # create consortium organization
        for org_id in settings.MASTER_ORGANIZATIONS:
            org = Organization.objects.create(internal_id=org_id, short_name=org_id, name=org_id)
            self.stderr.write(self.style.SUCCESS(f'Created organization "{org_id}"'))
            # assign all existing users to the consortium organization
            for user in User.objects.all():
                UserOrganization.objects.get_or_create(
                    user=user, organization=org, defaults={"is_admin": True}
                )
                self.stderr.write(
                    self.style.SUCCESS(f'Assigned user "{user.email}" to organization "{org_id}"')
                )

        # set knowledgebase source so that it uses token from the settings
        res = DataSource.objects.filter(
            type=DataSource.TYPE_KNOWLEDGEBASE, url__startswith="https://brain.celus.net"
        ).update(token="$")
        self.stderr.write(
            self.style.SUCCESS(f"Updated {res} knowledgebase sources to use token from settings")
        )

        # delete all platforms with null source
        count, details = Platform.objects.filter(source__isnull=True).delete()
        self.stderr.write(self.style.SUCCESS(f"Deleted platforms with null source: {details}"))

        # look for obsolete table `error_report_error` and remove it
        # it is a remnant of a removed app, so it must be removed manually using raw SQL
        self.stderr.write(self.style.WARNING("Looking for obsolete table `error_report_error`"))
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS error_report_error")
        self.stderr.write(self.style.SUCCESS("Obsolete table `error_report_error` removed"))

        if options["bootstrap"]:
            # remove all non-staff users
            User.objects.exclude(is_staff=True).delete()
            self.stderr.write(self.style.SUCCESS("Bootstrap: Removed all non-staff users"))
            # make sure all remaining users have 2fa enabled
            User.objects.all().update(skip_2fa=False)
            self.stderr.write(self.style.SUCCESS("Bootstrap: Enabled 2fa for all users"))
            # create verified email addresses for all users
            for user in User.objects.all():
                EmailAddress.objects.update_or_create(
                    user=user, email=user.email, defaults={"verified": True, "primary": True}
                )
            self.stderr.write(
                self.style.SUCCESS("Bootstrap: Created verified email addresses for all users")
            )

        if not options["doit"]:
            raise ValueError("preventing db commit, use --do-it to really do it ;)")
