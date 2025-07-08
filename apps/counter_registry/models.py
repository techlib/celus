import logging
import typing

from core.models import DataSource, User
from dateutil.relativedelta import relativedelta
from django.db.models import (
    CASCADE,
    BooleanField,
    Case,
    CharField,
    DateTimeField,
    Exists,
    F,
    IntegerField,
    JSONField,
    Manager,
    Max,
    Model,
    OneToOneField,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    TextField,
    Value,
    When,
)
from django.db.transaction import atomic
from django.template.loader import render_to_string
from django.utils.timezone import now
from django_celus_registry import models as proxied_models
from events.models import Event, EventCategory, EventImportance
from publications import models as publications_models
from sushi import models as sushi_models

logger = logging.getLogger(__name__)


class PlatformQueryset(QuerySet):
    def sync_knowledgebase(self):
        from .serializers import KnowledgebaseSerializer

        changes = []
        for platform in Platform.objects.all():
            kb = KnowledgebaseSerializer(platform).data
            extra, created = PlatformExtras.objects.get_or_create(
                platform=platform, defaults={"knowledgebase": kb}
            )
            if not created:
                extra.knowledgebase = kb
                changes.append(extra)
        if changes:
            PlatformExtras.objects.bulk_update(changes, ["knowledgebase"])
        return changes


