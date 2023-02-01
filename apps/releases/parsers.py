import logging
import re
import traceback

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


def parse_source_of_releases():
    if settings.RELEASES_SOURCEFILE:
        with (settings.BASE_DIR / settings.RELEASES_SOURCEFILE).open(
            'rt', encoding='utf-8'
        ) as releases:
            try:
                return yaml.safe_load(releases)
            except Exception as exc:
                logger.exception(exc)
                from core.tasks import async_mail_admins

                async_mail_admins.delay(
                    'Error parsing releases',
                    f'Error:\n\n {exc}\n\nTraceback:\n\n{traceback.format_exc()}',
                )
    return None


def parse_changelog(content: str):
    list_of_releases = content.split("## [")
    list_of_releases.pop(0)
    releases = []
    for release in list_of_releases:
        rel_parts = release.split("\n\n", 1)
        if m := re.match(
            r"^((?:\d+\.\d+\.\d+)|Unreleased)](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$", rel_parts[0]
        ):
            version = m.group(1)
            date = m.group(2)
        else:
            raise ValueError("Cannot parse release header: " + rel_parts[0])
        rel_dict = {"version": version, "date": date, "markdown": rel_parts[1]}
        releases.append(rel_dict)
    return releases
