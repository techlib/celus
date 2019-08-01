import csv
from collections import Counter

from organizations.models import SushiCredentials, Organization
from publications.models import Platform


def import_sushi_credentials_from_csv(filename) -> dict:
    with open(filename, 'r') as infile:
        reader = csv.DictReader(infile)
        records = list(reader)  # read all records from the reader
    return import_sushi_credentials(records)


def import_sushi_credentials(records: [dict]) -> dict:
    """
    Imports SUSHI credentials from a list of dicts describing the data
    :param records:
    :return:
    """
    stats = Counter()
    db_credentials = {(cr.organization_id, cr.platform_id, cr.version): cr
                      for cr in SushiCredentials.objects.all()}
    platforms = {pl.short_name: pl for pl in Platform.objects.all()}
    organizations = {org.internal_id: org for org in Organization.objects.all()}
    for record in records:
        organization = organizations.get(record.get('organization'))
        platform = platforms.get(record.get('platform'))
        version = int(record.get('version'))
        key = (organization.pk, platform.pk, version)
        extra_attrs = record.get('extra_attrs', {})
        if extra_attrs:
            extra_attrs = parse_params(extra_attrs)
        optional = {}
        if "auth" in extra_attrs:
            optional['http_username'], optional['http_password'] = extra_attrs['auth']
            del extra_attrs['auth']
        if key in db_credentials:
            # we update it
            pass
        else:
            cr = SushiCredentials.objects.create(
                organization=organization,
                platform=platform,
                version=version,
                client_id=record.get('client_id'),
                requestor_id=record.get('requestor_id'),
                url=record.get('URL'),
                extra_params=extra_attrs,
                **optional,
            )
            db_credentials[key] = cr
            stats['added'] += 1
    return stats


def parse_params(text) -> dict:
    out = {}
    for part in text.split(';'):
        if '=' in part:
            name, value = part.split('=')
            name = name.strip()
            value = value.strip()
            if name == 'auth':
                value = tuple(value.split(','))
            out[name] = value
    return out
