from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel


class Organization(MPTTModel):

    ext_id = models.PositiveIntegerField(unique=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                            related_name='children')
    ico = models.CharField(max_length=20, unique=True)
    internal_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=250)
    short_name = models.CharField(max_length=100)
    url = models.URLField()
    fte = models.PositiveIntegerField(help_text="Last available FTE number for organization")
    address = JSONField(default=dict)


class UserOrganization(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
