import json
import logging
import os
import traceback
from copy import deepcopy
from datetime import timedelta, date
from functools import reduce
from hashlib import blake2b
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
from django.utils.translation import gettext_lazy as _
from pycounter.exceptions import SushiException
from rest_framework.exceptions import PermissionDenied

from core.logic.dates import parse_date
from core.models import UL_CONS_ADMIN, UL_ORG_ADMIN, UL_CONS_STAFF, CreatedUpdatedMixin, User
from core.task_support import cache_based_lock
from logs.models import AccessLog, ImportBatch
from nigiri.client import (
    Sushi5Client,
    Sushi4Client,
    SushiException as SushiExceptionNigiri,
    SushiClientBase,
    SushiError,
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

    def not_fake(self):
        """ List credentials which are not from fake URLs """
        # Constructs condition - Q() | Q(url__icontains=url1) | Q(url__icontains=url2) ...
        cond = reduce(
            lambda x, y: x | models.Q(url__icontains=y), settings.FAKE_SUSHI_URLS, models.Q()
        )
        return self.exclude(cond)


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

        status = AttemptStatus.INITIAL
        partial_data = False
        when_processed = None
        log = ''
        error_code = ''
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
            try:
                errors = client.extract_errors_from_data(file_data)
                if errors:
                    error_code = errors[0].code
                    if error_code == 'non-sushi':
                        # this is an exception in pycounter itself, not an exception extracted
                        # from SUSHI response
                        # lets add the exception to the errors as it cannot be collected by
                        # `client.extract_errors_from_data`
                        status = AttemptStatus.PARSING_FAILED
                        errors.insert(
                            0,
                            SushiError(
                                code='non-sushi',
                                text=str(e),
                                full_log=str(e),
                                severity='Exception',
                            ),
                        )
                    else:
                        error_code = int(error_code)
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

                if status == AttemptStatus.INITIAL:
                    # the status has not been set yet
                    # Mark that status is no data when there is no data error
                    # Otherwise mark as failed download
                    if any(
                        str(e.code)
                        in (
                            str(ErrorCode.NO_DATA_FOR_DATE_ARGS.value),
                            str(ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value),
                        )
                        for e in errors
                    ):
                        status = AttemptStatus.NO_DATA
                    else:
                        status = AttemptStatus.DOWNLOAD_FAILED

                log = '\n'.join(error.full_log for error in errors)
                filename = 'foo.xml'  # we just need the extension
            except Exception as e:
                # if this happens, it means we were not able to handle the data correctly
                # and something failed in our own code - we want a traceback and error report
                # in the logger
                status = AttemptStatus.PARSING_FAILED
                logger.error("Incorrect sushi format: %s", e)
                error_code = 'wrong-sushi'
                log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
                filename = 'foo.xml'  # we just need the extension

        except Exception as e:
            status = AttemptStatus.PARSING_FAILED
            logger.error("Error: %s", e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            filename = 'foo.xml'  # we just need the extension
        else:
            if len(report.pubs) > 0:
                status = AttemptStatus.IMPORTING
            else:
                status = AttemptStatus.NO_DATA
        finally:
            when_processed = now()

        if report:
            # Write tsv report
            data_file = ContentFile(client.report_to_string(report))
        else:
            # Write error file
            file_data.seek(0)
            data_file = File(file_data)

        data_file.name = filename

        return dict(
            status=status,
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            data_file=data_file,
            log=log,
            error_code=error_code,
            when_processed=when_processed,
            partial_data=partial_data,
        )

    def _fetch_report_v5(
        self, client: Sushi5Client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> dict:
        status = AttemptStatus.INITIAL
        when_processed = None
        partial_data = False
        filename = 'foo.json'
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
            status = AttemptStatus.DOWNLOAD_FAILED
        except SushiExceptionNigiri as e:
            logger.warning('Error: %s', e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            status = AttemptStatus.PARSING_FAILED
        except Exception as e:
            logger.error('Error: %s', e)
            error_code = 'non-sushi'
            log = f'Exception: {e}\nTraceback: {traceback.format_exc()}'
            status = AttemptStatus.PARSING_FAILED
        else:
            # Check for partial data
            partial_data = any(
                str(w.code)
                in (
                    str(ErrorCode.PARTIAL_DATA_RETURNED.value),
                    str(ErrorCode.NO_LONGER_AVAILABLE.value),
                )
                for w in report.warnings
            )
            # override default status
            error_code = ''
            error_code = (
                str(ErrorCode.NO_LONGER_AVAILABLE.value)
                if any(
                    str(w.code) == str(ErrorCode.NO_LONGER_AVAILABLE.value) for w in report.warnings
                )
                else error_code
            )
            error_code = (
                str(ErrorCode.PARTIAL_DATA_RETURNED.value)
                if any(
                    str(w.code) == str(ErrorCode.PARTIAL_DATA_RETURNED.value)
                    for w in report.warnings
                )
                else error_code
            )

            # append to log
            log = ''
            if report.errors:
                log += 'Errors: ' + '; '.join(str(e) for e in report.errors) + '\n' * 2
            if report.infos:
                log = 'Infos: ' + '; '.join(str(e) for e in report.infos) + '\n' * 2
            if report.warnings:
                log += 'Warnings: ' + '; '.join(str(e) for e in report.warnings) + "\n" * 2

            # This indicates fatal error
            error = report.errors or (report.warnings and not report.record_found)
            if error:
                if report.errors:
                    logger.warning('Found errors: %s', report.errors)
                    error_obj = report.errors[0]
                elif report.warnings:
                    error_obj = report.warnings[0]

                if isinstance(error_obj, TransportError):
                    # transport error means something bad and no valid json in response
                    status = AttemptStatus.DOWNLOAD_FAILED
                    error_code = 'non-sushi'
                else:
                    error_code = str(error_obj.code) if hasattr(error_obj, 'code') else ''

                    # Mark that status is no data when there is no data error
                    # Otherwise mark as failed download
                    if str(error_code) in (
                        str(ErrorCode.NO_DATA_FOR_DATE_ARGS.value),
                        str(ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value),
                    ):
                        status = AttemptStatus.NO_DATA
                    else:
                        status = AttemptStatus.DOWNLOAD_FAILED

                    when_processed = now()
            else:
                if partial_data:
                    # Treat partial data as if download failed
                    # we want to proceed only with complete data
                    status = AttemptStatus.DOWNLOAD_FAILED
                else:
                    if report.record_found:
                        status = AttemptStatus.IMPORTING
                    else:
                        status = AttemptStatus.NO_DATA

        # now create the attempt instance
        file_data.seek(0)  # make sure that file is rewind to the start
        django_file = File(file_data)
        django_file.name = filename

        return dict(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            status=status,
            data_file=django_file,
            log=log,
            error_code=error_code,
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

    def successful(self):
        return self.filter(status__in=AttemptStatus.successes())

    def current_or_successful(self):
        return self.current() | self.successful()


class AttemptStatus(models.TextChoices):
    # -> DOWNLOADING, CANCELED
    INITIAL = 'initial', _("Initial")
    # -> PARSING_FAILED, DOWNLOAD_FAILED, NO_DATA, CANCELED, IMPORTING
    DOWNLOADING = 'downloading', _("Downloading")
    # -> SUCCESS, IMPORT_FAILED, CANCELED, NO_DATA
    IMPORTING = 'importing', _("Importing")

    # Terminators
    # -> IMPORTING
    SUCCESS = 'success', _("Success")
    # -> IMPORTING
    UNPROCESSED = 'unprocessed', _("Unprocessed")
    # -> IMPORTING
    NO_DATA = 'no_data', _("No data")
    # -> IMPORTING
    IMPORT_FAILED = 'import_failed', _("Import failed")
    PARSING_FAILED = 'parsing_failed', _("Parsing failed")
    DOWNLOAD_FAILED = 'download_failed', _("Download failed")
    CANCELED = 'canceled', _("Canceled")

    @classmethod
    def terminated(cls):
        return {
            cls.SUCCESS,
            cls.UNPROCESSED,
            cls.NO_DATA,
            cls.IMPORT_FAILED,
            cls.PARSING_FAILED,
            cls.DOWNLOAD_FAILED,
        }

    @classmethod
    def running(cls):
        return {e for e in cls} - cls.terminated()

    @classmethod
    def errors(cls):
        return {
            cls.IMPORT_FAILED,
            cls.PARSING_FAILED,
            cls.DOWNLOAD_FAILED,
        }

    @classmethod
    def warnings(cls):
        return {cls.NO_DATA, cls.CANCELED}

    @classmethod
    def successes(cls):
        return {cls.SUCCESS}

    @classmethod
    def unprocessable(cls):
        return {cls.SUCCESS, cls.NO_DATA, cls.IMPORT_FAILED, cls.PARSING_FAILED, cls.UNPROCESSED}


class SushiFetchAttempt(models.Model):

    objects = SushiFetchAttemptQuerySet.as_manager()

    status = models.CharField(
        max_length=20, choices=AttemptStatus.choices, default=AttemptStatus.INITIAL
    )

    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
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
        return self.status in [AttemptStatus.IMPORTING]

    def mark_processed(self):
        if self.status in AttemptStatus.terminated() and not self.when_processed:
            self.when_processed = now()
            self.save()

    @property
    def ok(self):
        return self.status not in AttemptStatus.errors()

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
        self.status = AttemptStatus.IMPORT_FAILED
        self.processing_info['import_crash_traceback'] = traceback.format_exc()
        self.save()

    @atomic
    def unprocess(self) -> Optional[dict]:
        """
        Changes the sushi attempt to undo changes of it being processed. This includes:
        * deleting any data related to the import_batch
        * deleting the import_batch itself
        * and mark attempt as if it didn't crashed
        """
        if self.status not in AttemptStatus.unprocessable():
            return None

        stats = {}

        if self.import_batch:
            stats = self.import_batch.delete()  # deletes the access logs as well
            self.import_batch = None
        self.status = AttemptStatus.UNPROCESSED
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

        if self.status == AttemptStatus.DOWNLOAD_FAILED:
            self.update_broken_credentials()
            self.update_broken_report_type()

    def any_success_lately(self, days: int = 15) -> bool:
        for attempt in SushiFetchAttempt.objects.filter(
            credentials=self.credentials, credentials_version_hash=self.credentials_version_hash,
        ).filter(when_processed__gte=now() - timedelta(days=days)):
            if attempt.status in (AttemptStatus.NO_DATA, AttemptStatus.SUCCESS):
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
