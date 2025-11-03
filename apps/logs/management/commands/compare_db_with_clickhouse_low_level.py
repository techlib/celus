import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import F
from organizations.models import Organization
from publications.models import Platform, Title

from logs.cubes import ch_backend
from logs.logic.export import CSVExport
from logs.models import AccessLog, DimensionText, Metric, ReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Does a record-by-record comparison of the DB and CH. It takes quite some time and is thus "
        "only suitable for debugging off of production. But it may come handy, so I am preserving "
        "it for future generations ;)"
    )

    def handle(self, *args, **options):
        dt_remap = {dt.pk: dt.text for dt in DimensionText.objects.all()}
        id_remaps = {
            "organization_id": {org.pk: org.name for org in Organization.objects.all()},
            "platform_id": {pl.pk: pl.name for pl in Platform.objects.all()},
            "metric_id": {m.pk: m.short_name for m in Metric.objects.all()},
            "report_type_id": {rt.pk: rt.short_name for rt in ReportType.objects.all()},
        }
        target_remap = {}

        def al_info(rec):
            dim_info = []
            for i, dim in enumerate(rec.report_type.dimensions_sorted):
                dim_val = getattr(rec, f"dim{i + 1}")
                dim_info.append(f"{dim.name}='{dt_remap.get(dim_val, dim_val)}'")
            if rec.target_id not in target_remap:
                target_remap[rec.target_id] = Title.objects.get(pk=rec.target_id).name
            base = [f"ib={rec.import_batch_id}", f"t={target_remap[rec.target_id]}"]
            for attr, remap in id_remaps.items():
                if getattr(rec, attr) in remap:
                    base.append(f"{attr[0]}={remap.get(getattr(rec, attr), getattr(rec, attr))}")
            base.append(f"v={rec.value}")
            return ", ".join(base + dim_info)

        stats = Counter()
        ch_missing_ibs = Counter()

        # we need to split the work by platform because Clickhouse would otherwise run out of memory
        # on large databases (like K1)
        for platform in Platform.objects.all():
            # the CSV exporter has functionality which comes handy here because it creates
            # queries which contain all the "key" dimensions of accesslogs, which is exactly
            # what we need to compare the records
            exporter = CSVExport({"platform_id": platform.pk}, use_clickhouse=True)
            logger.info("CH count: %d", exporter.record_count)
            dqs = exporter.create_queryset()
            cqs = exporter.create_clickhouse_query()
            fields = [g.name for g in cqs.groups]
            dqs = (
                dqs.order_by(*[F(f).asc(nulls_first=True) for f in fields])
                .values_list(*fields)
                .iterator()
            )
            # ch uses 0 instead of None in its data
            dgen = (tuple(f if f is not None else 0 for f in r) for r in dqs)
            cqs = cqs.order_by(*fields)
            cgen = (
                tuple(getattr(r, f) for f in fields)
                for r in ch_backend.get_records(cqs, streaming=True)
            )
            drec = next(dgen, None)
            crec = next(cgen, None)
            while drec is not None and crec is not None:
                if drec == crec:
                    stats["ok"] += 1
                    drec = next(dgen, None)
                    crec = next(cgen, None)
                elif drec < crec:
                    stats["ch missing"] += 1
                    logger.info("CH missing: %s", drec)
                    seen_ibs_ids = set()
                    for al in AccessLog.objects.filter(
                        **{
                            k if v != 0 else f"{k}__isnull": v or True
                            for k, v in zip(fields, drec, strict=True)
                        }
                    ):
                        logger.info("  %s", al_info(al))
                        ch_missing_ibs[al.import_batch_id] += 1
                        seen_ibs_ids.add(al.import_batch_id)
                    if len(seen_ibs_ids) > 1:
                        logger.warning("Multiple ibs ids found: %s", seen_ibs_ids)
                    drec = next(dgen, None)
                elif drec > crec:
                    stats["db missing"] += 1
                    logger.info("DB missing: %s", crec)
                    crec = next(cgen, None)
                if sum(stats.values()) % 100000 == 0:
                    print(stats)

            while drec is not None:
                stats["ch missing"] += 1
                logger.info("CH missing: %s", drec)
                drec = next(dgen, None)
            while crec is not None:
                stats["db missing"] += 1
                logger.info("DB missing: %s", crec)
                crec = next(cgen, None)

            print(stats)
            print("Missing ibs:", ch_missing_ibs)

        print(stats)
        print("Missing ibs:", ch_missing_ibs)
