import logging
import os
import re
import typing
from collections import Counter
from copy import deepcopy
from enum import Enum
from functools import lru_cache
from pathlib import Path

import magic
from celus_nibbler import PoopStats
from celus_nigiri import CounterRecord
from core.exceptions import ModelUsageError
from core.models import (
    UL_ROBOT,
    USER_LEVEL_CHOICES,
    CreatedUpdatedMixin,
    DataSource,
    SourceFileMixin,
    User,
)
from core.models import where_to_store as core_where_to_store
from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist, ValidationError
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
from hcube.api.models.aggregation import Count as HCount
from hcube.api.models.aggregation import Sum as HSum
from nibbler.logic.dict_reader import get_dict_reader_from_csv
from nibbler.logic.processing import (
    celus_format_poops,
    counter_format_poops,
    get_months_from_nibbler_output,
    get_records_from_nibbler_output,
    is_success,
)
from nibbler.logic.utils import all_nibbler_counter_parsers
from nibbler.models import NibblerOutput, ParserDefinition
from organizations.models import Organization, OrganizationAltName
from publications.models import Item, Platform, Title

import logs

from .exceptions import OrganizationHasToBeSelected, WrongOrganizations, WrongState

logger = logging.getLogger(__name__)


DIMENSION_COUNT = 8


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

    # TODO: switch to just functools.cache, once we do not need support for Python 3.8
    @lru_cache  # noqa B019 - caching a method without an argument, so no memory leak
    def _get_interest_rt(self):
        # we use get_or_create to make sure interest is always present
        # this is mostly for tests, because in production it should be always present
        return self.get_or_create(
            short_name="interest", source__isnull=True, defaults={"name": "Interest"}
        )[0]

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
    default_platform_interest = models.BooleanField(
        default=False,
        help_text="Should this report type be automatically connected to new platforms?",
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
        return list(self.dimensions.all().order_by("reporttypetodimension__position"))

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
                return f"dim{i+1}"
        return None

    @classmethod
    def is_explicit_dimension(cls, dim_name: str) -> bool:
        return bool(re.match(r"dim(\d)", dim_name))

    @property
    def is_interest_rt(self) -> bool:
        return self.short_name == "interest" and self.source is None


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


class ReportInterestMetric(models.Model):
    """
    Links a report type to metric which signifies interest for that report type.
    If it is desired that in the outcome, the metric appears as a different one,
    it may be remapped by using target_metric
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    target_metric = models.ForeignKey(
        Metric,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_report_interest_metrics",
    )
    interest_group = models.ForeignKey(InterestGroup, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("interest_group", "metric", "report_type")

    def __str__(self):
        return f"{self.report_type} - {self.metric} ({self.interest_group})"


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
    materialization_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Internal information about materialized report data in this batch",
    )
    last_clickhoused = models.DateTimeField(
        null=True, help_text="When was the import batch last synced with clickhouse"
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


def where_to_store(instance: "ManualDataUpload", filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime("%Y%m%d-%H%M%S.%f")
    return (
        f"custom/{instance.user_id}/{instance.report_type.short_name}-"
        f"{instance.platform.short_name}_{ts}{ext}"
    )


def validate_mime_type(fileobj):
    detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
    fileobj.seek(0)

    # there is not one type to rule them all - magic is not perfect and we need to consider
    # other possibilities that could be detected - for example the text/x-Algol68 seems
    # to be returned for some CSV files with some version of libmagic
    # (the library magic uses internally)
    allowed_types = [
        "text/csv",
        "text/plain",
        "application/csv",
        "text/x-Algol68",
        "application/json",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",  # xls
        "application/CDFV2",  # xls (sometimes)
        "application/x-dosexec",  # Japanese (SHIFT_JIS) encoding
    ]

    if fileobj.name and fileobj.name.endswith(".xlsx"):
        allowed_types.append("application/octet-stream")

    if detected_type not in allowed_types:
        raise ValidationError(
            _(
                "The uploaded file is not in required file type or is corrupted. "
                "The file type seems to be '{detected_type}'. "
                "Please upload your file in required file type."
            ).format(detected_type=detected_type)
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
        return f'{self.user.username if self.user else ""}: {self.report_type}, {self.platform}'

    def mail_report_format(self):
        report_type = self.report_type or ""

        return f"""\
        User: {self.user.username} ( {self.user.email} )
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
    def crt(self) -> typing.Optional["logs.models.CounterReportType"]:
        try:
            return self.report_type.counterreporttype
        except ObjectDoesNotExist:
            return None

    def histograms_with_stats(
        self,
    ) -> typing.Tuple[typing.Dict[str, Counter], Counter, typing.List[str]]:
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

    def get_nibbler_output(self) -> (NibblerOutput, MduMethod):
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

    def resolve_explicit_dimension(self, dim_name: str) -> Dimension:
        """
        When dimension is called `dimX`, its meaning cannot be resolved without checking which
        report_type is active for this report. This is what we do here.
        """
        if dim_name.startswith("dim"):
            # this is an explicit dimension
            rts = self.used_report_types()
            if len(rts) == 1:
                return rts[0].dimension_by_attr_name(dim_name)
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

    def used_report_types(self) -> [ReportType]:
        rt_filters = [
            f for f in self.report_config.get("filters", []) if f["dimension"] == "report_type"
        ]
        rts = []
        for rt_filter in rt_filters:
            rts += list(ReportType.objects.filter(short_name__in=rt_filter["values"]))
        return rts


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
