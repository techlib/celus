from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Q
from organizations.models import Organization
from publications.models import Platform

from logs.logic.export_analytical import BACKENDS
from logs.models import ReportType


def print_table(data: List, columns: List[str], outstream):
    header = [c.replace("_", " ").title() for c in columns]
    table = [header, ["=" * len(s) for s in header]]
    column_widths = [len(s) for s in header]
    for row in data:
        table.append([str(getattr(row, col)) for col in columns])
        for i, _col in enumerate(columns):
            column_widths[i] = max(column_widths[i], len(table[-1][i]))
    for col in table:
        for i in range(len(col)):
            outstream.write(f"{col[i]: <{column_widths[i]}}  ", ending="")
        outstream.write("\n")


class Command(BaseCommand):
    help = "Exports analytical data with a chosen backend"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b",
            "--backend",
            help=f"Backend to use {(*BACKENDS.keys(),)} (default: csv)",
            default="csv",
            dest="backend",
        )
        parser.add_argument(
            "-o",
            "--output",
            help="Where to export to. Either a file path or an URL, depending on the backend. "
            "Some backends support direct compression when they detect .gz/.zst in the filename.",
            default=None,
        )
        parser.add_argument(
            "-f",
            "--force",
            help="Force overwrite the file if it already exists",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "-t", "--tags", help="Add Title tags to the output", default=False, action="store_true"
        )
        parser.add_argument(
            "--no-internal-tags",
            help="Do not include internal tags in the output",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "report_type",
            help="ID, name or short name of the report type to export",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "--organization",
            help="ID, name or short name of the organization to export (leave empty to export all)",
            default=None,
        )
        parser.add_argument(
            "--platform",
            help="ID, name or short name of the platform to export (leave empty to export all)",
            default=None,
        )

    def get(self, key, arg):
        model = {"report_type": ReportType, "organization": Organization, "platform": Platform}[key]
        try:
            return model.objects.get(id=int(arg))
        except (ValueError, ObjectDoesNotExist):
            pass

        finds = model.objects.filter(Q(name=arg) | Q(short_name=arg)).distinct()
        if finds.count() == 1:
            return finds.first()

        if finds.count() == 0:
            self.stderr.write(f"No '{arg}' {model} found")
        else:
            self.stderr.write(f"(Short) name '{arg}' {model} is not unique")

        print_table(model.objects.order_by("id").all(), ["id", "short_name", "name"], self.stderr)
        return None

    def handle(self, *args, **options):
        output = options["output"]

        for key in ["report_type", "organization", "platform"]:
            if key == "report_type" or options[key]:
                if find := self.get(key, options[key]):
                    options[key] = find
                else:
                    return

        try:
            b = BACKENDS[options["backend"]]
        except KeyError:
            self.stderr.write(
                self.style.ERROR(
                    f"Not a known backend ({options['backend']}) - {(*BACKENDS.keys(),)}"
                )
            )
            return

        try:
            b(
                stderr=self.stderr,
                style=self.style,
                output=output,
                report_type=options["report_type"],
                organization=options["organization"],
                platform=options["platform"],
                force_overwrite=options["force"],
                tags=options["tags"],
                no_internal_tags=options["no_internal_tags"],
            ).export()
        except KeyboardInterrupt:
            self.stderr.write("\nCancelled by user")
