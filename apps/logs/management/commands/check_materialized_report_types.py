import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.db.utils import IntegrityError

from logs.logic.materialized_reports import sync_materialized_reports
from logs.models import ReportMaterializationSpec, ReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Checks that a standard set of materialized report types is present and set up correctly"

    mat_rts = [
        {"name": "Interest without item", "base_rt": "interest", "exclude": ["item"]},
        {
            "name": "Interest without title and item",
            "base_rt": "interest",
            "exclude": ["item", "target"],
        },
        {"name": "C5 TR without title", "base_rt": "TR", "exclude": ["target", "item"]},
        {
            "name": "C5 TR without title, YOP, Publisher and COUNTER Platform",
            "base_rt": "TR",
            "exclude": ["target", "item", "YOP", "Publisher", "Platform"],
        },
        {"name": "C51 TR without title", "base_rt": "TR51", "exclude": ["target", "item"]},
        {
            "name": "C51 TR without title, YOP, Publisher and COUNTER Platform",
            "base_rt": "TR51",
            "exclude": ["target", "item", "YOP", "Publisher", "Platform"],
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        fix_it = options["fix_it"]

        seen_spec_ids = set()
        new_mat_rts = []

        for mat_rt in self.mat_rts:
            base_rt: ReportType = ReportType.objects.get(short_name=mat_rt["base_rt"])
            # find to which dimensions the exclude list refers - if not explicit, use the name
            clean_exclude = [base_rt.dim_name_to_dim_attr(exc) or exc for exc in mat_rt["exclude"]]
            # we look for the spec by its definition, rather than by its name to avoid duplicates
            keep_dict = self.exclude_to_keeps(clean_exclude)
            try:
                spec = ReportMaterializationSpec.objects.get(base_report_type=base_rt, **keep_dict)
            except ReportMaterializationSpec.DoesNotExist:
                # create the missing spec
                spec = ReportMaterializationSpec.objects.create(
                    name=mat_rt["name"],
                    base_report_type=ReportType.objects.get(short_name=mat_rt["base_rt"]),
                    **keep_dict,
                )
                logger.info("Created materialization spec: %s", spec)
                stats["created_spec"] += 1
                if rt := self.create_rt(spec):
                    new_mat_rts.append(rt)
            else:
                if spec.name != mat_rt["name"]:
                    logger.info("Spec name mismatch: '%s' != '%s'", spec.name, mat_rt["name"])
                    stats["name_fixed"] += 1
                    spec.name = mat_rt["name"]
                    spec.save()
                else:
                    logger.debug("Found existing spec: %s", spec)
                    stats["ok"] += 1
                # check associated report type - we added a constraint to the model to ensure there
                # cannot be more than one report type per spec
                try:
                    rt = spec.reporttype
                except ReportType.DoesNotExist:
                    logger.warning("No report type for spec: %s", spec)
                    stats["created_rts"] += 1
                    if rt := self.create_rt(spec):
                        new_mat_rts.append(rt)
                else:
                    # check if the report type name matches the spec name
                    if rt.short_name != spec.name:
                        logger.info("RT name mismatch: '%s' != '%s'", rt.short_name, spec.name)
                        stats["rt_name_fixed"] += 1
                        rt.short_name = spec.name
                        rt.save()
            seen_spec_ids.add(spec.pk)

        # find specs which are not in the standard set
        for spec in ReportMaterializationSpec.objects.exclude(pk__in=seen_spec_ids):
            logger.warning("Extra spec: %s", spec)
            stats["extra_spec"] += 1
            logger.info("Delete stats: count: %d, details: %s", *spec.delete())

        logger.info("Stats: %s", stats)

        if not fix_it:
            raise ValueError("Dry run. To actually fix the issues, use --fix-it")

        # compute data for new report types
        if new_mat_rts:
            logger.info("Syncing data for new materialized reports, this may take a while")
            sync_materialized_reports(
                ReportType.objects.filter(pk__in=[rt.pk for rt in new_mat_rts])
            )

    @classmethod
    def exclude_to_keeps(cls, exclude: [str]) -> dict:
        """
        Convert the `exclude` list to a dict which can be passed to
        `ReportMaterializationSpec.objects.filter` to find the corresponding
        `ReportMaterializationSpec` objects.
        """
        out = {}
        for fields in ReportMaterializationSpec._meta.get_fields():
            if fields.name.startswith("keep_"):
                out[fields.name] = True
        for exc in exclude:
            fname = f"keep_{exc}"
            if fname in out:
                out[fname] = False
            else:
                raise ValueError(f"Unknown exclude field: {exc}")
        return out

    @atomic
    def create_rt(self, spec: ReportMaterializationSpec):
        # without atomic, we could not ignore the IntegrityError
        try:
            return ReportType.objects.create(
                materialization_spec=spec, short_name=spec.name, name=spec.name
            )
        except IntegrityError as e:
            # this can happen if the short name is already taken, but has different
            # spec - we just log it and continue, the user has to fix it manually
            logger.warning("Could not create RT: %s (%s)", spec.name, e)
            logger.warning("You need to fix this manually")
