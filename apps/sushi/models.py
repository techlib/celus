import os
import logging
import traceback
from hashlib import blake2b
from datetime import timedelta, datetime
from itertools import takewhile
from typing import Optional

import requests
from django.contrib.postgres.fields import JSONField
from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now
from pycounter.exceptions import SushiException

from django.conf import settings

from core.task_support import cache_based_lock
from logs.models import ImportBatch
from nigiri.client import Sushi5Client, Sushi4Client, SushiException as SushiExceptionNigiri, \
    SushiClientBase
from nigiri.counter4 import Counter4JR1Report, Counter4BR2Report, Counter4DB1Report, \
    Counter4PR1Report, Counter4BR1Report, Counter4JR2Report, Counter4DB2Report, Counter4BR3Report
from nigiri.counter5 import Counter5DRReport, Counter5PRReport, Counter5TRReport
from organizations.models import Organization
from publications.models import Platform


logger = logging.getLogger(__name__)

COUNTER_VERSIONS = (
    (4, 'COUNTER 4'),
    (5, 'COUNTER 5'),
)

COUNTER_REPORTS = (
    # version 4
    ('JR1', 4, Counter4JR1Report),
    ('JR1a', 4, Counter4JR1Report),
    ('JR1GOA', 4, Counter4JR1Report),
    ('JR2', 4, Counter4JR2Report),
    # ('JR5', 4, None),
    ('BR1', 4, Counter4BR1Report),
    ('BR2', 4, Counter4BR2Report),
    ('BR3', 4, Counter4BR3Report),
    ('DB1', 4, Counter4DB1Report),
    ('DB2', 4, Counter4DB2Report),
    ('PR1', 4, Counter4PR1Report),
    # version 5
    ('TR', 5, Counter5TRReport),
    ('PR', 5, Counter5PRReport),
    ('DR', 5, Counter5DRReport),
)


class CounterReportType(models.Model):

    CODE_CHOICES = [(cr[0], cr[0]) for cr in COUNTER_REPORTS]

    code = models.CharField(max_length=10, choices=CODE_CHOICES)
    name = models.CharField(max_length=128, blank=True)
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    report_type = models.OneToOneField('logs.ReportType', on_delete=models.CASCADE)
    active = models.BooleanField(default=True,
                                 help_text='When turned off, this type of report will not be '
                                           'automatically downloaded')
    superseeded_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='superseeds')

    class Meta:
        unique_together = (('code', 'counter_version'),)
        verbose_name_plural = 'COUNTER report types'
        verbose_name = 'COUNTER report type'

    def __str__(self):
        return f'{self.code} ({self.counter_version}) - {self.name}'

    def get_reader_class(self):
        for code, version, reader in COUNTER_REPORTS:
            if code == self.code and version == self.counter_version:
                return reader
        return None


