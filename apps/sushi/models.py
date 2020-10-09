import os
import json
import logging
import traceback
from copy import deepcopy
from datetime import timedelta, datetime, date
from hashlib import blake2b
from itertools import takewhile
from tempfile import TemporaryFile
from typing import Optional, Dict, Iterable, IO, Union

import requests
import reversion
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.files.base import ContentFile, File
from django.db import models
from django.db.models import F, Exists, Max, OuterRef
from django.db.transaction import atomic
from django.utils.timezone import now
from pycounter.exceptions import SushiException
from rest_framework.exceptions import PermissionDenied

from core.logic.dates import month_end, parse_date
from core.models import UL_CONS_ADMIN, UL_ORG_ADMIN, UL_CONS_STAFF, User
from core.task_support import cache_based_lock
from logs.models import AccessLog, ImportBatch
from nigiri.client import (
    Sushi5Client,
    Sushi4Client,
    SushiException as SushiExceptionNigiri,
    SushiClientBase,
    SushiErrorMeaning,
)
from nigiri.counter4 import (
    Counter4JR1Report,
    Counter4BR2Report,
    Counter4DB1Report,
    Counter4PR1Report,
    Counter4BR1Report,
    Counter4JR2Report,
    Counter4DB2Report,
    Counter4BR3Report,
)
from nigiri.counter5 import Counter5DRReport, Counter5PRReport, Counter5TRReport, TransportError
from nigiri.error_codes import ErrorCode
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


NO_DATA_RETRY_PERIOD = timedelta(days=45)  # cca month and half
NO_DATA_READY_PERIOD = timedelta(days=7)


class BrokenCredentialsMixin(models.Model):
    BROKEN_HTTP = 'http'
    BROKEN_SUSHI = 'sushi'

    BROKEN_CHOICES = (
        (BROKEN_HTTP, 'HTTP'),
        (BROKEN_SUSHI, 'SUSHI'),
    )

    first_broken_attempt = models.OneToOneField(
        'SushiFetchAttempt',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Which was the first broken attempt",
    )
    broken = models.CharField(
        max_length=20,
        choices=BROKEN_CHOICES,
        null=True,
        help_text="Indication that credentails are broken",
    )

    def set_broken(self, attempt: 'SushiFetchAttempt', broken_type: str):
        if self.first_broken_attempt is None:
            self.first_broken_attempt = attempt
        self.broken = broken_type
        self.save()

    def unset_broken(self):
        self.broken = None
        self.first_broken_attempt = None
        self.save()

    class Meta:
        abstract = True


class CounterReportType(models.Model):

    CODE_CHOICES = [(cr[0], cr[0]) for cr in COUNTER_REPORTS]

    code = models.CharField(max_length=10, choices=CODE_CHOICES)
    name = models.CharField(max_length=128, blank=True)
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    report_type = models.OneToOneField('logs.ReportType', on_delete=models.CASCADE)
    active = models.BooleanField(
        default=True,
        help_text='When turned off, this type of report will not be ' 'automatically downloaded',
    )

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


class SushiCredentialsQuerySet(models.QuerySet):
    def working(self):
        """ Were these credentials working? Do we have any data? """
        return self.annotate(
            has_access_log=Exists(
                AccessLog.objects.filter(
                    import_batch__sushifetchattempt__credentials_id=OuterRef('pk')
                )
            )
        ).filter(has_access_log=True)


