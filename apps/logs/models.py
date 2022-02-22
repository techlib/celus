from chardet.universaldetector import UniversalDetector
import codecs
import csv
import os
import re
import typing
from copy import deepcopy
from datetime import date
from enum import Enum

import magic
from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.db.models import Index, UniqueConstraint, Q, QuerySet, OuterRef, Exists, Max
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from core.exceptions import ModelUsageError
from core.models import USER_LEVEL_CHOICES, UL_ROBOT, DataSource, CreatedUpdatedMixin
from nigiri.counter5 import CounterRecord
from organizations.models import Organization
from publications.models import Platform, Title


class OrganizationPlatform(models.Model):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    sushi_credentials = models.JSONField(default=list)

    def __str__(self):
        return f'{self.organization} | {self.platform}'


class ReportType(models.Model):

    """
    Represents type of report, such as 'TR' or 'DR' in Sushi
    """

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)
    dimensions = models.ManyToManyField(
        'Dimension', related_name='report_types', through='ReportTypeToDimension'
    )
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    interest_metrics = models.ManyToManyField(
        'Metric', through='ReportInterestMetric', through_fields=('report_type', 'metric')
    )
    superseeded_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='superseeds'
    )
    materialization_spec = models.ForeignKey(
        'ReportMaterializationSpec', null=True, blank=True, on_delete=models.SET_NULL
    )
    default_platform_interest = models.BooleanField(default=False)
    materialization_date = models.DateTimeField(
        default=now,
        help_text="All data materialized before this data will be recomputed - can be used to "
        "force recomputation",
    )
    approx_record_count = models.PositiveBigIntegerField(
        default=0,
        help_text='Automatically filled in by periodic check to have some fast measure of the record count',
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['short_name', 'source'], name='report_type_short_name_source_not_null'
            ),
            UniqueConstraint(
                fields=['short_name'],
                condition=Q(source=None),
                name='report_type_short_name_source_null',
            ),
        ]

    def __str__(self):
        return self.short_name

    @cached_property
    def dimension_short_names(self):
        return [dim.short_name for dim in self.dimensions.all()]

    @cached_property
    def dimensions_sorted(self):
        if self.materialization_spec:
            return self.materialization_spec.base_report_type.dimensions_sorted
        return list(self.dimensions.all().order_by('reporttypetodimension__position'))

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if (
            ReportType.objects.exclude(pk=self.pk)
            .filter(short_name=self.short_name, source__isnull=True)
            .exists()
        ):
            raise ValidationError("Attribute 'short_name' should be unique for each data source")

    @property
    def public(self):
        return self.source is None

    def dimension_by_attr_name(self, attr_name: str) -> 'Dimension':
        """
        Given an attribute name like `dim1` return the appropriate dimension instance
        """
        m = re.match(r'dim(\d)', attr_name)
        if m:
            idx = int(m.group(1)) - 1
            return self.dimensions_sorted[idx] if idx < len(self.dimensions_sorted) else None
        return None

    @classmethod
    def is_explicit_dimension(cls, dim_name: str) -> bool:
        return bool(re.match(r'dim(\d)', dim_name))


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
        limit_choices_to={'materialization_spec__isnull': True},
    )
    keep_metric = models.BooleanField(default=True)
    keep_organization = models.BooleanField(default=True)
    keep_platform = models.BooleanField(default=True)
    keep_target = models.BooleanField(default=True)
    keep_dim1 = models.BooleanField(default=True)
    keep_dim2 = models.BooleanField(default=True)
    keep_dim3 = models.BooleanField(default=True)
    keep_dim4 = models.BooleanField(default=True)
    keep_dim5 = models.BooleanField(default=True)
    keep_dim6 = models.BooleanField(default=True)
    keep_dim7 = models.BooleanField(default=True)
    keep_date = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.base_report_type} {self.description})'

    @property
    def description(self):
        _keep, missing = self.split_attributes()
        return ' -' + ' -'.join(missing)

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
        id_postfix = '_id' if add_id_postfix else ''
        for attr in ('metric', 'organization', 'platform', 'target'):
            if getattr(self, 'keep_' + attr):
                keep.append(attr + id_postfix)
            else:
                remove.append(attr + id_postfix)
        if self.keep_date:
            keep.append('date')
        else:
            remove.append('date')
        for i in range(1, 8):
            if getattr(self, f'keep_dim{i}'):
                keep.append(f'dim{i}')
            else:
                remove.append(f'dim{i}')
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
        default=False, help_text='Important interest groups should be shown preferentially to users'
    )
    position = models.PositiveSmallIntegerField(help_text='Used for sorting')

    class Meta:
        ordering = ('position', 'important')

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
        default=True, help_text='Only active metrics are reported to users'
    )
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ('short_name', 'name')
        constraints = [
            UniqueConstraint(
                fields=['short_name', 'source'], name='metric_short_name_source_not_null'
            ),
            UniqueConstraint(
                fields=['short_name'],
                condition=Q(source=None),
                name='metric_short_name_source_null',
            ),
        ]

    def __str__(self):
        if self.name and self.name != self.short_name:
            return f'{self.short_name} => {self.name}'
        return self.short_name


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
        related_name='source_report_interest_metrics',
    )
    interest_group = models.ForeignKey(
        InterestGroup, null=True, blank=True, on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)


