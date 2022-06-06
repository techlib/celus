import logging
import re

from isbnlib import is_isbn13, is_isbn10, to_isbn13, canonical

logger = logging.getLogger(__name__)
issn_matcher = re.compile(r'(\d{4})-?(\d{3}[\dXx])')


class ValidationError(Exception):

    pass


def normalize_issn(text: str, raise_error=True) -> str:
    """
    Removes all whitespace and checks if ISSN looks like ISSN. But even if not, it still
    returns the original value, so that we can save at least that.
    """
    clean = ''.join(text.split())  # remove all whitespace
    if m := issn_matcher.search(clean):
        # upper() because 'X' can be also lowercase
        return m.group(1) + '-' + m.group(2).upper()
    if raise_error:
        raise ValidationError(f'Invalid ISSN: "{text}"')
    logger.warning('Invalid ISSN: "%s"', text)
    # only 9 characters - we do not support more
    return clean[:9]


def normalize_isbn(isbn: str) -> str:
    """
    checks if str is valid isbn and returns:
     - isbn13 in canonical form (digits only) if isbn in valid
     - source string with whitespace and dashes removed if isbn is not valid
    """
    if len(isbn) > 20:
        # too long; we need to cut it
        # we split it by whitespace and take the first 20 chars of the first part
        # this is crude, but it is here only to handle complete bullshit from the data, so we do
        # not care much - it just needs to fit into our ISBN model
        isbn = isbn.split()[0][:20]
    isbn = isbn.replace(' ', '').replace('-', '')
    if is_isbn13(isbn):
        return canonical(isbn)
    if is_isbn10(isbn):
        return to_isbn13(isbn)
    return isbn


def normalize_title(title: str) -> str:
    clean = ' '.join(title.split())  # normalize whitespace
    return clean
