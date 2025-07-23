from urllib.parse import urlsplit

from core.logic.url import normalize_url
from publications.models import Platform as CelusPlatform
from rest_framework.fields import CharField, ReadOnlyField
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    IntegerField,
    JSONField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
    SerializerMethodField,
    URLField,
    UUIDField,
)
from sushi.models import CounterVersionChoices

from .models import Platform, Report, SushiService


class AssignedReportTypeSerializer(ModelSerializer):
    report_type = CharField(source="report_id")
    not_valid_before = ReadOnlyField(default=None)
    not_valid_after = ReadOnlyField(default=None)

    class Meta:
        model = Report
        fields = ("report_type", "not_valid_before", "not_valid_after")


class ProviderDetails(ModelSerializer):
    pk = SerializerMethodField()
    name = SerializerMethodField()
    url = SerializerMethodField()
    extra = ReadOnlyField(default={})
    monthly = ReadOnlyField(default=None)
    yearly = ReadOnlyField(default=None)
    monthly = ReadOnlyField(default=None)
    counter_registry_id = CharField(source="id")  # UUID of SushiService

    class Meta:
        model = SushiService
        fields = ("pk", "name", "url", "extra", "yearly", "monthly", "counter_registry_id")

    def get_pk(self, obj):
        # no external object -> discard the link
        return None

    def get_url(self, obj: SushiService):
        return normalize_url(obj.url).rstrip("/")

    def get_name(self, obj: SushiService):
        return urlsplit(obj.url)[1]


class ProviderSerializer(ModelSerializer):
    provider = ProviderDetails(source="*")
    counter_version = ChoiceField(source="counter_release", choices=CounterVersionChoices.values)
    assigned_report_types = AssignedReportTypeSerializer(source="reports", many=True)

    class Meta:
        model = SushiService
        fields = ("provider", "counter_version", "assigned_report_types")


class KnowledgebaseSerializer(ModelSerializer):
    """From registry Platform to Celus knowledgebase extractor"""

    report_types = ReadOnlyField(default=[])  # non-counter report_types
    platform_filter = ReadOnlyField(default=None)
    notes_url = ReadOnlyField(default=None)
    providers = ProviderSerializer(source="sushi_services", read_only=True, many=True)

    class Meta:
        model = Platform
        fields = ("report_types", "platform_filter", "notes_url", "providers")


class PlatformDiffSerializer(ModelSerializer):
    id = UUIDField()
    url = URLField(source="website")
    short_name = CharField(source="abbrev")
    provider = CharField(source="content_provider_name")
    knowledgebase = JSONField(source="platformextras.knowledgebase")
    notes = CharField(source="platformextras.notes")

    related_platform = IntegerField()
    related_platform_url = URLField()
    related_platform_name = CharField()
    related_platform_provider = CharField()
    related_platform_short_name = CharField()
    related_platform_knowledgebase = JSONField()

    keep_name = BooleanField()
    keep_short_name = BooleanField()
    keep_provider = BooleanField()
    keep_url = BooleanField()
    keep_knowledgebase = BooleanField()

    class Meta:
        model = Platform
        fields = (
            "id",
            "url",
            "name",
            "short_name",
            "provider",
            "knowledgebase",
            "notes",
            "related_platform",
            "related_platform_url",
            "related_platform_name",
            "related_platform_short_name",
            "related_platform_provider",
            "related_platform_knowledgebase",
            "keep_name",
            "keep_short_name",
            "keep_provider",
            "keep_url",
            "keep_knowledgebase",
        )


class ApplyItemSerializer(Serializer):
    id = UUIDField()
    name = BooleanField(default=False)
    short_name = BooleanField(default=False)
    url = BooleanField(default=False)
    provider = BooleanField(default=False)
    sushi_services = BooleanField(default=False)


class ApplySerializer(Serializer):
    updates = ApplyItemSerializer(many=True)


class UpdateNotesSerializer(ModelSerializer):
    notes = CharField(
        source="platformextras.notes", write_only=True, required=True, allow_blank=True
    )

    def update(self, instance, validated_data):
        instance.platformextras.notes = validated_data["platformextras"]["notes"]
        instance.platformextras.save()
        return instance

    class Meta:
        model = Platform
        fields = ("notes",)


class CelusPlatformSerializer(Serializer):
    url = URLField()
    name = CharField()
    provider = CharField()
    short_name = CharField()
    related_platform = IntegerField(source="pk")
    related_platform_url = URLField(source="url")
    related_platform_name = CharField(source="name")
    related_platform_provider = CharField(source="provider")
    related_platform_short_name = CharField(source="short_name")
    related_platform_knowledgebase = JSONField(source="knowledgebase")

    class Meta:
        model = CelusPlatform
        fields = (
            "url",
            "name",
            "provider",
            "short_name",
            "related_platform",
            "related_platform_url",
            "related_platform_name",
            "related_platform_short_name",
            "related_platform_provider",
            "related_platform_knowledgebase",
        )


class LinkSerializer(Serializer):
    platform_id = PrimaryKeyRelatedField(
        queryset=CelusPlatform.objects.filter(counter_registry_id__isnull=True)
    )
