import csv
import json
import logging
import traceback
import typing
import urllib
from datetime import timedelta
from io import StringIO, BytesIO
from xml.etree import ElementTree as ET

import requests
from pycounter import sushi
from pycounter import report
from requests import Response

from .counter5 import (
    Counter5TRReport,
    Counter5DRReport,
    Counter5PRReport,
    Counter5ReportBase,
    Counter5IRReport,
    CounterError,
)
from .error_codes import ErrorCode
from .exceptions import SushiException

logger = logging.getLogger(__name__)

ns_soap = 'http://schemas.xmlsoap.org/soap/envelope/'
ns_sushi = 'http://www.niso.org/schemas/sushi'
ns_counter = 'http://www.niso.org/schemas/sushi/counter'

namespaces = {
    's': ns_soap,
    'sushi': ns_sushi,
    'sushi_alt': f"{ns_sushi}/",  # sushi alternative with / in the end
    'counter': ns_counter,
}


class SushiError:
    def __init__(self, code='', text='', full_log='', raw_data=None, severity=None):
        self.code = code
        self.severity = severity
        self.text = text
        self.full_log = full_log
        self.raw_data = raw_data

    def __str__(self):
        return self.full_log


class SushiErrorMeaning:

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


def recursive_finder(
    et: ET.Element, names: typing.List[str], namespaces: typing.Dict[str, str]
) -> typing.Generator[ET.Element, None, None]:

    for name in names:
        for element in et.findall(name, namespaces):
            yield element

    for e in et:
        for element in recursive_finder(e, names, namespaces):
            yield element


