import csv
import json
import urllib
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Union, Optional
from urllib.parse import urljoin
import logging
from xml.etree import ElementTree as ET
import traceback

import requests

from pycounter import sushi
from pycounter.csvhelper import UnicodeWriter

from .counter5 import Counter5TRReport, Counter5DRReport, Counter5ReportBase
from .exceptions import SushiException

logger = logging.getLogger(__name__)


ns_soap = 'http://schemas.xmlsoap.org/soap/envelope/'
ns_sushi = 'http://www.niso.org/schemas/sushi'
ns_counter = 'http://www.niso.org/schemas/sushi/counter'

namespaces = {'s': ns_soap, 'sushi': ns_sushi, 'counter': ns_counter}


class SushiError(object):
    def __init__(self, code='', text='', full_log='', raw_data=None, severity=None):
        self.code = code
        self.severity = severity
        self.text = text
        self.full_log = full_log
        self.raw_data = raw_data

    def __str__(self):
        return self.full_log


class SushiErrorMeaning(object):

    RETRY_IN_MINUTES = 1
    RETRY_IN_HOURS = 2
    RETRY_IN_DAYS = 3
    RETRY_IN_WEEKS = 4
    RETRY_IN_MONTHS = 5
    RETRY_AFTER_CHECKUP = 100

    RETRY_INTERVAL_TO_TIMEDELTA = {
        RETRY_IN_MINUTES: timedelta(minutes=1),
        RETRY_IN_HOURS: timedelta(hours=1),
        RETRY_IN_DAYS: timedelta(days=1),
        RETRY_IN_WEEKS: timedelta(weeks=1),
        RETRY_IN_MONTHS: timedelta(days=30),
    }

    def __init__(
        self,
        should_retry=False,
        needs_checking=True,
        setup_ok=False,
        retry_interval=RETRY_AFTER_CHECKUP,
    ):
        """

        :param should_retry:
        :param needs_checking: the credentials or the whole setup should be checked - no sense
            in retrying before changing something
        :param retry_interval: how fast should be retry
        :param setup_ok: if true, it means the credentials and report type are OK, just that there
            was something other with the request (wrong date, etc.) - we can try other dates
        """
        self.should_retry = should_retry
        self.needs_checking = needs_checking
        self.retry_interval = retry_interval
        self.setup_ok = setup_ok

    @property
    def retry_interval_timedelta(self):
        return self.RETRY_INTERVAL_TO_TIMEDELTA.get(self.retry_interval)


class SushiClientBase(object):
    def __init__(self, url, requestor_id, customer_id=None, extra_params=None, auth=None):
        self.url = url
        self.requestor_id = requestor_id
        self.customer_id = customer_id
        self.extra_params = extra_params
        self.auth = auth

    def extract_errors_from_data(self, report_data) -> [SushiError]:
        raise NotImplementedError()

    def report_to_string(self, report_data):
        raise NotImplementedError()

    def get_report_data(self, report_type, begin_date, end_date, params=None):
        raise NotImplementedError()

    @classmethod
    def explain_error_code(cls, error_code) -> SushiErrorMeaning:
        try:
            error_code = int(error_code)
        except ValueError:
            return SushiErrorMeaning(should_retry=True, needs_checking=True, setup_ok=False)

        if error_code in (3000, 3010):
            # report is not supported, so it was successful, but no data
            return SushiErrorMeaning(should_retry=False, needs_checking=False, setup_ok=False)
        elif error_code in (3030,):
            # no usage data for the requested period, it is success, but again no data
            # unfortunately, some providers, such as Clarivate (Web Of Science) use this
            # wrongly in cases when 3031 should be used, so we need to treat it like this
            return SushiErrorMeaning(
                should_retry=True,
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_WEEKS,
            )
        elif error_code in (1010, 1011, 1020):
            # some forms of 'try it later' errors
            return SushiErrorMeaning(
                should_retry=True,
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_MINUTES,
            )
        elif error_code in (3031,):
            # the data is not yet available - usually some months are missing
            return SushiErrorMeaning(
                should_retry=True,
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_WEEKS,
            )
        elif error_code >= 4000:
            # some other stuff for which we want to check later if the data exists
            # in the wild, we have seen 4010
            return SushiErrorMeaning(
                should_retry=True,
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_WEEKS,
            )
        else:
            return SushiErrorMeaning(should_retry=True, needs_checking=True, setup_ok=False)


