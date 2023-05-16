import csv
import logging
from collections import Counter
from enum import Enum, auto
from typing import Optional

import reversion
from django.db.models import Count, Q
from openpyxl import load_workbook
from organizations.models import Organization
from publications.models import Platform
from sushi.logic.export import Col

from ..models import SushiCredentials

logger = logging.getLogger(__name__)


class Perform(Enum):
    UPDATE_NONE = auto()
    UPDATE_NOT_VERIFIED = auto()
    UPDATE_ALL = auto()


def import_sushi_credentials_from_xlsx(
    filename,
    sheet_no: int = 2,
    single_org: Optional[str] = None,
    log_diff: bool = True,
    log_trivial: bool = False,
    update_credentials=Perform.UPDATE_NONE,
    reversion_comment: Optional[str] = None,
) -> dict:
    workbook = load_workbook(filename=filename, read_only=True)
    if sheet_no > len(workbook.worksheets):
        raise ValueError("chosen sheet doesn't exist")
    credentials_sheet = workbook.worksheets[sheet_no - 1]
    if credentials_sheet.max_row > 1:
        headers = [header.value for header in credentials_sheet[1] if header.value]
    else:
        raise ValueError("sheet is empty")
    if Col.PUBLISHER_VENDOR_PLATFORM.value not in headers or Col.CUSTOMER_ID.value not in headers:
        raise ValueError("essential headers are missing")

    EXPECTED_COLS = {
        Col.TITLE,
        Col.PUBLISHER_VENDOR_PLATFORM,
        Col.REQUESTOR_ID,
        Col.CUSTOMER_ID,
        Col.API_KEY,
        Col.PLATFORM_FILTER,
    }
    if single_org:
        if type(single_org) == int or single_org.isdigit():
            single_org = Organization.objects.get(pk=single_org)
        else:
            single_org = Organization.objects.get(Q(name_en=single_org) | Q(short_name=single_org))

    elif Col.ORGANIZATION.value not in headers:
        raise ValueError(
            "provide correct organization reference if importing for a single organization "
            "or add 'organization' column to the sheet if importing for consortium"
        )
    else:
        EXPECTED_COLS.add(Col.ORGANIZATION)

    # checking expected headers
    EXPECTED_COLS = {col.value for col in EXPECTED_COLS}
    missing_cols = EXPECTED_COLS - set(headers)
    if missing_cols:
        logger.warning(
            f"Following columns are missing in the sheet: {', '.join(missing_cols)}. "
            "Make sure you don't need to import data expected to be in these columns.",
        )
    excessive_cols = set(headers) - EXPECTED_COLS
    if excessive_cols:
        logger.warning(
            f"Following columns are not expected in the sheet: {', '.join(excessive_cols)}. "
            "Data in these columns will be ignored.",
        )
    start_row = 2
    end_row = credentials_sheet.max_row
    rows = credentials_sheet.iter_rows(min_row=start_row, max_row=end_row, values_only=True)
    records = [dict(zip(headers, row)) for row in rows]

    return import_sushi_credentials_new(
        records,
        single_org=single_org,
        log_diff=log_diff,
        log_trivial=log_trivial,
        update_credentials=update_credentials,
        reversion_comment=reversion_comment,
    )


