from core.models import DataSource
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    BooleanField,
    CurrentUserDefault,
    DateTimeField,
    HiddenField,
    JSONField,
    ReadOnlyField,
    SerializerMethodField,
    URLField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import IntegerField, ModelSerializer, Serializer
from sushi.models import CounterReportPlatform, CounterReportType

from .models import Author, Item, Platform, Title, TitleOverlapBatch


class SimplePlatformSerializer(ModelSerializer):
    class Meta:
        model = Platform
        fields = ("pk", "ext_id", "short_name", "name", "provider", "url", "counter_registry_id")


class DataSourceSerializer(ModelSerializer):
    organization = OrganizationSerializer()

    class Meta:
        model = DataSource
        fields = ("short_name", "organization", "type")


class CounterReportPlatformSerializer(ModelSerializer):
    pk = ReadOnlyField(source="counter_report.pk")
    code = ReadOnlyField(source="counter_report.code")
    name = ReadOnlyField(source="counter_report.name")
    counter_version = ReadOnlyField(source="counter_report.counter_version")

    class Meta:
        model = CounterReportPlatform
        fields = ("pk", "code", "name", "counter_version")


class PlatformSerializer(ModelSerializer):
    ext_id = IntegerField(read_only=True)
    source = DataSourceSerializer(read_only=True)
    counter_reports = PrimaryKeyRelatedField(
        queryset=CounterReportType.objects.all(), many=True, read_only=False, write_only=True
    )
    counter_reports_long = CounterReportPlatformSerializer(
        many=True, source="counterreportplatform_set", read_only=True
    )

    class Meta:
        model = Platform
        fields = (
            "pk",
            "ext_id",
            "short_name",
            "name",
            "provider",
            "url",
            "knowledgebase",
            "source",
            "counter_registry_id",
            "sushi_arrival_stats",
            "counter_reports",
            "counter_reports_long",
            "counter_reports_source",
        )


class AllPlatformSerializer(ModelSerializer):
    ext_id = IntegerField(read_only=True)
    source = DataSourceSerializer(read_only=True)
    has_raw_parser = BooleanField(read_only=True)
    counter_reports_long = CounterReportPlatformSerializer(
        many=True, source="counterreportplatform_set", read_only=True
    )

    class Meta:
        model = Platform
        fields = (
            "pk",
            "ext_id",
            "short_name",
            "name",
            "provider",
            "url",
            "knowledgebase",
            "source",
            "has_raw_parser",
            "counter_registry_id",
            "counter_reports_long",
            "counter_reports_source",
        )


class DetailedPlatformSerializer(ModelSerializer):
    title_count = IntegerField(read_only=True)
    interests = JSONField(read_only=True)
    has_data = BooleanField(read_only=True)

    class Meta:
        model = Platform
        fields = (
            "pk",
            "ext_id",
            "short_name",
            "name",
            "provider",
            "url",
            "title_count",
            "interests",
            "has_data",
            "counter_registry_id",
        )


class PlatformSushiCredentialsSerializer(ModelSerializer):
    count = IntegerField(read_only=True, source="sushi_credentials_count")

    class Meta:
        model = Platform
        fields = ("pk", "count")


class TitleSerializer(ModelSerializer):
    pub_type_name = SerializerMethodField()

    class Meta:
        model = Title
        fields = (
            "pk",
            "name",
            "pub_type",
            "isbn",
            "issn",
            "eissn",
            "doi",
            "pub_type_name",
            "proprietary_ids",
        )

    def get_pub_type_name(self, obj: Title):
        return obj.get_pub_type_display()


class TitleCountSerializer(TitleSerializer):
    interests = JSONField(read_only=True)
    platform_count = IntegerField(read_only=True)
    nonzero_platform_count = IntegerField(read_only=True)
    platform_ids = JSONField(read_only=True)
    total_interest = IntegerField(read_only=True)
    yops = JSONField(read_only=True)

    class Meta:
        model = Title
        fields = TitleSerializer.Meta.fields + (
            "interests",
            "platform_count",
            "nonzero_platform_count",
            "platform_ids",
            "total_interest",
            "yops",
        )


class UseCaseSerializer(Serializer):
    url = URLField(required=True)
    organization = IntegerField(required=True)
    platform = IntegerField(required=True)
    counter_version = IntegerField(required=True)
    counter_report = IntegerField(required=True)
    latest = DateTimeField(required=True)
    count = IntegerField(required=True)


class TitleOverlapBatchSerializer(ModelSerializer):
    organization = OrganizationSerializer(read_only=True, required=False)

    class Meta:
        model = TitleOverlapBatch
        fields = (
            "pk",
            "organization",
            "created",
            "last_updated",
            "state",
            "source_file",
            "annotated_file",
            "processing_info",
        )


class TitleOverlapBatchCreateSerializer(TitleOverlapBatchSerializer):
    last_updated_by = HiddenField(default=CurrentUserDefault())
    organization = PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False)

    class Meta(TitleOverlapBatchSerializer.Meta):
        fields = TitleOverlapBatchSerializer.Meta.fields + ("last_updated_by",)

    def validate(self, attrs):
        result = super().validate(attrs)
        user = attrs["last_updated_by"]
        if attrs.get("organization"):
            if not user.accessible_organizations().filter(pk=attrs["organization"].pk).exists():
                raise PermissionDenied("User does not have access to this organization")
        else:
            if (
                not user.is_superuser
                and not user.is_admin_of_master_organization
                and not user.is_user_of_master_organization
            ):
                raise PermissionDenied("User cannot set empty organization")
        return result


class DeleteAllDataPlatformSerializer(Serializer):
    delete_platform = BooleanField(required=False, default=False)
    delete_credentials = BooleanField(required=False, default=False)


class AuthorSerializer(ModelSerializer):
    class Meta:
        model = Author
        fields = ("pk", "name", "isni", "orcid")


class ItemSerializer(ModelSerializer):
    interests = JSONField(read_only=True)
    authors = AuthorSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = (
            "pk",
            "name",
            "pub_type",
            "publication_date",
            "doi",
            "isbn",
            "issn",
            "eissn",
            "uris",
            "proprietary_ids",
            "authors",
            "interests",
        )
