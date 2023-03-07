import typing
from pathlib import Path

import logs
from celus_nibbler import Poop, eat
from celus_nibbler.definitions.celus_format import (
    CelusFormatAreaDefinition,
    CelusFormatParserDefinition,
    DataFormatDefinition,
)
from celus_nibbler.parsers.base import IDS
from celus_nibbler.sources import ExtractParams
from celus_nigiri import CounterRecord
from logs.exceptions import NibblerErrors
from publications.models import Platform

from ..models import get_errors


def celus_format_to_records(
    path: Path,
    default_metric: 'logs.models.Metric',
    report_type: 'logs.models.ReportType',
    platform: Platform,
) -> typing.Generator[CounterRecord, None, None]:
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

    poops = eat(path, platform.short_name, [f"^{parser.name}$"], dynamic_parsers=[parser])
    if not any(isinstance(poop, Poop) for poop in poops):
        raise NibblerErrors(get_errors(poops))

    for poop in (p for p in poops if isinstance(p, Poop)):
        yield from poop.records()


def counter_format_to_records(path: Path, parser_name: str, platform: Platform):
    poops = eat(
        path, platform.short_name, parsers=[parser_name], check_platform=False, use_heuristics=True
    )

    if not any(isinstance(poop, Poop) for poop in poops):
        raise NibblerErrors(get_errors(poops))

    for poop in (p for p in poops if isinstance(p, Poop)):
        yield from poop.records()
