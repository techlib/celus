from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, List, Optional, Tuple

from core.logic.dates import months_in_range
from logs.logic.reporting.filters import (
    DateDimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText, Metric, ReportType
from publications.models import Platform


class Report:

    primary_dimension = "platform"

    def __init__(self, name: str, description: str, parts: Optional[List[dict]] = None):
        self.name = name
        self.description = description
        self.parts = []
        parts = parts or []
        for part in parts:
            name = part["name"]
            description = part["description"]
            primary_source = self.create_source(part["mainReportDefinition"])
            fallback_source = self.create_source(part.get("fallbackReportDefinition"))
            subtracted_fallback_source = self.create_source(
                part.get("subtractedFallbackReportDefinition")
            )
            implementation_note = part.get("implementationNote")
            self.parts.append(
                ReportPart(
                    name,
                    description,
                    primary_source,
                    fallback_source,
                    subtracted_fallback_source,
                    implementation_note=implementation_note,
                )
            )
        # computed data
        self._prim_dim_remap = {}
        self._covered_months = []
        self.organization = None
        self.start_date = None
        self.end_date = None

    @classmethod
    def from_definition(cls, definition: dict) -> "Report":
        return cls(definition["name"], definition["description"], definition.get("parts", []))

    @classmethod
    def create_source(cls, definition: dict) -> Optional["ReportDataSource"]:
        if not definition:
            return None
        report_type = ReportType.objects.get(short_name=definition["reportType"])
        try:
            metric = (
                Metric.objects.get(short_name=definition["metric"])
                if definition["metric"]
                else None
            )
        except Metric.DoesNotExist:
            raise ValueError(f"Metric {definition['metric']} does not exist")
        return ReportDataSource(report_type, metric, definition.get("filters", {}))

    @property
    def covered_months(self) -> List[date]:
        return self._covered_months

    def get_primary_model_qs(self):
        if self.primary_dimension == 'platform':
            return Platform.objects.filter(organizationplatform__organization=self.organization)
        raise ValueError(f"Unsupported primary dimension: {self.primary_dimension}")

    def retrieve_data(self, organization, start_date: date, end_date: date):
        # store the parameters for later use
        self.organization = organization
        self.start_date = start_date
        self.end_date = end_date
        self._covered_months = list(months_in_range(start_date, end_date))
        # retrieve data
        model_qs = self.get_primary_model_qs()
        self._prim_dim_remap = {obj.pk: obj for obj in model_qs}
        primary_ids = set(self._prim_dim_remap.keys())
        for part in self.parts:
            part.retrieve_data(organization, start_date, end_date, primary_ids=primary_ids)

    def gen_output(self) -> Generator[Tuple["ReportPart", List["ResultRow"]], None, None]:
        for part in self.parts:
            rows = []
            for pk, obj in self._prim_dim_remap.items():
                total = 0
                rt = None
                prim_data = part.primary_results_.get(pk, None)
                if prim_data and (total := prim_data.get('_total', 0)) > 0:
                    monthly_data = self.extract_monthly_data(prim_data)
                    rt = part.primary_source.report_type
                elif part.fallback_source:
                    fallback_data = part.fallback_results_.get(pk, None)
                    if fallback_data and (total := fallback_data.get('_total', 0)) > 0:
                        monthly_data = self.extract_monthly_data(fallback_data)
                        # subtract the subtracted fallback data if defined
                        if part.subtracted_fallback_source:
                            subtracted_data = part.subtracted_fallback_results_.get(pk, None)
                            if subtracted_data:
                                for month in self._covered_months:
                                    monthly_data[month] -= subtracted_data.get(f'grp-{month}', 0)
                        rt = part.fallback_source.report_type
                if not total:
                    monthly_data = self.extract_monthly_data({})
                rows.append(
                    ResultRow(
                        primary_pk=pk,
                        primary_obj=obj,
                        monthly_data=monthly_data,
                        total=total,
                        used_report_type=rt,
                    )
                )
            yield part, rows

    def extract_monthly_data(self, rec: dict) -> dict:
        out = {}
        for month in self._covered_months:
            out[month] = rec.get(f'grp-{month}', 0)
        return out


class ReportPart:
    def __init__(
        self,
        name: str,
        description: str,
        primary_source: "ReportDataSource",
        fallback_source: Optional["ReportDataSource"] = None,
        subtracted_fallback_source: Optional["ReportDataSource"] = None,
        implementation_note: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.subtracted_fallback_source = subtracted_fallback_source
        self.implementation_note = implementation_note
        # the following are computed data filled in later
        # the structure is {primary_id: {date: value}}
        self.primary_results_ = {}
        self.fallback_results_ = {}
        self.subtracted_fallback_results_ = {}

    def retrieve_data(
        self, organization, start_date, end_date, primary_ids: Optional[set] = None
    ) -> None:
        for rec in self.primary_source.get_data(
            organization, start_date, end_date, primary_ids=primary_ids
        ):
            pk = rec.pop('pk')
            self.primary_results_[pk] = rec
        # only get fallbacks if we did not resolve all primary keys
        if primary_ids:
            remaining_ids = primary_ids - set(self.primary_results_.keys())
            if remaining_ids and self.fallback_source:
                for rec in self.fallback_source.get_data(
                    organization, start_date, end_date, primary_ids=remaining_ids
                ):
                    pk = rec.pop('pk')
                    self.fallback_results_[pk] = rec
                if self.subtracted_fallback_source:
                    for rec in self.subtracted_fallback_source.get_data(
                        organization, start_date, end_date, primary_ids=remaining_ids
                    ):
                        pk = rec.pop('pk')
                        self.subtracted_fallback_results_[pk] = rec


class ReportDataSource:
    """
    Defines the report type which to use and what metric to extract. Optionally, it can also
    define filters to apply to the report.
    """

    def __init__(
        self, report_type: ReportType, metric: Optional[Metric], filters: Optional[dict] = None
    ):
        self.report_type = report_type
        self.metric = metric
        self.filters = filters or {}

    def get_data(
        self, organization, start_date, end_date, primary_ids: Optional[set] = None
    ) -> List[dict]:
        slicer = FlexibleDataSlicer(
            primary_dimension=Report.primary_dimension,
            include_all_zero_rows=False,
            use_clickhouse=True,
        )
        if primary_ids:
            slicer.add_filter(ExplicitDimensionFilter(Report.primary_dimension, primary_ids))
        slicer.add_filter(DateDimensionFilter('date', start_date, end_date), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter('organization', [organization]))
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', [self.report_type.pk]))
        if self.metric:
            slicer.add_filter(ForeignKeyDimensionFilter('metric', [self.metric.pk]))
        for dim_name, values in self.filters.items():
            if type(values) not in (list, tuple, set):
                values = [values]
            if dim_attr := self.report_type.dim_name_to_dim_attr(dim_name):
                dim_obj = self.report_type.dimension_by_attr_name(dim_attr)
                dim_values = DimensionText.objects.filter(
                    dimension=dim_obj, text__in=values
                ).values_list('pk', flat=True)
                slicer.add_filter(ExplicitDimensionFilter(dim_attr, dim_values))
            else:
                raise ValueError(f'Unknown dimension "{dim_name}" for rt "{self.report_type}"')
        return list(slicer.get_data())


@dataclass
class ResultRow:

    primary_pk: int
    primary_obj: Any
    monthly_data: dict
    total: int
    used_report_type: Optional[ReportType] = None  # None means no data

    def as_dict(self) -> dict:
        return {
            'primary_pk': self.primary_pk,
            'primary_obj': self.primary_obj.short_name,
            'monthly_data': {
                key.strftime('%Y-%m'): value for key, value in self.monthly_data.items()
            },
            'total': self.total,
            'used_report_type': self.used_report_type.short_name if self.used_report_type else None,
        }
