import codecs
import csv
from abc import ABCMeta, abstractmethod
from collections import Counter, defaultdict
from datetime import date
from io import BytesIO
from itertools import islice
from logging import getLogger
from typing import Any, Dict, Generator, Iterable, List, Optional

from core.logic.dates import month_end, month_start, months_in_range
from django.conf import settings
from django.utils.timezone import now
from hcube.api.models.aggregation import Max, Min
from hcube.api.models.transforms import StoredMap
from organizations.models import Organization
from publications.logic.validation import format_isbn_for_counter
from publications.models import AuthorToItem, Platform

from logs.cubes import AccessLogCube, AccessLogCubeRecord, ch_backend
from logs.exceptions import DataStructureError
from logs.models import DIMENSION_COUNT, ReportType

logger = getLogger(__name__)


class Counter5Export(metaclass=ABCMeta):
    TITLE_PRELOAD_SIZE = 10_000
    CSV_LINE_BATCH = 10_000

    def __init__(
        self,
        organization: Organization,
        platform: Platform,
        report_type: ReportType,
        start_date: Optional[date],
        end_date: Optional[date],
    ):
        self.organization = organization
        self.report_type = report_type

        filters = {
            "report_type_id": report_type.pk,
            "platform_id": platform.pk,
            "organization_id": organization.pk,
        }

        # get filters
        if not start_date or not end_date:
            if ch_backend.get_count(AccessLogCube.query()):
                rec = ch_backend.get_one_record(
                    AccessLogCube.query().aggregate(end=Max("date"), start=Min("date"))
                )
                # Note that in the current version of hcube
                # rec.start and rec.end contains 1970-01-01
                # when no record is present
                start_date = start_date or rec.start
                end_date = end_date or rec.end

            start_date = start_date or date(1970, 1, 1)
            end_date = end_date or now().date()

        self.start_date = month_start(start_date)
        self.end_date = month_end(end_date)

        filters["date__gte"] = self.start_date
        filters["date__lte"] = self.end_date
        self.months = tuple(months_in_range(start_date, end_date))

        self.dimensions_mapping = {
            e: report_type.dim_name_to_dim_attr(e) for e in report_type.dimension_short_names
        }

        order_bys = (
            ["target_id", "item_id"]
            + list(self.dimensions_mapping.values())
            + ["metric_id", "date"]
        )
        query = (
            AccessLogCube.query()
            .filter(**filters)
            .transform(
                target=StoredMap("target_id", "title", "name"),
                target__issn=StoredMap("target_id", "title", "issn"),
                target__eissn=StoredMap("target_id", "title", "eissn"),
                target__isbn=StoredMap("target_id", "title", "isbn"),
                target__doi=StoredMap("target_id", "title", "doi"),
                item=StoredMap("item_id", "item", "name"),
                item__issn=StoredMap("item_id", "item", "issn"),
                item__eissn=StoredMap("item_id", "item", "eissn"),
                item__isbn=StoredMap("item_id", "item", "isbn"),
                item__doi=StoredMap("item_id", "item", "doi"),
                item__publication_date=StoredMap("item_id", "item", "publication_date"),
                metric=StoredMap("metric_id", "metric", "short_name"),
                **{
                    f"dim{i + 1}_text": StoredMap(f"dim{i + 1}", "dim", "text")
                    for i in range(DIMENSION_COUNT)
                },
            )
            .order_by(*order_bys)
        )

        self.errors = Counter()

        # Initial record generator
        self.ordered_records = ch_backend.get_records(query, streaming=True)

    @property
    @abstractmethod
    def report_name(self) -> str:
        pass

    @property
    @abstractmethod
    def report_id(self) -> str:
        pass

    @property
    @abstractmethod
    def attributes_to_show(self) -> List[str]:
        pass

    @property
    def extras(self) -> Dict[str, Any]:
        return {}

    def make_file_header(self) -> List[List[str]]:
        """Prepare file header"""
        attrs = (
            f"Attributes_To_Show={'|'.join(self.attributes_to_show)}"
            if self.attributes_to_show
            else ""
        )
        extras = [f"{k}={v}" for k, v in self.extras.items()]
        return [
            ["Report_Name", self.report_name],
            ["Report_ID", self.report_id],
            ["Release", "5"],
            ["Institution_Name", "CELUS"],
            ["Institution_ID", "ISNI:0000000000000000"],
            ["Metric_Types", ""],
            ["Report_Filters", ""],
            ["Report_Attributes", ";".join(e for e in [attrs] + extras if e)],
            ["Exceptions", ""],
            [
                "Reporting_Period",
                f"Begin_Date={self.start_date.isoformat()}; "
                f"End_Date={self.end_date.isoformat()}",
            ],
            ["Created", now().replace(microsecond=0).isoformat()],
            ["Created_By", f"CELUS {settings.CELUS_VERSION}"],
        ]

    def same_line(self, r1: AccessLogCubeRecord, r2: AccessLogCubeRecord) -> bool:
        """Determines whether two AccessLogCubeRecord belong to the same line"""
        # date and import_batch_id should not be checked
        # platform_id and report_id doesn't need to be checked
        return (
            r1.organization_id == r2.organization_id
            and r1.target_id == r2.target_id
            and r1.item_id == r2.item_id
            and r1.metric_id == r2.metric_id
            and all(
                getattr(r1, f"dim{i + 1}") == getattr(r2, f"dim{i + 1}")
                for i in range(DIMENSION_COUNT)
            )
        )

    def line_records(self) -> Generator[List[AccessLogCubeRecord], None, None]:
        """Groups record which belongs to the same line"""
        line = None
        for record in self.ordered_records:
            if error := self.get_record_error(record):
                self.errors[error] += 1
            if not line:
                line = [record]
            elif self.same_line(record, line[0]):
                line.append(record)
            else:
                yield line
                line = [record]
        if line:
            yield line

        if self.errors:
            logger.warning(
                "There are structural errors in the data",
                exc_info=DataStructureError(", ".join(f"{k}: {v}" for k, v in self.errors.items())),
            )

    @abstractmethod
    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        pass

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        return None

    @abstractmethod
    def make_record_header(self) -> List[str]:
        pass

    @abstractmethod
    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        pass

    def lines(self) -> Generator[List[str], None, None]:
        yield from self.make_file_header()
        yield []
        yield self.make_record_header()

        for line_records in self.line_records():
            # Extract months
            line_records_idx = 0
            month_values = []
            for month in self.months:
                if line_records_idx >= len(line_records):
                    # Fill in values for last months
                    month_values.append(0)
                elif line_records[line_records_idx].date == month:
                    month_values.append(line_records[line_records_idx].value)
                    line_records_idx += 1
                else:
                    # Missing record
                    month_values.append(0)

            yield self.make_record_line(line_records[0], month_values)

    def csv(self) -> Generator[bytes, None, None]:
        """Format the stream of lists into csv encoded bytes stream"""
        generator = self.lines()
        buff = BytesIO()
        encoder = codecs.getwriter("utf-8")(buff)
        buff.write(codecs.BOM_UTF8)  # we need to write BOM after encoder initialization
        writer = csv.writer(encoder, dialect="excel")
        while lines := tuple(islice(generator, self.CSV_LINE_BATCH)):
            writer.writerows(lines)
            yield buff.getvalue()
            # Clear the buffer so it won't consume extra memory
            buff.seek(0)
            buff.truncate(0)

    def get_dimension_value(self, record: AccessLogCubeRecord, dim_name: str):
        return getattr(record, f"{self.dimensions_mapping[dim_name]}_text", None)


