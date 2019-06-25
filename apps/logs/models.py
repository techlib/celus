from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import now

from core.models import USER_LEVEL_CHOICES, UL_ROBOT
from organizations.models import Organization
from publications.models import Platform, Title


class OrganizationPlatform(models.Model):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    sushi_credentials = JSONField(default=list)


class ReportType(models.Model):

    """
    Represents type of report, such as 'TR' or 'DR' in Sushi
    """

    short_name = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)
    dimensions = models.ManyToManyField('Dimension', related_name='report_types',
                                        through='ReportTypeToDimension')

    def __str__(self):
        return self.short_name

    @cached_property
    def dimension_short_names(self):
        return [dim.short_name for dim in self.dimensions.all()]

    @cached_property
    def dimensions_sorted(self):
        return list(self.dimensions.all())


class Metric(models.Model):

    """
    Type of metric, such as 'Unique_Item_Requests', etc.
    """

    short_name = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)

    def __str__(self):
        return self.short_name


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

    short_name = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    type = models.PositiveSmallIntegerField(choices=DIMENSION_TYPE_CHOICES)
    desc = models.TextField(blank=True)

    class Meta:
        ordering = ('reporttypetodimension', )

    def __str__(self):
        return '{} ({})'.format(self.short_name, self.get_type_display())


class ReportTypeToDimension(models.Model):

    """
    Intermediate model to facilitate connection between report_type and dimension with
    additional position attribute
    """

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = (('report_type', 'dimension'), )
        ordering = ('position',)

    def __str__(self):
        return '{}-{} #{}'.format(self.report_type, self.dimension, self.position)


class AccessLog(models.Model):

    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE)
    source = models.ForeignKey(OrganizationPlatform, on_delete=models.CASCADE,
                               help_text='Oranization and platform for which this log was created')
    target = models.ForeignKey(Title, on_delete=models.CASCADE,
                               help_text='Title for which this log was created')
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
        help_text='Level of user who created this record - used to determine who can modify it'
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
