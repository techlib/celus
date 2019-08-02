import json
import urllib
from datetime import datetime
from typing import List, Dict, Union
from urllib.parse import urljoin
import logging

import requests

from pycounter import sushi

logger = logging.getLogger(__name__)


class SushiException(Exception):

    pass


class Sushi5Client(object):

    """
    Client for SUSHI and COUNTER 5 protocol
    """

    CUSTOMER_ID_PARAM = 'customer_id'
    REQUESTOR_ID_PARAM = 'requestor_id'

    report_types = {
        'tr': {
            'name': 'Title report',
            'subreports': {
                'b1': 'Book requests excluding OA_Gold',
                'b2': 'Books - access denied',
                'b3': 'Book Usage by Access Type',
                'j1': 'Journal requests excluding OA_Gold',
                'j2': 'Journal articles - access denied',
                'j3': 'Journal usage by Access Type',
                'j4': 'Journal Requests by YOP (Excluding OA_Gold)',
            },
        },
        'dr': {
            'name': 'Database report',
            'subreports': {
                'd1': 'Search and Item usage',
                'd2': 'Database Access Denied'
            },
        },
        'ir': {
            'name': 'Item report',
            'subreports': {
                'a1': 'Journal article requests',
                'm1': 'Multimedia item requests',
            },
        },
        'pr': {
            'name': 'Platform report',
            'subreports': {
                'p1': 'View by Metric_Type',
            },
        }
    }

    # sets of additional parameters for specific setups
    EXTRA_PARAMS = {
        # split data in TR report to most possible dimensions for most granular data
        'tr_maximum_split': {
            'attributes_to_show': 'yop|Access_Method|Access_Type|Data_Type|Section_Type'
        }
    }

    def __init__(self, url, requestor_id, customer_id=None):
        self.url = url
        self.requestor_id = requestor_id
        self.customer_id = customer_id
        self.session = requests.Session()
        self.session.headers.update(
            {'User-Agent':
                 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'
             })

    @classmethod
    def _encode_date(cls, value) -> str:
        """
        >>> Sushi5Client._encode_date('2018-02-30')
        '2018-02'
        >>> Sushi5Client._encode_date(datetime(2018, 7, 6, 12, 25, 30))
        '2018-07'
        """
        if hasattr(value, 'isoformat'):
            return value.isoformat()[:7]
        return value[:7]

    def _construct_url_params(self, extra=None):
        result = {
            self.REQUESTOR_ID_PARAM: self.requestor_id,
            self.CUSTOMER_ID_PARAM: self.customer_id if self.customer_id else self.requestor_id,
        }
        if extra:
            result.update(extra)
        return result

    def _make_request(self, url, params):
        logger.debug('Making request to :%s?%s', url, urllib.parse.urlencode(params))
        return self.session.get(url, params=params)

    def get_available_reports_raw(self, params=None) -> bytes:
        """
        Return a list of available reports
        :return:
        """
        url = '/'.join([self.url.rstrip('/'), 'reports/'])
        params = self._construct_url_params(extra=params)
        response = self._make_request(url, params)
        response.raise_for_status()
        return response.content

    def get_available_reports(self, params=None) -> list:
        content = self.get_available_reports_raw(params=params)
        reports = self.report_to_data(content)
        return reports

    def get_report(self, report_type, begin_date, end_date, params=None):
        """
        Return a SUSHI report based on the provided params
        :param report_type:
        :param begin_date:
        :param end_date:
        :param params:
        :return:
        """
        report_type = self._check_report_type(report_type)
        url = '/'.join([self.url.rstrip('/'), 'reports', report_type])
        params = self._construct_url_params(extra=params)
        params['begin_date'] = self._encode_date(begin_date)
        params['end_date'] = self._encode_date(end_date)
        response = self._make_request(url, params)
        response.raise_for_status()
        return response.content

    def get_report_data(self, report_type, begin_date, end_date, params=None):
        content = self.get_report(report_type, begin_date, end_date, params=params)
        return self.report_to_data(content)

    def report_to_data(self, report: bytes, validate=True):
        data = json.loads(report)
        if validate:
            self.validate_data(data)
        return data

    @classmethod
    def validate_data(cls, data: Union[Dict, List]):
        """
        Checks that the provided data contain valid COUNTER data and not an error.
        If the data contains an error message, it will raise SushiException
        :param data:
        :return:
        """
        if type(data) is list:
            # we do not do any validation for lists
            return
        if 'Exception' in data:
            exc = data['Exception']
            raise SushiException(cls._format_error(exc))
        if 'Severity' in data and data['Severity'] == 'Error':
            raise SushiException(cls._format_error(data))
        header = data.get('Report_Header', {})
        errors = []
        for exception in header.get('Exceptions', []):
            if exception.get('Severity') == 'Warning':
                logging.warning("Warning Exception in COUNTER 5 report: %s",
                                cls._format_error(exception))
            else:
                errors.append(exception)
        if errors:
            message = '; '.join(cls._format_error(error) for error in errors)
            raise SushiException(message)

    @classmethod
    def _format_error(cls, exc: dict):
        message = '{Severity} error {Code}: {Message}'.format(**exc)
        if 'Data' in exc:
            message += '; {}'.format(exc['Data'])
        return message

    def _check_report_type(self, report_type):
        report_type = report_type.lower()
        if '_' in report_type:
            main_type, subtype = report_type.split('_', 1)
        else:
            main_type = report_type
            subtype = None
        if main_type not in self.report_types:
            raise ValueError(f'Report type {main_type} is not supported.')
        if subtype and subtype not in self.report_types[main_type]['subreports']:
            raise ValueError(f'Report subtype {subtype} is not supported for type {main_type}.')
        return report_type


class Sushi4Client(object):

    """
    Client for SUSHI and COUNTER 5 protocol - a simple proxy for the pycounter.sushi
    implementation
    """

    def __init__(self, url, requestor_id, customer_id=None):
        self.url = url
        self.requestor_id = requestor_id
        self.customer_id = customer_id

    @classmethod
    def _encode_date(cls, value) -> str:
        if hasattr(value, 'isoformat'):
            return value.isoformat()[:7]
        return value[:7]

    def get_report_data(self, report_type, begin_date, end_date, params=None):
        kwargs = {'customer_reference': self.customer_id}
        if self.requestor_id:
            kwargs['requestor_id'] = self.requestor_id
        if params:
            kwargs.update(params)
        report = sushi.get_report(self.url, begin_date, end_date, report=report_type, **kwargs)
        return report

