import logging
import typing

from core.models import DataSource
from django.db.models import (
    CASCADE,
    BooleanField,
    Case,
    CharField,
    Exists,
    F,
    IntegerField,
    JSONField,
    Manager,
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
from django_celus_registry import models as proxied_models
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
