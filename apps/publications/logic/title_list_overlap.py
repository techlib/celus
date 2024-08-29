from typing import Callable, List, Optional

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Max, Min
from logs.logic.interest import get_interest_subdim_ids_implying_availability
from logs.models import AccessLog, ReportType
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
        We only want to match titles that have interest for a specific organization
        `self.organization` or have some interest at all.

        We only use types of interest which imply that the title is available on a platform.
        :return:
        """
        interest_rt = ReportType.objects.get_interest_rt()
        # resolving the dims into list makes the subsequent query slightly faster
        dim1_ids = list(get_interest_subdim_ids_implying_availability(interest_rt))
        title_ids_query = AccessLog.objects.filter(
            report_type=interest_rt, dim1__in=dim1_ids, target_id__isnull=False, **self.org_filter()
        ).values("target_id")
        qs = Title.objects.filter(pk__in=title_ids_query)
        return qs

    def extra_column_names(self) -> [str]:
        return [
            self.platform_list_column,
            self.start_date_column,
            self.end_date_column,
            self.match_column,
        ]

    def annotate_dump_record(self, record: TitleTaggingRecord) -> List:
        return [
            ", ".join(record.extra_data["platforms"]),
            record.extra_data["start_date"],
            record.extra_data["end_date"],
            len(record.title_ids),
        ] + list(map(self.dump_id_formatter, sorted(record.title_ids)))

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
