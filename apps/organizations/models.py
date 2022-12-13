from core.models import DataSource
from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import ugettext as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel


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
    raw_data_import_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ('name',)
        unique_together = (('ico', 'level'),)  # duplicated ico can only be between parent and child
        verbose_name = _('Organization')
        constraints = (
            models.UniqueConstraint(
                fields=('short_name',),
                condition=models.Q(source__isnull=True),
                name='organization_unique_global_shortname',
            ),
            models.UniqueConstraint(
                fields=('short_name', 'source'),
                name='organization_unique_short_name_source',
                condition=models.Q(
                    ext_id__isnull=True
                ),  # external organizations might have empty short_name
            ),
        )

    def __str__(self):
        return self.name

    @property
    def is_raw_data_import_enabled(self) -> bool:
        if settings.ENABLE_RAW_DATA_IMPORT == "All":
            return True
        elif settings.ENABLE_RAW_DATA_IMPORT == "PerOrg":
            return self.raw_data_import_enabled
        return False

    def get_or_create_private_source(self):
        def_name = DataSource.create_default_short_name(None, self.name)
        return DataSource.objects.get_or_create(
            organization=self, type=DataSource.TYPE_ORGANIZATION, defaults={'short_name': def_name}
        )[0]


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
