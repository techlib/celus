from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.apps import apps

#Organization = apps.get_model(app_label='organizations', model_name='Organization')

UL_NORMAL = 100
UL_ROBOT = 200
UL_ORG_ADMIN = 300
UL_CONS_STAFF = 400
UL_CONS_ADMIN = 1000

USER_LEVEL_CHOICES = (
    (UL_NORMAL, _('Normal user')),
    (UL_ROBOT, _('Robot')),
    (UL_ORG_ADMIN, _('Organization admin')),
    (UL_CONS_STAFF, _('Consortium staff')),
    (UL_CONS_ADMIN, _('Consortium admin')),
)


class DataSource(models.Model):

    """
    Represents a source of data, such as identities, organizations, etc.
    Its main purpose is to be able to distinguish where did different pieces of data come
    from and not to mix user created and ERMS provided data.
    """

    TYPE_API = 1
    TYPE_ORGANIZATION = 2
    TYPE_CHOICES = (
        (TYPE_API, 'API'),
        (TYPE_ORGANIZATION, 'Organization'),
    )

    short_name = models.SlugField()
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    url = models.URLField(blank=True)
    organization = models.OneToOneField('organizations.Organization', on_delete=models.CASCADE,
                                        null=True, blank=True, related_name='private_data_source',
                                        help_text='Used to define data sources private to an '
                                                  'organization')


class User(AbstractUser):

    ext_id = models.PositiveIntegerField(null=True,
                                         help_text='ID used in original source of this user data')
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self) -> str:
        return self.get_usable_name()

    def get_usable_name(self) -> str:
        if self.first_name or self.last_name:
            return "{0} {1}".format(self.first_name, self.last_name)
        return self.email


class Identity(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    identity = models.CharField(max_length=100, unique=True, db_index=True,
                                help_text='External identifier of the person, usually email')
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.identity



