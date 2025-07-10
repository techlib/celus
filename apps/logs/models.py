import logging
import os
import re
import tempfile
import typing
from collections import Counter
from copy import deepcopy
from datetime import date
from enum import Enum
from functools import cache
from pathlib import Path

from celus_nigiri import CounterRecord
from core.exceptions import ModelUsageError
from core.logic.dates import month_end, month_start
from core.models import (
    UL_ROBOT,
    USER_LEVEL_CHOICES,
    CreatedUpdatedMixin,
    DataSource,
    SourceFileMixin,
    User,
)
from core.models import where_to_store as core_where_to_store
from core.validators import validate_mime_type_based_on_extension as validate_mime_type
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.core.exceptions import (
    FieldDoesNotExist,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models import (
    Count,
    Exists,
    Field,
    Index,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Sum,
    UniqueConstraint,
)
from django.db.models.functions import Coalesce
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext as _
from export.enums import FileFormat
from hcube.api.models.aggregation import Count as HCount
from hcube.api.models.aggregation import Sum as HSum
from nibbler.logic.utils import all_nibbler_counter_parsers
from organizations.models import Organization, OrganizationAltName
from publications.models import Item, Platform, Title

from logs.logic.interest.definitions import DEFAULT_INTEREST_DIMENSIONS, INTEREST_DEFAULT_PROFILES

from .exceptions import OrganizationHasToBeSelected, WrongOrganizations, WrongState

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from nibbler.models import NibblerOutput
    from sushi.models import CounterReportType

    from logs.logic.reporting import FlexibleDataSlicer

DIMENSION_COUNT = 8

if typing.TYPE_CHECKING:
    from sushi.models import CounterReportType


class OrganizationPlatform(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("organization", "platform")

    def __str__(self):
        return f"{self.organization} | {self.platform}"


class ReportTypeQuerySet(models.QuerySet):
    def get_interest_rt(self):
        # we want to cache this, but `as_manager()` uses some dark magic to only
        # copy some methods to the resulting manager and a `cache` is not one of them.
        # But by caching a private method, we can achieve the same effect, because private
        # methods are all copied
        return self._get_interest_rt()

    @cache  # noqa B019 - caching a method without an argument, so no memory leak
    def _get_interest_rt(self):
        # we use get_or_create to make sure interest is always present
        # this is mostly for tests, because in production it should be always present
        rt, created = self.get_or_create(
            short_name="interest", source__isnull=True, defaults={"name": "Interest"}
        )
        if created:
            # if the interest RT was just created, we need to set it up completely
            for i, ddef in enumerate(DEFAULT_INTEREST_DIMENSIONS):
                dim = Dimension.objects.get_or_create(
                    short_name=ddef["short_name"], defaults={"name": ddef["name"]}
                )[0]
                rtd = ReportTypeToDimension.objects.get_or_create(
                    report_type=rt, dimension=dim, position=i
                )[0]
                if not ddef.get("auto"):
                    # auto is computed in the code, so it does not need default value
                    InterestDimensionValueMapping.objects.get_or_create(
                        interest_rtdim=rtd,
                        source_rtdim=None,
                        defaults={"default_value": ddef.get("default_value")},
                    )
        return rt

    def get_interest_rt_no_create(self) -> typing.Optional["ReportType"]:
        return self.filter(short_name="interest", source__isnull=True).first()

    def only_materialized(self):
        return self.filter(materialization_spec__isnull=False)

    def exclude_materialized(self):
        return self.filter(materialization_spec__isnull=True)


class ReportType(models.Model):
    """
    Represents type of report, such as 'TR' or 'DR' in Sushi
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)
    dimensions = models.ManyToManyField(
        "Dimension", related_name="report_types", through="ReportTypeToDimension"
    )
    uses_items = models.BooleanField(default=False)
    uses_titles = models.BooleanField(default=True)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    interest_metrics = models.ManyToManyField(
        "Metric", through="ReportInterestMetric", through_fields=("report_type", "metric")
    )
    superseded_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes"
    )
    materialization_spec = models.OneToOneField(
        "ReportMaterializationSpec", null=True, blank=True, on_delete=models.CASCADE
    )
    materialization_date = models.DateTimeField(
        default=now,
        help_text="All data materialized before this data will be recomputed - can be used to "
        "force recomputation",
    )
    approx_record_count = models.PositiveBigIntegerField(
        default=0,
        help_text="Automatically filled in by periodic check to have some fast measure of the "
        "record count",
    )
    controlled_metrics = models.ManyToManyField(
        "Metric", through="ControlledMetric", related_name="controlled"
    )
    ext_id = models.PositiveIntegerField(unique=True, null=True, default=None, blank=True)

    objects = ReportTypeQuerySet.as_manager()

    class Meta:
        verbose_name = _("Report type")
        constraints = [
            UniqueConstraint(
                fields=["short_name", "source"], name="report_type_short_name_source_not_null"
            ),
            UniqueConstraint(
                fields=["source", "ext_id"], name="report_type_unique_ext_id_per_source"
            ),
            UniqueConstraint(
                fields=["short_name"],
                condition=Q(source=None),
                name="report_type_short_name_source_null",
            ),
        ]

    def __str__(self):
        return self.short_name

    @cached_property
    def dimension_short_names(self) -> typing.List[str]:
        return [dim.short_name for dim in self.dimensions.all()]

    @cached_property
    def dimensions_sorted(self) -> typing.List["Dimension"]:
        if self.materialization_spec:
            return self.materialization_spec.base_report_type.dimensions_sorted
        if (dim_prefetched := getattr(self, "dim_set_prefetched", None)) is not None:
            return [dim.dimension for dim in dim_prefetched]
        return list(self.dimensions.all().order_by("reporttypetodimension__position"))

    @cached_property
    def explicit_dimensions(self) -> typing.List[str]:
        return [f"dim{i + 1}" for i, _dim in enumerate(self.dimensions_sorted)]

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if (
            ReportType.objects.exclude(pk=self.pk)
            .filter(short_name=self.short_name, source__isnull=True)
            .exists()
        ):
            raise ValidationError("Attribute 'short_name' should be unique for each data source")

    @property
    def public(self) -> bool:
        return self.source is None

    def dimension_by_attr_name(self, attr_name: str) -> typing.Optional["Dimension"]:
        """
        Given an attribute name like `dim1` return the appropriate dimension instance
        """
        m = re.match(r"dim(\d)", attr_name)
        if m:
            idx = int(m.group(1)) - 1
            return self.dimensions_sorted[idx] if idx < len(self.dimensions_sorted) else None
        return None

    def dim_name_to_dim_attr(self, dim_short_name: str) -> typing.Optional[str]:
        """
        Given a short_name of a dimension like 'Data_Type' returns the attribute name for that
        dimension like 'dim2'. If dimension is not present, returns None
        """
        for i, dim in enumerate(self.dimensions_sorted):
            if dim.short_name == dim_short_name:
                return f"dim{i + 1}"
        return None

    def dim_to_dim_attr(self, dim: "Dimension") -> typing.Optional[str]:
        """
        Given a dimension, returns the attribute name for that dimension like 'dim2'. If dimension
        is not present, returns None
        """
        for i, d in enumerate(self.dimensions_sorted):
            if d == dim:
                return f"dim{i + 1}"
        return None

    @classmethod
    def is_explicit_dimension(cls, dim_name: str) -> bool:
        return bool(re.match(r"dim(\d)", dim_name))

    @property
    def is_interest_rt(self) -> bool:
        return self.short_name == "interest" and self.source is None

    @cached_property
    def materialized_subreport_types(self) -> typing.List["ReportType"]:
        return list(ReportType.objects.filter(materialization_spec__base_report_type=self))


class ReportMaterializationSpec(models.Model):
    """
    Describes how to slice a report type to get a new one. Used for materializing new report
    types from existing ones.
    """

    name = models.CharField(max_length=100)
    note = models.TextField(blank=True)
    base_report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        limit_choices_to={"materialization_spec__isnull": True},
    )
    keep_metric = models.BooleanField(default=True)
    keep_organization = models.BooleanField(default=True)
    keep_platform = models.BooleanField(default=True)
    keep_target = models.BooleanField(default=True)
    keep_item = models.BooleanField(default=False)
    for i in range(DIMENSION_COUNT):
        locals()[f"keep_dim{i + 1}"] = models.BooleanField(default=True)
    keep_date = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.base_report_type} {self.description})"

    @property
    def description(self):
        _keep, missing = self.split_attributes()
        return " -" + " -".join(missing)

    @cached_property
    def kept_dimensions(self):
        return self.split_attributes()[0]

    @cached_property
    def removed_dimensions(self):
        return self.split_attributes()[1]

    def split_attributes(self, add_id_postfix=False) -> ([], []):
        """
        return two lists of attribute names for the AccessLog models - the ones to keep and the
        ones to remove
        :param add_id_postfix: if given, the _id postfix will be added to the fk based attrs
        :return: (keep, remove)
        """
        keep = []
        remove = []
        id_postfix = "_id" if add_id_postfix else ""
        for attr in ("metric", "organization", "platform", "target", "item"):
            if getattr(self, "keep_" + attr):
                keep.append(attr + id_postfix)
            else:
                remove.append(attr + id_postfix)
        if self.keep_date:
            keep.append("date")
        else:
            remove.append("date")
        for i in range(DIMENSION_COUNT):
            if getattr(self, f"keep_dim{i + 1}"):
                keep.append(f"dim{i + 1}")
            else:
                remove.append(f"dim{i + 1}")
        return keep, remove


class Metric(models.Model):
    """
    Type of metric, such as 'Unique_Item_Requests', etc.
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250, blank=True)
    desc = models.TextField(blank=True)
    active = models.BooleanField(
        default=True, help_text="Only active metrics are reported to users"
    )
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ("short_name", "name")
        verbose_name = _("Metric")
        constraints = [
            UniqueConstraint(
                fields=["short_name", "source"], name="metric_short_name_source_not_null"
            ),
            UniqueConstraint(
                fields=["short_name"],
                condition=Q(source=None),
                name="metric_short_name_source_null",
            ),
        ]

    def __str__(self):
        if self.name and self.name != self.short_name:
            return f"{self.short_name} => {self.name}"
        return self.short_name


class ControlledMetric(models.Model):
    created = models.DateTimeField(default=now)
    updated = models.DateTimeField(auto_now=True)

    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["metric_id", "report_type_id"],
                name="controlled_report_type_and_metric_unique",
            )
        ]


