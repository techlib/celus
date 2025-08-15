import logging
from argparse import FileType

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from sushi.logic.data_import import Perform, import_sushi_credentials_from_xlsx

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load SUSHI credentials from a .xlsx file"

    def add_arguments(self, parser):
        # we use a named argument because it is then possible to pass an open file from python
        # code instead of a file path - this makes it easier to use this command from the API
        # (call_command runs *args through argparse, while **kwargs are passed directly:
        # https://docs.djangoproject.com/en/3.2/ref/django-admin/#django.core.management.call_command
        # )
        # for the same reason, the argument is not required - otherwise argparse would complain
        parser.add_argument("-f", dest="file", help=".xlsx file to import", type=FileType("rb"))
        parser.add_argument(
            "--single-org",
            dest="single_org",
            type=str,
            default=None,
            metavar="_ORG_ID_",  # this tells the UI to show selector for organizations
            help="pk, name_en or short_name_en of the organization for which you intend to import "
            "credentials",
        )
        parser.add_argument(
            "--parse-sheet-no",
            dest="parse_sheet_no",
            type=int,
            default=2,
            help="index of the sheet in which the credentials are stored",
        )
        parser.add_argument(
            "--update-unverified",
            dest="update_unverified",
            action="store_true",
            help="update unverified credentials",
        )
        parser.add_argument(
            "--update-all", dest="update_all", action="store_true", help="update all credentials"
        )
        parser.add_argument(
            "--log-diff-off",
            dest="log_diff_off",
            action="store_true",
            default=False,
            help="turn off logging of differences between old and new",
        )
        parser.add_argument(
            "--log-trivial",
            dest="log_trivial",
            action="store_true",
            default=False,
            help="log trivial messages - empty or unchanged rows",
        )
        parser.add_argument(
            "--harvest-months",
            dest="harvest_months",
            type=int,
            default=None,
            help="Number of months to harvest for new credentials (0 = no auto-harvesting)",
        )
        parser.add_argument("--do-it", dest="doit", action="store_true")

    @atomic
    def handle(self, *args, **options):
        update_credentials = (
            Perform.UPDATE_ALL
            if options["update_all"]
            else Perform.UPDATE_NOT_VERIFIED
            if options["update_unverified"]
            else Perform.UPDATE_NONE
        )

        stats = import_sushi_credentials_from_xlsx(
            options["file"],
            sheet_no=options["parse_sheet_no"],
            single_org=options["single_org"],
            log_diff=not options["log_diff_off"],
            log_trivial=options["log_trivial"],
            update_credentials=update_credentials,
            reversion_comment='Updated/created by command line script "load_sushi_credentials"',
            harvest_months=options["harvest_months"],
        )
        self.stderr.write(self.style.WARNING(f"\nImport stats: {stats}"))
        if not options["doit"]:
            raise ValueError("preventing db commit, use --do-it to really do it ;)")
