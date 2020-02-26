from django.conf import settings
from django.db import models
from django.utils.timezone import now


class UserActivity(models.Model):

    ACTION_TYPE_LOGIN = 'LGN'

    ACTION_TYPE_CHOICES = (
        (ACTION_TYPE_LOGIN, 'Login'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=3, choices=ACTION_TYPE_CHOICES)
    timestamp = models.DateTimeField(default=now)

    class Meta:
        verbose_name_plural = 'User activities'