class Dimension(models.Model):
    """
    Represents a specific dimension of multidimensional data
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)

    class Meta:
        ordering = ("reporttypetodimension",)
        constraints = [UniqueConstraint(fields=["short_name"], name="short_name_unique")]

    def __str__(self):
        return self.short_name


class ReportTypeToDimension(models.Model):
    """
    Intermediate model to facilitate connection between report_type and dimension with
    additional position attribute
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = (("report_type", "dimension"),)
        ordering = ("position",)

    def __str__(self):
        return "{}-{} #{}".format(self.report_type, self.dimension, self.position)


class ImportBatchQuerySet(models.QuerySet):
    def data_matrix(
        self,
        organizations: typing.Optional[typing.Iterable[Organization]] = None,
        platforms: typing.Optional[typing.Iterable[Platform]] = None,
        report_types: typing.Optional[typing.Iterable[ReportType]] = None,
    ):
        filter = {}
        if organizations:
            filter["organization__in"] = organizations
        if platforms:
            filter["platform__in"] = platforms
        if report_types:
            filter["report_type__in"] = report_types

        return (
            self.filter(**filter)
            .order_by("date")
            .annotate(
                has_logs=Exists(AccessLog.objects.filter(import_batch=OuterRef("pk"))),
                mdu_id=Max("mdu"),  # max is fine here, there can be only one mdu
                attempt_id=Max("sushifetchattempt__pk"),
            )
            .select_related("sushifetchattempt")
            .prefetch_related("mdu")
        )


class ImportBatch(models.Model):
    """
    Represents one batch of imported data. Such data share common source, such as a file
    and the user who created them.
    """

    PREPROCESSED_DATA_DIR = Path("/tmp/")

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    date = models.DateField()
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text="Level of user who created this record - used to determine who can modify it",
    )
    manual_empty = models.BooleanField(
        default=False, help_text="If the batch was created manually by the user as empty"
    )
    log = models.TextField(blank=True)
    interest_timestamp = models.DateTimeField(
        null=True, blank=True, help_text="When was interest processed for this batch"
    )
    interest_ib = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_interest_ibs",
        help_text="Link to the import batch that includes interest data for this batch - "
        "can be either the same batch or a superseding one",
    )
    materialization_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Internal information about materialized report data in this batch",
    )
    last_clickhoused = models.DateTimeField(
        null=True, help_text="When was the import batch last synced with clickhouse"
    )
    record_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of associated accesslog records without artificial ones "
        "(no interest, no materialized report types)",
    )

    objects = ImportBatchQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Import batches"
        indexes = (BrinIndex(fields=("date",)),)
        ordering = ("id",)
        unique_together = ("report_type", "organization", "platform", "date")

    @cached_property
    def accesslog_count(self):
        return self.accesslog_set.count()


class AccessLogQuerySet(QuerySet):
    def delete(self, i_know_what_i_am_doing=False):
        if not i_know_what_i_am_doing:
            raise ModelUsageError(
                "Deleting individual AccessLogs is not permitted - they may only be deleted in "
                "cascade from ImportBatch."
            )
        return super().delete()