class SushiCredentials(models.Model):

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    url = models.URLField()
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    requestor_id = models.CharField(max_length=128)
    customer_id = models.CharField(max_length=128, blank=True)
    http_username = models.CharField(max_length=128, blank=True)
    http_password = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=128, blank=True)
    extra_params = JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    active_counter_reports = models.ManyToManyField(CounterReportType)

    class Meta:
        unique_together = (('organization', 'platform', 'counter_version'),)
        verbose_name_plural = 'Sushi credentials'

    def __str__(self):
        return f'{self.organization} - {self.platform}, {self.get_counter_version_display()}'

    def create_sushi_client(self):
        attrs = {
            'url': self.url,
            'requestor_id': self.requestor_id,
            'customer_id': self.customer_id,
        }
        extra = self.extra_params or {}
        if self.api_key:
            extra['api_key'] = self.api_key
        if self.http_password and self.http_username:
            attrs['auth'] = (self.http_username, self.http_password)
        if self.counter_version == 4:
            return Sushi4Client(**attrs)
        else:
            return Sushi5Client(extra_params=extra, **attrs)

    @property
    def url_lock_name(self):
        """
        Creates a name for lock which should be used to ensure only one attempt to fetch data
        from a specific URL at a time.
        """
        url_hash = blake2b(self.url.encode('utf-8'), digest_size=16).hexdigest()
        return f'url-lock-{url_hash}'

    def when_can_access(self, base_wait_unit=5) -> float:
        """
        Computes the number of seconds required to wait before we can download data
        using the current credentials.
        This is used to get around issues with providers who limit the number of attempts
        per unit of time
        :return:
        """
        last_attempts = self.sushifetchattempt_set.order_by('-timestamp').\
            values('error_code', 'timestamp')[:16]
        too_many_attempts = list(takewhile(lambda x: x['error_code'] == '1020', last_attempts))
        if too_many_attempts:
            seconds = base_wait_unit * 2**len(too_many_attempts)
            last_timestamp = too_many_attempts[0]['timestamp']
            diff = (last_timestamp + timedelta(seconds=seconds) - now()).seconds
            if diff > 0:
                return diff
        return 0

    def fetch_report(self, counter_report: CounterReportType, start_date, end_date,
                     fetch_attempt: 'SushiFetchAttempt' = None, use_url_lock=True) -> \
            'SushiFetchAttempt':
        """
        :param counter_report:
        :param start_date:
        :param end_date:
        :param fetch_attempt: when provides, new SushiFetchAttempt will not be created but rather
                              the given one updated
        :param use_url_lock: if True, a cache based lock will be used to ensure exclusive access
                             to one URL
        :return:
        """
        client = self.create_sushi_client()
        fetch_m = self._fetch_report_v4 if self.counter_version == 4 else self._fetch_report_v5
        if use_url_lock:
            with cache_based_lock(self.url_lock_name):
                attempt_params = fetch_m(client, counter_report, start_date, end_date)
        else:
            attempt_params = fetch_m(client, counter_report, start_date, end_date)
        attempt_params['in_progress'] = False
        if fetch_attempt:
            for key, value in attempt_params.items():
                setattr(fetch_attempt, key, value)
            fetch_attempt.save()
            return fetch_attempt
        else:
            attempt = SushiFetchAttempt.objects.create(**attempt_params)
            return attempt

    def _fetch_report_v4(self, client, counter_report, start_date, end_date) -> dict:
        file_data = None
        contains_data = False
        download_success = False
        processing_success = False
        log = ''
        data_file = None
        error_code = ''
        queued = False
        try:
            report = client.get_report_data(counter_report.code, start_date, end_date,
                                            params={'sushi_dump': True})
        except SushiException as e:
            logger.error("Error: %s", e)
            file_data = e.raw
            errors = client.extract_errors_from_data(file_data)
            if errors:
                error_code = errors[0].code
                error_explanation = client.explain_error_code(error_code)
                queued = error_explanation.should_retry if error_explanation else False
                download_success = not (error_explanation.needs_checking
                                        if error_explanation else True)
                processing_success = download_success
            log = '\n'.join(error.full_log for error in errors)
            filename = 'foo.xml'  # we just need the extension
        except Exception as e:
            logger.error("Error: %s", e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            filename = 'foo.xml'  # we just need the extension
        else:
            file_data = client.report_to_string(report)
            filename = 'foo.tsv'  # we just need the extension
            contains_data = True
            download_success = True
            processing_success = True
        if file_data:
            data_file = ContentFile(file_data)
            data_file.name = filename
        when_queued = now() if queued else None
        return dict(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            download_success=download_success,
            processing_success=processing_success,
            data_file=data_file,
            log=log,
            error_code=error_code,
            contains_data=contains_data,
            queued=queued,
            when_queued=when_queued,
        )

    def _fetch_report_v5(self, client, counter_report, start_date, end_date) -> dict:
        file_data = None
        contains_data = False
        download_success = False
        processing_success = False
        data_file = None
        filename = 'foo.json'
        queued = False
        error_code = ''
        # we want extra split data from the report
        params = client.EXTRA_PARAMS['maximum_split'].get(counter_report.code.lower(), {})
        try:
            report = client.get_report_data(counter_report.code, start_date, end_date,
                                            params=params)
        except requests.exceptions.ConnectionError as e:
            logger.error('Connection error: %s', e)
            error_code = 'connection'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
        except Exception as e:
            logger.error('Error: %s', e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
        else:
            download_success = True
            # check for errors
            if report.errors:
                logger.error('Found errors: %s', report.errors)
                log = '; '.join(str(e) for e in report.errors)
                error_code = report.errors[0].code
                contains_data = False
                error_explanation = client.explain_error_code(error_code)
                queued = error_explanation.should_retry if error_explanation else False
                processing_success = not (error_explanation.needs_checking
                                          if error_explanation else True)
            else:
                contains_data = True
                processing_success = True
                queued = report.queued
                file_data = client.report_to_string(report.raw_data)
                log = ''
        # now create the attempt instance
        if file_data:
            data_file = ContentFile(file_data)
            data_file.name = filename
        when_queued = now() if queued else None
        return dict(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            download_success=download_success,
            data_file=data_file,
            queued=queued,
            log=log,
            error_code=error_code,
            contains_data=contains_data,
            processing_success=processing_success,
            when_queued=when_queued,
        )


def where_to_store(instance: 'SushiFetchAttempt', filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    return f'counter/{instance.credentials.organization.internal_id}/' \
           f'{instance.credentials.platform.short_name}/' \
           f'{instance.credentials.counter_version}_{instance.counter_report.code}_{ts}{ext}'


class SushiFetchAttempt(models.Model):

    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    in_progress = models.BooleanField(default=False,
                                      help_text='True if the data is still downloading')
    download_success = models.BooleanField(default=False,
                                           help_text="True if there was no error downloading data")
    processing_success = models.BooleanField(default=False,
                                             help_text="True if there was no error extracting "
                                                       "data from the downloaded material")
    contains_data = models.BooleanField(default=False,
                                        help_text='Does the report actually contain data for '
                                                  'import')
    import_crashed = models.BooleanField(default=False,
                                         help_text='Set to true if there was an error during '
                                                   'data import. Details in log and '
                                                   'processing_info')
    queued = models.BooleanField(default=False,
                                 help_text='Was the attempt queued by the provider and should be '
                                           'refetched?')
    when_queued = models.DateTimeField(null=True, blank=True)
    queue_previous = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                       related_query_name='queue_following')
    data_file = models.FileField(upload_to=where_to_store, blank=True, null=True)
    log = models.TextField(blank=True)
    error_code = models.CharField(max_length=12, blank=True)
    is_processed = models.BooleanField(default=False,
                                       help_text='Was the data converted into logs?')
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)
    processing_info = JSONField(default=dict, help_text='Internal info')

    def __str__(self):
        return f'{self.status}: {self.credentials}, {self.counter_report}'

    @property
    def status(self):
        status = 'SUCCESS'
        if not self.download_success:
            status = 'FAILURE'
        elif not self.processing_success:
            status = 'BROKEN'
        elif not self.contains_data:
            status = 'NO_DATA'
        if self.queued:
            status = 'QUEUED'
        return status

    def mark_processed(self):
        if not self.is_processed:
            self.is_processed = True
            self.when_processed = now()
            self.save()

    @property
    def ok(self):
        return self.download_success and self.processing_success

    def retry(self):
        attempt = self.credentials.fetch_report(counter_report=self.counter_report,
                                                start_date=self.start_date,
                                                end_date=self.end_date)
        attempt.queue_previous = self
        attempt.save()
        return attempt

    def previous_attempt_count(self):
        """
        Goes through the possible linked list of queue_previous and counts the how long the list
        is.
        """
        count = 0
        current = self
        while current.queue_previous:
            count += 1
            current = current.queue_previous
        return count

    def retry_interval_simple(self) -> Optional[timedelta]:
        """
        Return the time interval after which it makes sense to retry. If None, it means no retry
        should be made unless something is changes - there was no error or the error was permanent
        """
        if not self.error_code:
            return None
        exp = SushiClientBase.explain_error_code(self.error_code)
        delta = exp.retry_interval_timedelta if exp else timedelta(days=30)
        return delta

    def retry_interval(self) -> Optional[timedelta]:
        """
        Retry interval taking into account how many previous attempts there already were
        by using exponential back-off
        """
        prev_count = self.previous_attempt_count()
        interval = self.retry_interval_simple()
        if not interval:
            return None
        if prev_count > settings.QUEUED_SUSHI_MAX_RETRY_COUNT:
            # we reached the maximum number of retries, we do not continue
            return None
        return interval * (2**prev_count)

    def when_to_retry(self) -> Optional[datetime]:
        """
        Uses the information about error (by using self.retry_interval) and self.when_queued to
        guess when (in absolute terms) it makes sense to retry
        """
        interval = self.retry_interval()
        if not interval:
            return now()
        ref_time = self.when_queued or self.timestamp
        return ref_time + interval

    def mark_crashed(self, exception):
        if self.log:
            self.log += '\n'
        self.log += str(exception)
        self.import_crashed = True
        self.processing_info['import_crash_traceback'] = traceback.format_exc()
        self.save()