class Sushi5Client(SushiClientBase):

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
            'subreports': {'d1': 'Search and Item usage', 'd2': 'Database Access Denied'},
        },
        'ir': {
            'name': 'Item report',
            'subreports': {'a1': 'Journal article requests', 'm1': 'Multimedia item requests',},
        },
        'pr': {'name': 'Platform report', 'subreports': {'p1': 'View by Metric_Type',},},
    }

    # sets of additional parameters for specific setups
    EXTRA_PARAMS = {
        # split data in TR report to most possible dimensions for most granular data
        'maximum_split': {
            'tr': {'attributes_to_show': 'YOP|Access_Method|Access_Type|Data_Type|Section_Type'},
            'pr': {'attributes_to_show': 'Access_Method|Data_Type'},
            'dr': {'attributes_to_show': 'Access_Method|Data_Type'},
        }
    }

    def __init__(self, url, requestor_id, customer_id=None, extra_params=None, auth=None):
        super().__init__(url, requestor_id, customer_id, extra_params, auth)
        self.session = requests.Session()
        self.session.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'
            }
        )

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
            self.CUSTOMER_ID_PARAM: self.customer_id if self.customer_id else self.requestor_id,
        }
        if self.requestor_id:
            result[self.REQUESTOR_ID_PARAM] = self.requestor_id
        if self.extra_params:
            result.update(self.extra_params)
        if extra:
            result.update(extra)
        return result

    def _make_request(self, url, params):
        logger.debug('Making request to :%s?%s', url, urllib.parse.urlencode(params))
        kwargs = {}
        if self.auth:
            kwargs['auth'] = self.auth
        return self.session.get(url, params=params, **kwargs)

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

    def get_report_data(self, report_type, begin_date, end_date, params=None) -> Counter5ReportBase:
        content = self.get_report(report_type, begin_date, end_date, params=params)
        if report_type.lower() == 'tr':
            report_class = Counter5TRReport
        elif report_type.lower() == 'dr':
            report_class = Counter5DRReport
        else:
            report_class = Counter5ReportBase
        data = json.loads(content)
        return report_class(data)

    def report_to_data(self, report: bytes, validate=True):
        try:
            data = json.loads(report)
        except ValueError as e:
            raise SushiException(str(e), content=report)
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
            # for list, we validate the whole list
            for item in data:
                cls.validate_data(item)
            return
        if 'Exception' in data:
            exc = data['Exception']
            raise SushiException(cls._format_error(exc), content=data)
        if 'Severity' in data and data['Severity'] == 'Error':
            raise SushiException(cls._format_error(data), content=data)
        header = data.get('Report_Header', {})
        errors = []
        for exception in header.get('Exceptions', []):
            if exception.get('Severity') in ('Info', 'Warning'):
                logging.warning(
                    "Warning Exception in COUNTER 5 report: %s", cls._format_error(exception)
                )
            else:
                errors.append(exception)
        if errors:
            message = '; '.join(cls._format_error(error).full_log for error in errors)
            raise SushiException(message, content=data)

    def extract_errors_from_data(self, report_data):
        if 'Exception' in report_data:
            exc = report_data['Exception']
            return self._format_error(exc)
        if 'Severity' in report_data and report_data['Severity'] == 'Error':
            return self._format_error(report_data)
        header = report_data.get('Report_Header', {})
        errors = []
        for exception in header.get('Exceptions', []):
            if exception.get('Severity') in ('Info', 'Warning'):
                logging.warning(
                    "Warning Exception in COUNTER 5 report: %s", self._format_error(exception)
                )
            else:
                errors.append(self._format_error(exception))
        return errors

    @classmethod
    def _format_error(cls, exc: dict):
        message = '{Severity} error {Code}: {Message}'.format(**exc)
        if 'Data' in exc:
            message += '; {}'.format(exc['Data'])
        error = SushiError(
            code=exc.get('Code', ''),
            text=exc.get('Message' ''),
            full_log=message,
            severity=exc.get('Severity'),
            raw_data=exc,
        )
        return error

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

    def report_to_string(self, report_data):
        return json.dumps(report_data, ensure_ascii=False, indent=2)


class Sushi4Client(SushiClientBase):

    """
    Client for SUSHI and COUNTER 4 protocol - a simple proxy for the pycounter.sushi
    implementation
    """

    @staticmethod
    def to_pycounter_report_type(celus_report_type: str) -> str:
        """ Celus and pycounter report types may differ """
        CONVERSIONS = {"JR1GOA": "JR1 GOA"}
        return CONVERSIONS.get(celus_report_type, celus_report_type)

    # remap of extra params into names that have special meaning for the pycounter client
    extra_params_remap = {
        'Name': 'requestor_name',
        'Email': 'requestor_email',
    }

    def __init__(self, url, requestor_id, customer_id=None, extra_params=None, auth=None):
        super().__init__(url, requestor_id, customer_id, extra_params, auth)

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
            # recode params that have special meaning
            for orig, new in self.extra_params_remap.items():
                if orig in params:
                    kwargs[new] = params.pop(orig)
            # put the rest in as it is
            kwargs.update(params)
        if self.auth:
            kwargs['auth'] = self.auth

        report_type = Sushi4Client.to_pycounter_report_type(report_type)
        report = sushi.get_report(self.url, begin_date, end_date, report=report_type, **kwargs)
        return report

    def extract_errors_from_data(self, report_data):
        try:
            envelope = ET.fromstring(report_data)
            body = envelope[0]
            response = body[0] if len(body) > 0 else None
        except Exception as e:
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            return [SushiError(code='non-sushi', text=str(e), full_log=log, severity='Exception',)]
        else:
            errors = []
            if response is not None:
                for exception in response.findall('sushi:Exception', namespaces):
                    code = exception.find('sushi:Number', namespaces)
                    code = code.text if code is not None else ''
                    message = exception.find('sushi:Message', namespaces)
                    message = message.text if message is not None else ''
                    severity = exception.find('sushi:Severity', namespaces)
                    severity = severity.text if severity is not None else 'Unknown'
                    full_log = f'{severity}: #{code}; {message}'
                    errors.append(
                        SushiError(
                            code=code,
                            text=message,
                            severity=severity,
                            full_log=full_log,
                            raw_data=str(exception),
                        )
                    )
            if not errors:
                errors.append(
                    SushiError(
                        code='non-sushi',
                        text='Could not find Exception data in XML, probably wrong format',
                        full_log='Could not find Exception data in XML, probably wrong format',
                        severity='Exception',
                    )
                )
            return errors

    def report_to_string(self, report_data):
        lines = report_data.as_generic()
        out = StringIO()
        writer = csv.writer(out, dialect='excel', delimiter="\t")
        writer.writerows(lines)
        return out.getvalue()