class PlatformManager(Manager):
    def get_queryset(self):
        related_platforms = publications_models.Platform.objects.filter(
            counter_registry_id=OuterRef("id")
        )
        return (
            super()
            .get_queryset()
            .annotate(
                linked=Exists(
                    publications_models.Platform.objects.filter(counter_registry_id=OuterRef("id"))
                ),
                related_platform=Subquery(
                    related_platforms.values_list("pk", flat=True)[:1], output_field=IntegerField()
                ),
                related_platform_knowledgebase=Subquery(
                    related_platforms.values_list("knowledgebase", flat=True)[:1],
                    output_field=JSONField(),
                ),
                related_platform_short_name=Subquery(
                    related_platforms.values_list("short_name", flat=True)[:1],
                    output_field=CharField(),
                ),
                related_platform_name=Subquery(
                    related_platforms.values_list("name_en", flat=True)[:1],
                    output_field=CharField(),
                ),
                related_platform_provider=Subquery(
                    related_platforms.values_list("provider_en", flat=True)[:1],
                    output_field=CharField(),
                ),
                related_platform_url=Subquery(
                    related_platforms.values_list("url", flat=True)[:1], output_field=CharField()
                ),
                keep_knowledgebase=Case(
                    When(
                        platformextras__knowledgebase=F("related_platform_knowledgebase"),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                keep_name=Case(
                    When(Q(name="") | Q(name=F("related_platform_name")), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                keep_short_name=Case(
                    When(
                        Q(abbrev="") | Q(abbrev=F("related_platform_short_name")), then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                keep_provider=Case(
                    When(
                        Q(content_provider_name="")
                        | Q(content_provider_name=F("related_platform_provider")),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
                keep_url=Case(
                    When(Q(website="") | Q(website=F("related_platform_url")), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .prefetch_related(Prefetch("reports", queryset=Report.objects.all()))
            .prefetch_related(Prefetch("sushi_services", queryset=SushiService.objects.all()))
            .select_related("platformextras")
        )


class Platform(proxied_models.Platform):
    objects = PlatformManager.from_queryset(PlatformQueryset)()

    class Meta:
        proxy = True

    def apply_related_platform(
        self,
        name: bool = False,
        short_name: bool = False,
        provider: bool = False,
        url: bool = False,
        sushi_services: bool = False,
    ) -> typing.Tuple[bool, "Platform"]:
        # Get registry source
        source, _ = DataSource.objects.get_or_create(
            short_name="counter_registry",
            defaults={
                "type": DataSource.TYPE_KNOWLEDGEBASE,
                "url": "https://registry.countermetrics.org/api/v1/",
                "token": "",
            },
        )
        try:
            celus_platform = publications_models.Platform.objects.get(counter_registry_id=self.id)
            if name:
                # Update english version only
                celus_platform.name_en = self.name

            if short_name and self.abbrev:
                # abbrev can be empty
                # in this case the most reasonable thing to do is to skip it
                # setting an empty short_name would break the short_name constraint
                celus_platform.short_name = self.abbrev

            if provider and self.content_provider_name:
                # provider can be empty
                # in this case it is smarter to keep the original value
                # as provider in celus is not allowed to be blank
                celus_platform.provider_en = self.content_provider_name

            if url:
                celus_platform.url = self.website

            if sushi_services:
                celus_platform.knowledgebase = self.platformextras.knowledgebase

            celus_platform.source = source

            return False, celus_platform

        except publications_models.Platform.DoesNotExist:
            # If platform doens't exists make new
            return True, publications_models.Platform(
                name_en=self.name,
                short_name=self.abbrev or self.name[:100],
                provider_en=self.content_provider_name,
                url=self.website or "https://example.com",
                knowledgebase=self.platformextras.knowledgebase,
                counter_registry_id=self.id,
                source=source,
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Platform.objects.filter(pk=self.pk).sync_knowledgebase()


class SushiService(proxied_models.SushiService):
    class Meta:
        proxy = True
        ordering = ("counter_release",)

    @property
    def uuid_str(self):
        return str(self.pk)

    @property
    def reports(self):
        return [e for e in self.platform.reports.all() if e.counter_release == self.counter_release]

    @property
    def report_codes(self):
        return sorted(
            e.report_id
            for e in self.platform.reports.all()
            if e.counter_release == self.counter_release
        )


class ReportManager(Manager):
    def get_queryset(self):
        # Only report which have their counter part in sushi
        return (
            super()
            .get_queryset()
            .filter(
                Exists(
                    sushi_models.CounterReportType.objects.filter(
                        code=OuterRef("report_id"), counter_version=OuterRef("counter_release")
                    )
                )
            )
        )


class Report(proxied_models.Report):
    objects = ReportManager()

    class Meta:
        proxy = True
        ordering = ("counter_release", "report_id")


class PlatformExtras(Model):
    platform = OneToOneField(Platform, on_delete=CASCADE)
    notes = TextField(blank=True)
    knowledgebase = JSONField()


class NotificationQuerySet(QuerySet):
    @atomic
    def sync_events(self):
        # Create events for the notification
        events = []
        existing_ids = NotificationEvent.objects.values_list("notification_id", flat=True)
        notification_ids = []
        platform_map = {
            e.counter_registry_id: e.pk
            for e in publications_models.Platform.objects.filter(counter_registry_id__isnull=False)
        }
        for notification in (
            proxied_models.Notification.objects.exclude(pk__in=existing_ids)
            .select_related("sushi_service")
            .order_by("published_date")
        ):
            notification_ids.append(notification.id)
            # TODO format notification message
            reports = ", ".join(
                [f"{e['report_id']} (R{e['counter_release']})" for e in notification.reports]
            )
            message = render_to_string(
                "counter_registry/event.md", {"notification": notification, "reports": reports}
            )
            importance = (
                EventImportance.HIGH if notification.type == "DATA EDIT" else EventImportance.NORMAL
            )
            # prepare event
            events.append(
                Event(
                    created=notification.published_date,
                    title=notification.subject,
                    description=message.strip(),
                    platform_id=notification.sushi_service
                    and platform_map.get(notification.sushi_service.platform_id),
                    category=EventCategory.PLATFORM_INFO,
                    importance=importance,
                    expiration_date=(notification.published_date + relativedelta(years=1)),
                )
            )

        if not events:
            return

        # create notification to event link
        created_events = Event.objects.bulk_create(events)
        new_notification_events = []
        for notification_id, event in zip(notification_ids, created_events):
            new_notification_events.append(
                NotificationEvent(notification_id=notification_id, event_id=event.id)
            )
        NotificationEvent.objects.bulk_create(new_notification_events)

    @atomic
    def assign_to_users(self):
        users_and_since = []
        profile_ids = []
        # We are using this to show only events which are not that old
        default_since = now() - relativedelta(years=1)
        for user in User.objects.all():
            # make sure that every user has a profile
            profile, _ = CounterRegistryProfile.objects.get_or_create(user=user)

            # collect the users and their last event
            if profile.events_from_counter_registry:
                profile_ids.append(profile.pk)
                users_and_since.append((user, profile.last_registry_event_date or default_since))

        # iterate through published notifications
        for ne in self.filter(notification__published_date__isnull=False):
            users = [
                user for user, since in users_and_since if since < ne.notification.published_date
            ]
            ne.event.assign_to_users(users)

        # update profiles
        if max_date := self.aggregate(max_date=Max("notification__published_date"))["max_date"]:
            CounterRegistryProfile.objects.filter(pk__in=profile_ids).update(
                last_registry_event_date=max_date
            )


class NotificationManager(Manager):
    def get_queryset(self):
        related_platforms = publications_models.Platform.objects.filter(
            counter_registry_id=OuterRef("notification__sushi_service__platform_id")
        )
        return (
            super()
            .get_queryset()
            .annotate(
                related_platform=Subquery(
                    related_platforms.values_list("pk", flat=True)[:1], output_field=IntegerField()
                )
            )
        )


class CounterRegistryProfile(Model):
    user = OneToOneField(User, on_delete=CASCADE, unique=True)
    events_from_counter_registry = BooleanField(default=True)
    last_registry_event_date = DateTimeField(null=True, blank=True)


class NotificationEvent(Model):
    notification = OneToOneField(proxied_models.Notification, on_delete=CASCADE, unique=True)
    event = OneToOneField(Event, on_delete=CASCADE, unique=True)

    objects = NotificationManager.from_queryset(NotificationQuerySet)()

    def __str__(self):
        return f"NotificationEvent {self.notification_id} - {self.event_id}"
