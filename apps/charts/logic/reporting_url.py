import typing

from core.logic.serialization import b64json
from logs.models import DIMENSION_COUNT, DimensionText, Metric, ReportType
from publications.models import Title
from tags.models import AccessibleBy, Tag, TagClass, TagScope, TitleTag

from charts.models import ReportDataView


def _convert_to_explicit_dimension(report_type: ReportType, name: str) -> str:
    # Conversion to explicit dimension "dimX" if it is possible
    # E.g. ReportType to dim1

    # Note that it is assumed here that dimension names don't clash with
    # Standard rows e.g. No dimension is named "date"
    return report_type.dim_name_to_dim_attr(name) or name


def make_url_params(
    report_view: typing.Union[ReportDataView, ReportType], params: dict
) -> typing.Optional[dict]:
    filters = {}
    if isinstance(report_view, ReportType):
        report_type = report_view
        dimension_filters = {}
        allowed_metrics = list(report_type.controlled_metrics.values_list("pk", flat=True)) or []
    else:
        report_type = report_view.base_report_type
        # dimension filters # in "dimX": [1,2,3] format
        dimension_filters = {
            report_type.dim_name_to_dim_attr(dim_name): list(
                DimensionText.objects.filter(dimension=dim_id, text__in=v).values_list(
                    "pk", flat=True
                )
            )
            for dim_id, dim_name, v in report_view.dimension_filters.select_related(
                "dimension"
            ).values_list("dimension__pk", "dimension__short_name", "allowed_values")
        }
        allowed_metrics = list(
            Metric.objects.filter(short_name__in=report_view.metric_allowed_values).values_list(
                "pk", flat=True
            )
        )
    filters["report_type"] = report_type.pk

    if organization := params.pop("organization", None):
        filters["organization"] = [organization]

    if platform := params.pop("platform", None):
        filters["platform"] = [platform]

    if allowed_metrics:
        filters["metric"] = allowed_metrics

    # process extra metric filter
    if metric := params.pop("metric", None):
        if allowed_metrics:
            filters["metric"] = list({metric} & set(filters["metric"]))
        else:
            filters["metric"] = [metric]

    # fill in start_date and end_date when present
    dr = {}
    if start_date := params.get("start_date"):
        dr["start"] = start_date
    if end_date := params.get("end_date"):
        dr["end"] = end_date

    title_tag = None
    if title_pk := params.pop("title", None):
        if title := Title.objects.filter(pk=title_pk).first():
            tag_class, _ = TagClass.objects.get_or_create(
                internal=True,
                name="Title Filter",
                scope=TagScope.TITLE,
                owner=None,
                owner_org=None,
                exclusive=True,
                can_modify=AccessibleBy.SYSTEM,
                can_create_tags=AccessibleBy.SYSTEM,
                default_tag_can_see=AccessibleBy.EVERYBODY,
                default_tag_can_assign=AccessibleBy.SYSTEM,
            )
            # Reporting is not aware of titles
            # we need to create a tag here and filter accordingly
            title_tag, _ = Tag.objects.get_or_create(
                name=f"ID_{title.pk}",
                tag_class=tag_class,
                owner=None,
                owner_org=None,
                can_see=AccessibleBy.EVERYBODY,
                can_assign=AccessibleBy.SYSTEM,
            )
            TitleTag.objects.get_or_create(target=title, tag=title_tag)
            filters["target"] = title_tag.id

    def encode(value: typing.Union[int, str, list, dict]) -> str:
        if not isinstance(value, (list, dict)):
            value = [value]
        return "--" + b64json(value)

    # dv b'{"dim1": [2], "dim2": [], ...}'
    dv = {
        f"dim{i + 1}": dimension_filters.get(f"dim{i + 1}", []) for i in range(0, DIMENSION_COUNT)
    }

    if secondary_dimension := params.get("secondary_dimension"):
        secondary_dimension = [_convert_to_explicit_dimension(report_type, secondary_dimension)]
    else:
        secondary_dimension = ["platform"]

    return {
        "rt": encode(report_type.pk),
        "r": _convert_to_explicit_dimension(report_type, params["primary_dimension"]),
        "c": encode(secondary_dimension),
        "dr": encode(dr) if start_date or end_date else "",
        "m": encode(filters["metric"]) if "metric" in filters else "",
        "p": encode(filters["platform"]) if "platform" in filters else "",
        "org": encode(filters["organization"]) if "organization" in filters else "",
        "dv": encode(dv) if dv else "",
        "f": encode(list(filters.keys()) + list(dimension_filters.keys())),
        "tt": encode(filters["target"]) if "target" in filters else "",
    }