class SushiCredentials(BrokenCredentialsMixin):

    objects = SushiCredentialsQuerySet.as_manager()

    UNLOCKED = 0

    LOCK_LEVEL_CHOICES = (
        (UNLOCKED, 'Unlocked'),
        (UL_ORG_ADMIN, 'Organization admin'),
        (UL_CONS_STAFF, 'Consortium staff'),
        (UL_CONS_ADMIN, 'Superuser'),
    )
    BLAKE_HASH_SIZE = 16

    title = models.CharField(max_length=120, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    url = models.URLField()
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    requestor_id = models.CharField(max_length=128, blank=True)
    customer_id = models.CharField(max_length=128)
    http_username = models.CharField(max_length=128, blank=True)
    http_password = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=128, blank=True)
    extra_params = JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    counter_reports = models.ManyToManyField(
        CounterReportType,
        through='CounterReportsToCredentials',
        through_fields=('credentials', 'counter_report'),
        related_name='sushicredentials_set',
    )
    outside_consortium = models.BooleanField(
        default=False,
        help_text='True if these credentials belong to access bought outside of the consortium - '
        'necessary for proper cost calculation',
    )
    # meta info
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    lock_level = models.PositiveSmallIntegerField(
        choices=LOCK_LEVEL_CHOICES,
        default=UL_ORG_ADMIN,
        help_text='Only user with the same or higher level can unlock it and/or edit it',
    )
    version_hash = models.CharField(
        max_length=BLAKE_HASH_SIZE * 2, help_text='Current hash of model attributes'
    )

    class Meta:
        unique_together = (('organization', 'platform', 'counter_version', 'title'),)
        verbose_name_plural = 'Sushi credentials'

    def __str__(self):
        return f'{self.organization} - {self.platform}, {self.get_counter_version_display()}'

    def save(self, *args, **kwargs):
        """
        We override the parent save method to make sure `version_hash` is recomputed on each save
        """
        computed_hash = self.compute_version_hash()
        with atomic():
            if self.version_hash != computed_hash:
                self.version_hash = computed_hash
                # remove broken flag
                self.broken = None
                self.first_broken_attempt = None

                # remove broken from all reports to credentials
                CounterReportsToCredentials.objects.filter(credentials=self).update(
                    first_broken_attempt=None, broken=None,
                )

            super().save(*args, **kwargs)

    def change_lock(self, user: User, level: int):
        """
        Set the lock_level on this object
        """
        owner_level = user.organization_relationship(self.organization_id)
        if self.lock_level > self.UNLOCKED:
            # we want to relock with different privileges
            if owner_level < self.lock_level:
                raise PermissionDenied(
                    f'User {user} does not have high enough privileges ' f'to lock {self}'
                )
        if owner_level < level:
            raise PermissionDenied(
                f'User {user} does not have high enough privileges '
                f'to lock {self} to level {level}'
            )
        with reversion.create_revision():
            self.lock_level = level
            self.save()
            reversion.set_comment('Lock changed')

    def can_edit(self, user: User):
        owner_level = user.organization_relationship(self.organization_id)
        if owner_level >= self.lock_level:
            return True
        return False

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
            return Sushi4Client(extra_params=extra, **attrs)
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
        last_attempts = self.sushifetchattempt_set.order_by('-timestamp').values(
            'error_code', 'timestamp'
        )[:16]
        too_many_attempts = list(takewhile(lambda x: x['error_code'] == '1020', last_attempts))
        if too_many_attempts:
            seconds = base_wait_unit * 2 ** len(too_many_attempts)
            last_timestamp = too_many_attempts[0]['timestamp']
            diff = (last_timestamp + timedelta(seconds=seconds) - now()).seconds
            if diff > 0:
                return diff
        return 0

    def version_dict(self) -> Dict:
        """
        Returns a dictionary will all the attributes of this object that may be subject to
        change between versions and which influence success with querying the remote
        server.
        It is used to store credentials version information with SushiFetchAttempts and as a
        source for hashing for `credentials_version_hash`.
        :return:
        """
        keys = {
            'url',
            'counter_version',
            'requestor_id',
            'customer_id',
            'http_username',
            'http_password',
            'api_key',
            'extra_params',
        }
        return {key: getattr(self, key) for key in keys}

    @classmethod
    def hash_version_dict(cls, data):
        """
        Return a has of a dictionary. Must take care of possible differences in ordering of keys
        :param data:
        :return:
        """
        dump = json.dumps(data, ensure_ascii=False, sort_keys=True)
        return blake2b(dump.encode('utf-8'), digest_size=cls.BLAKE_HASH_SIZE).hexdigest()

    def compute_version_hash(self):
        """
        A hash of the variable things of current credentials  - may be used to detect changes
        in credentials.
        :return:
        """
        return self.hash_version_dict(self.version_dict())

    def fetch_report(
        self,
        counter_report: CounterReportType,
        start_date: Union[str, date],
        end_date: Union[str, date],
        fetch_attempt: 'SushiFetchAttempt' = None,
        use_url_lock=True,
    ) -> 'SushiFetchAttempt':
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

        if isinstance(start_date, str):
            start_date = parse_date(start_date)

        if isinstance(end_date, str):
            end_date = parse_date(end_date)

        client = self.create_sushi_client()
        output_file = TemporaryFile("w+b")
        fetch_m = self._fetch_report_v4 if self.counter_version == 4 else self._fetch_report_v5
        if use_url_lock:
            with cache_based_lock(self.url_lock_name):
                attempt_params = fetch_m(client, counter_report, start_date, end_date, output_file)
        else:
            attempt_params = fetch_m(client, counter_report, start_date, end_date, output_file)
        attempt_params['in_progress'] = False
        # add version info to the attempt
        attempt_params['credentials_version_hash'] = self.version_hash
        # now store it - into an existing object or a new one
        if fetch_attempt:
            for key, value in attempt_params.items():
                setattr(fetch_attempt, key, value)
            fetch_attempt.processing_info['credentials_version'] = self.version_dict()
            fetch_attempt.save()
        else:
            if 'processing_info' in attempt_params:
                attempt_params['processing_info']['credentials_version'] = self.version_dict()
            else:
                attempt_params['processing_info'] = {'credentials_version': self.version_dict()}
            fetch_attempt = SushiFetchAttempt.objects.create(**attempt_params)

        fetch_attempt.update_broken()

        return fetch_attempt

    def _fetch_report_v4(
        self, client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> dict:
        contains_data = False
        download_success = False
        processing_success = False
        is_processed = False
        when_processed = None
        log = ''
        error_code = ''
        queued = False
        params = self.extra_params or {}
        params['sushi_dump'] = True
        filename = 'foo.tsv'  # we just need the extension
        report = None

        try:
            report = client.get_report_data(
                counter_report.code, start_date, end_date, output_content=file_data, params=params,
            )
        except SushiException as e:
            logger.warning("pycounter Error: %s", e)
            errors = client.extract_errors_from_data(file_data)
            if errors:
                error_code = errors[0].code
                error_explanation = client.explain_error_code(
                    error_code, SushiFetchAttempt.fetched_near_end_date(end_date, datetime.now())
                )
                queued = error_explanation.should_retry and error_explanation.setup_ok
                download_success = (
                    not error_explanation.needs_checking and error_explanation.setup_ok
                )
                processing_success = download_success

                # mark as processed (for outdated 3030 reports)
                if (
                    error_explanation.setup_ok
                    and not error_explanation.should_retry
                    and not error_explanation.needs_checking
                ):
                    is_processed = True
                    when_processed = now()
            log = '\n'.join(error.full_log for error in errors)
            filename = 'foo.xml'  # we just need the extension
        except Exception as e:
            logger.error("Error: %s", e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            filename = 'foo.xml'  # we just need the extension
        else:
            contains_data = True
            download_success = True
            processing_success = True

        if report:
            # Write tsv report
            data_file = ContentFile(client.report_to_string(report))
        else:
            # Write error file
            file_data.seek(0)
            data_file = File(file_data)

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
            is_processed=is_processed,
            when_processed=when_processed,
        )

    def _fetch_report_v5(
        self, client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> dict:
        contains_data = False
        download_success = False
        processing_success = False
        is_processed = False
        when_processed = None
        filename = 'foo.json'
        queued = False
        error_code = ''
        # we want extra split data from the report
        # params must be a copy, otherwise we will pollute EXTRA_PARAMS
        params = deepcopy(client.EXTRA_PARAMS['maximum_split'].get(counter_report.code.lower(), {}))
        extra = self.extra_params or {}
        params.update(extra)
        http_status_code = None
        try:
            report = client.get_report_data(
                counter_report.code, start_date, end_date, output_content=file_data, params=params
            )
            http_status_code = report.http_status_code
        except requests.exceptions.ConnectionError as e:
            logger.warning('Connection error: %s', e)
            error_code = 'connection'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
        except SushiExceptionNigiri as e:
            logger.warning('Error: %s', e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
        except Exception as e:
            logger.error('Error: %s', e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
        else:
            download_success = True
            contains_data = report.record_found

            error = report.errors or (report.warnings and not report.record_found)
            # check for errors
            if error:
                if report.errors:
                    logger.warning('Found errors: %s', report.errors)
                    log = '; '.join(str(e) for e in report.errors)
                    error_obj = report.errors[0]
                else:
                    log = 'Warnings: ' + '; '.join(str(e) for e in report.warnings)
                    error_obj = report.warnings[0]

                if isinstance(error_obj, TransportError):
                    # transport error means something bad and no valid json in response
                    queued = False
                    processing_success = False
                    download_success = False
                    error_code = 'non-sushi'
                else:
                    error_code = error_obj.code if hasattr(error_obj, 'code') else ''

                    error_explanation = client.explain_error_code(
                        error_code,
                        SushiFetchAttempt.fetched_near_end_date(end_date, datetime.now()),
                    )
                    queued = error_explanation.should_retry and error_explanation.setup_ok
                    processing_success = (
                        not error_explanation.needs_checking and error_explanation.setup_ok
                    )

                    # mark as processed (for outdated 3030 reports)
                    if (
                        error_explanation.setup_ok
                        and not error_explanation.should_retry
                        and not error_explanation.needs_checking
                    ):
                        is_processed = True
                        when_processed = now()
            else:
                processing_success = True
                queued = report.queued
                log = ''

        # now create the attempt instance
        file_data.seek(0)  # make sure that file is rewind to the start
        django_file = File(file_data)
        django_file.name = filename
        when_queued = now() if queued else None
        return dict(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            download_success=download_success,
            data_file=django_file,
            queued=queued,
            log=log,
            error_code=error_code,
            contains_data=contains_data,
            processing_success=processing_success,
            when_queued=when_queued,
            is_processed=is_processed,
            when_processed=when_processed,
            http_status_code=http_status_code,
        )

    def broken_report_types(self):
        return CounterReportsToCredentials.objects.filter(
            credentials=self, broken__isnull=False
        ).annotate(code=F('counter_report__code'))


def where_to_store(instance: 'SushiFetchAttempt', filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    organization = instance.credentials.organization
    return (
        f'counter/{organization.internal_id or organization.pk}/'
        f'{instance.credentials.platform.short_name}/'
        f'{instance.credentials.counter_version}_{instance.counter_report.code}_{ts}{ext}'
    )


class SushiFetchAttemptQuerySet(models.QuerySet):
    def last_queued(self):
        res = self.annotate(
            is_previous=Exists(SushiFetchAttempt.objects.filter(queue_previous=OuterRef('pk')))
        ).filter(is_previous=False)
        return res

    def current(self):
        return self.filter(credentials_version_hash=F('credentials__version_hash'))

    def successful(self, success_measure='is_processed'):
        assert success_measure in (
            'is_processed',
            'download_success',
            'processing_success',
            'contains_data',
        )
        return self.filter(**{success_measure: True})

    def current_or_successful(self, success_measure='is_processed'):
        return self.current() | self.successful(success_measure=success_measure)

    def fetched_near_end_date(self) -> models.QuerySet:
        """ Attempts which were fetchted near to end_date

        there is a chance that the provider doesn't have the data for requested period yet
        """
        return self.filter(end_date__gt=F('timestamp') - NO_DATA_RETRY_PERIOD)


class SushiFetchAttempt(models.Model):

    objects = SushiFetchAttemptQuerySet.as_manager()

    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    in_progress = models.BooleanField(
        default=False, help_text='True if the data is still downloading'
    )
    download_success = models.BooleanField(
        default=False, help_text="True if there was no error downloading data"
    )
    processing_success = models.BooleanField(
        default=False,
        help_text="True if there was no error extracting " "data from the downloaded material",
    )
    contains_data = models.BooleanField(
        default=False, help_text='Does the report actually contain data for ' 'import'
    )
    import_crashed = models.BooleanField(
        default=False,
        help_text='Set to true if there was an error during '
        'data import. Details in log and '
        'processing_info',
    )
    queued = models.BooleanField(
        default=False,
        help_text='Was the attempt queued by the provider and should be ' 'refetched?',
    )
    when_queued = models.DateTimeField(null=True, blank=True)
    queue_id = models.IntegerField(
        null=True, blank=True, help_text='Identifier for attempt queue',
    )  # None if attempt is not queued
    queue_previous = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_query_name='queue_following',
        related_name='queue_following',
    )
    data_file = models.FileField(upload_to=where_to_store, blank=True, null=True, max_length=256)
    log = models.TextField(blank=True)
    error_code = models.CharField(max_length=12, blank=True)
    http_status_code = models.PositiveSmallIntegerField(null=True)
    is_processed = models.BooleanField(default=False, help_text='Was the data converted into logs?')
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)
    credentials_version_hash = models.CharField(
        max_length=2 * SushiCredentials.BLAKE_HASH_SIZE,
        help_text='Hash computed from the credentials at the time this attempt was made',
    )
    processing_info = JSONField(default=dict, help_text='Internal info')
    triggered_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        help_text="User who triggered the attempt or null if attempt was triggered by e.g. cron",
    )

    def __str__(self):
        return f'{self.status}: {self.credentials}, {self.counter_report}'

    def save(self, *args, **kwargs):
        if not self.credentials_version_hash and self.credentials:
            self.credentials_version_hash = self.credentials.version_hash
        super().save(*args, **kwargs)

    @property
    def can_import_data(self):
        return (
            not self.is_processed
            and self.download_success
            and self.contains_data
            and not self.import_crashed
        )

    @classmethod
    def fetched_near_end_date(cls, end_date: date, when_triggered: datetime) -> bool:
        return end_date > when_triggered.date() - NO_DATA_RETRY_PERIOD

    @property
    def is_fetched_near_end_date(self) -> bool:
        """ Is attempt triggered close to end_data

        there is a chance that the provider doesn't have the data for requested period yet
        """
        return self.fetched_near_end_date(self.end_date, self.timestamp)

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

    @property
    def queueing_explanation(self):
        if not self.queued:
            return 'Not queued'
        following_count = self.queue_following.count()
        if following_count:
            return (
                f'{following_count} following attempt(s) exist - no queueing applies for '
                f'this attempt'
            )
        output = []
        cred_based_delay = self.credentials.when_can_access()
        cred_based_retry = now() + timedelta(seconds=cred_based_delay)
        output.append(f'Credentials based retry date: {cred_based_retry}')
        attempt_retry = self.when_to_retry()
        output.append(f'Attempt retry date: {attempt_retry}')
        if not attempt_retry:
            when_retry = None
        else:
            when_retry = max(attempt_retry, cred_based_retry)
        output.append('------------------')
        if when_retry and when_retry <= now():
            # we are ready to retry
            output.append('Ready to retry')
        else:
            if when_retry:
                retry_delay = when_retry - now()
                output.append(f'Too soon to retry - need {retry_delay}')
            else:
                output.append('Should not retry automatically')
        return '\n'.join(output)

    def conflicting(self, fully_enclosing: bool = False) -> Iterable['SushiFetchAttempt']:
        """
        Returns a queryset with `SushiFetchAttempts` for the same credentials, report_type and
        times as this one
        :fully_enclosing: should the conflicting attempts fully enclose self?
        :return: queryset of SushiFetchAttempts
        """
        max_start_date = self.start_date if fully_enclosing else self.end_date
        min_end_date = self.end_date if fully_enclosing else self.start_date
        return SushiFetchAttempt.objects.filter(
            credentials=self.credentials,
            counter_report=self.counter_report,
            start_date__lte=max_start_date,
            end_date__gte=min_end_date,
        ).exclude(pk=self.pk)

    def retry(self):
        with atomic():
            # set queue queue_id if not already set
            if not self.queue_id:
                self.queue_id = self.pk
                self.save()

            attempt = self.credentials.fetch_report(
                counter_report=self.counter_report,
                start_date=self.start_date,
                end_date=month_end(self.end_date),
            )
            attempt.queue_previous = self
            attempt.queue_id = self.queue_id
            attempt.triggered_by = self.triggered_by
            attempt.save()
        return attempt

    def previous_attempt_count(self):
        """
        Goes through the possible linked list of queue_previous and counts how long the list is.
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
        should be made unless something is changed - there was no error or the error was permanent
        """
        if not self.error_code:
            return None
        exp = self.error_explanation()
        delta = exp.retry_interval_timedelta if exp else timedelta(days=30)
        return delta

    def error_explanation(self) -> SushiErrorMeaning:
        exp = SushiClientBase.explain_error_code(self.error_code, self.is_fetched_near_end_date)
        return exp

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
        return interval * (2 ** prev_count)

    def when_to_retry(self) -> Optional[datetime]:
        """
        Uses the information about error (by using self.retry_interval) and self.when_queued to
        guess when (in absolute terms) it makes sense to retry
        """
        interval = self.retry_interval()
        if not interval:
            return None
        ref_time = self.when_queued or self.timestamp
        return ref_time + interval

    def mark_crashed(self, exception):
        if self.log:
            self.log += '\n'
        self.log += str(exception)
        self.import_crashed = True
        self.processing_info['import_crash_traceback'] = traceback.format_exc()
        self.save()

    @atomic
    def unprocess(self) -> dict:
        """
        Changes the sushi attempt to undo changes of it being processed. This includes:
        * deleting any data related to the import_batch
        * deleting the import_batch itself
        * changing is_processed to False
        * and mark attempt as if it didn't crashed
        """
        stats = {}
        if self.import_batch:
            stats = self.import_batch.delete()  # deletes the access logs as well
            self.import_batch = None
        self.is_processed = False
        self.import_crashed = False
        self.log = ''
        if 'import_crash_traceback' in self.processing_info:
            del self.processing_info['import_crash_traceback']
        self.save()
        return stats

    @atomic
    def update_broken(self):
        if self.credentials.version_hash != self.credentials_version_hash:
            # credentials changed -> result of this fetch attempt is irrelevant
            return

        if self.status in ('BROKEN', 'FAILURE'):
            self.update_broken_credentials()
            self.update_broken_report_type()

    def any_success_lately(self, days: int = 15) -> bool:
        for attempt in SushiFetchAttempt.objects.filter(
            credentials=self.credentials, credentials_version_hash=self.credentials_version_hash,
        ).filter(when_processed__gte=now() - timedelta(days=days)):
            if attempt.status in ('NO_DATA', 'SUCCESS'):
                return True

        return False

    def update_broken_credentials(self):
        # Check http status code
        if self.http_status_code in (401, 403):
            self.credentials.set_broken(self, SushiCredentials.BROKEN_HTTP)
            return

        if self.http_status_code in (500, 400):
            if not self.any_success_lately():
                self.credentials.set_broken(self, SushiCredentials.BROKEN_HTTP)
                return

        # Check for sushi error
        if self.error_code in (ErrorCode.NOT_AUTHORIZED, ErrorCode.INVALID_API_KEY):
            self.credentials.set_broken(self, SushiCredentials.BROKEN_SUSHI)
            return

    def update_broken_report_type(self):
        def mark_broken(broken_type: str):
            # try to get the report
            try:
                cr2c = CounterReportsToCredentials.objects.get(
                    credentials=self.credentials, counter_report=self.counter_report
                )
                cr2c.set_broken(self, broken_type)
            except CounterReportsToCredentials.DoesNotExist:
                # Counter report was removed from credentials
                return

        if self.http_status_code in (404,):
            mark_broken(SushiCredentials.BROKEN_HTTP)
            return

        if self.error_code in (
            ErrorCode.REPORT_NOT_SUPPORTED,
            ErrorCode.REPORT_VERSION_NOT_SUPPORTED,
        ):
            mark_broken(SushiCredentials.BROKEN_SUSHI)
            return


class CounterReportsToCredentials(BrokenCredentialsMixin):
    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('credentials', 'counter_report'),)
