import re

issn_matcher = re.compile(r'^\d{4}-\d{3}[\dX]$')


class ValidationError(Exception):

    pass


def clean_and_validate_issn(text: str) -> str:
    clean = ''.join(text.split())  # remove all whitespace
    if issn_matcher.match(clean):
        return clean
    raise ValidationError(f'Invalid ISSN: "{text}"')