class AccessLog(models.Model):
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE, db_index=False)
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    target = models.ForeignKey(
        Title, on_delete=models.CASCADE, null=True, help_text="Title for which this log was created"
    )
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, null=True, help_text="Item for which this log was created"
    )
    for i in range(DIMENSION_COUNT):
        locals()[f"dim{i + 1}"] = models.IntegerField(
            null=True, blank=True, help_text=f"Value in dimension #{i + 1}"
        )
    value = models.PositiveIntegerField(help_text="The value representing number of accesses")
    date = models.DateField(verbose_name=_("Date"))
    # internal fields
    created = models.DateTimeField(default=now)
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text="Level of user who created this record - used to determine who can modify it",
    )
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE)

    objects = AccessLogQuerySet.as_manager()

    class Meta:
        indexes = (
            BrinIndex(fields=("report_type",)),
            BrinIndex(fields=("platform",)),
            BrinIndex(fields=("organization",)),
            BrinIndex(fields=("date",)),
            Index(fields=("report_type", "organization")),  # these occur often, so we optimize
            # the following index makes it possible to answer queries about unique report_type
            # for a platform (and potentially organization) using IndexScan only
            # this speeds up the /api/organization/X/platform/Y/report-views/ endpoint by
            # a factor of 10 when organization is given and factor of 2 for all organizations
            # it takes about 5 % of the table size
            Index(fields=("platform", "organization", "report_type")),
        )

    def delete(self, using=None, keep_parents=False):
        raise ModelUsageError(
            "Deleting individual AccessLogs is not permitted - they may only be deleted in cascade "
            "from ImportBatch."
        )

    @classmethod
    def get_dimension_field(
        cls, dimension: str
    ) -> typing.Tuple[typing.Optional[Field], typing.Optional[str]]:
        """
        This is used in reporting to get a field matching a string description of the field
        :param dimension:
        :return:
        """
        modifier = ""
        if "__" in dimension:
            dimension, modifier = dimension.split("__", 1)
        try:
            return cls._meta.get_field(dimension), modifier
        except FieldDoesNotExist:
            return None, None

    def compare(self, other: "AccessLog") -> typing.List[str]:
        """
        Compares two access logs and return a list attributes which are different
        """
        attrs = [
            "organization_id",
            "platform_id",
            "report_type_id",
            "target_id",
            "metric_id",
            "value",
            "date",
        ] + [f"dim{i + 1}" for i in range(DIMENSION_COUNT)]
        return [attr for attr in attrs if getattr(self, attr) != getattr(other, attr)]


class DimensionText(models.Model):
    """
    Mapping between text value and integer values for a specific dimension
    """

    id = models.AutoField(primary_key=True)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    text = models.TextField(db_index=True)
    text_local = models.TextField(blank=True)

    class Meta:
        unique_together = (("dimension", "text"),)

    def __str__(self):
        if self.text_local:
            return self.text_local
        return self.text


## interest


class DimensionFilter(models.Model):
    """
    Describes a filter for a dimension.
    """

    dimension = models.ForeignKey(
        "Dimension", on_delete=models.CASCADE, related_name="interest_filters"
    )
    values = models.JSONField(default=list)
    negated = models.BooleanField(default=False)

    def __str__(self):
        sign = "!" if self.negated else ""
        return f"{self.dimension} {sign}{self.values}"


class InterestProfileQuerySet(models.QuerySet):
    def default(self) -> "InterestProfile":
        if out := self.filter(interest_config__organization=None).first():
            return out
        default_def = next(p for p in INTEREST_DEFAULT_PROFILES if p["default"])
        return self.create(
            short_name=default_def["short_name"],
            name=default_def["name"],
            desc=default_def["description"],
        )


class InterestProfile(models.Model):
    """
    Describes a profile for computation of interest.
    Makes it possible to have 'Unique' or 'Total' interest computations for different organizations
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)

    objects = InterestProfileQuerySet.as_manager()

    class Meta:
        ordering = ("short_name", "name")

    def __str__(self):
        return self.name


class InterestGroup(models.Model):
    """
    Describes a measure of interest of users. It is assigned to Metrics which are
    deemed as interest-defining. If more metrics refer to the same InterestGroup
    they are treated as describing the same interest.
    There will for instance be interest in books which would be described by different
    metrics in COUNTER 4 and 5, then there will be the interest in databases, etc.
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    metric = models.OneToOneField(
        Metric,
        on_delete=models.CASCADE,
        related_name="interest_group",
        help_text="Metric which represents this kind of interest",
    )
    important = models.BooleanField(
        default=False, help_text="Important interest groups should be shown preferentially to users"
    )
    position = models.PositiveSmallIntegerField(help_text="Used for sorting")
    implies_availability = models.BooleanField(
        default=True,
        help_text="Does existence of this kind of interest imply that the resource is available? "
        "Should be set to False for denials.",
    )

    class Meta:
        ordering = ("position", "important")

    def __str__(self):
        return self.name


