import typing
from datetime import date
from functools import reduce
from pathlib import Path

import logs
from celus_nibbler import NibblerError, Poop, eat
from celus_nigiri import CounterRecord
from logs.exceptions import NibblerErrors
from publications.models import Platform

from ..models import NibblerOutput


def is_success(nibbler_output: NibblerOutput) -> bool:
    """Returns true if nibbler was able to parse at least one sheet"""
    return any(isinstance(e, Poop) for e in nibbler_output)


def get_errors(nibbler_output: NibblerOutput) -> typing.List[NibblerError]:
    return [e for e in nibbler_output if isinstance(e, NibblerError)]


def output_to_poops(poops_or_errors: NibblerOutput) -> typing.List[Poop]:
    res = [e for e in poops_or_errors if isinstance(e, Poop)]
    if not res:
        raise NibblerErrors(get_errors(poops_or_errors))

    return res


def celus_format_poops(
    path: Path,
    default_metric: 'logs.models.Metric',
    report_type: 'logs.models.ReportType',
    platform: Platform,
) -> typing.List[Poop]:
    # Delay nibbler imports to speed up startup
    from celus_nibbler.definitions.celus_format import (
        CelusFormatAreaDefinition,
        CelusFormatParserDefinition,
        DataFormatDefinition,
    )
    from celus_nibbler.parsers.base import IDS
    from celus_nibbler.sources import ExtractParams

    parser_area = CelusFormatAreaDefinition(
        title_column_names=['title', 'Title', 'source', 'Source'],
        organization_column_names=['Organization', 'organization', 'org', 'Org'],
        metric_column_names=['metric', 'Metric'],
        default_metric=default_metric.short_name,
        title_ids_mapping={e: e for e in IDS},
        dimension_mapping={e: e for e in report_type.dimension_short_names},
        value_extract_params=ExtractParams(default=0),
    )

    parser = CelusFormatParserDefinition(
        parser_name="Tabular",
        data_format=DataFormatDefinition(name=report_type.short_name, id=report_type.ext_id),
        areas=[parser_area],
        platforms=[platform.short_name],
    ).make_parser()

    return output_to_poops(
        eat(path, platform.short_name, [f"^{parser.name}$"], dynamic_parsers=[parser])
    )


def counter_format_poops(path: Path, parser_name: str, platform: Platform) -> typing.List[Poop]:
    return output_to_poops(
        eat(
            path,
            platform.short_name,
            parsers=[parser_name],
            check_platform=False,
            use_heuristics=True,
        )
    )


def get_records_from_nibbler_output(
    nibbler_output: NibblerOutput,
) -> typing.Generator[CounterRecord, None, None]:
    for poop in [e for e in nibbler_output if isinstance(e, Poop)]:
        for _idx, record in poop.records_basic():
            yield record


def get_months_from_nibbler_output(nibbler_output: NibblerOutput) -> typing.Set[date]:
    def unique_flatten(list_of_lists):
        return reduce(lambda x, y: x | set(y), list_of_lists, set())

    return unique_flatten(
        unique_flatten(e.get_months()) for e in nibbler_output if isinstance(e, Poop)
    )
