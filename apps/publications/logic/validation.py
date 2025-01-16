import logging
import re

from isbnlib import NotValidISBNError, canonical, is_isbn10, is_isbn13, mask, to_isbn13

logger = logging.getLogger(__name__)
# hyphen, en dash, em dash, minus, fullwidth hyphen
issn_matcher = re.compile(r"(\d{4})[-–—−\uFF0D]?(\d{3}[\dXx])")
issn_number_matcher = re.compile(r"^\d{0,7}[\dXx]$")

AUTHOR_ID_LEN = 16
AUTHOR_NAME_LEN = 250


def normalize_issn(text: str) -> str:
    """
    Removes all whitespace and checks if ISSN looks like ISSN. But even if not, it still
    returns the original value, so that we can save at least that.
    """
    clean = "".join(text.split())  # remove all whitespace
    if m := issn_matcher.search(clean):
        # upper() because 'X' can be also lowercase
        return m.group(1) + "-" + m.group(2).upper()
    # sometimes the leading zeros are missing, so we add them
    if issn_number_matcher.match(clean):
        clean = (8 - len(clean)) * "0" + clean
        return clean[:4] + "-" + clean[4:].upper()
    if clean:
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
    isbn = isbn.replace(" ", "").replace("-", "")
    if is_isbn13(isbn):
        return canonical(isbn)
    if is_isbn10(isbn):
        return to_isbn13(isbn)
    return isbn


def normalize_title(title: str) -> str:
    clean = " ".join(title.split())  # normalize whitespace
    return clean


def normalize_author_id(value: str) -> str:
    if not value:
        return ""
    value = value.replace("-", "")
    # Zeroes are going to be filled
    value = value.lstrip("0")

    if len(value) > AUTHOR_ID_LEN:
        # Invalid identifier => don't use it
        logger.warning("Wrong author ID '%s'", value)
        return ""

    # fill in zeros
    return value.zfill(AUTHOR_ID_LEN)


def normalize_author_name(value: str) -> str:
    return value.strip()[:AUTHOR_NAME_LEN].strip()  # strip potential whitespace after truncation


def format_isbn_for_counter(isbn: str) -> str:
    """
    If the value is a valid ISBN, we hyphenate (mask) it to be compatible with CoP requirements.
    If it is not, we leave it as it is to at least preserve the original value.
    If it is any empty value, we return an empty string.
    """
    if not isbn:
        return ""
    try:
        return mask(isbn)
    except NotValidISBNError:
        return isbn
