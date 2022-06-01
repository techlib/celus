import hashlib
import json
import logging
import traceback
import typing
from collections import Counter
from enum import Enum, auto
from urllib.parse import urljoin

import requests
from core.models import DataSource
from core.tasks import async_mail_admins
from django.core.validators import MinLengthValidator
from django.db import models, transaction
from django.db.transaction import on_commit
from django.utils import timezone
from logs.models import Dimension, Metric, ReportType, ReportTypeToDimension
from publications.models import Platform

from .serializers import PlatformSerializer, ReportTypeSerializer

logger = logging.getLogger(__name__)


class AuthTokenMixin:
    @property
    def request_headers_extra(self) -> dict:
        return {}

    @property
    def request_headers(self) -> dict:
        res = {'Authorization': f'Token {self.source.token}', 'Content-Type': 'application/json'}
        res.update(self.request_headers_extra)
        return res


class RouterSyncAttempt(AuthTokenMixin, models.Model):
    class Target(models.TextChoices):
        ABSENT = "A", "absent"
        PRESENT = "P", "present"

    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    prefix = models.CharField(max_length=8, validators=[MinLengthValidator(8)])
    target = models.CharField(max_length=1, choices=Target.choices, default=Target.PRESENT)
    retries = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    done = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, null=True)

    @property
    def url(self):
        return urljoin(self.source.url, f"/router/api-key-prefix/{self.prefix}/")

    def trigger(self) -> bool:
        # Deleting prefix should not be performed before Insert
        #
        # So if there is a Target.PRESENT attempt which is not
        # not propagaged yet, don't perform Target.ABSENT
        if self.target == self.Target.ABSENT:
            if RouterSyncAttempt.objects.filter(
                prefix=self.prefix, target=self.Target.PRESENT, done__isnull=True
            ).exists():
                return False

        res = False
        try:
            self.last_error = None
            if self.target == self.Target.PRESENT:
                resp = requests.put(self.url, headers=self.request_headers)
                resp.raise_for_status()
            elif self.target == self.Target.ABSENT:
                resp = requests.delete(self.url, headers=self.request_headers)
                if resp.status_code != 404:  # already deleted
                    resp.raise_for_status()

            self.done = timezone.now()
            res = True
        except Exception as e:
            logger.warning("An error occured: %s", e)
            logger.debug(traceback.format_exc())

            self.last_error = str(e)
            self.retries = models.F('retries') + 1
        finally:
            self.save()

        return res

    @staticmethod
    def propagate_prefix(prefix: str, target: 'RouterSyncAttempt.Target'):
        with transaction.atomic():
            for source in DataSource.objects.filter(type=DataSource.TYPE_KNOWLEDGEBASE):
                sync_attempt, _ = RouterSyncAttempt.objects.get_or_create(
                    prefix=prefix, target=target, source=source
                )
                on_commit(lambda: sync_attempt.plan())

    def plan(self):
        from .tasks import sync_route

        sync_route.delay(self.pk)


