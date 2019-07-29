import argparse
import json
import sys
from collections import Counter
from datetime import date
import logging
import csv
from io import StringIO
from time import sleep
from xml.etree import ElementTree as ET

import requests
from pycounter import sushi
from pycounter.exceptions import SushiException

from sushi.client import Sushi5Client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ns_soap = 'http://schemas.xmlsoap.org/soap/envelope/'
ns_sushi = 'http://www.niso.org/schemas/sushi'
ns_counter = 'http://www.niso.org/schemas/sushi/counter'

namespaces = {
    's': ns_soap,
    'sushi': ns_sushi,
    'counter': ns_counter
}


def test_sushi_access_v4(url, customer_id, requestor_id, start=None, end=None, report='JR1'):
    kwargs = {
        'customer_reference': customer_id,
    }
    if requestor_id:
        kwargs['requestor_id'] = requestor_id
    if not start:
        start = date(2018, 1, 1)
    if not end:
        end = date(2018, 6, 30)
    error_output = ''
    try:
        data = sushi.get_report(url, start, end, report=report, **kwargs)
    except SushiException as e:
        logger.error("Error: %s", e)
        error_output += 'Error: {}'.format(e)
        try:
            envelope = ET.fromstring(e.raw)
            body = envelope[0]
            response = body[0]
        except Exception:
            pass
        else:
            if response is not None:
                for exception in response.findall('sushi:Exception', namespaces):
                    message = exception.find('sushi:Message', namespaces)
                    if message is not None:
                        logger.error('  - error detail: %s', message.text)
                        error_output += '; detail: {}'.format(message.text)
        return False, error_output
    else:
        logger.info("Success - got: %s", data)
        return True, ''


def test_sushi_access_v5(url, customer_id, requestor_id, start=None, end=None, report='tr',
                         extra_params=None):
    client = Sushi5Client(url, customer_id=customer_id, requestor_id=requestor_id)
    try:
        data = client.get_report_data(report, begin_date=start, end_date=end, params=extra_params)
    except requests.exceptions.ConnectionError as e:
        logger.error('Connection error: %s', e)
        return False, 'Connection error: {}'.format(e)
    except SushiException as e:
        logger.error('Sushi error: %s', e)
        return False, 'Sushi error: {}'.format(e)
    except Exception as e:
        logger.error('Error: %s', e)
        return False, 'Error: {}'.format(e)
    else:
        logger.info('Success - got {} records'.format(len(data.get('Report_Items', []))))
    return True, ''


def parse_params(text):
    out = {}
    for part in text.split(';'):
        if '=' in part:
            name, value = part.split('=')
            out[name.strip()] = value.strip()
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Sushi credentials loaded from CSV file')
    parser.add_argument('input_file', help='input CSV file with Sushi credentials')
    parser.add_argument('-o', dest='output_file',
                        help='file name of output CSV with processed data')
    args = parser.parse_args()

    stats = Counter()
    output = StringIO()
    with open(args.input_file, 'r') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        for field in ['ok', 'error']:
            if field not in fieldnames:
                fieldnames.append(field)
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        last_url = None
        last_skipped = False
        for record in reader:
            url = record['URL']
            customer_id = record['customer_id']
            requestor_id = record['requestor_id']
            platform = record['platform']
            organization = record['organization']
            version = int(record['version'])
            do_it = int(record.get('do_it', 1))
            extra_params = parse_params(record.get('extra_attrs', ''))
            # add sleep when requesting data from the same URL
            if last_url == url and not last_skipped:
                sleep(1)
            last_url = url
            if do_it:
                logger.info("Checking v%d for '%s' @%s", version, organization, platform)
                if version == 4:
                    start = date(2018, 1, 1)
                    end = date(2018, 12, 31)
                    ok, error = test_sushi_access_v4(url, customer_id, requestor_id,
                                                     start=start, end=end, report='JR1')
                    stats[ok] += 1
                elif version == 5:
                    start = '2019-01'
                    end = '2019-05'
                    ok, error = test_sushi_access_v5(url, customer_id, requestor_id,
                                                     start=start, end=end,
                                                     report='tr_j1', extra_params=extra_params)
                    stats[ok] += 1
                else:
                    logger.error('Unsupported version: %d', version)
                    ok = False
                    error = 'Unsupported Sushi version: {}'.format(version)
                    stats[False] += 1
                record['ok'] = 1 if ok else 0
                record['do_it'] = record['ok']
                record['error'] = error
                last_skipped = False
            else:
                logger.info("Skipping v%d for '%s' @%s", version, organization, platform)
                last_skipped = True
                stats['skipped'] += 1
            # write the modified record to the output
            writer.writerow(record)
    logger.info('Stats of success: %s', stats)
    if args.output_file:
        with open(args.output_file, 'w') as outfile:
            outfile.write(output.getvalue())

