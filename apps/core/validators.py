import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.logic.dates import parse_month

MIN_YEAR = 1900
MAX_YEAR = 3000

ROR_LENGTH = 9
ISNI_LENGTH = 16


def validate_year(value):
    if value < MIN_YEAR or value > MAX_YEAR:
        raise ValidationError(
            _("%(value)s is not in range for valid year (%(minv)d-%(maxv)d)"),
            params={"value": value, "minv": MIN_YEAR, "maxv": MAX_YEAR},
        )


def month_validator(text: str):
    value = parse_month(text)
    if value is None:
        raise ValidationError(f"{text} is not a valid input for month value (YYYY-MM)")


def pk_list_validator(text: str):
    for part in text.split(","):
        if not part.isdigit():
            raise ValidationError(f"{part} must be an integer")


def ror_validator(text: str):
    if not text.isalnum():
        raise ValidationError("is not alphanumerical")
    if not len(text) == ROR_LENGTH:
        raise ValidationError(f"ROR ID length should be {ROR_LENGTH}")


def isni_validator(text: str):
    if not re.match(r"^[0-9]{15}([0-9xX])$", text):
        raise ValidationError("wrong isni format [0-9]{15}[0-9xX]")
