from core.models import User
from core.validators import validate_year
from django.db import models
from django.utils.timezone import now


class Payment(models.Model):

    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    platform = models.ForeignKey('publications.Platform', on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField(validators=[validate_year])
    price = models.PositiveIntegerField(help_text='Price in reference currency')
    # internal stuff
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(default=now)
    last_updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, blank=True)

    class Meta:
        unique_together = (('organization', 'platform', 'year'),)
