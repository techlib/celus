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
from pycounter.exceptions import SushiException

from sushi.client import Sushi5Client, Sushi4Client

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


def test_sushi_access_v4(url, customer_id, requestor_id, start=None, end=None, report='JR1',
                         save_as=None, extra_params=None):
    kwargs = {}
    if extra_params:
        kwargs.update(extra_params)
    if not start:
        start = date(2018, 1, 1)
    if not end:
        end = date(2018, 6, 30)
    error_output = ''
    client = Sushi4Client(url, customer_id=customer_id, requestor_id=requestor_id)
    try:
        data = client.get_report_data(report, start, end, params=kwargs)
    except SushiException as e:
        logger.error("Error: %s", e)
        error_output += 'Error: {}'.format(e)
        if save_as:
            with open(save_as, 'wb') as outfile:
                outfile.write(e.raw)
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
        if save_as:
            data.write_tsv(save_as)
        return True, ''


def test_sushi_access_v5(url, customer_id, requestor_id, start=None, end=None, report='tr',
                         extra_params=None, save_as=None):
    client = Sushi5Client(url, customer_id=customer_id, requestor_id=requestor_id)
    content = None
    try:
        content = client.get_available_reports_raw(params=extra_params)
        data = client.report_to_data(content)
    except requests.exceptions.ConnectionError as e:
        logger.error('Connection error: %s', e)
        return False, 'Connection error: {}'.format(e)
    except SushiException as e:
        logger.error('Sushi error: %s', e)
        return False, 'Sushi error: {}'.format(e)
    except Exception as e:
        logger.error('Error: %s', e)
        if content and save_as:
            with open(save_as, 'wb') as outfile:
                outfile.write(content)
        return False, 'Error: {}'.format(e)
    else:
        if save_as:
            with open(save_as, 'w') as outfile:
                json.dump(data, outfile, ensure_ascii=False, indent=2)
        logger.info('Success - got following reports: %s',
                    [report.get('Report_ID') for report in data])
    return True, ''


def parse_params(text):
    out = {}
    for part in text.split(';'):
        if '=' in part:
            name, value = part.split('=')
            name = name.strip()
            value = value.strip()
            if name == 'auth':
                value = tuple(value.split(','))
            out[name] = value
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Sushi credentials loaded from CSV file')
    parser.add_argument('input_file', help='input CSV file with Sushi credentials')
    parser.add_argument('-o', dest='output_file',
                        help='file name of output CSV with processed data')
    parser.add_argument('-r', dest='reverse_do_it', action='store_true',
                        help='mark output records with "do_it" in the reverse way - 1 for those '
                             'failing and 0 for those OK')
    args = parser.parse_args()

    report_types_v4 = ['JR1', 'PR1', 'BR1', 'DR1']

    stats = Counter()
    output = StringIO()
    with open(args.input_file, 'r') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        for field in ['ok', 'error']:
            if field not in fieldnames:
                fieldnames.append(field)
        writer = csv.DictWriter(output, fieldnames=fieldnames, dialect='unix')
        writer.writeheader()
        last_url = None
        last_skipped = False
        for i, record in enumerate(reader):
            logger.info('Line #%d', i+2)
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
                    for report_type in report_types_v4:
                        logger.info("Report type: %s", report_type)
                        ok, error = test_sushi_access_v4(url, customer_id, requestor_id,
                                                         start=start, end=end, report=report_type,
                                                         extra_params=extra_params,
                                                         save_as='_tmp_{:04d}.data'.format(i+2))
                        if not ok and 'Report Not Supported' in error:
                            # try again with a different report type
                            pass
                        else:
                            break
                    stats[ok] += 1
                elif version == 5:
                    start = '2019-01'
                    end = '2019-05'
                    ok, error = test_sushi_access_v5(url, customer_id, requestor_id,
                                                     start=start, end=end,
                                                     report='tr_j1', extra_params=extra_params,
                                                     save_as='_tmp_{:04d}.data'.format(i+2))
                    stats[ok] += 1
                else:
                    logger.error('Unsupported version: %d', version)
                    ok = False
                    error = 'Unsupported Sushi version: {}'.format(version)
                    stats[False] += 1
                record['ok'] = 1 if ok else 0
                record['do_it'] = record['ok']
                if args.reverse_do_it:
                    record['do_it'] = int(not record['do_it'])
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

