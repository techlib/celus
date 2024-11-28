import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from charts.models import ReportDataView, ReportViewToChartType

logger = logging.getLogger(__name__)


def fill_missing_charts(
    rdv_from: ReportDataView, rdv_into: ReportDataView, fix_it: bool
) -> Counter:
    stats = Counter()
    from_mapping = {
        e.chart_definition: e for e in rdv_from.reportviewtocharttype_set.order_by("position")
    }
    into_mapping = {e.chart_definition: e for e in rdv_into.reportviewtocharttype_set.all()}
    for chart_def in from_mapping:
        if chart_def not in into_mapping:
            stats["not_mapped"] += 1
            logger.warning(
                "Missing mapping for ReportDataView '%s' to ChartDefinition '%s'",
                from_mapping[chart_def],
                chart_def,
            )

            if fix_it:
                # Position has to be unique together with ReportDataView (db constraint)
                # the following code will find first unused position
                position = from_mapping[chart_def].position
                while position in [e.position for e in into_mapping.values()]:
                    position += 1

                into_mapping[chart_def] = ReportViewToChartType.objects.create(
                    chart_definition=chart_def, report_data_view=rdv_into, position=position
                )
                stats["mapping_created"] += 1
                logger.warning(
                    "Mapping for ReportDataView '%s' to ChartDefinition '%s' created",
                    from_mapping[chart_def],
                    chart_def,
                )
    return stats


class Command(BaseCommand):
    help = """\
    Creates chart link for C5.1 ReportDataViews based on C5 ReportDataViews
"""

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        fix_it = options["fix_it"]
        stats = Counter()

        c5_rdvs_map = {
            e.short_name: e
            for e in ReportDataView.objects.filter(
                base_report_type__counterreporttype__counter_version=5
            ).prefetch_related("reportviewtocharttype_set")
        }
        c51_rdvs = ReportDataView.objects.filter(
            base_report_type__counterreporttype__counter_version=51
        ).prefetch_related("reportviewtocharttype_set")

        for c51_rdv in c51_rdvs:
            if c5_rdv := c5_rdvs_map.get(c51_rdv.short_name):
                stats.update(fill_missing_charts(c5_rdv, c51_rdv, fix_it))

        if not fix_it:
            logger.warning("No changes were made. Use `--fix-it` to perform the changes")

        print(stats)
