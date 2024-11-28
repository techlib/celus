import logging
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.models import Dimension, ReportType

from charts.models import COUNTER_REPORT_DATA_VIEWS, DimensionFilter, ReportDataView

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """\
Checks that basic COUNTER ReportDataViews are properly defined (with correct names, filters, ...)
"""

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        fix_it = options["fix_it"]

        report_type_names_map = {e.short_name: e for e in ReportType.objects.filter(source=None)}

        if settings.ENABLE_ITEMS:
            crdvs = COUNTER_REPORT_DATA_VIEWS
        else:
            crdvs = [
                e
                for e in COUNTER_REPORT_DATA_VIEWS
                if e.short_name not in ["IR", "IR_A1", "IR_M1"]
                or e.base_report_type_short_name == "IR_M1"
            ]

        for crdv in crdvs:
            # check the report-data-view
            if rt := report_type_names_map.get(crdv.base_report_type_short_name):
                pass
            else:
                logger.warning("Missing ReportType '%s'", crdv.base_report_type_short_name)
                stats["missing_report_type"] += 1
                continue

            rdvs = list(
                ReportDataView.objects.filter(base_report_type=rt, short_name=crdv.short_name)
            )

            if len(rdvs) > 1:
                logger.error(
                    "Multiple ReportDataView sets detected (%s, %s) -> skipping",
                    rdvs[0].base_report_type.short_name,
                    rdvs[0].short_name,
                )
                continue

            if rdvs:
                rdv = rdvs[0]
                for attr in [
                    "name",
                    "desc",
                    "position",
                    "is_standard_view",
                    "metric_allowed_values",
                ]:
                    stored = getattr(rdv, attr)
                    defined = getattr(crdv, attr)
                    if stored != defined:
                        logger.warning(
                            'RDV %s mismatch (%s): "%s" != "%s"',
                            attr,
                            rt.short_name,
                            stored,
                            defined,
                        )
                        if fix_it:
                            setattr(rdv, attr, getattr(crdv, attr))
                            rdv.save()
                            stats[f"fixed_rdv_{attr}"] += 1

            else:
                logger.warning("Missing data view for: %s", rt.short_name)
                stats["missing_data_view"] += 1
                if fix_it:
                    rdv = ReportDataView.objects.create(
                        base_report_type=rt,
                        name=crdv.name,
                        desc=crdv.desc,
                        short_name=crdv.short_name,
                        is_standard_view=crdv.is_standard_view,
                        metric_allowed_values=crdv.metric_allowed_values,
                        position=crdv.position,
                    )
                    stats["created_data_view"] += 1
                else:
                    continue

            rdv_filters = {
                e.dimension.short_name: e.allowed_values
                for e in rdv.dimension_filters.select_related("dimension").all()
            }
            crdv_filters = {e.dimension: e.allowed_values for e in crdv.filters}

            if rdv_filters != crdv_filters:
                logger.warning(
                    "ReportDataView (%s) filters mismatch: %s != %s",
                    rdv.short_name,
                    rdv_filters,
                    crdv_filters,
                )
                if fix_it:
                    dimension_filters = []
                    for fltr in crdv.filters:
                        dimension, created = Dimension.objects.get_or_create(
                            short_name=fltr.dimension
                        )
                        if created:
                            logger.warning("Dimension created: %s", fltr.dimension)
                            stats["created_dimension"] += 1

                        dimension_filters.append(
                            DimensionFilter(dimension=dimension, allowed_values=fltr.allowed_values)
                        )

                    rdv.dimension_filters.all().delete()
                    rdv.dimension_filters.set(dimension_filters, bulk=False)
                    stats["dimension_filters_updated"] += 1

        if not fix_it:
            logger.warning("No changes were made. Use `--fix-it` to perform the changes")

        existing = {
            (e.base_report_type.short_name, e.short_name): e.pk
            for e in ReportDataView.objects.filter(
                base_report_type__counterreporttype__isnull=False
            )
        }
        in_definition = {(e.base_report_type_short_name, e.short_name) for e in crdvs}
        extras = set(existing.keys()) - in_definition
        if extras:
            logger.warning("Extra COUNTER ReportDataViews detected!")
            for extra in extras:
                logger.warning("%s - pk=%d", extra, existing[extra])

        print("Stats:", stats)
