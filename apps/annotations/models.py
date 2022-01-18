from enum import Enum

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from core.models import UL_CONS_STAFF, UL_ORG_ADMIN, USER_LEVEL_CHOICES, User


class Validity(Enum):
    VALID = "valid"
    FUTURE = "future"
    OUTDATED = "outdated"

    def as_query(self):
        today = now().date()
        return {
            self.VALID: (Q(start_date__lte=today) | Q(start_date__isnull=True))
            & (Q(end_date__gte=today) | Q(end_date__isnull=True)),
            self.FUTURE: Q(start_date__gte=today)
            & (Q(end_date__gte=today) | Q(end_date__isnull=True)),
            self.OUTDATED: (Q(start_date__lte=today) | Q(start_date__isnull=True))
            & Q(end_date__lte=today),
        }[self]


class Annotation(models.Model):
    """
    Object represents a message that should be shown to the user under specific conditions,
    such as when visiting a page of specific Platform, etc.
    """

    LEVEL_IMPORTANT = 'important'
    LEVEL_INFO = 'info'

    LEVEL_CHOICES = ((LEVEL_INFO, 'info'), (LEVEL_IMPORTANT, 'important'))

    subject = models.CharField(max_length=200)
    short_message = models.TextField(blank=True)
    message = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    organization = models.ForeignKey(
        'organizations.Organization', null=True, blank=True, on_delete=models.CASCADE
    )
    platform = models.ForeignKey(
        'publications.Platform', on_delete=models.CASCADE, null=True, blank=True
    )
    level = models.CharField(choices=LEVEL_CHOICES, default=LEVEL_INFO, max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, blank=True
    )
    owner_level = models.PositiveSmallIntegerField(
        choices=USER_LEVEL_CHOICES,
        default=UL_ORG_ADMIN,
        help_text='Level of user who created this record - used to determine who can modify it',
    )

    def can_edit(self, user: User):
        if self.organization_id is None:
            owner_level = UL_CONS_STAFF
        else:
            owner_level = user.organization_relationship(self.organization_id)
        if owner_level >= self.owner_level:
            return True
        return False
