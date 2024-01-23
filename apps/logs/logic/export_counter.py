import csv
from abc import ABCMeta, abstractmethod
from collections import Counter
from datetime import date
from io import StringIO
from itertools import islice
from logging import getLogger
from typing import Generator, Iterable, List, Optional

from core.logic.dates import month_end, month_start, months_in_range
from django.conf import settings
from django.utils.timezone import now
from hcube.api.models.aggregation import Max, Min
from hcube.api.models.transforms import StoredMap
from organizations.models import Organization
from publications.models import Platform

from logs.cubes import AccessLogCube, AccessLogCubeRecord, ch_backend
from logs.exceptions import DataStructureError
from logs.models import ReportType

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

        order_bys = ["target_id"] + list(self.dimensions_mapping.values()) + ["metric_id", "date"]
        query = (
            AccessLogCube.query()
            .filter(**filters)
            .transform(
                target=StoredMap("target_id", "title", "name"),
                target__issn=StoredMap("target_id", "title", "issn"),
                target__eissn=StoredMap("target_id", "title", "eissn"),
                target__isbn=StoredMap("target_id", "title", "isbn"),
                target__doi=StoredMap("target_id", "title", "doi"),
                metric=StoredMap("metric_id", "metric", "short_name"),
                dim1_text=StoredMap("dim1", "dim", "text"),
                dim2_text=StoredMap("dim2", "dim", "text"),
                dim3_text=StoredMap("dim3", "dim", "text"),
                dim4_text=StoredMap("dim4", "dim", "text"),
                dim5_text=StoredMap("dim5", "dim", "text"),
                dim6_text=StoredMap("dim6", "dim", "text"),
                dim7_text=StoredMap("dim7", "dim", "text"),
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
    def attributes_to_show(self) -> str:
        pass

    def make_file_header(self) -> List[List[str]]:
        """Prepare file header"""
        return [
            ["Report_Name", self.report_name],
            ["Report_ID", self.report_id],
            ["Release", "5"],
            ["Institution_Name", "Celus"],
            ["Institution_ID", "ISNI:0000000000000000"],
            ["Metric_Types", ""],
            ["Report_Filters", ""],
            [
                "Report_Attributes",
                f"Attributes_To_Show={'|'.join(self.attributes_to_show)}"
                if self.attributes_to_show
                else "",
            ],
            ["Exceptions", ""],
            [
                "Reporting_Period",
                f"Begin_Date={self.start_date.isoformat()}; "
                f"End_Date={self.end_date.isoformat()}",
            ],
            ["Created", now().replace(microsecond=0).isoformat()],
            ["Created_By", f"Celus {settings.CELUS_VERSION}"],
        ]

    def same_line(self, r1: AccessLogCubeRecord, r2: AccessLogCubeRecord) -> bool:
        """Determines whether two AccessLogCubeRecord belong to the same line"""
        # date and import_batch_id should not be checked
        # platform_id and report_id doesn't need to be checked
        return (
            r1.organization_id == r2.organization_id
            and r1.target_id == r2.target_id
            and r1.dim1 == r2.dim1
            and r1.dim2 == r2.dim2
            and r1.dim3 == r2.dim3
            and r1.dim4 == r2.dim4
            and r1.dim5 == r2.dim5
            and r1.dim6 == r2.dim6
            and r1.dim7 == r2.dim7
            and r1.metric_id == r2.metric_id
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
            logger.warn(
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
    def make_record_line(
        self,
        record: AccessLogCubeRecord,
        month_values: List[int],
    ) -> List[str]:
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
        buff = StringIO()
        writer = csv.writer(buff, dialect="excel")
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
    attributes_to_show = [
        "Data_Type",
        "Section_Type",
        "YOP",
        "Access_Type",
        "Access_Method",
    ]

    def get_record_error(self, record: AccessLogCubeRecord) -> Optional[str]:
        if not record.target_id:
            return "Missing Title for TR"

    def get_target_ids(self, record: AccessLogCubeRecord) -> Iterable[str]:
        # proprietary_ID and uri are empty
        return (
            record.target or "",
            record.target__doi or "",
            "",  # Proprietary_ID
            record.target__isbn or "",
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

    def make_record_line(
        self,
        record: AccessLogCubeRecord,
        month_values: List[int],
    ) -> List[str]:
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

    def make_record_line(
        self,
        record: AccessLogCubeRecord,
        month_values: List[int],
    ) -> List[str]:
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

    def make_record_line(
        self,
        record: AccessLogCubeRecord,
        month_values: List[int],
    ) -> List[str]:
        platform = self.get_target_ids(record)[0]
        return (
            platform,
            self.get_dimension_value(record, "Data_Type"),
            self.get_dimension_value(record, "Access_Method"),
            record.metric,
            sum(month_values),
            *month_values,
        )


class IR_M1Counter5Export(Counter5Export):
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

    def make_record_line(
        self,
        record: AccessLogCubeRecord,
        month_values: List[int],
    ) -> List[str]:
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