class ImportAttempt(AuthTokenMixin, models.Model):
    class State(Enum):
        QUEUE = auto()
        DOWNLOADING = auto()
        PROCESSING = auto()
        SKIPPED = auto()
        SUCCESS = auto()
        FAILED = auto()

    class MergeStrategy(Enum):
        NONE = auto()  # No merging is performed
        EMPTY_SOURCE = auto()  # Merges by short_name only when source is empty
        ALL = auto()  # Merges by short_name regardless of the source

    KIND_PLATFORM = 'platform'
    KIND_REPORT_TYPE = 'report_type'

    KINDS = (
        (KIND_PLATFORM, 'Platform'),
        (KIND_REPORT_TYPE, 'Report type'),
    )

    URL_MAP = {
        KIND_PLATFORM: '/knowledgebase/platforms/',
        KIND_REPORT_TYPE: '/knowledgebase/report_types/',
    }

    url = models.URLField()
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=KINDS)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    started_timestamp = models.DateTimeField(null=True, blank=True)
    downloaded_timestamp = models.DateTimeField(null=True, blank=True)
    processing_timestamp = models.DateTimeField(null=True, blank=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)
    data_hash = models.CharField(
        max_length=64, help_text="SHA-256 hash of attempt", null=True, blank=True
    )
    stats = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True, null=True)

    @property
    def status(self) -> 'ImportAttempt.State':
        if self.error is not None:
            return ImportAttempt.State.FAILED

        if self.started_timestamp is None:
            return ImportAttempt.State.QUEUE

        if not self.data_hash:
            return ImportAttempt.State.DOWNLOADING

        if self.end_timestamp is None:
            return ImportAttempt.State.PROCESSING

        if self.processing_timestamp is None:
            return ImportAttempt.State.SKIPPED

        return ImportAttempt.State.SUCCESS

    @property
    def failed(self) -> bool:
        """attempt failed"""
        return self.status == ImportAttempt.State.FAILED

    @property
    def success(self) -> bool:
        return self.status in (ImportAttempt.State.SUCCESS, ImportAttempt.State.SKIPPED)

    @property
    def running(self):
        """running or to be run"""
        return not self.failed and not self.success

    def save(self, *args, **kwargs):
        self.kind = self.required_kind
        self.url = urljoin(self.source.url, ImportAttempt.URL_MAP[self.kind])
        return super().save(*args, **kwargs)

    def perform(self, merge=MergeStrategy.EMPTY_SOURCE):
        """Downloads data from knowledgebase and imports it

        :param merge: Try to merge with existing platforms without a source (should be used rarely)
        """
        self.started_timestamp = timezone.now()
        self.save()

        try:
            # find latest digest
            latest_download = (
                ImportAttempt.objects.filter(
                    source=self.source,
                    kind=self.required_kind,
                    downloaded_timestamp__isnull=False,
                    data_hash__isnull=False,
                )
                .exclude(data_hash__exact="")
                .order_by('-downloaded_timestamp')
                .first()
            )

            # download
            resp = requests.get(self.url, headers=self.request_headers)
            resp.raise_for_status()

            # store hash
            data = resp.json()
            sha256 = hashlib.sha256()
            sha256.update(json.dumps(data).encode())
            self.downloaded_timestamp = timezone.now()
            self.data_hash = sha256.hexdigest()
            self.save()

            # process data
            if not latest_download or latest_download.data_hash != self.data_hash:
                self.processing_timestamp = timezone.now()
                self.save()
                self.process(data, merge)

        except Exception as e:
            logger.warning("An error occured: %s", e)
            logger.debug(traceback.format_exc())

            self.error = str(e)

        finally:
            self.end_timestamp = timezone.now()
            self.save()


class PlatformImportAttempt(ImportAttempt):
    class Meta:
        proxy = True

    def plan(self):
        from .tasks import update_platforms

        update_platforms.delay(self.pk)

    @transaction.atomic
    def process(self, data: typing.List[dict], merge=ImportAttempt.MergeStrategy.EMPTY_SOURCE):
        counter: typing.Counter[str] = Counter()

        UPDATABLE_FIELDS = (
            'short_name',
            'name',
            'provider',
            'url',
            'knowledgebase',
            'counter_registry_id',
        )

        # parse data
        serializer = PlatformSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        counter["total"] = len(data)

        updated_platforms_ids = []

        for record in data:

            # make sure that counter_registry_id is
            # not used for other platform
            if record["counter_registry_id"]:
                Platform.objects.filter(
                    models.Q(counter_registry_id=record["counter_registry_id"])
                    & ~models.Q(ext_id=record["pk"])
                ).update(counter_registry_id=None)

            updatable = dict(
                short_name=record["short_name"],
                name=record["name"],
                provider=record["provider"],
                url=record["url"],
                knowledgebase={"providers": record["providers"]},
                counter_registry_id=record["counter_registry_id"],
            )

            if merge == ImportAttempt.MergeStrategy.NONE:
                # Only new or existing with the same source
                platform, created = Platform.objects.get_or_create(
                    defaults=updatable, ext_id=record["pk"], source=self.source
                )
            elif merge in [
                ImportAttempt.MergeStrategy.EMPTY_SOURCE,
                ImportAttempt.MergeStrategy.ALL,
            ]:
                try:
                    # Try to get existing record (non-knowledgebase) record
                    query_args = models.Q(short_name=record["short_name"]) & ~models.Q(
                        source__type=DataSource.TYPE_KNOWLEDGEBASE
                    )
                    if merge == ImportAttempt.MergeStrategy.EMPTY_SOURCE:
                        query_args = query_args & models.Q(source__isnull=True)
                    platform = Platform.objects.get(query_args)

                    # update existing platform
                    platform.source = self.source
                    platform.ext_id = record["pk"]
                    platform.save()
                    created = False

                except Platform.DoesNotExist:
                    platform, created = Platform.objects.get_or_create(
                        defaults=updatable, ext_id=record["pk"], source=self.source
                    )
                except Platform.MultipleObjectsReturned:
                    # if multiple objects are returned we are not sure which one to merge
                    # so lets skip it and don't update platform
                    logger.warning(
                        "Multiple platforms with '%s' in db. Not sure which one to merge => skip",
                        record["short_name"],
                    )
                    counter["skipped"] += 1
                    continue

            else:
                raise ValueError(f'Unsupported value for "merge": {merge}')

            updated_platforms_ids.append(platform.pk)
            needs_update = any(updatable[e] != getattr(platform, e) for e in UPDATABLE_FIELDS)

            if created:
                logger.info("Platform '%s' created", record["short_name"])
                platform.create_default_interests()
                counter["created"] += 1

            elif needs_update:
                for e in UPDATABLE_FIELDS:
                    setattr(platform, e, updatable[e])
                platform.save()
                logger.info("Platform '%s' updated", record["short_name"])
                counter["updated"] += 1

            else:
                logger.info("Platform '%s' remained the same", record["short_name"])
                counter["same"] += 1

        # Wipe knowledgebase data which were removed from knowledgebase
        for platform in Platform.objects.filter(
            source=self.source, knowledgebase__isnull=False
        ).exclude(pk__in=updated_platforms_ids):
            logger.info("Knowledgebase data from platform '%s' wiped", platform.short_name)
            platform.knowledgebase = None
            platform.save()
            counter["wiped"] += 1

        self.stats = dict(counter)

        self.save()

    @property
    def required_kind(self):
        return ImportAttempt.KIND_PLATFORM


