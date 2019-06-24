import json
import logging

from django.core.management.base import BaseCommand

from sushi.client import Sushi5Client

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Loads contact info from mailchimp and synchronizes it with the database'

    def add_arguments(self, parser):
        parser.add_argument('url', help='URL of the SUSHI API')
        parser.add_argument('-c', dest='customer_id', type=str, help='Customer ID')
        parser.add_argument('-r', dest='requestor_id', type=str, help='Requestor ID')

    def handle(self, *args, **options):
        client = Sushi5Client(options['url'],
                              customer_id=options['customer_id'],
                              requestor_id=options['requestor_id'])
        self.stdout.write(self.style.WARNING('Getting TR report'))
        report = client.get_report('tr', begin_date='2019-01', end_date='2019-05')
        data = json.loads(report)
        self.stdout.write('Got {} records in {} bytes.'.format(len(data['Report_Items']),
                                                               len(report)))
        self.stdout.write(self.style.WARNING('Getting DR report'))
        report = client.get_report('dr', begin_date='2019-01', end_date='2019-05')
        data = json.loads(report)
        self.stdout.write('Got {} records in {} bytes.'.format(len(data['Report_Items']),
                                                               len(report)))
