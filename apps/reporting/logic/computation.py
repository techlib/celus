from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from core.logic.dates import months_in_range
from logs.logic.reporting.filters import (
    DateDimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText, Metric, ReportType
from organizations.models import Organization
from publications.models import Platform
from rest_framework.exceptions import ValidationError

from reporting.logic.parsing import (
    ReportDataSourceSerializer,
    ReportPartSerializer,
    ReportPartStageSerializer,
    ReportSerializer,
    parse_formula,
)


class ReportingContext:
    """
    Stores information about the currently generated report, such as the organization,
    the start and end dates, and other params. It also holds links to the sources and stages
    that are used in the report.
    """

    def __init__(
        self, report: "Report", organization: Organization, start_date: date, end_date: date
    ):
        self.report = report
        self.organization = organization
        self.start_date = start_date
        self.end_date = end_date
        self.covered_months = list(months_in_range(start_date, end_date))
        self._current_part_id = None
        # retrieve data
        self.primary_id_to_obj = {obj.pk: obj for obj in self.get_primary_model_qs()}
        self.primary_ids = set(self.primary_id_to_obj.keys())

    @property
    def sorted_primary_ids(self):
        return [
            r[0] for r in sorted(self.primary_id_to_obj.items(), key=lambda x: (x[1].name, x[0]))
        ]

    def get_primary_model_qs(self):
        if self.report.primary_dimension == "platform":
            return Platform.objects.filter(organizationplatform__organization=self.organization)
        raise ValueError(f"Unsupported primary dimension: {self.report.primary_dimension}")

    def get_stage_for_current_part(self, stage_id: str) -> "ReportPartStage":
        if self._current_part_id is None:
            raise ValueError("Current part not set, call `set_current_part()` first")
        return self.report.stages_by_part_and_id[self._current_part_id].get(stage_id)

    def set_current_part(self, part_id: str):
        """
        Should be set before any computation is performed on a part of the report. It sets
        the right context for the computation as stage IDs are evaluated separately for each part.
        """
        self._current_part_id = part_id

    def perform_computation(
        self, parsed_formula: List[Union[str, List]], source_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        :param parsed_formula: a list of strings and lists, representing a formula
        :param source_name: if given, it will be stored in the source_name column of the output,
               otherwise the source_name will be computed from the formula
        :return:
        """
        if len(parsed_formula) == 1:
            variable = parsed_formula[0]
            if isinstance(variable, list):
                return self.perform_computation(variable, source_name=source_name)
            if stage := self.get_stage_for_current_part(variable):
                out = stage.report_data_.copy()
                out["source_name"] = stage.name
                return out
            if source := self.report.get_source(variable):
                out = source.report_data_.copy()
                out["source_name"] = source.report_type
                return out
            raise ValueError(f"Unknown variable: {variable}")
        if len(parsed_formula) == 3:
            left, op, right = parsed_formula
            left_data = self.perform_computation([left])
            right_data = self.perform_computation([right])
            if op == "|":
                # use the left value for each cell if it's non-zero, otherwise use the right value
                # ensure right_data has the same index as left_data for proper alignment
                right_data_aligned = right_data.reindex(left_data.index)
                out = left_data.copy()
                # merge cell-by-cell: for each monthly column, use right value if left is zero
                for col in self.covered_months:
                    out[col] = left_data[col].where(left_data[col] != 0, right_data_aligned[col])
                # recompute total from the merged monthly data
                out[self.report.total_col] = out[self.covered_months].sum(axis=1)
                # update source_name based on merging:
                # - if left total was 0 and merged total > 0:
                #   all data came from right, use right name
                # - if left total > 0 and merged total > left total: partial merge, join names
                # - otherwise: keep left name
                left_total = left_data[self.report.total_col]
                merged_total = out[self.report.total_col]
                # all data from right
                all_from_right = (left_total == 0) & (merged_total > 0)
                out.loc[all_from_right, "source_name"] = right_data_aligned.loc[
                    all_from_right, "source_name"
                ]
                # partial merge (left had data, but some zeros were replaced)
                partial_merge = (left_total > 0) & (merged_total > left_total)
                out.loc[partial_merge, "source_name"] = (
                    left_data.loc[partial_merge, "source_name"]
                    + " | "
                    + right_data_aligned.loc[partial_merge, "source_name"]
                )
                return out
            if op == "-":
                out = left_data.copy()
                # the following uses dataframe operations, so the references to the `source_name`
                # column cannot be used in an f-string (it would be evaluated on the whole dataframe
                # level instead of on each row, resulting in a Series instead of a string)
                out["source_name"] = source_name or (
                    left_data["source_name"] + " - " + right_data["source_name"]
                )
                out[self.covered_months] = (
                    left_data[self.covered_months] - right_data[self.covered_months]
                )
                # make sure we don't have negative values
                out[self.covered_months] = out[self.covered_months].where(
                    out[self.covered_months] > 0, 0
                )
                # recompute total, because non-negative subtraction does not allow simple
                # subtraction of the total column
                out[self.report.total_col] = out[self.covered_months].sum(axis=1)
                return out
            if op == "+":
                out = left_data + right_data
                # the following uses dataframe operations, so the references to the `source_name`
                # column cannot be used in an f-string (it would be evaluated on the whole dataframe
                # level instead of on each row, resulting in a Series instead of a string)
                out["source_name"] = source_name or (
                    left_data["source_name"] + " + " + right_data["source_name"]
                )
                return out
            raise ValueError(f"Unsupported operator: {op}")
        raise ValueError(f"Unsupported formula: {parsed_formula}")

    def df_as_result_rows(self, df: pd.DataFrame) -> List["ResultRow"]:
        """
        Converts a dataframe to a format suitable for the frontend.
        """
        return [
            ResultRow(
                source_name=row["source_name"],
                primary_pk=idx,
                primary_obj=self.primary_id_to_obj[idx],
                monthly_data={month: row[month] for month in self.covered_months},
                total=row[self.report.total_col],
            )
            for idx, row in df.iterrows()
        ]


class Report:
    primary_dimension = "platform"
    total_col = "_total_"

    def __init__(self, name: str, description: str, info_url: str = None, general_info: str = None):
        self.name = name
        self.description = description
        self.info_url = info_url
        self.general_info = general_info
        self.parts = []
        # computed data
        self.sources_by_id = {}
        self.stages_by_part_and_id = {}
        self.context: Optional[ReportingContext] = None
        self._results: Dict[str, pd.DataFrame] = {}

    @classmethod
    def from_dict(cls, definition: dict) -> "Report":
        s = ReportSerializer(data=definition)
        s.is_valid(raise_exception=True)
        out = cls(
            s.validated_data["name"],
            s.validated_data.get("description", ""),
            info_url=s.validated_data.get("infoUrl"),
            general_info=s.validated_data.get("generalInfo"),
        )
        for value in s.validated_data["dataSources"]:
            data_source = ReportDataSource.from_dict(value, out)
            out.register_source(data_source)
            if data_source.fallback_for:
                try:
                    data_source.fallback_for_report = out.get_source(data_source.fallback_for)
                except ValueError:
                    raise ValidationError(
                        f"Could not resolve fallbackFor: {data_source.fallback_for}"
                    ) from None
        for part_def in s.validated_data["parts"]:
            part = ReportPart.from_dict(part_def, out)
            out.parts.append(part)
            for stage in part.stages:
                out.register_stage(part.name, stage)
                # the following validates the formulas in the stages
                stage.get_used_data_sources()
        return out

    def register_source(self, source: "ReportDataSource"):
        if source.id in self.sources_by_id:
            raise ValidationError(f"Duplicate source ID: {source.id}")
        self.sources_by_id[source.id] = source

    def get_source(self, source_id: str) -> "ReportDataSource":
        try:
            return self.sources_by_id[source_id]
        except KeyError:
            raise ValueError(f"Unknown source ID: {source_id}") from None

    def register_stage(self, part_id: str, stage: "ReportPartStage"):
        if stage.id in self.stages_by_part_and_id.get(part_id, {}):
            raise ValidationError(f"Duplicate stage ID: '{stage.id}' for part '{part_id}'")
        if stage.id in self.sources_by_id:
            raise ValidationError(
                f"Stage must not have the same ID as a source: '{stage.id}' for part '{part_id}'"
            )
        self.stages_by_part_and_id.setdefault(part_id, {})[stage.id] = stage

    def get_used_data_sources(
        self, part_id: str, parsed_formula: List[Union[str, list]]
    ) -> List[str]:
        """
        Returns a list of data source IDs that are used in the given formula. Also serves
        as a formula validator.
        """
        if len(parsed_formula) == 1:
            variable = parsed_formula[0]
            if isinstance(variable, list):
                return self.get_used_data_sources(part_id, variable)
            if stage := self.stages_by_part_and_id[part_id].get(variable):
                return self.get_used_data_sources(part_id, stage.parsed_formula)
            if source := self.sources_by_id.get(variable):
                return [source.id]
            raise ValidationError(f"Unknown variable: '{variable}'")
        if len(parsed_formula) == 3:
            left, op, right = parsed_formula
            return self.get_used_data_sources(part_id, [left]) + self.get_used_data_sources(
                part_id, [right]
            )
        raise ValidationError(f"Unsupported formula: {parsed_formula}")

    def create_context(self, organization, start_date: date, end_date: date):
        return ReportingContext(self, organization, start_date, end_date)

    @property
    def sorted_sources(self) -> ["ReportDataSource"]:
        # sort data sources by dependency
        source_ids = [id_ for id_, ds in self.sources_by_id.items() if ds.fallback_for is None]
        while len(source_ids) < len(self.sources_by_id):
            last_len = len(source_ids)
            for id_, ds in self.sources_by_id.items():
                if ds.fallback_for and ds.fallback_for not in source_ids:
                    continue
                if id_ not in source_ids:
                    source_ids.append(id_)
            if len(source_ids) == last_len:
                raise ValueError("Could not resolve data source dependencies")
        return [self.sources_by_id[sid] for sid in source_ids]

    def retrieve_data(self, organization, start_date: date, end_date: date):
        self.context = self.create_context(organization, start_date, end_date)
        # retrieve data - sources are ordered so that the fallbacks follow the main sources
        for source in self.sorted_sources:
            source.retrieve_data()
        # compute data
        for part in self.parts:
            self.context.set_current_part(part.name)
            for stage in part.stages:
                stage.compute_data()

    def get_output(self, as_dicts=False) -> dict:
        """
        Returns the report data in a format suitable for the frontend.
        """
        out = {}
        for part in self.parts:
            out[part.name] = {"stages": []}
            self.context.set_current_part(part.name)
            for stage in part.stages:
                stage_data = self.context.df_as_result_rows(stage.report_data_)
                if as_dicts:
                    stage_data = [row.as_dict() for row in stage_data]
                out[part.name]["stages"].append(
                    {
                        "name": stage.name,
                        "used_data_sources": stage.get_used_data_sources(),
                        "data": stage_data,
                    }
                )
        return out


class ReportPart:
    def __init__(
        self,
        report: Report,
        name: str,
        description: str,
        implementation_note: Optional[str] = None,
        explanation: Optional[str] = None,
    ):
        self.report = report
        self.name = name
        self.description = description
        self.explanation = explanation
        self.implementation_note = implementation_note
        self.stages: List["ReportPartStage"] = []

    @classmethod
    def from_dict(cls, definition: dict, report: "Report") -> "ReportPart":
        s = ReportPartSerializer(data=definition)
        s.is_valid(raise_exception=True)
        out = cls(
            report,
            s.validated_data["name"],
            s.validated_data.get("description", ""),
            implementation_note=s.validated_data.get("implementationNote"),
            explanation=s.validated_data.get("explanation"),
        )
        if not (stages := s.validated_data["stages"]):
            raise ValidationError("Report part must have at least one stage")
        for stage_def in stages:
            out.stages.append(ReportPartStage.from_dict(stage_def, report, out))
        return out


class ReportPartStage:
    def __init__(
        self,
        report: Report,
        part: ReportPart,
        id_: str,
        name: str,
        formula: str,
        description: Optional[str] = None,
    ):
        self.report = report
        self.part = part
        self.id = id_
        self.name = name
        self.description = description
        self.formula = formula
        self.parsed_formula = parse_formula(self.formula)
        self.report_data_: Optional[pd.DataFrame] = None

    @classmethod
    def from_dict(cls, definition: dict, report: Report, part: ReportPart) -> "ReportPartStage":
        s = ReportPartStageSerializer(data=definition)
        s.is_valid(raise_exception=True)
        return cls(
            report,
            part,
            s.validated_data["id"],
            s.validated_data["name"],
            s.validated_data["formula"],
            description=s.validated_data.get("description"),
        )

    def compute_data(self) -> pd.DataFrame:
        data = self.report.context.perform_computation(self.parsed_formula, source_name=self.name)
        self.report_data_ = data
        return data

    def get_used_data_sources(self) -> List[str]:
        return self.report.get_used_data_sources(self.part.name, self.parsed_formula)


class ReportDataSource:
    """
    Defines the report type which to use and what metric to extract. Optionally, it can also
    define filters to apply to the report.
    """

    def __init__(
        self,
        report: Report,
        id_: str,
        name: str,
        report_type: str,
        metric: Optional[str],
        filters: Optional[dict] = None,
        fallback_for: Optional[str] = None,
    ):
        self.report = report
        self.id = id_
        self.name = name
        self.report_type = report_type
        self.metric = metric
        self.filters = filters or {}
        self.fallback_for: str = fallback_for
        # the following are computed data filled in later
        self.fallback_for_report: ReportDataSource = None
        self.report_data_: Optional[pd.DataFrame] = None

    @classmethod
    def from_dict(cls, data: Dict, report: Report) -> "ReportDataSource":
        s = ReportDataSourceSerializer(data=data)
        s.is_valid(raise_exception=True)
        return cls(
            report,
            id_=s.validated_data["id"],
            name=s.validated_data["name"],
            report_type=s.validated_data["reportType"],
            metric=s.validated_data.get("metric"),
            filters=s.validated_data.get("filters"),
            fallback_for=s.validated_data.get("fallbackFor"),
        )

    def resolve_report_type(self) -> Optional[ReportType]:
        try:
            return ReportType.objects.get(short_name=self.report_type)
        except ReportType.DoesNotExist:
            return None

    def resolve_metric(self) -> Optional[Metric]:
        try:
            return Metric.objects.get(short_name=self.metric, source__isnull=True)
        except Metric.DoesNotExist:
            return None

    def slicer_result_to_df(self, result: [dict]) -> pd.DataFrame:
        pk_to_row = {row["pk"]: row for row in result}
        data = []
        for _i, pk in enumerate(self.report.context.sorted_primary_ids):
            row = pk_to_row.get(pk, {})
            data.append(
                [
                    self.report_type,
                    *[row.get(f"grp-{month}", 0) for month in self.report.context.covered_months],
                ]
            )
        out = pd.DataFrame(
            data,
            columns=["source_name", *self.report.context.covered_months],
            index=self.report.context.sorted_primary_ids,
        )
        out[self.report.total_col] = out[self.report.context.covered_months].sum(axis=1)
        return out

    def retrieve_data(self):
        """
        if `primary_ids` is provided, the returned data will be filtered to only include
        rows for the given primary ids. Otherwise, all rows will be returned.
        """
        if self.report_data_ is not None:
            return
        slicer = FlexibleDataSlicer(
            [self.report.primary_dimension], include_all_zero_rows=False, use_clickhouse=True
        )

        context = self.report.context
        rt_obj = self.resolve_report_type()
        metric_obj = self.resolve_metric() if self.metric else None
        if not context.primary_ids or not rt_obj or (self.metric and not metric_obj):
            # no data to return - we either do not have the data for the remaining primary ids
            # or the report type or metric does not exist
            self.report_data_ = self.slicer_result_to_df([])
            return
        slicer.add_filter(
            ExplicitDimensionFilter(self.report.primary_dimension, context.primary_ids)
        )
        slicer.add_filter(
            DateDimensionFilter("date", context.start_date, context.end_date), add_group=True
        )
        slicer.add_filter(ForeignKeyDimensionFilter("organization", [context.organization]))
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", [rt_obj.pk]))
        if self.metric:
            slicer.add_filter(ForeignKeyDimensionFilter("metric", [metric_obj.pk]))
        for dim_name, values in self.filters.items():
            if type(values) not in (list, tuple, set):
                values = [values]
            if dim_attr := rt_obj.dim_name_to_dim_attr(dim_name):
                dim_obj = rt_obj.dimension_by_attr_name(dim_attr)
                dim_values = DimensionText.objects.filter(
                    dimension=dim_obj, text__in=values
                ).values_list("pk", flat=True)
                slicer.add_filter(ExplicitDimensionFilter(dim_attr, dim_values))
            else:
                raise ValueError(f'Unknown dimension "{dim_name}" for rt "{self.report_type}"')
        # store the resulting data into a pandas DataFrame and remember the primary ids for
        # which we have data
        out = list(slicer.get_data())
        self.report_data_ = self.slicer_result_to_df(out)


@dataclass
class ResultRow:
    primary_pk: int
    primary_obj: Any
    monthly_data: dict
    total: int
    source_name: Optional[str] = None  # None means no data

    def as_dict(self) -> dict:
        return {
            "primary_pk": self.primary_pk,
            "primary_obj": self.primary_obj.short_name,
            "monthly_data": {
                key.strftime("%Y-%m"): value for key, value in self.monthly_data.items()
            },
            "total": self.total,
            "source_name": self.source_name,
        }