def import_sushi_credentials_new(
    records: [dict],
    single_org: Optional[Organization] = None,
    log_diff: bool = True,
    log_trivial: bool = False,
    update_credentials=Perform.UPDATE_NONE,
    reversion_comment: Optional[str] = None,
) -> dict:
    """
    Imports SUSHI credentials from a list of dicts describing the data - new version for xlsx
    :param reversion_comment: comment that will be passed to the reversion version, if None a
         default will be provided
    :param records:
    :return:
    """
    stats = Counter()
    sushi_credentials = SushiCredentials.objects.all()
    db_identical_credentials = set(
        sushi_credentials.values_list('organization_id', 'platform_id', 'counter_version')
        .alias(count=Count('id'))
        .filter(count__gt=1)
    )

    db_credentials = {
        (cr.organization_id, cr.platform_id, cr.counter_version): cr for cr in sushi_credentials
    }
    platform_objects = Platform.objects.all()
    source_id = lambda pl: pl.source.organization_id if pl.source else None  # noqa: E731
    db_platforms = {(pl.name_en.lower(), source_id(pl)): pl for pl in platform_objects}

    organization_objects = Organization.objects.all()
    db_organizations = {org.internal_id: org for org in organization_objects}
    db_organizations.update({org.name_en.lower(): org for org in organization_objects})

    def to_clean_str(value):
        if value is None:
            return value
        if not isinstance(value, str):
            value = str(value)
        return " ".join(value.split())

    def log(message: str, *args, stat_name='error', trivial=False, level=logging.ERROR):
        if log_trivial or not trivial:
            logger.log(level, "row #%03d: " + message, i + 2, *args)
        stats[stat_name] += 1

    for i, record in enumerate(records):
        customer_id = to_clean_str(record.get(Col.CUSTOMER_ID.value))
        if not customer_id:
            log(
                'Customer ID empty - interpretting as empty row',
                stat_name='empty_customer_id',
                trivial=True,
                level=logging.INFO,
            )
            # skip empty lines
            continue
        organization_name = (
            single_org.name_en if single_org else to_clean_str(record.get(Col.ORGANIZATION.value))
        )
        if not organization_name:
            log('Organization name empty')
            continue
        organization = db_organizations.get(organization_name.lower())
        if not organization:
            log('Unknown organization: "%s"', organization_name)
            continue
        platform_name = to_clean_str(record.get(Col.PUBLISHER_VENDOR_PLATFORM.value))
        plat_source_org = db_platforms.get(
            (platform_name.lower(), organization.id)
        )  # type: Platform
        plat_source_other = db_platforms.get((platform_name.lower(), None))
        if plat_source_org and plat_source_other:
            log(
                'name_en of platform "%s" created by organization "%s" '
                'conflicts with name_en of one of global platforms',
                plat_source_org.name_en,
                organization.name_en,
            )
            continue

        if not plat_source_other and not plat_source_org:
            log(
                'Unknown platform "%s" for organization "%s"',
                platform_name,
                organization_name,
            )
            continue
        platform = plat_source_other or plat_source_org
        optional = dict()
        if title := to_clean_str(record.get(Col.TITLE.value)):
            optional['title'] = title

        if platform_filter := to_clean_str(record.get(Col.PLATFORM_FILTER.value)):
            optional['extra_params'] = {'platform': platform_filter}

        if api_key := to_clean_str(record.get(Col.API_KEY.value)):
            optional['api_key'] = api_key

        if requestor_id := to_clean_str(record.get(Col.REQUESTOR_ID.value)):
            optional['requestor_id'] = requestor_id
        providers = []
        if platform.knowledgebase:
            providers = [
                p
                for p in platform.knowledgebase.get('providers', [])
                if p['counter_version'] == 5 and 'provider' in p and 'url' in p['provider']
            ]
        if providers:
            url = providers[0]['provider']['url']
        else:
            log(
                "can't assign url due to missing provider for the platform: '%s'",
                platform.name_en,
            )
            continue
        key = (organization.pk, platform.pk, 5)
        if key in db_credentials:
            if key in db_identical_credentials:
                log(
                    'Credentials for organization "%s" platform "%s" counter 5: '
                    'have more than one corresponding instance in the database.',
                    organization.name_en,
                    platform.name_en,
                    stat_name='duplicates_skipped',
                )
                continue

            to_sync = dict(
                customer_id=customer_id,
                url=url,
                **optional,
            )
            cr = db_credentials[key]
            diff = {}
            for key, value in to_sync.items():
                current_value = getattr(cr, key)
                if value != current_value:
                    setattr(cr, key, value)
                    diff[key] = (current_value, value)
            if diff:

                def create_diff_info(status):
                    info = (
                        f"{status}: credentials (id: {cr.pk}, organization: {organization.name_en},"
                        f" platform: {platform.name_en}):"
                    )
                    for key, (current_value, value) in diff.items():
                        info += f"\n          {key}: '{current_value}' -> '{value}'"
                    return info

                if (update_credentials == Perform.UPDATE_NONE) or (
                    update_credentials == Perform.UPDATE_NOT_VERIFIED and cr.is_verified
                ):
                    if log_diff:
                        log(
                            create_diff_info("diff_skipped"),
                            stat_name='diff_skipped',
                            level=logging.WARNING,
                        )
                    continue
                with reversion.create_revision():
                    cr.save()
                    reversion.set_comment(
                        reversion_comment
                        or 'Updated from logic.data_import.import_sushi_credentials'
                    )
                if log_diff:
                    log(
                        create_diff_info("diff_updated"),
                        stat_name='diff_updated',
                        level=logging.WARNING,
                    )
            else:
                log(
                    "Credentials already exist in the same version",
                    stat_name='skipped',
                    trivial=True,
                    level=logging.INFO,
                )
        else:
            with reversion.create_revision():
                cr = SushiCredentials.objects.create(
                    organization=organization,
                    platform=platform,
                    counter_version=5,
                    customer_id=customer_id,
                    url=url,
                    **optional,
                )
                reversion.set_comment(
                    reversion_comment or 'Created by logic.data_import.import_sushi_credentials'
                )
                db_credentials[key] = cr
            log("Credentials created", stat_name='added', level=logging.WARNING)
    return stats


def import_sushi_credentials_from_csv(
    filename, prefer_knowledgebase_urls: bool = False, reversion_comment: Optional[str] = None
) -> dict:
    if hasattr(filename, 'read'):
        reader = csv.DictReader(filename)
        records = list(reader)  # read all records from the reader
    else:
        with open(filename, 'r') as infile:
            reader = csv.DictReader(infile)
            records = list(reader)  # read all records from the reader
    return import_sushi_credentials_old(
        records,
        prefer_knowledgebase_urls=prefer_knowledgebase_urls,
        reversion_comment=reversion_comment,
    )


