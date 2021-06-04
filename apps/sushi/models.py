import json
import logging
import os
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
from django.core.files.base import ContentFile, File
from django.db import models
from django.db.models import F, Exists, OuterRef
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
    Counter4MR1Report,
)
from nigiri.counter5 import (
    Counter5DRReport,
    Counter5PRReport,
    Counter5TRReport,
    TransportError,
    Counter5TableReport,
    Counter5IRM1Report,
)
from nigiri.error_codes import ErrorCode
from organizations.models import Organization
from publications.models import Platform

logger = logging.getLogger(__name__)

COUNTER_VERSIONS = (
    (4, 'COUNTER 4'),
    (5, 'COUNTER 5'),
)

COUNTER_REPORTS = (
    # (code, version, json, reader, sushi_compatible)
    # version 4
    ('JR1', 4, False, Counter4JR1Report, True),
    ('JR1a', 4, False, Counter4JR1Report, True),
    ('JR1GOA', 4, False, Counter4JR1Report, True),
    ('JR2', 4, False, Counter4JR2Report, True),
    # ('JR5', 4, False, , None, True),
    ('BR1', 4, False, Counter4BR1Report, True),
    ('BR2', 4, False, Counter4BR2Report, True),
    ('BR3', 4, False, Counter4BR3Report, True),
    ('DB1', 4, False, Counter4DB1Report, True),
    ('DB2', 4, False, Counter4DB2Report, True),
    ('PR1', 4, False, Counter4PR1Report, True),
    ('MR1', 4, False, Counter4MR1Report, True),
    # version 5
    ('TR', 5, True, Counter5TRReport, True),
    ('PR', 5, True, Counter5PRReport, True),
    ('DR', 5, True, Counter5DRReport, True),
    ('IR_M1', 5, True, Counter5IRM1Report, True),
    ('TR', 5, False, Counter5TableReport, False),
    ('PR', 5, False, Counter5TableReport, False),
    ('DR', 5, False, Counter5TableReport, False),
    ('IR', 5, False, Counter5TableReport, False),
)


class CreatedUpdatedMixin(models.Model):
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True


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
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Which was the first broken attempt",
    )
    broken = models.CharField(
        max_length=20,
        choices=BROKEN_CHOICES,
        null=True,
        blank=True,
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

    def is_broken(self):
        return True if self.broken is not None else False

    class Meta:
        abstract = True


class CounterReportType(models.Model):

    CODE_CHOICES = [(cr[0], cr[0]) for cr in COUNTER_REPORTS if cr[4]]

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

    def get_reader_class(self, json_format: bool = False):
        for code, version, reads_json, reader, sushi_compatible in COUNTER_REPORTS:
            if code == self.code and version == self.counter_version and reads_json is json_format:
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


class SushiCredentials(BrokenCredentialsMixin, CreatedUpdatedMixin):

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
    extra_params = models.JSONField(default=dict, blank=True)
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

    def create_sushi_client(self) -> SushiClientBase:
        attrs = {
            'url': self.url,
            'requestor_id': self.requestor_id,
            'customer_id': self.customer_id,
        }
        extra = self.extra_params or {}
        if self.api_key:
            extra['api_key'] = self.api_key
        if self.http_password and self.http_username and self.counter_version == 4:
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
        fetch_m = (
            self._fetch_report_v4 if isinstance(client, Sushi4Client) else self._fetch_report_v5
        )
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
        self, client: Sushi4Client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> dict:
        contains_data = False
        download_success = False
        processing_success = False
        is_processed = False
        partial_data = False
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
                queued = False
                download_success = False
                processing_success = False
                is_processed = True
                when_processed = now()

                # Check whether it contains partial data
                if any(
                    str(e.code)
                    in (
                        str(ErrorCode.PARTIAL_DATA_RETURNED.value),
                        str(ErrorCode.NO_LONGER_AVAILABLE.value),
                    )
                    for e in errors
                ):
                    partial_data = True

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
            partial_data=partial_data,
        )

    def _fetch_report_v5(
        self, client: Sushi5Client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> dict:
        contains_data = False
        download_success = False
        processing_success = False
        is_processed = False
        when_processed = None
        partial_data = False
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
            download_success = len(report.errors) == 0
            contains_data = report.record_found

            # Check for partial data
            partial_data = any(
                str(w.code)
                in (
                    str(ErrorCode.PARTIAL_DATA_RETURNED.value),
                    str(ErrorCode.NO_LONGER_AVAILABLE.value),
                )
                for w in report.warnings
            )

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

                    queued = False
                    processing_success = False
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
            partial_data=partial_data,
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
    partial_data = models.BooleanField(default=False, help_text='Data may not be complete')
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)
    credentials_version_hash = models.CharField(
        max_length=2 * SushiCredentials.BLAKE_HASH_SIZE,
        help_text='Hash computed from the credentials at the time this attempt was made',
    )
    processing_info = models.JSONField(default=dict, help_text='Internal info')
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

    @property
    def status(self):
        status = 'SUCCESS'
        if not self.download_success:
            status = 'FAILURE'
        elif not self.processing_success:
            status = 'BROKEN'
        elif not self.contains_data:
            status = 'NO_DATA'
        elif self.partial_data:
            status = 'PARTIAL_DATA'
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

    def file_is_json(self) -> Optional[bool]:
        """
        Returns True if the file seems to be a JSON file.
        """
        if not self.data_file:
            return None
        char = self.data_file.read(1)
        while char and char.isspace():
            char = self.data_file.read(1)
        self.data_file.seek(0)
        if char in b'[{':
            return True
        return False

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
                # Don't break entire credentials for specific error codes
                if str(self.error_code) not in (str(ErrorCode.INVALID_REPORT_FILTER.value),):
                    self.credentials.set_broken(self, SushiCredentials.BROKEN_HTTP)
                return

        # Check for sushi error
        if str(self.error_code) in (
            str(ErrorCode.NOT_AUTHORIZED.value),
            str(ErrorCode.NOT_AUTHORIZED_INSTITUTION.value),
            str(ErrorCode.INVALID_API_KEY.value),
            str(ErrorCode.INSUFFICIENT_DATA.value),
        ):
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

        if str(self.error_code) in (
            str(ErrorCode.REPORT_NOT_SUPPORTED.value),
            str(ErrorCode.REPORT_VERSION_NOT_SUPPORTED.value),
            str(ErrorCode.INVALID_REPORT_FILTER.value),
        ):
            mark_broken(SushiCredentials.BROKEN_SUSHI)
            return


class CounterReportsToCredentials(BrokenCredentialsMixin):
    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('credentials', 'counter_report'),)
        verbose_name_plural = 'Counter reports to credentials'
