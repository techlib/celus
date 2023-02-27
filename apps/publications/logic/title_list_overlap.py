from typing import Callable, Optional

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Exists, OuterRef
from organizations.models import Organization
from publications.models import PlatformTitle, Title
from tags.logic.titles_lists import CsvReaderMixin, TitleListReader, TitleTaggingRecord


class CsvTitleListOverlapReader(CsvReaderMixin, TitleListReader):

    has_explicit_tags = False
    match_column = '_Matched titles_'
    platform_list_column = '_Found on platforms_'

    def __init__(
        self,
        organization: Optional[Organization] = None,
        dump_id_formatter: Callable[[int], str] = str,
    ):
        super().__init__()
        self.organization = organization
        self.dump_id_formatter = dump_id_formatter

    def org_filter(self):
        if self.organization:
            return {'organization_id': self.organization.pk}
        return {}

    def title_qs(self):
        """
        We only want to match titles that are linked to the organization in `self.organization`.
        :return:
        """
        return Title.objects.filter(
            Exists(PlatformTitle.objects.filter(title_id=OuterRef('pk'), **self.org_filter()))
        )

    def extra_column_names(self) -> [str]:
        return [self.platform_list_column, self.match_column]

    def annotate_dump_record(self, record: TitleTaggingRecord) -> dict:
        out = {}
        if record.title_ids:
            title_ids = ', '.join(map(self.dump_id_formatter, sorted(record.title_ids)))
            out[self.match_column] = title_ids
            out[self.platform_list_column] = ', '.join(record.extra_data['platforms'])
        return out

    def add_extra_data_to_rec_batch(self, records: [TitleTaggingRecord]):
        title_ids = set()
        for record in records:
            if record.title_ids:
                title_ids |= record.title_ids
        title_id_to_platform_names = {
            title_id: plaform_names
            for title_id, plaform_names in PlatformTitle.objects.filter(
                title_id__in=title_ids, **self.org_filter()
            )
            .values('title_id')
            .annotate(platform_names=ArrayAgg('platform__name', distinct=True))
            .values_list('title_id', 'platform_names')
        }
        for record in records:
            platforms = set()
            for title_id in record.title_ids:
                platforms |= set(title_id_to_platform_names.get(title_id, []))
            record.extra_data = {'platforms': list(sorted(platforms))}
