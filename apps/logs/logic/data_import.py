from publications.models import Title
from ..models import ReportType, Metric, DimensionText, OrganizationPlatform
from sushi.counter5 import CounterRecord


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

    def __init__(self):
        self.key_to_title_id = {(t.name, t.pub_type, t.isbn, t.issn, t.eissn, t.doi): t.pk
                                for t in Title.objects.all()}

    @classmethod
    def decode_pub_type(cls, pub_type: str) -> str:
        if pub_type in 'JB':
            return pub_type
        elif pub_type.lower() == 'journal':
            return Title.PUB_TYPE_JOURNAL
        elif pub_type.lower() == 'book':
            return Title.PUB_TYPE_BOOK
        raise ValueError('Unknown publication type: {}'.format(pub_type))

    def get_or_create(self, name, pub_type, isbn, issn, eissn, doi) -> int:
        pub_type = self.decode_pub_type(pub_type)
        key = (name, pub_type, isbn, issn, eissn, doi)
        if key in self.key_to_title_id:
            return self.key_to_title_id[key]
        title = Title.objects.create(name=name, pub_type=pub_type, isbn=isbn, issn=issn,
                                     eissn=eissn, doi=doi)
        self.key_to_title_id[key] = title.pk
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
        return self.get_or_create(title, pub_type, isbn, issn, eissn, doi)


def import_counter_records(report_type: ReportType, source: OrganizationPlatform,
                           records: [CounterRecord]):
    # prepare all remaps
    metrics = {metric.short_name: metric for metric in Metric.objects.all()}
    text_to_int_remaps = {}
    for dim_text in DimensionText.objects.all():
        if dim_text.dimension_id not in text_to_int_remaps:
            text_to_int_remaps[dim_text.dimension_id] = {}
        text_to_int_remaps[dim_text.dimension_id][dim_text.text] = dim_text.pk
    tm = TitleManager()
    #
    dimensions = report_type.dimension_short_names
    for record in records:  # type: CounterRecord
        # attributes that define the identity of the log
        id_attrs = {
            'report_type': report_type,
            'metric': get_or_create_with_map(Metric, metrics, 'short_name', record.metric),
            'source': source,
            'target_id': tm.get_or_create_from_counter_record(record),
            'date': record.start,
        }
        for i, dim in enumerate(dimensions):
            dim_value = record.dimension_data.get(dim)
            id_attrs[f'dim{i+1}'] = dim_value
