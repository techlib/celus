from datetime import datetime
from urllib.parse import urljoin

import requests


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

    def __init__(self, url, requestor_id, customer_id=None):
        self.url = url
        self.requestor_id = requestor_id
        self.customer_id = customer_id
        self.session = requests.Session()

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
        return self.session.get(url, params=params)

    def get_report(self, report_type, begin_date, end_date, params=None):
        self.check_report_type(report_type)
        url = urljoin(self.url, 'reports/'+report_type)
        params = self._construct_url_params(extra=params)
        params['begin_date'] = self._encode_date(begin_date)
        params['end_date'] = self._encode_date(end_date)
        response = self._make_request(url, params)
        return response.content

    def check_report_type(self, report_type):
        if '_' in report_type:
            main_type, subtype = report_type.split('_', 1)
        else:
            main_type = report_type
            subtype = None
        if main_type not in self.report_types:
            raise ValueError(f'Report type {main_type} is not supported.')
        if subtype and subtype not in self.report_types[main_type]['subreports']:
            raise ValueError(f'Report subtype {subtype} is not supported for type {main_type}.')