class TRCounter5Export(Counter5Export):
    report_name = "Title Master Report"
    report_id = "TR"
    attributes_to_show = ["Data_Type", "Section_Type", "YOP", "Access_Type", "Access_Method"]

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not record.target_id:
            return "Missing Title for TR"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        # proprietary_ID and uri are empty
        return (
            record.target or "",
            record.target__doi or "",
            "",  # Proprietary_ID
            format_isbn_for_counter(record.target__isbn),
            record.target__issn or "",
            record.target__eissn or "",
            "",  # URI
        )

    def make_record_header(self) -> List[str]:
        return [
            "Title",
            "Publisher",
            "Publisher_ID",
            "Platform",
            "DOI",
            "Proprietary_ID",
            "ISBN",
            "Print_ISSN",
            "Online_ISSN",
            "URI",
            "Data_Type",
            "Section_Type",
            "YOP",
            "Access_Type",
            "Access_Method",
            "Metric_Type",
            "Reporting_Period_Total",
        ] + [e.strftime("%b-%Y") for e in self.months]

    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        title, *title_ids = self.get_target_ids(record)
        return (
            title,
            self.get_dimension_value(record, "Publisher"),
            "",  # Publisher_ID
            self.get_dimension_value(record, "Platform"),
            *title_ids,
            self.get_dimension_value(record, "Data_Type"),
            self.get_dimension_value(record, "Section_Type"),
            self.get_dimension_value(record, "YOP"),
            self.get_dimension_value(record, "Access_Type"),
            self.get_dimension_value(record, "Access_Method"),
            record.metric,
            sum(month_values),
            *month_values,
        )


