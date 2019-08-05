import logging
from collections import Counter

from organizations.models import Organization
from publications.models import Title, Platform
from ..models import ReportType, Metric, DimensionText, OrganizationPlatform, AccessLog
from nigiri.counter5 import CounterRecord


logger = logging.getLogger(__name__)


def get_or_create_with_map(model, mapping, attr_name, attr_value, other_attrs=None):
    if attr_value not in mapping:
        data = {attr_name: attr_value}
        if other_attrs:
            data.update(other_attrs)
        obj = model.objects.create(**data)
        mapping[attr_value] = obj
        return obj
    else:
        return mapping[attr_value]


class TitleManager(object):

    data_type_to_pubtype = {
        'journal': Title.PUB_TYPE_JOURNAL,
        'book': Title.PUB_TYPE_BOOK,
        'database': Title.PUB_TYPE_DATABASE,
        'other': Title.PUB_TYPE_OTHER,
        'report': Title.PUB_TYPE_REPORT,
        'newspaper or newsletter': Title.PUB_TYPE_NEWSPAPER,
    }

    def __init__(self):
        self.key_to_title_id_and_pub_type = {(t.name, t.isbn, t.issn, t.eissn, t.doi):
                                             (t.pk, t.pub_type)
                                             for t in Title.objects.all()}

    @classmethod
    def decode_pub_type(cls, pub_type: str) -> str:
        if not pub_type:
            return Title.PUB_TYPE_UNKNOWN
        if pub_type in Title.PUB_TYPE_MAP:
            return pub_type
        elif pub_type.lower() == 'journal':
            return Title.PUB_TYPE_JOURNAL
        elif pub_type.lower() == 'book':
            return Title.PUB_TYPE_BOOK
        return Title.PUB_TYPE_UNKNOWN

    def get_or_create(self, name, pub_type, isbn, issn, eissn, doi) -> int:
        if not name:
            logger.error('Record is missing or has empty title, skipping: '
                         'ISBN: %s, ISSN: %s, eISSN: %s, DOI: %s', isbn, issn, eissn, doi)
            return
        pub_type = self.decode_pub_type(pub_type)
        key = (name, isbn, issn, eissn, doi)
        if key in self.key_to_title_id_and_pub_type:
            title_pk, db_pub_type = self.key_to_title_id_and_pub_type[key]
            # check if we need to improve the pub_type from UNKNOWN to something better
            if db_pub_type == Title.PUB_TYPE_UNKNOWN and pub_type != Title.PUB_TYPE_UNKNOWN:
                logger.info('Upgrading publication type from unknown to "%s"', pub_type)
                Title.objects.filter(pk=title_pk).update(pub_type=pub_type)
            return title_pk
        title = Title.objects.create(name=name, pub_type=pub_type, isbn=isbn, issn=issn,
                                     eissn=eissn, doi=doi)
        self.key_to_title_id_and_pub_type[key] = (title.pk, pub_type)
        return title.pk

    def get_or_create_from_counter_record(self, record: CounterRecord) -> int:
        title = record.title
        isbn = None
        issn = None
        eissn = None
        doi = None
        for key, value in record.title_ids.items():
            if key == 'DOI':
                doi = value
            elif key == 'Online_ISSN':
                eissn = value
            elif key == 'Print_ISSN':
                issn = value
            elif key == 'ISBN':
                isbn = value
        pub_type = 'B' if isbn else 'J' if issn or eissn else None
        if not pub_type:
            if isbn is None and issn is not None:
                pub_type = 'J'
            elif isbn is not None and issn is None:
                pub_type = 'B'
        if not pub_type:
            # try based on data
            if 'Data_Type' in record.dimension_data:
                data_type = record.dimension_data['Data_Type'].lower()
                if data_type in self.data_type_to_pubtype:
                    pub_type = self.data_type_to_pubtype[data_type]
                elif 'news' in data_type:
                    pub_type = Title.PUB_TYPE_NEWSPAPER
                else:
                    logger.warning('Unrecognized Data_Type for publication type recognition: %s',
                                   data_type)
        # convert None values for the following attrs to empty strings
        isbn = '' if isbn is None else isbn
        issn = '' if issn is None else issn
        eissn = '' if eissn is None else eissn
        doi = '' if doi is None else doi
        return self.get_or_create(title, pub_type, isbn, issn, eissn, doi)


def import_counter_records(report_type: ReportType, organization: Organization, platform: Platform,
                           records: [CounterRecord]) -> Counter:
    stats = Counter()
    # prepare all remaps
    metrics = {metric.short_name: metric for metric in Metric.objects.all()}
    text_to_int_remaps = {}
    for dim_text in DimensionText.objects.all():
        if dim_text.dimension_id not in text_to_int_remaps:
            text_to_int_remaps[dim_text.dimension_id] = {}
        text_to_int_remaps[dim_text.dimension_id][dim_text.text] = dim_text
    tm = TitleManager()
    #
    dimensions = report_type.dimensions_sorted
    for record in records:  # type: CounterRecord
        # attributes that define the identity of the log
        title_id = tm.get_or_create_from_counter_record(record)
        if title_id is None:
            # the title could not be found or created (probably missing required field like title)
            stats['error'] += 1
        id_attrs = {
            'report_type': report_type,
            'metric': get_or_create_with_map(Metric, metrics, 'short_name', record.metric),
            'organization': organization,
            'platform': platform,
            'target_id': title_id,
            'date': record.start,
        }
        for i, dim in enumerate(dimensions):
            dim_value = record.dimension_data.get(dim.short_name)
            if dim.type != dim.TYPE_INT and dim_value is not None:
                remap = text_to_int_remaps.get(dim.pk)
                if not remap:
                    remap = {}
                    text_to_int_remaps[dim.pk] = remap
                dim_text_obj = get_or_create_with_map(DimensionText, remap, 'text', dim_value,
                                                      other_attrs={'dimension_id': dim.pk})
                dim_value = dim_text_obj.pk
            id_attrs[f'dim{i+1}'] = dim_value
        al, created = AccessLog.objects.get_or_create(**id_attrs, defaults={'value': record.value})
        if created:
            stats['new logs'] += 1
        else:
            if al.value != record.value:
                logger.warning(f'Clashing values between import and db: '
                               f'{record.value} x {al.value}')
                stats['update logs'] += 1
            else:
                logger.info('Record already present with the same value')
                stats['skipped logs'] += 1
    return stats
