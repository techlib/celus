from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint, Q
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from publications.models import Platform


class Organization(MPTTModel):

    ext_id = models.PositiveIntegerField(
        unique=True, help_text='object ID taken from EMRS', null=True, default=None, blank=True,
    )
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    ico = models.PositiveIntegerField(
        help_text='Business registration number', null=True, blank=True
    )
    internal_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text='special ID used for internal purposes',
    )
    name = models.CharField(max_length=250)
    short_name = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    fte = models.PositiveIntegerField(
        help_text='Last available FTE number for organization', default=0
    )
    address = models.JSONField(default=dict, blank=True)
    source = models.ForeignKey(
        'core.DataSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defined_organizations',
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through='UserOrganization', related_name='organizations'
    )
    platforms = models.ManyToManyField('publications.Platform', through='logs.OrganizationPlatform')
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        unique_together = (('ico', 'level'),)  # duplicated ico can only be between parent and child

    def __str__(self):
        return self.name


class OrganizationAltName(models.Model):

    """
    Represents an alternative name for an organization. It is mostly useful for data import when
    trying to match organization with an ID in imported document
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    source = models.ForeignKey('core.DataSource', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        # the following make name and source unique together even if source is NULL which is not
        # the case when simply using unique_together
        # The idea here is that you can only have one name mapped to one Organization,
        # on the other hand, if different organizations create their own alt-names using
        # their organization source, it should be allowed because we will take this into account
        # then importing data.
        constraints = [
            UniqueConstraint(fields=['name', 'source'], name='name_source_not_null'),
            UniqueConstraint(fields=['name'], condition=Q(source=None), name='name_source_null'),
        ]

    def validate_unique(self, exclude=None):
        return super().validate_unique(exclude)

    def __str__(self):
        return self.name


class UserOrganization(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    source = models.ForeignKey('core.DataSource', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.organization} / {self.user}'
