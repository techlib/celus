from typing import Callable, Optional

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Exists, Max, Min, OuterRef
from organizations.models import Organization
from tags.logic.titles_lists import CsvReaderMixin, TitleListReader, TitleTaggingRecord

from publications.models import PlatformTitle, Title


class CsvTitleListOverlapReader(CsvReaderMixin, TitleListReader):
    match_column = "_Matched titles_"
    platform_list_column = "_Found on platforms_"
    start_date_column = "_First usage data_"
    end_date_column = "_Last usage data_"

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
            return {"organization_id": self.organization.pk}
        return {}

    def title_qs(self):
        """
        We only want to match titles that are linked to the organization in `self.organization`.
        :return:
        """
        return Title.objects.filter(
            Exists(PlatformTitle.objects.filter(title_id=OuterRef("pk"), **self.org_filter()))
        )

    def extra_column_names(self) -> [str]:
        return [
            self.platform_list_column,
            self.match_column,
            self.start_date_column,
            self.end_date_column,
        ]

    def annotate_dump_record(self, record: TitleTaggingRecord) -> dict:
        out = {}
        if record.title_ids:
            title_ids = ", ".join(map(self.dump_id_formatter, sorted(record.title_ids)))
            out[self.match_column] = title_ids
            out[self.platform_list_column] = ", ".join(record.extra_data["platforms"])
            out[self.start_date_column] = record.extra_data["start_date"]
            out[self.end_date_column] = record.extra_data["end_date"]
        return out

    def add_extra_data_to_rec_batch(self, records: [TitleTaggingRecord]):
        title_ids = set()
        for record in records:
            if record.title_ids:
                title_ids |= record.title_ids
        title_id_to_platform_names = dict(
            PlatformTitle.objects.filter(title_id__in=title_ids, **self.org_filter())
            .values("title_id")
            .annotate(platform_names=ArrayAgg("platform__name", distinct=True))
            .values_list("title_id", "platform_names")
        )
        title_id_to_start_end_dates = {
            title_id: (start_date, end_date)
            for title_id, start_date, end_date in PlatformTitle.objects.filter(
                title_id__in=title_ids, **self.org_filter()
            )
            .values("title_id")
            .annotate(start_date=Min("date"), end_date=Max("date"))
            .values_list("title_id", "start_date", "end_date")
        }
        for record in records:
            platforms = set()
            start_date = None
            end_date = None
            for title_id in record.title_ids:
                platforms |= set(title_id_to_platform_names.get(title_id, []))
                if dates := title_id_to_start_end_dates.get(title_id):
                    sd, ed = dates
                    start_date = min(start_date, sd) if start_date else sd
                    end_date = max(end_date, ed) if end_date else ed
            record.extra_data = {
                "platforms": sorted(platforms),
                "start_date": start_date,
                "end_date": end_date,
            }