class ReportInterestMetric(models.Model):
    """
    Links a report type to metric which signifies interest for that report type.
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    interest_group = models.ForeignKey(InterestGroup, on_delete=models.CASCADE)
    interest_profile = models.ForeignKey(
        InterestProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="If given, this RIM will be taken into account only for organizations "
        "which have this profile active. If null, will be used regardless of profile.",
    )
    filters = models.ManyToManyField(DimensionFilter, through="ReportInterestMetricFilter")
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("interest_group", "metric", "report_type")

    def __str__(self):
        profile = self.interest_profile.short_name if self.interest_profile else "default"
        return f"{self.report_type} - {self.metric} ({self.interest_group}) profile={profile}"


class ReportInterestMetricFilter(models.Model):
    """
    Describes a filter for a ReportInterestMetric.
    """

    report_interest_metric = models.ForeignKey(ReportInterestMetric, on_delete=models.CASCADE)
    filter = models.ForeignKey(
        DimensionFilter, on_delete=models.CASCADE, related_name="rim_filters"
    )

    class Meta:
        unique_together = ("report_interest_metric", "filter")

    def __str__(self):
        return f"{self.report_interest_metric} - {self.filter}"


class InterestDimensionValueMapping(models.Model):
    """
    Describes a mapping between a dimension value in the interest report and a dimension value
    in the source report type.

    The idea is as follows:

    Get an InterestDimensionValueMapping object for a given interest dimension and source report
    type:
    - if a source report type does not have this record, a record with source_rtdim=None is used
    - if a source report type has this record, that record is used

    Get a value for the interest dimension from the source data:
    - if this is the default record, or the value is not found in the mapping, the default value is
      used
    - otherwise, use the key from mapping where the value is listed in the list of values
    """

    interest_rtdim = models.ForeignKey(
        ReportTypeToDimension, on_delete=models.CASCADE, related_name="interest_value_mappings"
    )
    source_rtdim = models.ForeignKey(
        ReportTypeToDimension,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If null, represents default for this interest dimension; otherwise report type "
        "specific dimension",
    )
    default_value = models.CharField(
        max_length=250, help_text="Used when value is not found in mapping"
    )
    mapping = models.JSONField(
        default=dict,
        help_text="Mapping between interest dimension value and source dimension values: "
        "str->[str]",
    )

    class Meta:
        unique_together = ("interest_rtdim", "source_rtdim")


class InterestConfigQuerySet(models.QuerySet):
    def default(self) -> "InterestConfig":
        if out := self.filter(organization=None).first():
            return out
        dp = InterestProfile.objects.default()
        return self.create(organization=None, interest_profile=dp)


class InterestConfig(CreatedUpdatedMixin, models.Model):
    """
    Describes how interest should be computed for an organization.
    """

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interest_config",
        unique=True,
        help_text="If not set, the config will be the default one",
    )
    interest_profile = models.ForeignKey(
        InterestProfile, on_delete=models.CASCADE, related_name="interest_config"
    )
    interest_filters = models.ManyToManyField(DimensionFilter, through="InterestFilter")

    objects = InterestConfigQuerySet.as_manager()

    class Meta:
        ordering = ("organization",)
        # only one default interest config is allowed
        constraints = [
            UniqueConstraint(
                # we coalesce null to 0, so that we can use it in the unique constraint
                Coalesce("organization", models.Value(0)),
                name="only_one_default_interest_config",
            )
        ]

    def __str__(self):
        return f"{self.organization or 'default'} / {self.interest_profile}"

    def get_interest_filters(self) -> typing.Tuple[typing.Dict[str, list], typing.Dict[str, list]]:
        """
        Returns a tuple of two dictionaries:
        - the first dictionary contains the filters for the interest report type
        - the second dictionary contains the negated (exclude) filters for the interest report type
        """
        interest_rt = ReportType.objects.get_interest_rt()
        filters = {}
        negated_filters = {}
        for filter in self.interest_filters.all():
            interest_dim_attr = interest_rt.dim_to_dim_attr(filter.dimension)
            values = DimensionText.objects.filter(
                dimension=filter.dimension, text__in=filter.values
            ).values_list("pk", flat=True)
            if filter.negated:
                negated_filters[interest_dim_attr + "__in"] = list(values)
            else:
                filters[interest_dim_attr + "__in"] = list(values)
        return filters, negated_filters


class InterestFilter(CreatedUpdatedMixin, models.Model):
    """
    Describes how interest should be filtered when displayed in the UI.
    """

    interest_config = models.ForeignKey(InterestConfig, on_delete=models.CASCADE)
    filter = models.ForeignKey(DimensionFilter, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.interest_config} / {self.filter}"

    def save(self, *args, **kwargs):
        """
        Enforce that one interest config can have only one filter per dimension.
        Enforce that the filter dimension is present in the interest report type.
        """
        interest_rt = ReportType.objects.get_interest_rt()
        # check if the filter dimension is present in the interest report type
        if self.filter.dimension not in interest_rt.dimensions.all():
            raise ValidationError("Filter dimension is not present in the interest report type")

        # check if the filter dimension is present in the interest report type
        qs = InterestFilter.objects.filter(
            interest_config=self.interest_config, filter__dimension=self.filter.dimension
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("One interest config can have only one filter per dimension")

        return super().save(*args, **kwargs)


## end of interest


def where_to_store(instance: "ManualDataUpload", filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime("%Y%m%d-%H%M%S.%f")
    return (
        f"custom/{instance.user_id}/{instance.report_type.short_name}-"
        f"{instance.platform.short_name}_{ts}{ext}"
    )


class MduState(models.TextChoices):
    INITIAL = "initial", _("Initial")
    CONFIRMED = "confirmed", _("Confirmed")
    PREFLIGHT = "preflight", _("Preflight")
    IMPORTING = "importing", _("Importing")
    IMPORTED = "imported", _("Imported")
    PREFAILED = "prefailed", _("Preflight failed")
    FAILED = "failed", _("Import failed")


class MduMethod(models.TextChoices):
    COUNTER = "counter", _("Counter format")
    CELUS = "celus", _("CELUS format")
    RAW = "raw", _("Raw data")


class ManualDataUpload(SourceFileMixin, models.Model):
    PREFLIGHT_FORMAT_VERSION = "5"

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text="Level of user who created this record - used to determine who can modify it",
    )
    created = models.DateTimeField(auto_now_add=True)
    data_file = models.FileField(
        upload_to=core_where_to_store,
        blank=True,
        null=True,
        max_length=256,
        validators=[validate_mime_type],
    )
    log = models.TextField(blank=True)
    error = models.CharField(max_length=50, null=True, blank=True)  # noqa: DJ001
    error_details = models.JSONField(blank=True, null=True)
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batches = models.ManyToManyField(
        ImportBatch, through="ManualDataUploadImportBatch", related_name="mdu"
    )
    preflight = models.JSONField(
        default=dict, blank=True, help_text="Data derived during pre-flight check"
    )
    extra = models.JSONField(
        default=dict, blank=True, help_text="Extra info obtained from parser (e.g. counter headers)"
    )
    state = models.CharField(max_length=20, choices=MduState.choices, default=MduState.INITIAL)
    method = models.CharField(max_length=20, choices=MduMethod.choices, default=MduMethod.COUNTER)

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=~(models.Q(method=MduMethod.CELUS) & models.Q(report_type__isnull=True)),
                name="celus-needs-report-type",
            ),
        )

    def __str__(self):
        return f"{self.user.username if self.user else ''}: {self.report_type}, {self.platform}"

    def mail_report_format(self):
        report_type = self.report_type or ""
        user = f"{self.user.username} ( {self.user.email} )" if self.user else "None"

        return f"""\
        User: {user}
        Organization: {self.organization}
        Platform: {self.platform}
        Method: {self.method}
        ReportType: {report_type}
        File: {self.data_file.url}"""

    def delete(self, using=None, keep_parents=False):
        for import_batch in self.import_batches.all():
            import_batch.delete()
        super().delete(using=using, keep_parents=keep_parents)

    def unprocess(self):
        self.import_batches.all().delete()
        self.state = MduState.INITIAL
        self.error_details = None
        self.error = None
        self.save()

    @property
    def accesslogs(self):
        return AccessLog.objects.filter(import_batch__in=self.import_batches.all())

    def mark_processed(self):
        if not self.is_processed:
            self.state = MduState.IMPORTED
            self.when_processed = now()
            self.save()

    @property
    def is_processed(self):
        return self.state == MduState.IMPORTED

    def to_record_dicts(self) -> [dict]:
        from nibbler.logic.dict_reader import get_dict_reader_from_csv  # noqa - slow import

        # Unwrap django file abstraction
        file = getattr(self.data_file, "file", self.data_file)
        file = getattr(file, "file", file)

        data = list(get_dict_reader_from_csv(file))
        return data

    def prepare_default_metric(self) -> Metric:
        return Metric.objects.get_or_create(
            short_name="visits",
            name_en="Visits",
            name_cs="Návštěvy",
            source=self.report_type.source,
        )[0]

    @property
    def crt(self) -> typing.Optional["CounterReportType"]:
        try:
            return self.report_type.counterreporttype
        except ObjectDoesNotExist:
            return None

    def histograms_with_stats(
        self,
    ) -> typing.Tuple[typing.Dict[str, Counter], Counter, typing.List[str]]:
        from celus_nibbler import PoopStats  # noqa - slow import
        from nibbler.logic.processing import get_months_from_nibbler_output  # noqa - slow import

        stats = PoopStats()
        for record in self.data_to_records():
            stats.process_record(record)

        stats_dict = stats.dict()

        # Fill in empty months from nibbler output when no data are present
        if stats_dict["total"]["count"] == 0:
            nibbler_output, _ = self.get_nibbler_output()
            stats_dict["months"] = {
                m.strftime("%Y-%m"): {"sum": 0, "count": 0}
                for m in get_months_from_nibbler_output(nibbler_output)
            }

        return (stats_dict, Counter(stats_dict["total"]), list(stats_dict["dimensions"].keys()))

    def get_nibbler_output(self) -> typing.Tuple["NibblerOutput", MduMethod]:
        from nibbler.logic.processing import celus_format_poops, counter_format_poops, is_success  # noqa - slow import
        from nibbler.models import ParserDefinition  # noqa - slow import

        if self.method == MduMethod.RAW:
            # Parsing raw data using nibbler (user can't pick report type)

            nibbler_output = ParserDefinition.objects.parse_file(
                self.data_file.path, self.platform.short_name
            )
            if not is_success(nibbler_output):
                # Try to parse the input using standard counter parsers
                nibbler_counter_output = counter_format_poops(
                    os.path.join(settings.MEDIA_ROOT, self.data_file.name), self.platform
                )
                if is_success(nibbler_counter_output):
                    # Method changed RAW -> COUNTER
                    return nibbler_counter_output, MduMethod.COUNTER

            return nibbler_output, self.method

        elif self.method == MduMethod.COUNTER:
            is_json = self.file_is_json()

            nibbler_parser = all_nibbler_counter_parsers(is_json)
            poops = counter_format_poops(
                os.path.join(settings.MEDIA_ROOT, self.data_file.name),
                self.platform,
                nibbler_parser,
            )

            return poops, self.method

        else:
            # Parsing data in "celus format" using nibbler (user can pick report type)
            default_metric = self.prepare_default_metric()
            return (
                celus_format_poops(
                    os.path.join(settings.MEDIA_ROOT, self.data_file.name),
                    default_metric,
                    self.report_type,
                    self.platform,
                ),
                self.method,
            )

    def data_to_records(self) -> typing.Generator[CounterRecord, None, None]:
        self.check_self_checksum()  # check the checksum before using the file

        from nibbler.logic.processing import get_records_from_nibbler_output  # noqa - slow import

        nibbler_output, _ = self.get_nibbler_output()
        yield from get_records_from_nibbler_output(nibbler_output)

    def file_is_json(self) -> bool:
        """
        Returns True if the file seems to be a JSON file.
        """
        char = self.data_file.read(1)
        while char and char.isspace():
            char = self.data_file.read(1)
        self.data_file.seek(0)
        if char in b"[{":
            return True
        return False

    def clashing_batches(self) -> models.QuerySet[ImportBatch]:
        """Get list of all conflicting batches"""

        if self.preflight and "months" in self.preflight:
            # Months can be present in preflight
            months = self.preflight["months"].keys()
        else:
            # Otherwise try to parse data file
            months = {record.start for record in self.data_to_records()}

        # get actual orgnizations
        organizations_with_names = self.organizations_from_data()
        if wrong_organizations := [e[0] for e in organizations_with_names if e[1] is None]:
            raise WrongOrganizations(wrong_organizations)

        organizations = [e[1] for e in organizations_with_names] or [self.organization]

        return ImportBatch.objects.filter(
            date__in=months,
            report_type=self.report_type,
            organization__in=organizations,
            platform=self.platform,
        )

    @cached_property
    def clashing_months(self) -> typing.Optional[typing.List[dict]]:
        """Display which months are in conflict with data to be imported

        return: list of dict
        """
        if (
            not self.preflight
            or "months" not in self.preflight
            or "format_version" not in self.preflight
            or self.preflight["format_version"] != self.PREFLIGHT_FORMAT_VERSION
        ):
            return None

        # get actual orgnizations
        organizations_with_names = self.organizations_from_data()
        if any(e[0] is None for e in organizations_with_names):
            # Unable to resolve organization from data => can determine whether
            # there are clashing data present
            return None
        organizations = [e[1] for e in organizations_with_names] or [self.organization]

        # preflight was performed
        return sorted(
            [
                {"month": e.date, "org_id": e.organization.pk}
                for e in ImportBatch.objects.filter(
                    report_type=self.report_type,
                    platform=self.platform,
                    organization__in=organizations,
                    date__in=list(self.preflight["months"]),
                )
            ],
            key=lambda x: (x["month"], x["org_id"]),
        )

    def preflight_organizations_names(self) -> typing.Optional[typing.List[str]]:
        if self.preflight and self.preflight.get("organizations"):
            return list(self.preflight["organizations"])

    @classmethod
    def organizations_from_data_cls(
        cls, organizations: typing.Optional[typing.List[str]]
    ) -> typing.List[typing.Tuple[str, typing.Optional[Organization]]]:
        if not organizations:
            return []

        def slugified_cmp(first: str, second: str) -> bool:
            return slugify(first, allow_unicode=True) == slugify(second, allow_unicode=True)

        res = []
        # Assuming that there will be a reasonable number of organizations
        org_instances = list(Organization.objects.all())
        alt_names = list(OrganizationAltName.objects.all().select_related("organization"))
        for organization_name in organizations:
            matched_org = None
            for org_instance in org_instances:
                # first try to match on entire name
                if slugified_cmp(organization_name, org_instance.name_en) or slugified_cmp(
                    organization_name, org_instance.name_cs
                ):
                    matched_org = org_instance
                    break

            else:
                # no relevant name, lets try short_name
                for org_instance in org_instances:
                    if slugified_cmp(
                        organization_name, org_instance.short_name_en
                    ) or slugified_cmp(organization_name, org_instance.short_name_cs):
                        matched_org = org_instance
                        break
                else:
                    # Lets try to match by alternative name
                    for alt_org_name in alt_names:
                        if slugified_cmp(alt_org_name.name, organization_name):
                            matched_org = alt_org_name.organization
                            break

            res.append((organization_name, matched_org))

        return res

    def organizations_from_data(
        self,
    ) -> typing.List[typing.Tuple[str, typing.Optional[Organization]]]:
        """
        Return organizations names from data mapped to actual Organization models
        """
        return self.organizations_from_data_cls(self.preflight_organizations_names())

    def wrong_organizations(self) -> typing.Optional[typing.List[str]]:
        """
        Returns wrong organizations names
        """
        if self.preflight:
            return [k for k, v in self.preflight["organizations"].items() if v.get("pk") is None]
        return None

    def check_organization_permissions(self, organization: Organization):
        # Permission are check only when RAW format is used
        if self.method == MduMethod.RAW:
            return organization.is_raw_data_import_enabled
        return True

    def can_import(self, user: User):
        # check state
        if self.state != MduState.PREFLIGHT:
            return False

        # check whether all organizations from data can be
        if self.multiple_organizations and self.wrong_organizations():
            return False

        # check clashing
        if self.clashing_months or self.clashing_months is None:
            return False

        # check metrics
        if "metrics" not in self.preflight:
            # metrics should be contained in preflight
            return False

        # check permissions for multiple_organizations
        if "organizations" in self.preflight:
            if self.multiple_organizations:
                # only master admins are allowed to import multiple organizations
                if not (user.is_superuser or user.is_user_of_master_organization):
                    return False

        controlled_metrics = list(
            self.report_type.controlled_metrics.values_list("short_name", flat=True)
        )
        if controlled_metrics:
            if not set(self.preflight["metrics"]).issubset(controlled_metrics):
                # Extra metrics occured
                return False

        else:
            if not settings.AUTOMATICALLY_CREATE_METRICS:
                all_metrics = Metric.objects.all().values_list("short_name", flat=True)
                # Check whether all metrics exist
                if not set(self.preflight["metrics"]).issubset(all_metrics):
                    return False

        return True

    def plan_preflight(self):
        if self.pk and self.state == MduState.CONFIRMED:
            from .tasks import prepare_preflight

            transaction.on_commit(lambda: prepare_preflight.delay(self.pk))

    def regenerate_preflight(self) -> bool:
        if self.state in (MduState.PREFLIGHT, MduState.PREFAILED):
            self.state = MduState.CONFIRMED
            self.save()
            transaction.on_commit(self.plan_preflight)
            return True
        else:
            return False

    def plan_import(self, user: User):
        if self.can_import(user):
            self.state = MduState.IMPORTING
            self.save()

            from .tasks import import_manual_upload_data

            transaction.on_commit(lambda: import_manual_upload_data.delay(self.pk, user.pk))

        elif self.state == MduState.IMPORTING:
            # skip when already importing data
            pass
        else:
            raise WrongState("MDU can't be imported in current state")

    def related_months_data(self) -> typing.Tuple[typing.Dict[str, int], typing.List[str]]:
        """Returns the number of access logs per month of all existing data which matches this MDU
        and a list of all metrics
        """
        # Get all counts for same (org, platform, report_type)
        filters = {"platform_id": self.platform_id, "report_type_id": self.report_type_id}
        if self.organization_id:
            filters["organization_id"] = self.organization_id
        else:
            if orgs_recs := self.organizations_from_data():
                # If no organization name is resolved return empty
                # list which should cause that no data are returned
                org_ids = [org.pk for _, org in orgs_recs if org]
                filters["organization_id__in"] = org_ids
            else:
                # when the .organization is None, we need to extract the organizations
                # from the data in preflight. In this case, preflight data is missing
                # and we can't continue
                raise OrganizationHasToBeSelected("Organization is missing in preflight data")

        if settings.CLICKHOUSE_QUERY_ACTIVE:
            from .cubes import AccessLogCube, ch_backend

            query = (
                AccessLogCube.query()
                .filter(**filters)
                .group_by("date")
                .aggregate(count=HCount(), sum=HSum("value"))
                .order_by("date")
            )
            counts = {
                e.date.strftime("%Y-%m-%d"): {"count": e.count, "sum": e.sum}
                for e in ch_backend.get_records(query)
            }
            # Get metrics
            metric_query = AccessLogCube.query().filter(**filters).group_by("metric_id")
            metric_ids = [e.metric_id for e in ch_backend.get_records(metric_query)]
        else:
            count_qs = (
                AccessLog.objects.filter(**filters)
                .values("date")
                .annotate(count=Coalesce(Count("pk"), 0), sum=Coalesce(Sum("value"), 0))
                .values("date", "count", "sum")
            )
            counts = {
                e["date"].strftime("%Y-%m-%d"): {"count": e["count"], "sum": e["sum"]}
                for e in count_qs
            }
            # Get metrics
            metric_ids = AccessLog.objects.filter(**filters).values_list("metric_id").distinct()

        metrics = [e.short_name for e in Metric.objects.filter(pk__in=metric_ids).order_by("pk")]
        return counts, metrics

    @property
    def multiple_organizations(self) -> typing.Optional[bool]:
        if not self.preflight or "organizations" not in self.preflight:
            # preflight not calculated or older version of preflight
            return None

        return self.preflight["organizations"] is not None


class ManualDataUploadImportBatch(models.Model):
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="mdu_link")
    mdu = models.ForeignKey(
        ManualDataUpload, on_delete=models.CASCADE, related_name="import_batch_link"
    )

    class Meta:
        constraints = [UniqueConstraint(fields=("import_batch",), name="one_import_batch_per_mdu")]
        ordering = ("mdu_id", "import_batch_id")


class FlexibleReport(models.Model):
    """
    Represents a stored report from the reporting module.
    """

    class Level(Enum):
        PRIVATE = 1
        ORGANIZATION = 2
        CONSORTIUM = 3

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    created = models.DateTimeField(default=now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_flexible_reports",
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="last_updated_flexible_reports",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    owner_organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True
    )
    report_config = models.JSONField(
        default=dict, help_text="Serialized configuration of the report", blank=True
    )

    serialization_models = {
        "report_type": {"model": ReportType, "key": "short_name"},
        "metric": {"model": Metric, "key": "short_name"},
        **{f"dim{i + 1}": {"model": DimensionText, "key": "text"} for i in range(DIMENSION_COUNT)},
    }

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=(
                    ~(
                        models.Q(owner__isnull=False) & models.Q(owner_organization__isnull=False)
                    )  # not owner and owner_organization
                ),
                name="only-one-owner-field",
            ),
        )

    def __str__(self):
        return self.name

    @property
    def access_level(self):
        if self.owner_organization_id:
            return self.Level.ORGANIZATION
        elif self.owner_id:
            return self.Level.PRIVATE
        return self.Level.CONSORTIUM

    @classmethod
    def create_from_slicer(cls, slicer: "FlexibleDataSlicer", **kwargs):  # noqa: F821
        return FlexibleReport.objects.create(
            report_config=cls.serialize_slicer_config(slicer.config()), **kwargs
        )

    @classmethod
    def serialize_slicer_config(cls, config: dict):
        """
        Prepares the slicer config for storage. The most important thing is that we need to
        translate primary keys to some more robust identifier in order to allow copying of
        public reports between CELUS instances.
        """
        new_config = {
            **config,
            "filters": [cls.serialize_slicer_filter(fltr) for fltr in config["filters"]],
            # TODO: turn on after demo
            # 'order_by': cls.resolve_order_by(config)
        }
        return new_config

    @classmethod
    def serialize_slicer_filter(cls, fltr: dict):
        model_desc = cls.serialization_models.get(fltr["dimension"])
        if model_desc:
            model_cls = model_desc["model"]
            key_attr = model_desc["key"]
            fltr["values"] = [
                obj[key_attr]
                for obj in model_cls.objects.filter(pk__in=fltr["values"]).values(key_attr)
            ]
        return fltr

    def deserialize_slicer_config(self):
        config = deepcopy(self.report_config)
        for fltr in config.get("filters", []):
            dim_name = fltr["dimension"]
            model_desc = self.serialization_models.get(dim_name)
            if model_desc:
                model_cls = model_desc["model"]
                key_attr = model_desc["key"]
                extra_filters = {}
                if ReportType.is_explicit_dimension(dim_name):
                    # explicit dimensions need an extra query parameter to properly resolve text
                    # back to pk
                    dim = self.resolve_explicit_dimension(dim_name)
                    if dim:
                        extra_filters = {"dimension_id": dim.pk}
                fltr["values"] = list(
                    model_cls.objects.filter(
                        **{f"{key_attr}__in": fltr["values"]}, **extra_filters
                    ).values_list("pk", flat=True)
                )
        return config

    @property
    def config(self):
        return self.deserialize_slicer_config()

    def resolve_explicit_dimension(self, dim_name: str) -> typing.Optional[Dimension]:
        """
        When dimension is called `dimX`, its meaning cannot be resolved without checking which
        report_type is active for this report. This is what we do here.
        """
        if dim_name.startswith("dim"):
            # this is an explicit dimension
            if rts := self.used_report_types():
                # the dimension should be common to all report types
                # but we want to ensure that
                dims = {rt.dimension_by_attr_name(dim_name) for rt in rts}
                if len(dims) > 1:
                    from logs.logic.reporting.slicer import SlicerConfigError, SlicerConfigErrorCode

                    raise SlicerConfigError(
                        code=SlicerConfigErrorCode.E113,
                        message="Dimension is not common to all used report types",
                    )
                return dims.pop()
        return None

    @classmethod
    def resolve_order_by(cls, config):
        """
        Order by may be something like `grp-10` or `grp-20,2020`. We need to map it similarly as
        filters, etc.
        :return:
        """
        ret = []
        order_by = config.get("order_by")
        if not order_by:
            return []
        ob_parts = order_by.split(",")
        for i, ob in enumerate(ob_parts):
            # group_by and order_by should be of the same length
            if ob.startswith("grp-"):
                groups = config.get("group_by")
                if i < len(groups):
                    group = groups[i]
                    pk = int(ob[4:])
                    ser_model = cls.serialization_models.get(group)
                    if ser_model:
                        obj = ser_model["model"].objects.get(pk=pk)
                        ret.append(getattr(obj, ser_model["key"]))
                    else:
                        raise ValueError(f"unsupported order by: {ob}")
                else:
                    raise ValueError(f"unexpected ordering without matching group: {ob}")
            else:
                ret.append(ob)
        return ret

    def used_report_types(self) -> typing.List[ReportType]:
        rt_filters = [
            f for f in self.report_config.get("filters", []) if f["dimension"] == "report_type"
        ]
        rts = []
        for rt_filter in rt_filters:
            rts += list(ReportType.objects.filter(short_name__in=rt_filter["values"]))
        return rts

    def users_with_view_access(self) -> QuerySet[User]:
        """
        Returns a queryset of users who have view access to this report
        """
        if self.owner:
            return User.objects.filter(pk=self.owner.pk) | User.objects.filter_consortium_admins()
        elif self.owner_organization:
            return self.owner_organization.users.all() | User.objects.filter_consortium_admins()
        return User.objects.all()  # consortium reports are visible to all users

    def users_with_edit_access(self) -> QuerySet[User]:
        """
        Returns a queryset of users who have edit access to this report
        """
        if self.owner:
            return User.objects.filter(pk=self.owner.pk) | User.objects.filter_consortium_admins()
        elif self.owner_organization:
            return self.owner_organization.admins(include_superusers=True)
        # consortium reports can be edited only by consortium admins
        return User.objects.filter_consortium_admins()


class FrequencyChoices(models.TextChoices):
    MONTHLY = "M", "Monthly"
    QUARTERLY = "Q", "Quarterly"
    HALF_YEARLY = "H", "Half-yearly"
    YEARLY = "Y", "Yearly"

    @classmethod
    def to_timedelta(cls, frequency: str) -> relativedelta:
        if frequency == cls.MONTHLY:
            return relativedelta(months=1)
        elif frequency == cls.QUARTERLY:
            return relativedelta(months=3)
        elif frequency == cls.HALF_YEARLY:
            return relativedelta(months=6)
        elif frequency == cls.YEARLY:
            return relativedelta(years=1)
        else:
            raise ValueError(f"Unknown frequency: {frequency}")


class FlexibleReportUserEmail(CreatedUpdatedMixin, models.Model):
    """
    Stores configuration of user preference for receiving periodic exports from a flexible report.

    This model can function in two modes:
    - as a standard model saved into the database and used for periodic exports
    - as a one-time model for a one-time export. In that case, it is not saved into the database
    """

    flexible_report = models.ForeignKey(FlexibleReport, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="flexible_report_emails"
    )
    file_format = models.CharField(
        max_length=16, choices=FileFormat.choices, default=FileFormat.XLSX
    )
    frequency = models.CharField(
        max_length=1, choices=FrequencyChoices.choices, default=FrequencyChoices.MONTHLY
    )
    fiscal_period = models.BooleanField(
        default=False, help_text="If True, the frequency is interpreted relative to the fiscal year"
    )
    number_of_periods = models.PositiveSmallIntegerField(default=1)
    last_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.flexible_report.name} - {self.user.email} "
            f"({self.number_of_periods}x{self.frequency})"
        )

    def save(self, *args, **kwargs):
        self._check_access()
        self._check_number_of_periods()
        super().save(*args, **kwargs)

    @property
    def first_month(self) -> int:
        """
        First month of the period.
        """
        if self.fiscal_period:
            # fiscal year start is stored as month in js format (0-11)
            return self.user.extra_data.get("fiscal_year_start_month", 0) + 1
        return 1

    @property
    def last_period_end(self) -> date:
        """
        Last period end is the end of the period closest to current date.
        """
        return self.period_end(now().date())

    @property
    def next_send(self) -> date:
        """
        The next time this mailing should be sent.

        Note: this is a property rather than a stored value because it depends on
        several other values (frequency, fiscal_period and user fiscal year start)
        and updating it in the database after each relevant change would be a pain
        """
        out = self.plan_next_send()
        if self.last_sent and out <= self.last_sent.date():
            # if the mail was already sent today (this is a feature of the computation)
            # use tomorrow as the reference date
            out = self.plan_next_send(ref_date=self.last_sent.date() + relativedelta(days=1))
        return out

    def period_end(self, ref_date: date) -> date:
        """
        Returns the end of the period closest to the reference date.
        """
        end_of_last_whole_month = month_end(ref_date - relativedelta(months=1))
        period_delta = FrequencyChoices.to_timedelta(self.frequency)
        # last finished period end date
        if self.frequency == FrequencyChoices.MONTHLY:
            return end_of_last_whole_month
        elif self.frequency in (
            FrequencyChoices.QUARTERLY,
            FrequencyChoices.HALF_YEARLY,
            FrequencyChoices.YEARLY,
        ):
            month_diff = end_of_last_whole_month.month - self.first_month + 1
            shift = month_diff % (period_delta.months + 12 * period_delta.years)
            return month_end(end_of_last_whole_month - relativedelta(months=shift))
        else:
            raise ValueError(f"Unknown frequency: {self.frequency}")

    def plan_next_send(self, ref_date: typing.Optional[date] = None) -> date:
        """
        Next send is one month after the end of the period closest to current date.
        For example, if it is 2025-04-20:
          - monthly report should be sent on 2025-04-30
          - quarterly report should be sent on 2025-07-31
          - half-yearly report should be sent on 2025-07-31
          - yearly report should be sent on 2026-01-31
        """
        ref_date = ref_date or now().date()
        # period_end is the end of month; we add one month
        out = month_end(self.period_end(ref_date) + relativedelta(months=1))
        # if out is before the reference date, we need to add one more period
        if out < ref_date:
            out += FrequencyChoices.to_timedelta(self.frequency)
        # we use month_end to protect against potential surprises from dateutil
        return month_end(out)

    def _check_access(self):
        if self.flexible_report.owner_id and self.flexible_report.owner_id != self.user_id:
            raise PermissionDenied("You are not allowed to create a mailing for this report")
        if (
            self.flexible_report.owner_organization_id
            and not self.user.accessible_organizations()
            .filter(pk=self.flexible_report.owner_organization_id)
            .exists()
        ):
            raise PermissionDenied("You are not allowed to create a mailing for this report")

    def has_access(self) -> bool:
        """
        Check if the user has access to the report.
        """
        try:
            self._check_access()
        except PermissionDenied:
            return False
        return True

    def _check_number_of_periods(self):
        if self.flexible_report.report_config.get("trend_mode") and self.number_of_periods % 2 != 0:
            raise ValidationError("Trend mode requires an even number of periods")

    def _date_filter_start(self) -> date:
        """
        Returns the start date of the date filter.
        """
        return month_start(
            self.last_period_end  # month end
            - FrequencyChoices.to_timedelta(self.frequency) * self.number_of_periods  # months back
            + relativedelta(days=15)  # 15 days to the future to ensure new month
        )

    def _create_date_filter_simple(self) -> dict:
        """
        Create a date filter based on the settings in this model. Used in non-trend mode.
        """
        return {
            "dimension": "date",
            "start": str(self._date_filter_start()),
            "end": str(self.last_period_end),
        }

    def _create_date_filter_trend(self) -> typing.Tuple[dict, dict]:
        """
        Create two date filters based on the settings in this model. Used in trend mode.
        """
        # split the period into two halves
        half_period = FrequencyChoices.to_timedelta(self.frequency) * (self.number_of_periods // 2)
        base_start = self._date_filter_start()
        base_end = base_start + half_period - relativedelta(days=1)
        compared_start = base_start + half_period
        compared_end = self.last_period_end
        return (
            {"dimension": "date", "start": str(base_start), "end": str(base_end)},
            {"dimension": "date", "start": str(compared_start), "end": str(compared_end)},
        )

    def adjust_dates(self, config: dict) -> dict:
        """
        Adjust the dates in the config to match the settings in this model
        """
        if self.flexible_report.report_config.get("trend_mode"):
            # in trend mode, we need to split the periods into two halves and
            # create two different date filters
            base_filter, compared_filter = self._create_date_filter_trend()
            config["base_subset_filters"] = [base_filter]
            config["compared_subset_filters"] = [compared_filter]
        else:
            date_filter = self._create_date_filter_simple()
            # if date filter is already present, replace it, otherwise add it
            for i, fltr in enumerate(config["filters"]):
                if fltr["dimension"] == "date":
                    config["filters"][i] = date_filter
                    break
            else:
                config["filters"].append(date_filter)
        return config

    def prepare_export(self, outfile: typing.BinaryIO):
        from logs.logic.reporting.export import format_to_exporter
        from logs.logic.reporting.helpers import user_visible_tags
        from logs.logic.reporting.slicer import FlexibleDataSlicer

        config = self.flexible_report.deserialize_slicer_config()
        config = self.adjust_dates(config)
        slicer = FlexibleDataSlicer.create_from_config(config)
        slicer.tag_filter = user_visible_tags(self.user, selected_tag_class=slicer.tag_class)
        slicer.add_extra_organization_filter(self.user.accessible_organizations())
        export_cls = format_to_exporter[self.file_format]
        exporter = export_cls(
            slicer,
            report_name=self.flexible_report.name,
            report_owner=self.user,
            include_tags=True,
            include_row_totals=config.get("row_totals", True),
            include_col_totals=config.get("col_totals", True),
        )
        return exporter.stream_data_to_sink(outfile)

    def send_email(self):
        try:
            self._check_access()
        except PermissionDenied:
            # this should not happen, because the mailing object should not be created
            # in the first place if the user does not have access
            # and it should be removed from the database if the user loses access
            #
            # but in case it happens, we want to log the fact that the user does not have access
            from core.tasks import async_mail_admins

            logger.warning(
                f"User {self.user.email} does not have access to report #{self.flexible_report_id}"
            )
            async_mail_admins.delay(
                f"User {self.user.email} does not have access to report #{self.flexible_report_id}",
                "Sending report was attempted but failed due to permission issues. This should not "
                "happen and it indicates a bug.",
            )
            raise
        # prepare the export
        ext = FileFormat.file_extension(self.file_format)
        email = EmailMessage(
            subject=f'Report "{self.flexible_report.name}"',
            body=f"Please find attached the report {self.flexible_report.name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.user.email],
        )
        with tempfile.NamedTemporaryFile(delete=False) as outfile:
            self.prepare_export(outfile)
            outfile.seek(0)
            email.attach(
                filename=f"{self.flexible_report.name}.{ext}",
                content=outfile.read(),
                mimetype=FileFormat.content_type(self.file_format),
            )
            email.send()
        self.last_sent = now()
        if self.pk:
            # only save if the object already exists
            self.save()


class ImportBatchSyncLog(CreatedUpdatedMixin, models.Model):
    """
    Used to register adding, change or removal of an import batch. It serves as a 'journal'
    for synchronization with Clickhouse, so that we can really make sure the data are in sync.
    """

    STATE_NO_CHANGE = 0
    STATE_SYNC = 1
    STATE_DELETE = 2
    STATE_SYNC_INTEREST = 3
    STATE_RESYNC = 4
    STATE_CHOICES = (
        (STATE_NO_CHANGE, "No change"),
        (STATE_SYNC, "Sync"),
        (STATE_DELETE, "Delete"),
        (STATE_SYNC_INTEREST, "Sync interest"),
        (STATE_RESYNC, "Resync"),
    )

    # Because we need to refer to deleted import batches, we do not use a foreign key here
    import_batch_id = models.PositiveBigIntegerField(primary_key=True)
    state = models.PositiveSmallIntegerField(choices=STATE_CHOICES, default=STATE_NO_CHANGE)


class LastAction(CreatedUpdatedMixin, models.Model):
    """
    Stores information about when an action was last made, so that it can be used in caching
    and other similar functions
    """

    action = models.CharField(max_length=64, unique=True, db_index=True)
    # `last_updated` is part of the CreatedUpdatedMixin

    def is_newer(self, ref_action: str) -> bool:
        """
        Return True if `self` is newer than `ref_action` or `ref_action` does not exist,
        False otherwise.
        """
        return not LastAction.objects.filter(
            action=ref_action, last_updated__gte=self.last_updated
        ).exists()

    @classmethod
    def should_run(cls, action: str, trigger_action: str) -> bool:
        """
        If `trigger_action` is newer than `action`, then `action` should run,
        otherwise it shouldn't.
        If `trigger_action` does not exist, then `action` should only run if it does not exist,
        otherwise it should not run.

        The use-case is like this:

        should_run('update_interest', 'interest_definition_has_changed')

        if 'update_interest' is older than 'interest_definition_has_changed', it should run
        if it is newer, it should not run
        if 'interest_definition_has_changed' does not exist, then 'update_interest' is always newer
        and shouldn't run, but only if it does exist at all - if 'update_interest' does not exist,
        then it should run.
        """
        try:
            trigger = LastAction.objects.get(action=trigger_action)
        except LastAction.DoesNotExist:
            return not LastAction.objects.filter(action=action).exists()
        return trigger.is_newer(action)

    @classmethod
    def update_action(cls, action: str):
        """
        Convenience method to update an action by name
        :param action:
        :return:
        """
        action, created = LastAction.objects.get_or_create(action=action)
        if not created:
            action.update()

    def update(self):
        self.save()
