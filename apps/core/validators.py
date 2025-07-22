import re
from pathlib import Path

import magic
from django.conf import settings
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


def _detect_mime_type(fileobj):
    pos = fileobj.tell()
    detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
    fileobj.seek(pos)
    return detected_type


def validate_mime_type_based_on_extension(fileobj):
    mime_type = _detect_mime_type(fileobj)
    if not fileobj.name:
        raise ValidationError("Unable to detect file name")
    ext = Path(fileobj.name).suffix.lstrip(".").lower()
    if mime_types := settings.ALLOWED_MIME_TYPES.get(ext):
        if mime_type not in mime_types:
            raise ValidationError(
                _(
                    "The uploaded file '{filename}' doesn't seem to have the right format "
                    "or is corrupted. "
                    "The file type seems to be '{detected_type}'. "
                    "Please upload your file in right format."
                ).format(detected_type=mime_type, filename=fileobj.name)
            )
    else:
        raise ValidationError(
            _("Files with '.{ext}' extension are not supported. ").format(ext=ext)
        )


def validate_mime_type_csv(fileobj):
    mime_type = _detect_mime_type(fileobj)
    if mime_type not in settings.ALLOWED_MIME_TYPES["csv"]:
        raise ValidationError(
            _(
                "The uploaded file does not seem to be a CSV file. "
                "The file type seems to be '{detected_type}'. "
                "Please upload a CSV file."
            ).format(detected_type=mime_type)
        )
