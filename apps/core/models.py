from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


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


class User(AbstractUser):

    ext_id = models.PositiveIntegerField(null=True,
                                         help_text='ID used in original source of this user data')

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

    def __str__(self):
        return self.identity
