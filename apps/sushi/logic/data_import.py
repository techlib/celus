import csv
import logging
from collections import Counter
from typing import Optional

import reversion
from organizations.models import Organization
from publications.models import Platform

from ..models import SushiCredentials

logger = logging.getLogger(__name__)


def import_sushi_credentials_from_csv(
    filename, prefer_knowledgebase_urls: bool = False, reversion_comment: Optional[str] = None
) -> dict:
    with open(filename, 'r') as infile:
        reader = csv.DictReader(infile)
        records = list(reader)  # read all records from the reader
    return import_sushi_credentials(
        records,
        prefer_knowledgebase_urls=prefer_knowledgebase_urls,
        reversion_comment=reversion_comment,
    )


def import_sushi_credentials(
    records: [dict],
    prefer_knowledgebase_urls: bool = False,
    reversion_comment: Optional[str] = None,
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
    platforms = {(pl.short_name, source_id(pl)): pl for pl in platform_objects}
    platforms.update({(pl.name, source_id(pl)): pl for pl in platform_objects})
    organization_objects = Organization.objects.all()
    organizations = {org.internal_id: org for org in organization_objects}
    organizations.update({org.short_name: org for org in organization_objects})
    for record in records:
        organization_name = record.get('organization')
        if not organization_name:
            logger.error('Organization name is missing')
            stats['error'] += 1
            continue
        organization = organizations.get(organization_name.strip())
        if not organization:
            logger.error(
                'Unknown organization: "%s" in "%s"',
                record.get('organization'),
                record.get('organization_name'),
            )
            stats['error'] += 1
            continue
        # at first try global platforms
        platform = platforms.get((record.get('platform').strip(), None))  # type: Platform
        if not platform:
            # then platforms specific for the organization
            platform = platforms.get((record.get('platform').strip(), organization.id))
            if not platform:
                logger.error(
                    'Unknown platform: "%s" for organization "%s"',
                    record.get('platform', '').strip(),
                    organization.short_name,
                )
                stats['error'] += 1
                continue
        version = int(record.get('version'))
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
