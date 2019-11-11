from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MIN_YEAR = 1900
MAX_YEAR = 3000


def validate_year(value):
    if value < MIN_YEAR or value > MAX_YEAR:
        raise ValidationError(
            _('%(value)s is not in range for valid year (%(minv)d-%(maxv)d)'),
            params={'value': value, 'minv': MIN_YEAR, 'maxv': MAX_YEAR},
        )
