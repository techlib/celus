from django.contrib.postgres.fields import JSONField
from django.db import models

from organizations.models import Organization
from publications.models import Platform


class SushiCredentials(models.Model):

    VERSION_CHOICES = (
        (4, 'COUNTER 4'),
        (5, 'COUNTER 5'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    url = models.URLField()
    version = models.PositiveSmallIntegerField(choices=VERSION_CHOICES)
    requestor_id = models.CharField(max_length=128)
    client_id = models.CharField(max_length=128, blank=True)
    http_username = models.CharField(max_length=128, blank=True)
    http_password = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=128, blank=True)
    extra_params = JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = (('organization', 'platform', 'version'),)
        verbose_name_plural = 'Sushi credentials'

    def __str__(self):
        return f'{self.organization} - {self.platform}, {self.get_version_display()}'