class SushiClientBase:
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

    def get_report_data(
        self,
        report_type,
        begin_date,
        end_date,
        output_content: typing.Optional[typing.IO] = None,
        params=None,
    ):
        raise NotImplementedError()

    @classmethod
    def explain_error_code(
        cls, error_code: typing.Union[int, str], contains_recent_data: bool
    ) -> SushiErrorMeaning:
        """ Tries to figure out a meaning of an error code
        :param error_code: Sushi error code
        :param contains_recent_data: are data relatively new to download date

        :returns: the meaning
        """
        try:
            error_code = int(error_code)
        except ValueError:
            return SushiErrorMeaning(should_retry=True, needs_checking=True, setup_ok=False)

        if error_code in (ErrorCode.REPORT_NOT_SUPPORTED, ErrorCode.REPORT_VERSION_NOT_SUPPORTED):
            # report is not supported, so it was successful, but no data
            return SushiErrorMeaning(should_retry=False, needs_checking=False, setup_ok=False)
        elif error_code in (ErrorCode.NO_DATA_FOR_DATE_ARGS,):
            # no usage data for the requested period, it is success, but again no data
            # unfortunately, some providers, such as Clarivate (Web Of Science) use this
            # wrongly in cases when 3031 should be used, so we need to treat it like this
            return SushiErrorMeaning(
                should_retry=contains_recent_data,  # reschedule only for "recent" data
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_WEEKS,
            )
        elif error_code in (
            ErrorCode.SERVICE_BUSY,
            ErrorCode.PREPARING_DATA,
            ErrorCode.TOO_MANY_REQUESTS,
        ):
            # some forms of 'try it later' errors
            return SushiErrorMeaning(
                should_retry=True,
                needs_checking=False,
                setup_ok=True,
                retry_interval=SushiErrorMeaning.RETRY_IN_MINUTES,
            )
        elif error_code in (ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS,):
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
            'ir': {'attributes_to_show': 'YOP|Access_Method|Access_Type|Data_Type'},
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

    def _make_request(self, url, params, stream=False):
        logger.debug('Making request to :%s?%s', url, urllib.parse.urlencode(params))
        kwargs = {}
        if self.auth:
            kwargs['auth'] = self.auth
        return self.session.get(url, params=params, stream=stream, **kwargs)

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

    def get_available_reports(self, params=None) -> typing.Generator[dict, None, None]:
        content = self.get_available_reports_raw(params=params)
        reports = self.report_to_data(content)
        return reports

    def fetch_report_data(
        self,
        report_type,
        begin_date,
        end_date,
        dump_file: typing.Optional[typing.IO] = None,
        params=None,
    ) -> Response:
        """
        Makes a request for the data, stores the resulting data into `dump_file` and returns
        the response object for further inspection
        :param report_type:
        :param begin_date:
        :param end_date:
        :param dump_file: where to put file output
        :param params:
        :return:
        """
        report_type = self._check_report_type(report_type)
        url = '/'.join([self.url.rstrip('/'), 'reports', report_type])
        params = self._construct_url_params(extra=params)
        params['begin_date'] = self._encode_date(begin_date)
        params['end_date'] = self._encode_date(end_date)
        response = self._make_request(url, params, stream=bool(dump_file))
        if dump_file is not None:
            for data in response.iter_content(1024 * 1024):
                dump_file.write(data)
            dump_file.seek(0)
        return response

    def get_report_data(
        self,
        report_type,
        begin_date,
        end_date,
        output_content: typing.Optional[typing.IO] = None,
        params=None,
    ) -> Counter5ReportBase:
        response = self.fetch_report_data(
            report_type, begin_date, end_date, params=params, dump_file=output_content
        )
        if 200 <= response.status_code < 300 or 400 <= response.status_code < 500:
            # status codes in the 4xx range may be OK and just provide additional signal
            # about an issue - we need to parse the result in case there is more info
            # in the body
            report_class: typing.Type[Counter5ReportBase]
            if report_type.lower() == 'tr':
                report_class = Counter5TRReport
            elif report_type.lower() == 'dr':
                report_class = Counter5DRReport
            elif report_type.lower() == 'pr':
                report_class = Counter5PRReport
            elif report_type.lower() == 'ir':
                report_class = Counter5IRReport
            else:
                raise NotImplementedError()

            if output_content:
                output_content.seek(0)
            return report_class(output_content, http_status_code=response.status_code)
        # response code most probably 5xx - we raise an error
        response.raise_for_status()

    def report_to_data(self, report: bytes, validate=True) -> typing.Generator[dict, None, None]:
        try:
            fd = BytesIO(report)
            counter_report = Counter5ReportBase()
            header, data = counter_report.fd_to_dicts(fd)
        except ValueError as e:
            raise SushiException(str(e), content=report)
        if validate:
            self.validate_data(counter_report.errors, counter_report.warnings)
        return data

    @classmethod
    def validate_data(cls, errors: typing.List[CounterError], warnings: typing.List[CounterError]):
        """ Checks that the parsed erorrs and warings are not fatal.
            If so, it will raise SushiException
        :param errors: list of errors
        :param warnings: list of warnings
        :return:
        """
        if len(errors) == 1:
            errors[0].raise_me()
        elif len(errors) >= 1:
            message = '; '.join(
                cls._format_error(error.to_sushi_dict()).full_log for error in errors
            )
            raise SushiException(message, content=[e.data for e in errors])

        # log warnings
        for warning in warnings:
            logging.warning(
                "Warning Exception in COUNTER 5 report: %s",
                cls._format_error(warning.to_sushi_dict()),
            )

    def extract_errors_from_data(self, report_data: dict):
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
        CONVERSIONS = {"JR1GOA": "JR1GOA"}
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

    def get_report_data(
        self,
        report_type,
        begin_date,
        end_date,
        output_content: typing.Optional[typing.IO] = None,
        params=None,
    ) -> report.CounterReport:
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
        report = sushi.get_report(
            self.url, begin_date, end_date, report=report_type, dump_file=output_content, **kwargs
        )
        return report

    def extract_errors_from_data(self, report_data: typing.IO[bytes]):
        try:
            report_data.seek(0)  # set to start
            content = report_data.read().decode('utf8', 'ignore')
            envelope = ET.fromstring(content)
            body = envelope[0]
            response = body[0] if len(body) > 0 else None
        except Exception as e:
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            return [SushiError(code='non-sushi', text=str(e), full_log=log, severity='Exception',)]
        else:
            errors = []
            if response is not None:
                for exception in recursive_finder(
                    response, ['sushi:Exception', 'sushi_alt:Exception'], namespaces
                ):
                    code = exception.find('sushi:Number', namespaces)
                    code = exception.find('sushi_alt:Number', namespaces) if code is None else code
                    code = code.text if code is not None else ''

                    message = exception.find('sushi:Message', namespaces)
                    message = (
                        exception.find('sushi_alt:Message', namespaces)
                        if message is None
                        else message
                    )
                    message = message.text if message is not None else ''

                    severity = exception.find('sushi:Severity', namespaces)
                    severity = (
                        exception.find('sushi_alt:Severity', namespaces)
                        if severity is None
                        else severity
                    )
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

    def report_to_string(self, report_data: report.CounterReport):
        lines = report_data.as_generic()
        out = StringIO()
        writer = csv.writer(out, dialect='excel', delimiter="\t")
        writer.writerows(lines)
        return out.getvalue()
