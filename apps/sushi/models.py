import json
import os
import logging
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from django.contrib.postgres.fields import JSONField
from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now
from pycounter.exceptions import SushiException

from logs.models import ImportBatch
from nigiri.client import Sushi5Client, Sushi4Client, SushiException as SushiExceptionNigiri
from nigiri.counter4 import Counter4JR1Report, Counter4BR2Report, Counter4DB1Report
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
    ('JR1a', 4, None),
    ('JR1GOA', 4, None),
    ('JR2', 4, None),
    ('JR5', 4, None),
    ('BR1', 4, None),
    ('BR2', 4, Counter4BR2Report),
    ('BR3', 4, None),
    ('DB1', 4, Counter4DB1Report),
    ('DB2', 4, None),
    ('PR1', 4, None),
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

    def fetch_report(self, counter_report: CounterReportType, start_date, end_date) -> \
            'SushiFetchAttempt':
        client = self.create_sushi_client()
        if self.counter_version == 4:
            attempt = self._fetch_report_v4(client, counter_report, start_date, end_date)
        else:
            attempt = self._fetch_report_v5(client, counter_report, start_date, end_date)
        return attempt

    def _fetch_report_v4(self, client, counter_report, start_date, end_date) -> \
            'SushiFetchAttempt':
        file_data = None
        success = True
        log = ''
        data_file = None
        filename = None
        try:
            report = client.get_report_data(counter_report.code, start_date, end_date,
                                            params={'sushi_dump': True})
        except SushiException as e:
            logger.error("Error: %s", e)
            file_data = e.raw
            success = False
            errors = client.extract_errors_from_data(file_data)
            log = '\n'.join(errors)
            filename = 'foo.xml'  # we just need the extension
        except Exception as e:
            logger.error("Error: %s", e)
            success = False
            errors = [str(e)]
            log = '\n'.join(errors)
            filename = 'foo.xml'  # we just need the extension
        else:
            file_data = client.report_to_string(report)
            filename = 'foo.tsv'  # we just need the extension
        if file_data:
            data_file = ContentFile(file_data)
            data_file.name = filename
        attempt = SushiFetchAttempt.objects.create(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            success=success,
            data_file=data_file,
            log=log,
        )
        return attempt

    def _fetch_report_v5(self, client, counter_report, start_date, end_date) -> \
            'SushiFetchAttempt':
        file_data = None
        success = True
        data_file = None
        filename = 'foo.json'
        errors = []
        queued = False
        # we want extra split data from the report
        params = client.EXTRA_PARAMS['maximum_split'].get(counter_report.code.lower(), {})
        try:
            report = client.get_report_data(counter_report.code, start_date, end_date,
                                            params=params)
        except requests.exceptions.ConnectionError as e:
            logger.error('Connection error: %s', e)
            errors = [str(e)]
            success = False
        except Exception as e:
            logger.error('Error: %s', e)
            errors = [str(e)]
            success = False
        else:
            # check for errors
            if report.errors:
                logger.error('Found errors: %s', report.errors)
                errors = [str(e) for e in report.errors]
                success = False
                if type(file_data) is dict:
                    file_data = json.dumps(file_data)
            else:
                success = True
                queued = report.queued
                file_data = client.report_to_string(report.raw_data)
        # now create the attempt instance
        log = '\n'.join(errors)
        if file_data:
            data_file = ContentFile(file_data)
            data_file.name = filename
        attempt = SushiFetchAttempt.objects.create(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            success=success,
            data_file=data_file,
            queued=queued,
            log=log,
        )
        return attempt


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
    success = models.BooleanField()
    queued = models.BooleanField(default=False,
                                 help_text='Was the attempt queued by the provider and should be '
                                           'refetched?')
    data_file = models.FileField(upload_to=where_to_store)
    log = models.TextField(blank=True)
    is_processed = models.BooleanField(default=False,
                                       help_text='Was the data converted into logs?')
    when_processed = models.DateTimeField(null=True, blank=True)
    when_queued = models.DateTimeField(null=True, blank=True)
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        status = 'SUCCESS' if self.success else 'FAILURE'
        return f'{status}: {self.credentials}, {self.counter_report}'

    def mark_processed(self):
        if not self.is_processed:
            self.is_processed = True
            self.when_processed = now()
            self.save()
