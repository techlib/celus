import os

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.management.base import BaseCommand

from logs.logic.export_analytical import BACKENDS
from logs.models import ReportType


class Command(BaseCommand):
    help = "Exports analytical data with a chosen backend"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b",
            "--backend",
            help=f"Backend to use {*BACKENDS.keys(),} (default: csv)",
            default="csv",
            dest="backend",
        )
        parser.add_argument(
            "-o",
            "--output",
            help="Name of the file to export to (if using a file backend)",
            default=None,
        )
        parser.add_argument(
            "report_type",
            help="ID or short name of the report type to export (leave empty to print available)",
            default=None,
            nargs="?",
        )

    def print_available_report_types(self):
        self.stderr.style_func = None
        self.stderr.write("No report type chosen, here is the table:")
        header = ("ID", "Short Name", "Name")
        table = [header, ["=" * len(s) for s in header]]
        columns = [len(s) for s in header]
        for rt in ReportType.objects.order_by("id"):
            table.append((str(rt.id), rt.short_name, rt.name))
            for col in range(len(header)):
                columns[col] = max(columns[col], len(table[-1][col]))
        for col in table:
            self.stderr.write(
                f"{col[0]: >{columns[0]}}  "
                f"{col[1]: <{columns[1]}}  "
                f"{col[2]: <{columns[2]}}  "
            )
        self.stderr.style_func = self.style.ERROR

    def handle(self, *args, **options):
        rt = options["report_type"]
        if rt is None:
            self.print_available_report_types()
            return
        path = options["output"]
        if path is not None:
            path = os.path.abspath(path)

        report = None
        try:
            rt = int(rt)
        except ValueError:
            try:
                report = ReportType.objects.get(short_name__iexact=rt)
            except ObjectDoesNotExist:
                self.stderr.write(
                    self.style.ERROR("Cannot find specified ReportType by its short name")
                )
            except MultipleObjectsReturned:
                self.stderr.write(
                    self.style.ERROR("There are multiple ReportTypes with this name! Use the ID")
                )
        else:
            try:
                report = ReportType.objects.get(id=rt)
            except ObjectDoesNotExist:
                self.stderr.write(self.style.ERROR("Cannot find specified ReportType by its ID"))

        if report is None:
            self.print_available_report_types()
            return

        try:
            b = BACKENDS[options["backend"]](
                stdout=self.stdout,
                stderr=self.stderr,
                style=self.style,
                path=path,
                report_type=report,
            )
        except KeyError:
            self.stderr.write(
                self.style.ERROR(
                    f"Not a known backend ({options['backend']}) - {*BACKENDS.keys(),}"
                )
            )
        else:
            b.export()