class DRCounter5Export(Counter5Export):
    report_name = "Database Master Report"
    report_id = "DR"
    attributes_to_show = ["Data_Type", "Access_Method"]

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not record.target_id:
            return "Missing Database for DR"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        return (
            record.target or "",
            "",  # Proprietary_ID
        )

    def make_record_header(self) -> List[str]:
        return [
            "Database",
            "Publisher",
            "Publisher_ID",
            "Platform",
            "Proprietary_ID",
            "Data_Type",
            "Access_Method",
            "Metric_Type",
            "Reporting_Period_Total",
        ] + [e.strftime("%b-%Y") for e in self.months]

    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        database, proprietary_id = self.get_target_ids(record)
        return (
            database,
            self.get_dimension_value(record, "Publisher"),
            "",  # Publisher_ID
            self.get_dimension_value(record, "Platform"),
            proprietary_id,
            self.get_dimension_value(record, "Data_Type"),
            self.get_dimension_value(record, "Access_Method"),
            record.metric,
            sum(month_values),
            *month_values,
        )


class PRCounter5Export(Counter5Export):
    report_name = "Platform Master Report"
    report_id = "PR"
    attributes_to_show = ["Data_Type", "Access_Method"]

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not self.get_dimension_value(record, "Platform"):
            return "Missing Platform dimension"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        return (self.get_dimension_value(record, "Platform") or "",)

    def make_record_header(self) -> List[str]:
        return [
            "Platform",
            "Data_Type",
            "Access_Method",
            "Metric_Type",
            "Reporting_Period_Total",
        ] + [e.strftime("%b-%Y") for e in self.months]

    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        platform = self.get_target_ids(record)[0]
        return (
            platform,
            self.get_dimension_value(record, "Data_Type"),
            self.get_dimension_value(record, "Access_Method"),
            record.metric,
            sum(month_values),
            *month_values,
        )


class BaseIRCounter5Export(Counter5Export):
    ITEM_BATCH_LINES_LEN = 1000

    def line_records(self) -> Generator[List[AccessLogCubeRecord], None, None]:
        generator = super().line_records()
        while batch := tuple(islice(generator, self.ITEM_BATCH_LINES_LEN)):
            # Prefetch item_id => author str mapping
            item_ids = {e[0].item_id for e in batch if e[0].item_id}
            item_id_to_author = defaultdict(list)
            for a2i in (
                AuthorToItem.objects.filter(item__in=item_ids)
                .select_related("author")
                .order_by("item_id", "position")
            ):
                item_id_to_author[a2i.item_id].append(str(a2i.author))

            self.item_id_to_author_str = {k: "; ".join(v) for k, v in item_id_to_author.items()}

            yield from batch

    def get_authors(self, pk: int) -> str:
        return self.item_id_to_author_str.get(pk, "")