def import_sushi_credentials_old(
    records: [dict],
    prefer_knowledgebase_urls: bool = False,
    reversion_comment: Optional[str] = None,
    default_version=5,
) -> dict:
    """
    Imports SUSHI credentials from a list of dicts describing the data
    :param reversion_comment: comment that will be passed to the reversion version, if None a
         default will be provided
    :param prefer_knowledgebase_urls: if True, the urls from the knowledgebase will be used instead
            of the ones from the file
    :param records:
    :return:
    """
    stats = Counter()
    db_credentials = {
        (cr.organization_id, cr.platform_id, cr.counter_version): cr
        for cr in SushiCredentials.objects.all()
    }
    platform_objects = Platform.objects.all()
    source_id = lambda pl: pl.source.organization_id if pl.source else None  # noqa: E731
    platforms = {(pl.short_name.lower(), source_id(pl)): pl for pl in platform_objects}
    platforms.update({(pl.name.lower(), source_id(pl)): pl for pl in platform_objects})
    organization_objects = Organization.objects.all()
    organizations = {org.internal_id: org for org in organization_objects}
    organizations.update({org.short_name.lower(): org for org in organization_objects})
    organizations.update({org.name.lower(): org for org in organization_objects})
    for record in records:
        organization_name = record.get('organization')
        if not organization_name:
            logger.error('Organization name is missing')
            stats['error'] += 1
            continue
        organization = organizations.get(organization_name.strip().lower())
        if not organization:
            logger.error(
                'Unknown organization: "%s" in "%s"',
                record.get('organization'),
                record.get('organization_name'),
            )
            stats['error'] += 1
            continue
        # at first try global platforms
        platform = platforms.get((record.get('platform').strip().lower(), None))  # type: Platform
        if not platform:
            # then platforms specific for the organization
            platform = platforms.get((record.get('platform').strip().lower(), organization.id))
            if not platform:
                logger.error(
                    'Unknown platform: "%s" for organization "%s"',
                    record.get('platform', '').strip(),
                    organization.short_name,
                )
                stats['error'] += 1
                continue
        version = int(record.get('version')) if 'version' in record else default_version
        key = (organization.pk, platform.pk, version)
        extra_attrs = record.get('extra_attrs', {})
        if extra_attrs:
            extra_attrs = parse_params(extra_attrs, version=version)
        optional = {}
        if 'auth' in extra_attrs:
            optional['http_username'], optional['http_password'] = extra_attrs['auth']
            del extra_attrs['auth']
        else:
            optional['http_username'] = ''
            optional['http_password'] = ''
        if 'api_key' in extra_attrs:
            optional['api_key'] = extra_attrs['api_key']
            del extra_attrs['api_key']
        elif 'api_key' in record:
            optional['api_key'] = record['api_key']
        else:
            optional['api_key'] = ''
        if 'title' in record:
            optional['title'] = record['title'].strip()
        url = record.get('URL') or record.get('url')
        if prefer_knowledgebase_urls:
            if platform.knowledgebase:
                providers = [
                    p
                    for p in platform.knowledgebase.get('providers', [])
                    if p['counter_version'] == version
                    and 'provider' in p
                    and 'url' in p['provider']
                ]
                if providers:
                    url = providers[0]['provider']['url']
                    stats['url_knowledgebase'] += 1
                else:
                    stats['url_no_provider'] += 1
            else:
                stats['url_no_knowlegdebase'] += 1

        if key in db_credentials:
            # we update it
            cr = db_credentials[key]
            to_sync = dict(
                customer_id=record.get('customer_id'),
                requestor_id=record.get('requestor_id'),
                url=url,
                extra_params=extra_attrs,
                **optional,
            )
            save = False
            for key, value in to_sync.items():
                if value != getattr(cr, key):
                    setattr(cr, key, value)
                    save = True
            if save:
                with reversion.create_revision():
                    cr.save()
                    reversion.set_comment(
                        reversion_comment
                        or 'Updated from logic.data_import.import_sushi_credentials'
                    )
                stats['synced'] += 1
            else:
                stats['skipped'] += 1
        else:
            with reversion.create_revision():
                cr = SushiCredentials.objects.create(
                    organization=organization,
                    platform=platform,
                    counter_version=version,
                    customer_id=record.get('customer_id'),
                    requestor_id=record.get('requestor_id'),
                    url=url,
                    extra_params=extra_attrs,
                    **optional,
                )
                reversion.set_comment(
                    reversion_comment or 'Created by logic.data_import.import_sushi_credentials'
                )
                db_credentials[key] = cr
            stats['added'] += 1
    return stats


def parse_params(text, version: Optional[int] = None) -> dict:
    out = {}
    text = text.strip()
    for part in text.split(';'):
        if '=' in part:
            name, value = part.split('=')
            name = name.strip()
            value = value.strip()
            if name == 'auth':
                value = tuple(value.split(','))
            out[name] = value
    if text and not out and version == 5:
        # there is some text, but we could not extract anything from it
        # if this is C5, we assume the value is the API key
        out['api_key'] = text
    return out