class ReportTypeImportAttempt(ImportAttempt):
    class Meta:
        proxy = True

    def plan(self):
        from .tasks import update_report_types

        update_report_types.delay(self.pk)

    @property
    def required_kind(self):
        return ImportAttempt.KIND_REPORT_TYPE

    @transaction.atomic
    def process(self, data: typing.List[dict], merge=ImportAttempt.MergeStrategy.NONE):
        # merge strategy should be always NONE - we are merging only
        # reporttypes which were created using import attempt

        counter: typing.Counter[str] = Counter()

        # parse data
        serializer = ReportTypeSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        counter["total"] = len(data)

        for report_type_data in data:
            report_type, created = ReportType.objects.get_or_create(
                source=self.source,
                ext_id=report_type_data["pk"],
                defaults={
                    "name": report_type_data["name"],
                    "short_name": report_type_data["short_name"],
                },
            )

            # Create dimensions (if needed)
            if created:
                dimensions = []
                for dimension_data in report_type_data["dimensions"]:
                    dimension, dimension_created = Dimension.objects.get_or_create(
                        source=self.source, short_name=dimension_data['short_name'],
                    )
                    if dimension_created:
                        logger.info(
                            "Dimension '%s' was created for report type '%s'",
                            dimension.short_name,
                            report_type_data['short_name'],
                        )
                    dimensions.append(dimension)
            else:
                dimensions = []

            # Create metrics (if needed)
            metrics = []
            for metric_data in report_type_data["metrics"]:
                metric, metric_created = Metric.objects.get_or_create(
                    source=self.source, short_name=metric_data['short_name'],
                )
                if metric_created:
                    logger.info(
                        "Metric '%s' was created for report type '%s'",
                        metric.short_name,
                        report_type_data['short_name'],
                    )

                metrics.append(metric)

            if created:
                report_type.controlled_metrics.set(metrics)
                # create dimensions
                for position, dimension in enumerate(dimensions):
                    ReportTypeToDimension.objects.create(
                        position=position, report_type=report_type, dimension=dimension,
                    )
                counter["created"] += 1
            else:
                updated = False

                # Compare metrics
                metrics_differ = set(e.pk for e in report_type.controlled_metrics.all()) != {
                    e.pk for e in metrics
                }
                if metrics_differ:
                    report_type.controlled_metrics.set(metrics)
                updated = updated or metrics_differ

                # Compare dimensions and send an email to admins when it differs
                dimensions = list(
                    enumerate([e["short_name"] for e in report_type_data["dimensions"]])
                )
                orig_dimensions = [
                    (e.position, e.dimension.short_name)
                    for e in report_type.reporttypetodimension_set.order_by(
                        'position'
                    ).select_related('dimension')
                ]
                if dimensions != orig_dimensions:
                    old_text = "".join(f'{e[0]}. - {e[1]}\n' for e in orig_dimensions)
                    new_text = "".join(f'{e[0]}. - {e[1]}\n' for e in dimensions)
                    async_mail_admins.delay(
                        "Report type dimensions were modified",
                        f"ReportType: {report_type} (source={report_type.source}, "
                        f"ext_id={report_type.ext_id})\n\n"
                        "Old dimensions:\n"
                        f"{old_text}\n"
                        "New dimensions:\n"
                        f"{new_text}\n",
                    )

                # Set attributes
                for field in ('short_name', 'name'):
                    updated = updated or (getattr(report_type, field) != report_type_data[field])
                    setattr(report_type, field, report_type_data[field])

                if updated:
                    counter['updated'] += 1
                    report_type.save()
                else:
                    counter['same'] += 1

        # Note that we don't want to delete report types automatically
        # Because it could seriously affect the data

        self.stats = dict(counter)
        self.save()
