from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from publications.models import Platform


class Organization(MPTTModel):

    ext_id = models.PositiveIntegerField(
        unique=True, help_text='object ID taken from EMRS', null=True, default=None
    )
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    ico = models.PositiveIntegerField(
        help_text='Business registration number', null=True, blank=True
    )
    internal_id = models.CharField(
        max_length=50, unique=True, null=True, help_text='special ID used for internal purposes'
    )
    name = models.CharField(max_length=250)
    short_name = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    fte = models.PositiveIntegerField(
        help_text='Last available FTE number for organization', default=0
    )
    address = JSONField(default=dict)
    source = models.ForeignKey(
        'core.DataSource',
        on_delete=models.CASCADE,
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


class UserOrganization(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    source = models.ForeignKey('core.DataSource', on_delete=models.CASCADE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.organization} / {self.user}'
