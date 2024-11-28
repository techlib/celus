import json
import logging
from copy import deepcopy
from datetime import date, timedelta

from celus_nigiri.client import CounterVersion
from django.core.management.base import BaseCommand
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pulls data from a Sushi server and displays some simple stats"

    def add_arguments(self, parser):
        parser.add_argument("--counter-version", type=CounterVersion, default=CounterVersion.C5)
        parser.add_argument("url", help="URL of the SUSHI API")
        parser.add_argument("-c", dest="customer_id", type=str, help="Customer ID")
        parser.add_argument("-r", dest="requestor_id", type=str, help="Requestor ID")
        parser.add_argument("-t", dest="report_type", type=str, default="TR", help="Report type")
        parser.add_argument(
            "-b", dest="begin_date", type=str, help="If not given, start of current year"
        )
        parser.add_argument(
            "-e", dest="end_date", type=str, help="If not given, end of previous month"
        )
        parser.add_argument(
            "-p",
            dest="print_output",
            action="store_true",
            help="If given, print out a nicely formatted version of the data on " "stdout",
        )

    def handle(self, *args, **options):
        counter_version = options["counter_version"]
        client_class = counter_version.sushi_client_class
        client = client_class(
            options["url"], customer_id=options["customer_id"], requestor_id=options["requestor_id"]
        )
        report_type = options["report_type"]
        # check and possibly setup basic params of the query
        today: date = now().date()
        begin_date = options["begin_date"] if options["begin_date"] else f"{today.year}-01"
        end_date = (
            options["end_date"]
            if options["end_date"]
            else (today - timedelta(days=today.day)).strftime("%Y-%m")
        )  # previous month
        # add params to ensure maximum split (most granular) data, we copy the value to prevent
        # possible pollution by later updates
        params = deepcopy(counter_version.get_report_class(report_type).extra_params)
        # fetch it
        self.stderr.write(
            self.style.WARNING(
                f"Getting {report_type} ({counter_version}) report from {begin_date} to {end_date}"
            )
        )
        data = client.get_report_data(
            report_type, begin_date=begin_date, end_date=end_date, params=params
        )
        # if requested, print out the output in indented format
        if options["print_output"]:
            self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
        self.stderr.write("Got {} records.".format(len(data["Report_Items"])))
