import logging
from collections import Counter
from typing import List

from celus_nibbler.parsers import get_parsers
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from sushi.models import COUNTER_REPORTS, CounterReportType

from logs.models import Dimension, ReportType, ReportTypeToDimension

logger = logging.getLogger(__name__)


def make_dimension_c51_based_on_c5(rt5: ReportType, rt51: ReportType, dimensions: List[str]):
    # We know that there are no textra dimesions in C5.1
    # only Section_Type dimesion was removed for TR in C5.1
    # so dims_to_create should cover all dimensions of rt51
    # We just need to keep the order here.
    dims_to_create = [
        e
        for e in rt5.reporttypetodimension_set.order_by("position").values_list(
            "dimension__short_name", flat=True
        )
        if e in dimensions
    ]

    for position, dimension in enumerate(dims_to_create):
        # dimension should be already created for C5 report
        dim = Dimension.objects.get(short_name=dimension)
        ReportTypeToDimension.objects.create(report_type=rt51, dimension=dim, position=position)


class Command(BaseCommand):
    help = """\
Checks that basic COUNTER defined ReportTypes, CounterReportTypes, ReportDataViews and
ChartDefinitions are properly defined (with correct dimensions, names, filters, ...)
"""

    dim_name_remap = {
        "Platform": {"en": "Platform in COUNTER data", "cs": "Platforma v COUNTER datech"}
    }

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        fix_it = options["fix_it"]

        reports_to_check = list(COUNTER_REPORTS)
        if not settings.ENABLE_ITEMS:
            reports_to_check = [r for r in reports_to_check if r[2] != "IR"]

        for version, rt_short_name, crt_code, name in reports_to_check:
            parser_key = rf"static\.counter{version}\.{crt_code}\.Tabular"
            if parsers := get_parsers([parser_key]):
                parser = parsers[0][1]
                dimensions = [e[0] for e in parser.areas[0].DIMENSION_NAMES_MAP]
            else:
                logger.error(
                    "Can't find parser '%s' for rt '%s' in nibbler", parser_key, rt_short_name
                )
                continue

            # Update ReportTypes
            try:
                rt = ReportType.objects.get(short_name=rt_short_name, source__isnull=True)
            except ReportType.DoesNotExist:
                print("Missing RT:", rt_short_name)
                stats["missing_rt"] += 1
                if fix_it:
                    rt = ReportType.objects.create(short_name=rt_short_name, name=name, source=None)
                    if version == 51:
                        if rt5 := ReportType.objects.filter(short_name=rt_short_name[:-2]).first():
                            make_dimension_c51_based_on_c5(rt5, rt, dimensions)
                else:
                    stats["missing_crt"] += 1
                    continue
            else:
                for code, _lang in settings.LANGUAGES:
                    if (orig_name := getattr(rt, f"name_{code}")) != name:
                        print(
                            f"RT name mismatch in lang={code} - ({rt_short_name}): "
                            f'"{orig_name}" != "{name}"'
                        )
                        stats["rt_name_mismatch"] += 1
                        if fix_it:
                            setattr(rt, f"name_{code}", name)
                            rt.save()
                            stats["fixed_rt_name"] += 1

            # check ReportType dimensions
            dims = set(dimensions)
            rt_dims = set(rt.dimension_short_names)
            if rt_dims != dims:
                fixable = rt_dims.issubset(dims)
                print("Mismatch:", rt_short_name, "fixable" if fixable else "CANNNOT FIX")
                print("   ", rt.dimension_short_names)
                print("   ", dimensions)
                stats[f'mismatch_{"fixable" if fixable else "unfixable"}'] += 1
                if fixable and fix_it:
                    pos = len(rt.dimension_short_names)
                    for i, dim_name in enumerate([e for e in dimensions if e not in rt_dims]):
                        if remap_data := self.dim_name_remap.get(dim_name):
                            def_names = {
                                f"name_{lang}": value for lang, value in remap_data.items()
                            }
                        else:
                            def_names = {"name": dim_name}
                        dim, _ = Dimension.objects.get_or_create(
                            short_name=dim_name, defaults=def_names
                        )
                        ReportTypeToDimension.objects.create(
                            report_type=rt, dimension=dim, position=pos + i
                        )
                    assert {dim.short_name for dim in rt.dimensions.all()} == dims
                    print("  Fixed!")
            else:
                print("dims OK:", rt_short_name)
                stats["dims_ok"] += 1

            # Update CounterReportTypes
            try:
                crt = rt.counterreporttype
                if crt.name != name:
                    print(f'CRT name mismatch ({crt_code}): "{crt.name}" != "{name}"')
                    stats["crt_name_mismatch"] += 1
                    if fix_it:
                        crt.name = name
                        crt.save()
                        stats["fixed_crt_name"] += 1
            except CounterReportType.DoesNotExist:
                stats["missing_crt"] += 1
                if fix_it:
                    CounterReportType.objects.create(
                        counter_version=version, code=crt_code, report_type=rt, name=name
                    )

        print("Stats:", stats)
