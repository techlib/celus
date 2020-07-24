import logging
import re

logger = logging.getLogger(__name__)
issn_matcher = re.compile(r'^\d{4}-\d{3}[\dX]$')


class ValidationError(Exception):

    pass


def clean_and_validate_issn(text: str, raise_error=True) -> str:
    clean = ''.join(text.split())  # remove all whitespace
    if issn_matcher.match(clean):
        return clean
    if raise_error:
        raise ValidationError(f'Invalid ISSN: "{text}"')
    logger.warning('Invalid ISSN: "%s"', text)
    return ''


def normalize_isbn(isbn: str) -> str:
    return isbn.replace(' ', '')
