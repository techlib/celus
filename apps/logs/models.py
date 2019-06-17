from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.timezone import now

from core.models import USER_LEVEL_CHOICES, UL_ROBOT
from organizations.models import Organization
from publications.models import Platform, Title


class OrganizationPlatform(models.Model):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    sushi_credentials = JSONField(default=list)


class LogType(models.Model):

    short_name = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)
    

class AccessLog(models.Model):

    source = models.ForeignKey(OrganizationPlatform, on_delete=models.CASCADE)
    target = models.ForeignKey(Title, on_delete=models.CASCADE)
    value = models.PositiveIntegerField()
    log_type = models.ForeignKey(LogType, on_delete=models.CASCADE)
    date = models.DateField()
    created = models.DateTimeField(default=now)
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ROBOT,
        help_text='Level of user who created this record - used to determine who can modify it'
    )
