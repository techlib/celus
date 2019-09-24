from django.conf import settings
from django.db import models


class Annotation(models.Model):
    """
    Object represents a message that should be shown to the user under specific conditions,
    such as when visiting a page of specific Platform, etc.
    """

    subject = models.CharField(max_length=200)
    short_message = models.TextField(blank=True)
    message = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    organization = models.ForeignKey('organizations.Organization', null=True, blank=True,
                                     on_delete=models.CASCADE)
    platform = models.ForeignKey('publications.Platform', on_delete=models.CASCADE, null=True,
                                 blank=True)
    report_type = models.ForeignKey('logs.ReportType', null=True, on_delete=models.CASCADE,
                                    blank=True)
    title = models.ForeignKey('publications.Title', null=True, on_delete=models.CASCADE,
                              blank=True)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                               blank=True)



