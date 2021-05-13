import codecs
import csv
import os

import magic
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import BrinIndex
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.db.models import Sum, Index
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from core.models import USER_LEVEL_CHOICES, UL_ROBOT, DataSource
from nigiri.counter5 import CounterRecord, Counter5TableReport
from organizations.models import Organization
from publications.models import Platform, Title


class OrganizationPlatform(models.Model):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    sushi_credentials = JSONField(default=list)

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
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    interest_metrics = models.ManyToManyField(
        'Metric', through='ReportInterestMetric', through_fields=('report_type', 'metric')
    )
    superseeded_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='superseeds'
    )
    materialization_spec = models.ForeignKey(
        'ReportMaterializationSpec', null=True, blank=True, on_delete=models.SET_NULL
    )
    materialization_date = models.DateTimeField(
        default=now,
        help_text="All data materialized before this data will be recomputed - can be used to "
        "force recomputation",
    )

    class Meta:
        unique_together = (('short_name', 'source'),)

    def __str__(self):
        return self.short_name

    @cached_property
    def dimension_short_names(self):
        return [dim.short_name for dim in self.dimensions.all()]

    @cached_property
    def dimensions_sorted(self):
        return list(self.dimensions.all())

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
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = (('short_name', 'source'),)
        ordering = ('short_name', 'name')

    def __str__(self):
        return self.name or self.short_name


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

    DIMENSION_TYPE_CHOICES = (
        (TYPE_INT, 'integer'),
        (TYPE_TEXT, 'text'),
    )

    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    type = models.PositiveSmallIntegerField(choices=DIMENSION_TYPE_CHOICES, default=TYPE_TEXT)
    desc = models.TextField(blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ('reporttypetodimension',)
        unique_together = (('short_name', 'source'),)

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


class ImportBatch(models.Model):

    """
    Represents one batch of imported data. Such data share common source, such as a file
    and the user who created them.
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(default=now)
    system_created = models.BooleanField(default=True)
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
    materialization_data = JSONField(
        default=dict,
        blank=True,
        help_text='Internal information about materialized report ' 'data in this batch',
    )

    class Meta:
        verbose_name_plural = "Import batches"

    def clean(self):
        super().clean()
        if not self.system_created and not self.user:
            raise ValidationError('When system_created is False, user must be filled in')

    @cached_property
    def accesslog_count(self):
        return self.accesslog_set.count()


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
    if detected_type not in ('text/csv', 'text/plain', 'application/csv', 'text/x-Algol68'):
        raise ValidationError(
            _(
                "The uploaded file is not a CSV file or is corrupted. "
                "The file type seems to be '{detected_type}'. "
                "Please upload a CSV file."
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
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)
    extra = JSONField(
        default=dict, blank=True, help_text='Internal data related to processing of the upload'
    )

    def __str__(self):
        return f'{self.user.username}: {self.report_type}, {self.platform}'

    def delete(self, using=None, keep_parents=False):
        if self.import_batch:
            self.import_batch.delete()
        super().delete(using=using, keep_parents=keep_parents)

    def mark_processed(self):
        if not self.is_processed:
            self.is_processed = True
            self.when_processed = now()
            self.save()

    def to_record_dicts(self) -> [dict]:
        reader = csv.DictReader(codecs.iterdecode(self.data_file.file, 'utf-8'))
        data = list(reader)
        return data

    def data_to_records(self) -> [CounterRecord]:
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
                initial_data={'platform_name': self.platform.name, 'metric': default_metric.pk},
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
