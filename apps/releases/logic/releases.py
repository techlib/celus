import logging
import traceback

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


def get_releases_entries():
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


def add_dates_to_releases_from_changelog(releases, changelog):
    rel_to_date = {log['version']: log['date'] for log in changelog}
    for release in releases:
        release['date'] = rel_to_date.get(release['version'], None)
    return releases