class IR_M1Counter5Export(BaseIRCounter5Export):
    report_name = "Multimedia Item Requests"
    report_id = "IR_M1"
    attributes_to_show = []

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not record.target_id:
            return "Missing Item for IR_M1"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        # proprietary_ID and uri are empty
        return (
            record.target or "",
            record.target__doi or "",
            "",  # Proprietary_ID
            "",  # URI
        )

    def make_record_header(self) -> List[str]:
        return [
            "Item",
            "Publisher",
            "Publisher_ID",
            "Platform",
            "DOI",
            "Proprietary_ID",
            "URI",
            "Metric_Type",
            "Reporting_Period_Total",
        ] + [e.strftime("%b-%Y") for e in self.months]

    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        item, *item_ids = self.get_target_ids(record)
        return (
            item,
            self.get_dimension_value(record, "Publisher"),
            "",  # Publisher_ID
            self.get_dimension_value(record, "Platform"),
            *item_ids,
            record.metric,
            sum(month_values),
            *month_values,
        )


class IRCounter5Export(BaseIRCounter5Export):
    report_name = "Item Master Report"
    report_id = "IR"
    attributes_to_show = [
        "Authors",
        "Publication_Date",
        "Article_Version",
        "Data_Type",
        "YOP",
        "Access_Type",
        "Access_Method",
    ]
    extras = {"Include_Parent_Details": True}

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not record.item_id:
            return "Missing Item for IR"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        # proprietary_ID and uri are empty
        return (
            record.target or "",
            record.target__doi or "",
            "",  # Proprietary_ID
            format_isbn_for_counter(record.target__isbn),
            record.target__issn or "",
            record.target__eissn or "",
            "",  # URI
        )

    def get_item_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        # proprietary_ID and uri are empty
        return (
            record.item or "",
            record.item__publication_date or "",
            record.item__doi or "",
            "",  # Proprietary_ID
            format_isbn_for_counter(record.item__isbn),
            record.item__issn or "",
            record.item__eissn or "",
            "",  # URI
        )

    def make_record_header(self) -> List[str]:
        return [
            "Item",
            "Publisher",
            "Publisher_ID",
            "Platform",
            "Authors",
            "Publication_Date",
            "Article_Version",
            "DOI",
            "Proprietary_ID",
            "ISBN",
            "Print_ISSN",
            "Online_ISSN",
            "URI",
            "Parent_Title",
            "Parent_Authors",
            "Parent_Publication_Date",
            "Parent_Article_Version",
            "Parent_Data_Type",
            "Parent_DOI",
            "Parent_Proprietary_ID",
            "Parent_ISBN",
            "Parent_Print_ISSN",
            "Parent_Online_ISSN",
            "Parent_URI",
            "Data_Type",
            "YOP",
            "Access_Type",
            "Access_Method",
            "Metric_Type",
            "Reporting_Period_Total",
        ] + [e.strftime("%b-%Y") for e in self.months]

    def make_record_line(self, record: AccessLogCubeRecord, month_values: List[int]) -> List[str]:
        parent, *parent_ids = self.get_target_ids(record)
        item, publication_date, *item_ids = self.get_item_ids(record)
        return (
            item,
            self.get_dimension_value(record, "Publisher"),
            "",  # Publisher_ID
            self.get_dimension_value(record, "Platform"),
            self.get_authors(record.item_id),
            publication_date,
            self.get_dimension_value(record, "Article_Version"),
            *item_ids,
            parent,
            "",  # Parent_Authors
            "",  # Parent_Publication_Date
            "",  # Parent_Article_Version
            self.get_dimension_value(record, "Parent_Data_Type"),
            *parent_ids,
            self.get_dimension_value(record, "Data_Type"),
            self.get_dimension_value(record, "YOP"),
            self.get_dimension_value(record, "Access_Type"),
            self.get_dimension_value(record, "Access_Method"),
            record.metric,
            sum(month_values),
            *month_values,
        )