class Dimension(models.Model):

    """
    Represents a specific dimension of multidimensional data
    """

    TYPE_INT = 1
    TYPE_TEXT = 2

    DIMENSION_TYPE_CHOICES = ((TYPE_INT, 'integer'), (TYPE_TEXT, 'text'))

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    type = models.PositiveSmallIntegerField(choices=DIMENSION_TYPE_CHOICES, default=TYPE_TEXT)
    desc = models.TextField(blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ('reporttypetodimension',)
        # the following make name and source unique together even if source is NULL which is not
        # the case when simply using unique_together
        constraints = [
            UniqueConstraint(fields=['short_name', 'source'], name='short_name_source_not_null'),
            UniqueConstraint(
                fields=['short_name'], condition=Q(source=None), name='short_name_source_null'
            ),
        ]

    def __str__(self):
        return '{} ({})'.format(self.short_name, self.get_type_display())

    @property
    def public(self):
        return self.source is None


class ReportTypeToDimension(models.Model):

    """
    Intermediate model to facilitate connection between report_type and dimension with
    additional position attribute
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = (('report_type', 'dimension'),)
        ordering = ('position',)

    def __str__(self):
        return '{}-{} #{}'.format(self.report_type, self.dimension, self.position)


class ImportBatchQuerySet(models.QuerySet):
    def data_matrix(
        self,
        organizations: typing.Optional[typing.Iterable[Organization]] = None,
        platforms: typing.Optional[typing.Iterable[Platform]] = None,
        report_types: typing.Optional[typing.Iterable[ReportType]] = None,
        start_date: typing.Optional[date] = None,
        end_date: typing.Optional[date] = None,
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
                has_logs=Exists(AccessLog.objects.filter(import_batch=OuterRef('pk'))),
                mdu_id=Max('mdu'),  # max is fine here, there can be only one mdu
                attempt_id=Max('sushifetchattempt__pk'),
            )
            .select_related('sushifetchattempt')
            .prefetch_related('mdu')
        )


class ImportBatch(models.Model):

    """
    Represents one batch of imported data. Such data share common source, such as a file
    and the user who created them.
    """

    objects = ImportBatchQuerySet.as_manager()

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    date = models.DateField(null=True)
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text='Level of user who created this record - used to determine who can modify it',
    )
    log = models.TextField(blank=True)
    interest_timestamp = models.DateTimeField(
        null=True, blank=True, help_text='When was interest processed for this batch'
    )
    materialization_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Internal information about materialized report data in this batch',
    )
    last_clickhoused = models.DateTimeField(
        null=True, help_text='When was the import batch last synced with clickhouse'
    )

    class Meta:
        verbose_name_plural = "Import batches"
        indexes = (BrinIndex(fields=('date',)),)

    @cached_property
    def accesslog_count(self):
        return self.accesslog_set.count()


class AccessLogQuerySet(QuerySet):
    def delete(self, i_know_what_i_am_doing=False):
        if not i_know_what_i_am_doing:
            raise ModelUsageError(
                'Deleting individual AccessLogs is not permitted - they may only be deleted in '
                'cascade from ImportBatch.'
            )
        super().delete()


class AccessLog(models.Model):

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE, db_index=False)
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    target = models.ForeignKey(
        Title, on_delete=models.CASCADE, null=True, help_text='Title for which this log was created'
    )
    dim1 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #1')
    dim2 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #2')
    dim3 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #3')
    dim4 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #4')
    dim5 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #5')
    dim6 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #6')
    dim7 = models.IntegerField(null=True, blank=True, help_text='Value in dimension #7')
    value = models.PositiveIntegerField(help_text='The value representing number of accesses')
    date = models.DateField()
    # internal fields
    created = models.DateTimeField(default=now)
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text='Level of user who created this record - used to determine who can modify it',
    )
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE)

    class Meta:
        indexes = (
            BrinIndex(fields=('report_type',)),
            BrinIndex(fields=('platform',)),
            BrinIndex(fields=('organization',)),
            BrinIndex(fields=('date',)),
            Index(fields=('report_type', 'organization')),  # these occur often, so we optimize
            # the following index makes it possible to answer queries about unique report_type
            # for a platform (and potentially organization) using IndexScan only
            # this speeds up the /api/organization/X/platform/Y/report-views/ endpoint by
            # a factor of 10 when organization is given and factor of 2 for all organizations
            # it takes about 5 % of the table size
            Index(fields=('platform', 'organization', 'report_type')),
        )

    objects = AccessLogQuerySet.as_manager()

    def delete(self, using=None, keep_parents=False):
        raise ModelUsageError(
            'Deleting individual AccessLogs is not permitted - they may only be deleted in cascade '
            'from ImportBatch.'
        )


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


def where_to_store(instance: 'ManualDataUpload', filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    return (
        f'custom/{instance.user_id}/{instance.report_type.short_name}-'
        f'{instance.platform.short_name}_{ts}{ext}'
    )


def validate_mime_type(fileobj):
    detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
    fileobj.seek(0)
    # there is not one type to rule them all - magic is not perfect and we need to consider
    # other possibilities that could be detected - for example the text/x-Algol68 seems
    # to be returned for some CSV files with some version of libmagic
    # (the library magic uses internally)
    if detected_type not in (
        'text/csv',
        'text/plain',
        'application/csv',
        'text/x-Algol68',
        'application/json',
    ):
        raise ValidationError(
            _(
                "The uploaded file is not in required file type or is corrupted."
                "The file type seems to be '{detected_type}'."
                "Please upload your file in required file type."
            ).format(detected_type=detected_type)
        )


def check_can_parse(fileobj):
    from logs.logic.custom_import import custom_data_import_precheck

    reader = csv.reader(codecs.iterdecode(fileobj, 'utf-8'))
    first_row = next(reader)
    try:
        second_row = next(reader)
    except StopIteration:
        raise ValidationError(
            _('Only one row in the uploaded file, there is not data to ' 'import')
        )
    fileobj.seek(0)
    problems = custom_data_import_precheck(first_row, [second_row])
    if problems:
        raise ValidationError(
            _('Errors understanding uploaded data: {}').format('; '.join(problems))
        )


class ManualDataUpload(models.Model):

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text='Level of user who created this record - used to determine who can modify it',
    )
    created = models.DateTimeField(auto_now_add=True)
    data_file = models.FileField(upload_to=where_to_store, validators=[validate_mime_type])
    log = models.TextField(blank=True)
    is_processed = models.BooleanField(default=False, help_text='Was the data converted into logs?')
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batches = models.ManyToManyField(
        ImportBatch, through='ManualDataUploadImportBatch', related_name='mdu'
    )
    extra = models.JSONField(
        default=dict, blank=True, help_text='Internal data related to processing of the upload'
    )

    def __str__(self):
        return f'{self.user.username if self.user else ""}: {self.report_type}, {self.platform}'

    def mail_report_format(self, request):
        return f"""\
        User: {self.user.username} ( {self.user.email} )
        Organization: {self.organization}
        Platform: {self.platform}
        ReportType: {self.report_type}
        File: {request.build_absolute_uri(self.data_file.url)}"""

    def delete(self, using=None, keep_parents=False):
        for import_batch in self.import_batches.all():
            import_batch.delete()
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def accesslogs(self):
        return AccessLog.objects.filter(import_batch__in=self.import_batches.all())

    def mark_processed(self):
        if not self.is_processed:
            self.is_processed = True
            self.when_processed = now()
            self.save()

    def detect_file_encoding(self) -> str:
        """
            returns encoding of the file uploaded
            """
        with open(self.data_file.path, "rb") as file:
            detector = UniversalDetector()
            for line in file.readlines():
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
            if detector.result['confidence'] < 0.8:
                return 'utf-8-sig'
            else:
                return detector.result['encoding']

    def to_record_dicts(self) -> [dict]:
        reader = csv.DictReader(codecs.iterdecode(self.data_file.file, self.detect_file_encoding()))
        data = list(reader)
        return data

    def data_to_records(self) -> typing.Generator[CounterRecord, None, None]:
        try:
            crt = self.report_type.counterreporttype
        except ObjectDoesNotExist:
            crt = None
        if not crt:
            # this is really custom data - there is no special counter report type associated
            from logs.logic.custom_import import custom_data_to_records

            data = self.to_record_dicts()
            default_metric, _created = Metric.objects.get_or_create(
                short_name='visits',
                name_en='Visits',
                name_cs='Návštěvy',
                source=self.report_type.source,
            )
            records = custom_data_to_records(
                data,
                extra_dims=self.report_type.dimension_short_names,
                initial_data={'metric': default_metric.pk},
            )
        else:
            reader = crt.get_reader_class(json_format=self.file_is_json())()
            records = reader.file_to_records(os.path.join(settings.MEDIA_ROOT, self.data_file.name))
        return records

    def file_is_json(self) -> bool:
        """
        Returns True if the file seems to be a JSON file.
        """
        char = self.data_file.read(1)
        while char and char.isspace():
            char = self.data_file.read(1)
        self.data_file.seek(0)
        if char in b'[{':
            return True
        return False

    def clashing_batches(self) -> typing.Iterable[ImportBatch]:
        """ Get list of all conflicting batches """
        months = set()
        for record in self.data_to_records():
            months.add(record.start)

        return ImportBatch.objects.filter(
            date__in=months,
            report_type=self.report_type,
            organization=self.organization,
            platform=self.platform,
        )


class ManualDataUploadImportBatch(models.Model):

    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='mdu_link')
    mdu = models.ForeignKey(
        ManualDataUpload, on_delete=models.CASCADE, related_name='import_batch_link'
    )

    class Meta:
        constraints = [UniqueConstraint(fields=('import_batch',), name='one_import_batch_per_mdu')]


class FlexibleReport(models.Model):
    class Level(Enum):
        PRIVATE = 1
        ORGANIZATION = 2
        CONSORTIUM = 3

    name = models.CharField(max_length=120)
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_flexible_reports',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    owner_organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True
    )
    report_config = models.JSONField(
        default=dict, help_text='Serialized configuration of the report', blank=True
    )

    serialization_models = {
        'report_type': {'model': ReportType, 'key': 'short_name'},
        'metric': {'model': Metric, 'key': 'short_name'},
        **{f'dim{i}': {'model': DimensionText, 'key': 'text'} for i in range(1, 8)},
    }

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=(
                    ~(
                        models.Q(owner__isnull=False) & models.Q(owner_organization__isnull=False)
                    )  # not owner and owner_organization
                ),
                name='only-one-owner-field',
            ),
        )

    def __str__(self):
        return self.name

    @property
    def access_level(self):
        if self.owner_organization:
            return self.Level.ORGANIZATION
        elif self.owner:
            return self.Level.PRIVATE
        return self.Level.CONSORTIUM

    @classmethod
    def create_from_slicer(cls, slicer: 'FlexibleDataSlicer', **kwargs):
        return FlexibleReport.objects.create(
            report_config=cls.serialize_slicer_config(slicer.config()), **kwargs
        )

    @classmethod
    def serialize_slicer_config(cls, config: dict):
        """
        Prepares the slicer config for storage. The most important thing is that we need to
        translate primary keys to some more robust identifier in order to allow copying of
        public reports between Celus instances.
        """
        new_config = {
            **config,
            'filters': [cls.serialize_slicer_filter(fltr) for fltr in config['filters']],
            # TODO: turn on after demo
            #'order_by': cls.resolve_order_by(config)
        }
        return new_config

    @classmethod
    def serialize_slicer_filter(cls, fltr: dict):
        model_desc = cls.serialization_models.get(fltr['dimension'])
        if model_desc:
            model_cls = model_desc['model']
            key_attr = model_desc['key']
            fltr['values'] = [
                obj[key_attr]
                for obj in model_cls.objects.filter(pk__in=fltr['values']).values(key_attr)
            ]
        return fltr

    def deserialize_slicer_config(self):
        config = deepcopy(self.report_config)
        for fltr in config.get('filters', []):
            dim_name = fltr['dimension']
            model_desc = self.serialization_models.get(dim_name)
            if model_desc:
                model_cls = model_desc['model']
                key_attr = model_desc['key']
                extra_filters = {}
                if ReportType.is_explicit_dimension(dim_name):
                    # explicit dimensions need an extra query parameter to properly resolve text
                    # back to pk
                    dim = self.resolve_explicit_dimension(dim_name)
                    if dim:
                        extra_filters = {'dimension_id': dim.pk}
                fltr['values'] = list(
                    model_cls.objects.filter(
                        **{f'{key_attr}__in': fltr['values']}, **extra_filters
                    ).values_list('pk', flat=True)
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
        if dim_name.startswith('dim'):
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
        order_by = config.get('order_by')
        if not order_by:
            return []
        ob_parts = order_by.split(',')
        for i, ob in enumerate(ob_parts):
            # group_by and order_by should be of the same length
            if ob.startswith('grp-'):
                groups = config.get('group_by')
                if i < len(groups):
                    group = groups[i]
                    pk = int(ob[4:])
                    ser_model = cls.serialization_models.get(group)
                    if ser_model:
                        obj = ser_model['model'].objects.get(pk=pk)
                        ret.append(getattr(obj, ser_model['key']))
                    else:
                        raise ValueError(f'unsupported order by: {ob}')
                else:
                    raise ValueError(f'unexpected ordering without matching group: {ob}')
            else:
                ret.append(ob)
        return ret

    def used_report_types(self) -> [ReportType]:
        rt_filters = [
            f for f in self.report_config.get('filters', []) if f['dimension'] == 'report_type'
        ]
        rts = []
        for rt_filter in rt_filters:
            rts += list(ReportType.objects.filter(short_name__in=rt_filter['values']))
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
    STATE_CHOICES = (
        (STATE_NO_CHANGE, 'No change'),
        (STATE_SYNC, 'Sync'),
        (STATE_DELETE, 'Delete'),
        (STATE_SYNC_INTEREST, 'Sync interest'),
    )

    # Because we need to refer to deleted import batches, we do not use a foreign key here
    import_batch_id = models.PositiveBigIntegerField(primary_key=True)
    state = models.PositiveSmallIntegerField(choices=STATE_CHOICES, default=STATE_NO_CHANGE)
