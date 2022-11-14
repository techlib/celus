import yaml
from django.conf import settings


def parse_source_of_releases():
    if settings.RELEASES_SOURCEFILE:
        with (settings.BASE_DIR / settings.RELEASES_SOURCEFILE).open() as releases:
            return yaml.safe_load(releases)
    return None
