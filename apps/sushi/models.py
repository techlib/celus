import io
import json
import logging
import os
import traceback
from copy import deepcopy
from datetime import date, timedelta
from functools import reduce
from hashlib import blake2b
from pathlib import Path
from tempfile import TemporaryFile
from time import time
from typing import IO, Dict, Iterable, Optional, Union
from urllib.parse import urlencode

import requests
import reversion
from celus_nibbler import Poop
from celus_nigiri.client import Sushi4Client, Sushi5Client, SushiClientBase, SushiError
from celus_nigiri.client import SushiException as SushiExceptionNigiri
from celus_nigiri.counter5 import Counter5ReportBase, CounterError, TransportError
from celus_nigiri.error_codes import ErrorCode
from celus_pycounter.exceptions import SushiException
from core.logic import url
from core.logic.dates import month_end, month_start, parse_date, this_month
from core.models import (
    UL_CONS_ADMIN,
    UL_CONS_STAFF,
    UL_ORG_ADMIN,
    CreatedUpdatedMixin,
    SourceFileMixin,
    User,
)
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.files.base import File
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Exists, ExpressionWrapper, F, OuterRef, Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.db.models.lookups import Exact
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from events.models import Event, EventCategory, EventImportance
from logs.exceptions import DataAlreadyPresent
from logs.models import AccessLog, ImportBatch
from nibbler.logic.processing import counter_format_poops, output_to_poops
from organizations.models import Organization
from publications.logic import knowledgebase
from publications.models import Platform
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

COUNTER_VERSIONS = ((4, "COUNTER 4"), (5, "COUNTER 5"))

COUNTER_REPORTS = (
    # version 4
    ("JR1", "Counter 4 - Journal Report 1"),
    ("JR1a", "Counter 4 - Journal Report 1a"),
    ("JR1GOA", "Counter 4 - Journal Report 1 Gold Open Access"),
    ("JR2", "Counter 4 - Journal Report 2"),
    # CounterReport# ('JR5',  'Counter X - Report4,, False, , None, True),
    ("BR1", "Counter 4 - Book Report 1"),
    ("BR2", "Counter 4 - Book Report 2"),
    ("BR3", "Counter 4 - Book Report 3"),
    ("DB1", "Counter 4 - Database Report 1"),
    ("DB2", "Counter 4 - Database Report 2"),
    ("PR1", "Counter 4 - Platform Report 1"),
    ("MR1", "Counter 4 - Multimedia Report 1"),
    # version 5
    ("TR", "Counter 5 - Title Report"),
    ("PR", "Counter 5 - Platform Report"),
    ("DR", "Counter 5 - Database Report"),
    ("IR", "Counter 5 - Item Report"),
    ("IR_M1", "Counter 5 - Multimedia Item Report 1"),
)


class BrokenCredentialsMixin(models.Model):
    BROKEN_HTTP = "http"
    BROKEN_SUSHI = "sushi"

    BROKEN_CHOICES = ((BROKEN_HTTP, "HTTP"), (BROKEN_SUSHI, "SUSHI"))

    first_broken_attempt = models.OneToOneField(
        "SushiFetchAttempt",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Which was the first broken attempt",
    )
    broken = models.CharField(  # noqa: DJ001
        max_length=20,
        choices=BROKEN_CHOICES,
        null=True,
        blank=True,
        help_text="Indication that credentials are broken",
    )

    class Meta:
        abstract = True

    def set_broken(self, attempt: "SushiFetchAttempt", broken_type: str):
        if self.first_broken_attempt is None:
            self.first_broken_attempt = attempt
        self.broken = broken_type
        self.save()

    def unset_broken(self):
        self.broken = None
        self.first_broken_attempt = None
        self.save()

    def is_broken(self):
        return self.broken is not None


class CounterReportType(models.Model):
    CODE_CHOICES = [(e[0], e[0]) for e in COUNTER_REPORTS]

    code = models.CharField(max_length=10, choices=CODE_CHOICES)
    name = models.CharField(max_length=128, blank=True)
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    report_type = models.OneToOneField("logs.ReportType", on_delete=models.CASCADE)
    active = models.BooleanField(
        default=True,
        help_text="When turned off, this type of report will not be " "automatically downloaded",
    )

    class Meta:
        unique_together = (("code", "counter_version"),)
        verbose_name_plural = "COUNTER report types"
        verbose_name = "COUNTER report type"

    def __str__(self):
        return f"{self.code} ({self.counter_version}) - {self.name}"

    def get_nibbler_parser(self, json_format: bool = False):
        name = "Json" if json_format else "Tabular"
        return f"static\\.counter{self.counter_version}\\.{self.code}\\.{name}"

    def get_counter_exporter_class(self):
        from logs.logic import export_counter

        if self.counter_version != 5:
            return None

        if self.code == "TR":
            return export_counter.TRCounter5Export
        elif self.code == "DR":
            return export_counter.DRCounter5Export
        elif self.code == "PR":
            return export_counter.PRCounter5Export
        elif self.code == "IR_M1":
            return export_counter.IR_M1Counter5Export
        elif self.code == "IR":
            return export_counter.IRCounter5Export

        return None


class SushiCredentialsQuerySet(models.QuerySet):
    def annotate_verified(self):
        """
        Annotates that credentials are verified
        this means that credentials needs to have
        download attempt (NO_DATA or SUCCESS) with current hash
        or forced_verified_hash which matches current version_hash
        """
        return self.annotate(
            verified_attempt=Exists(
                SushiFetchAttempt.objects.filter(
                    credentials_id=OuterRef("pk"),
                    status__in=[AttemptStatus.NO_DATA, AttemptStatus.SUCCESS],
                    credentials_version_hash=OuterRef("version_hash"),
                )
            ),
            verified_forced=Exact(F("forced_verified_hash"), F("version_hash")),
        ).annotate(
            verified=ExpressionWrapper(
                Q(verified_attempt=True) | Q(verified_forced=True),
                output_field=models.BooleanField(),
            )
        )

    def working(self):
        """Were these credentials working? Do we have any data?"""
        return self.annotate(
            has_access_log=Exists(
                AccessLog.objects.filter(
                    import_batch__sushifetchattempt__credentials_id=OuterRef("pk")
                )
            )
        ).filter(has_access_log=True)

    def not_fake(self):
        """List credentials which are not from fake URLs"""
        # Constructs condition - Q() | Q(url__icontains=url1) | Q(url__icontains=url2) ...
        cond = reduce(
            lambda x, y: x | Q(url__icontains=y.rstrip("/")), settings.FAKE_SUSHI_URLS, Q()
        )
        return self.exclude(cond)


class SushiCredentials(BrokenCredentialsMixin, CreatedUpdatedMixin):
    UNLOCKED = 0
    LOCK_LEVEL_CHOICES = (
        (UNLOCKED, "Unlocked"),
        (UL_ORG_ADMIN, "Organization admin"),
        (UL_CONS_STAFF, "Consortium staff"),
        (UL_CONS_ADMIN, "Superuser"),
    )
    BLAKE_HASH_SIZE = 16
    NUMBER_OF_MONTHS_REPLANNED = 2

    title = models.CharField(max_length=120, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    url = models.URLField()
    auto_update_url = models.BooleanField(default=True)
    forced_verified_hash = models.CharField(
        max_length=BLAKE_HASH_SIZE * 2,
        help_text="Force verified=True for given hash - useful to preserve verification"
        " when URL is automatically updated",
        blank=True,
    )
    counter_version = models.PositiveSmallIntegerField(choices=COUNTER_VERSIONS)
    requestor_id = models.CharField(max_length=128, blank=True)
    customer_id = models.CharField(max_length=128)
    http_username = models.CharField(max_length=128, blank=True)
    http_password = models.CharField(max_length=128, blank=True)
    api_key = models.CharField(max_length=400, blank=True)
    extra_params = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    counter_reports = models.ManyToManyField(
        CounterReportType,
        through="CounterReportsToCredentials",
        through_fields=("credentials", "counter_report"),
        related_name="sushicredentials_set",
    )
    outside_consortium = models.BooleanField(
        default=False,
        help_text="True if these credentials belong to access bought outside of the consortium - "
        "necessary for proper cost calculation",
    )
    # meta info
    lock_level = models.PositiveSmallIntegerField(
        choices=LOCK_LEVEL_CHOICES,
        default=UL_ORG_ADMIN,
        help_text="Only user with the same or higher level can unlock it and/or edit it",
    )
    version_hash = models.CharField(
        max_length=BLAKE_HASH_SIZE * 2, help_text="Current hash of model attributes"
    )

    objects = SushiCredentialsQuerySet.as_manager()

    class Meta:
        unique_together = (("organization", "platform", "counter_version", "title"),)
        verbose_name_plural = "Sushi credentials"

    def __str__(self):
        return f"{self.organization} - {self.platform}, {self.get_counter_version_display()}"

    def save(self, *args, **kwargs):
        """
        We override the parent save method to make sure `version_hash` is recomputed on each save
        """
        self.url = url.normalize_url(self.url)
        computed_hash = self.compute_version_hash()
        with atomic():
            if self.version_hash != computed_hash:
                self.version_hash = computed_hash
                # remove broken flag
                self.broken = None
                self.first_broken_attempt = None

                # remove broken from all reports to credentials
                CounterReportsToCredentials.objects.filter(credentials=self).update(
                    first_broken_attempt=None, broken=None
                )

            super().save(*args, **kwargs)

    def force_current_version_verified(self):
        """
        Forces current credentials to act as they were verified,
        even though there is no successful attempt
        """
        self.url = url.normalize_url(self.url)
        self.forced_verified_hash = self.compute_version_hash()
        if self.pk:
            # Don't use save method to preserve broken state
            SushiCredentials.objects.filter(pk=self.pk).update(
                forced_verified_hash=self.forced_verified_hash,
                version_hash=self.forced_verified_hash,
                url=self.url,
            )

    def perform_auto_update(self, new_url: str) -> bool:
        from scheduler.models import Automatic, FetchIntention, Harvest

        new_url = url.normalize_url(new_url)
        if new_url == self.url:
            return False

        verified = self.is_verified
        self.url = new_url

        if verified:
            # When credentials were verified we need to keep the verification
            # `force_current_version_verified` also saves the object to the db
            self.force_current_version_verified()

            if self.enabled:
                # Try to plan a harvest for last NUMBER_OF_MONTHS_REPLANNED

                # Remove broken status
                self.unset_broken()
                for cr2c in self.counterreportstocredentials_set.filter(broken__isnull=False):
                    cr2c.unset_broken()

                # Get related months
                current_month = this_month()
                months = [
                    current_month - relativedelta(months=i + 1)
                    for i in range(self.NUMBER_OF_MONTHS_REPLANNED)
                ]

                # Find out which months contain data
                present = {
                    (e.date, e.report_type.counterreporttype.pk)
                    for e in ImportBatch.objects.filter(
                        date__in=months,
                        organization=self.organization,
                        platform=self.platform,
                        report_type__counterreporttype__isnull=False,
                    ).select_related("report_type", "report_type__counterreporttype")
                }

                # Plan the harvests
                for month in months:
                    month_e = month_end(month)
                    automatic = Automatic.get_or_create(month, self.organization)
                    intentions = []
                    for cr2c in self.counterreportstocredentials_set.all():
                        if (month, cr2c.counter_report_id) not in present:
                            intentions.append(
                                FetchIntention(
                                    priority=FetchIntention.PRIORITY_NORMAL,
                                    credentials=self,
                                    counter_report=cr2c.counter_report,
                                    start_date=month,
                                    end_date=month_e,
                                )
                            )

                    if intentions:
                        Harvest.plan_harvesting(intentions, automatic.harvest)

        # Save will update the hashes
        self.save()

        return True

    def change_lock(self, user: User, level: int):
        """
        Set the lock_level on this object
        """
        owner_level = user.organization_relationship(self.organization_id)
        if self.lock_level > self.UNLOCKED and owner_level < self.lock_level:
            raise PermissionDenied(
                f"User {user} does not have high enough privileges to lock {self}"
            )
        if owner_level < level:
            raise PermissionDenied(
                f"User {user} does not have high enough privileges "
                f"to lock {self} to level {level}"
            )
        with reversion.create_revision():
            self.lock_level = level
            self.save()
            reversion.set_comment("Lock changed")

    def can_edit(self, user: User):
        owner_level = user.organization_relationship(self.organization_id)
        return owner_level >= self.lock_level

    @cached_property
    def is_verified(self):
        return (
            self.version_hash == self.forced_verified_hash
            or self.current_successful_attempts.exists()
        )

    @property
    def knowledgebase_url(self) -> Optional[str]:
        return knowledgebase.get_url(self.platform.knowledgebase or {}, self.counter_version)

    @property
    def current_successful_attempts(self):
        return self.sushifetchattempt_set.filter(
            status__in=[AttemptStatus.NO_DATA, AttemptStatus.SUCCESS],
            credentials_version_hash=self.version_hash,
        )

    def create_sushi_client(self) -> SushiClientBase:
        attrs = {
            "url": self.url,
            "requestor_id": self.requestor_id,
            "customer_id": self.customer_id,
        }
        extra = deepcopy(self.extra_params) or {}
        if self.api_key:
            extra["api_key"] = self.api_key
        if self.http_password and self.http_username and self.counter_version == 4:
            attrs["auth"] = (self.http_username, self.http_password)
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
        url_hash = blake2b(self.url.encode("utf-8"), digest_size=16).hexdigest()
        return f"url-lock-{url_hash}"

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
            "url",
            "counter_version",
            "requestor_id",
            "customer_id",
            "http_username",
            "http_password",
            "api_key",
            "extra_params",
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
        return blake2b(dump.encode("utf-8"), digest_size=cls.BLAKE_HASH_SIZE).hexdigest()

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
    ) -> "SushiFetchAttempt":
        """
        :param counter_report:
        :param start_date:
        :param end_date:
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
        fetch_attempt: SushiFetchAttempt = fetch_m(
            client, counter_report, start_date, end_date, output_file
        )
        # add version info to the attempt and store it
        fetch_attempt.credentials_version_hash = self.version_hash
        fetch_attempt.processing_info["credentials_version"] = self.version_dict()
        fetch_attempt.save()

        fetch_attempt.update_broken()

        from scheduler.logic.automatic import update_verified_for_automatic_scheduling

        # credentials may become verified
        update_verified_for_automatic_scheduling(fetch_attempt)

        return fetch_attempt

    def _fetch_report_v4(
        self, client: Sushi4Client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> "SushiFetchAttempt":
        attempt = SushiFetchAttempt(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
        )
        params = self.extra_params or {}
        params["sushi_dump"] = True
        filename = "foo.tsv"  # we just need the extension
        report = None

        try:
            report = client.get_report_data(
                counter_report.code, start_date, end_date, output_content=file_data, params=params
            )
        except SushiException as e:
            logger.warning("pycounter Error: %s", e)
            try:
                errors: [SushiError] = client.extract_errors_from_data(file_data)
                if errors:
                    error_code = errors[0].code
                    if error_code == "non-sushi":
                        # this is an exception in pycounter itself, not an exception extracted
                        # from SUSHI response
                        # lets add the exception to the errors as it cannot be collected by
                        # `client.extract_errors_from_data`
                        attempt.status = AttemptStatus.PARSING_FAILED
                        errors.insert(
                            0,
                            SushiError(
                                code="non-sushi", text=str(e), full_log=str(e), severity="Exception"
                            ),
                        )
                    else:
                        attempt.error_code = int(error_code)
                        # Check whether it contains partial data
                        if any(
                            str(e.code)
                            in (
                                str(ErrorCode.PARTIAL_DATA_RETURNED.value),
                                str(ErrorCode.NO_LONGER_AVAILABLE.value),
                            )
                            for e in errors
                        ):
                            attempt.partial_data = True

                if attempt.status == AttemptStatus.INITIAL:
                    # the status has not been set yet
                    # Mark that status is no data when there is no data error
                    # Otherwise mark as failed download
                    if any(
                        str(e.code)
                        in (
                            str(ErrorCode.PARTIAL_DATA_RETURNED.value),
                            str(ErrorCode.NO_DATA_FOR_DATE_ARGS.value),
                            str(ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value),
                        )
                        for e in errors
                    ):
                        attempt.status = AttemptStatus.NO_DATA
                    else:
                        attempt.status = AttemptStatus.DOWNLOAD_FAILED

                attempt.log = "\n".join(error.full_log for error in errors)
                filename = "foo.xml"  # we just need the extension
            except Exception as e:
                # if this happens, it means we were not able to handle the data correctly
                # and something failed in our own code - we want a traceback and error report
                # in the logger
                attempt.status = AttemptStatus.PARSING_FAILED
                logger.error("Incorrect sushi format: %s", e)
                attempt.error_code = "wrong-sushi"
                attempt.log = f"Exception: {e}\nTraceback: {traceback.format_exc()}"
                filename = "foo.xml"  # we just need the extension

        except Exception as e:
            attempt.status = AttemptStatus.PARSING_FAILED
            logger.error("Error: %s", e)
            attempt.error_code = "non-sushi"
            attempt.log = f"Exception: {e}\nTraceback: {traceback.format_exc()}"
            filename = "foo.xml"  # we just need the extension
        else:
            if len(report.pubs) > 0:
                attempt.status = AttemptStatus.IMPORTING
            else:
                attempt.status = AttemptStatus.NO_DATA
        finally:
            attempt.when_processed = now()

        if report:
            # Write tsv report into output (otherwise original file will remain there)
            data = client.report_to_string(report).encode()
            file_data.seek(0)
            file_data.truncate()
            file_data.write(data)

        # Set file of the new attempt
        file_data.seek(0)
        attempt.data_file = File(file_data)

        attempt.checksum, attempt.file_size = SourceFileMixin.checksum_fileobj(attempt.data_file)
        attempt.data_file.name = filename

        # Make sure that file is written to disk
        attempt.data_file.flush()
        try:
            os.fsync(attempt.data_file.fileno())
        except io.UnsupportedOperation:
            # we don't care if it fails here
            pass

        return attempt

    def _build_params(self, client, counter_report):
        # params must be a copy, otherwise we will pollute it with EXTRA_PARAMS
        params = deepcopy(client.EXTRA_PARAMS["maximum_split"].get(counter_report.code.lower(), {}))
        params.update(deepcopy(client.EXTRA_PARAMS["filters"].get(counter_report.code.lower(), {})))
        extra = self.extra_params or {}
        params.update(extra)
        return params

    def _v5_get_report_data(
        self, client, counter_report, start_date, end_date, file_data
    ) -> Counter5ReportBase:
        params = self._build_params(client, counter_report)
        report = client.get_report_data(
            counter_report.code, start_date, end_date, output_content=file_data, params=params
        )
        return report

    def _fetch_report_v5(
        self, client: Sushi5Client, counter_report, start_date, end_date, file_data: IO[bytes]
    ) -> "SushiFetchAttempt":
        """
        Returns an usaved SushiFetchAttempt object
        """
        url = client.make_download_url(counter_report.code)
        params = self._build_params(client, counter_report)
        params = client.make_download_params(params, start_date, end_date)
        used_url = url + "?" + urlencode(params)

        attempt = SushiFetchAttempt(
            credentials=self,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            used_url=used_url,
        )
        try:
            report = self._v5_get_report_data(
                client, counter_report, start_date, end_date, file_data
            )
        except requests.exceptions.ConnectionError as e:
            logger.warning("Connection error: %s", e)
            attempt.error_code = "connection"
            attempt.log = f"Exception: {e}\nTraceback: {traceback.format_exc()}"
            attempt.status = AttemptStatus.DOWNLOAD_FAILED
        except (SushiExceptionNigiri, Exception) as e:
            logger.log(
                logging.WARNING if isinstance(e, SushiExceptionNigiri) else logging.ERROR,
                "Error: %s",
                e,
            )
            attempt.error_code = "non-sushi"
            attempt.log = f"Exception: {e}\nTraceback: {traceback.format_exc()}"
            attempt.status = AttemptStatus.PARSING_FAILED
        else:
            # no exception, but we need to deal with SUSHI errors, etc.
            attempt.http_status_code = report.http_status_code
            attempt.extract_header_data(report.header)
            self._v5_extract_status_and_errors(report, attempt)

        # now generic stuff independent of success or failure
        file_data.seek(0)  # make sure that file is rewound to the start
        attempt.checksum, attempt.file_size = SourceFileMixin.checksum_fileobj(file_data)
        attempt.data_file = File(file_data)
        attempt.data_file.name = "foo.json"  # we just need the extension

        # Make sure that file is written to disk
        attempt.data_file.flush()
        try:
            os.fsync(attempt.data_file.fileno())
        except io.UnsupportedOperation:
            # we don't care if it fails here
            pass

        return attempt

    @classmethod
    def _stringify_error(cls, error: Union[CounterError, TransportError]) -> str:
        base = str(error)
        if data := getattr(error, "data", None):
            base += f" ({data})"
        return base

    @classmethod
    def _v5_extract_status_and_errors(
        cls, report: Counter5ReportBase, attempt: "SushiFetchAttempt"
    ) -> "SushiFetchAttempt":
        """
        Modifies `attempt` in place to fill in status, error_code, log and partial_data.
        Returns the attempt back for convenience.
        """
        # check for explicitly declared partial data
        partial_data_code = str(ErrorCode.PARTIAL_DATA_RETURNED.value)
        if w := next((w for w in report.warnings if str(w.code) == partial_data_code), None):
            attempt.error_code = str(w.code)
            attempt.partial_data = True
        # if data is present, some more error codes would mean `partial_data`
        # note: this only makes sense if more than one month is requested, which should not
        # happen in Celus. But we have tests for it and nobody knows what data we will get
        # so it is better to be prepared
        if report.record_found:
            possible_partial_codes = (
                str(ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value),
                str(ErrorCode.NO_LONGER_AVAILABLE.value),
            )
            if w := next(
                (w for w in report.warnings if str(w.code) in possible_partial_codes), None
            ):
                attempt.error_code = str(w.code)
                attempt.partial_data = True

        # append to log
        for code, errors in (
            ("Errors", report.errors),
            ("Warnings", report.warnings),
            ("Infos", report.infos),
        ):
            if errors:
                attempt.log += (
                    f"{code}: " + "; ".join(cls._stringify_error(e) for e in errors) + "\n" * 2
                )

        if report.errors or (report.warnings and not report.record_found):
            # we have either an error or a warning without any data
            if report.errors:
                logger.warning("Found errors: %s", report.errors)
                error_obj = report.errors[0]
            elif report.warnings:
                error_obj = report.warnings[0]
            else:
                raise ValueError("This should not happen")  # just a sanity check

            if isinstance(error_obj, TransportError):
                # transport error means something bad and no valid json in response
                attempt.status = AttemptStatus.DOWNLOAD_FAILED
                attempt.error_code = "non-sushi"
            else:
                attempt.error_code = str(error_obj.code) if hasattr(error_obj, "code") else ""
                # Mark that status is no data when there is no data error
                # Otherwise mark as failed download
                if str(attempt.error_code) in (
                    str(ErrorCode.NO_DATA_FOR_DATE_ARGS.value),
                    str(ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value),
                ):
                    attempt.status = AttemptStatus.NO_DATA
                else:
                    attempt.status = AttemptStatus.DOWNLOAD_FAILED

                attempt.when_processed = now()
        else:
            # no errors, if warnings then with data
            if report.record_found:
                attempt.status = AttemptStatus.IMPORTING
            else:
                attempt.status = AttemptStatus.NO_DATA
        return attempt

    def broken_report_types(self):
        return CounterReportsToCredentials.objects.filter(
            credentials=self, broken__isnull=False
        ).annotate(code=F("counter_report__code"))


# the following must stay here as it is used in a migration
# it is however not used anymore
def where_to_store(instance: "SushiFetchAttempt", filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime("%Y%m%d-%H%M%S.%f")
    organization = instance.credentials.organization
    return (
        f"counter/{organization.internal_id or organization.pk}/"
        f"{instance.credentials.platform.short_name}/"
        f"{instance.credentials.counter_version}_{instance.counter_report.code}_{ts}{ext}"
    )


class AttemptStatus(models.TextChoices):
    # -> DOWNLOADING
    INITIAL = "initial", _("Initial")
    # -> PARSING_FAILED, DOWNLOAD_FAILED, NO_DATA, NOT_USED, IMPORTING
    DOWNLOADING = "downloading", _("Downloading")
    # -> SUCCESS, IMPORT_FAILED, NO_DATA
    IMPORTING = "importing", _("Importing")

    # Terminators
    # -> IMPORTING
    SUCCESS = "success", _("Success")
    # -> IMPORTING
    NO_DATA = "no_data", _("No data")
    # -> IMPORTING
    IMPORT_FAILED = "import_failed", _("Import failed")
    PARSING_FAILED = "parsing_failed", _("Parsing failed")
    DOWNLOAD_FAILED = "download_failed", _("Download failed")
    NOT_USED = "not_used", _("Not used")

    @classmethod
    def terminated(cls):
        return {
            cls.SUCCESS,
            cls.NO_DATA,
            cls.NOT_USED,
            cls.IMPORT_FAILED,
            cls.PARSING_FAILED,
            cls.DOWNLOAD_FAILED,
        }

    @classmethod
    def running(cls):
        return set(cls) - cls.terminated()

    @classmethod
    def errors(cls):
        return {cls.IMPORT_FAILED, cls.PARSING_FAILED, cls.DOWNLOAD_FAILED}

    @classmethod
    def warnings(cls):
        return {cls.NO_DATA, cls.NOT_USED}

    @classmethod
    def successes(cls):
        return {cls.SUCCESS}

    @classmethod
    def reimportable(cls):
        return {cls.SUCCESS, cls.NO_DATA, cls.IMPORT_FAILED, cls.PARSING_FAILED}


class SushiFetchAttempt(SourceFileMixin, models.Model):
    status = models.CharField(
        max_length=20, choices=AttemptStatus.choices, default=AttemptStatus.INITIAL
    )

    credentials = models.ForeignKey(SushiCredentials, null=True, on_delete=models.SET_NULL)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    log = models.TextField(blank=True)
    error_code = models.CharField(max_length=12, blank=True)
    http_status_code = models.PositiveSmallIntegerField(null=True)
    partial_data = models.BooleanField(default=False, help_text="Data may not be complete")
    when_processed = models.DateTimeField(null=True, blank=True)
    import_batch = models.OneToOneField(ImportBatch, null=True, on_delete=models.SET_NULL)
    clashing_import_batch = models.ForeignKey(
        ImportBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If the attempt cannot be imported because of a clashing import batch, "
        "this field will contain the clashing import batch",
        related_name="clashing_attempts",
    )
    credentials_version_hash = models.CharField(
        max_length=2 * SushiCredentials.BLAKE_HASH_SIZE,
        help_text="Hash computed from the credentials at the time this attempt was made",
    )
    processing_info = models.JSONField(default=dict, help_text="Internal info")
    triggered_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        help_text="User who triggered the attempt or null if attempt was triggered by e.g. cron",
    )
    extracted_data = models.JSONField(
        default=dict, help_text="Information extracted from the SUSHI data header"
    )
    used_url = models.TextField(
        help_text="Url used for sushi harvesting",
        blank=True,
        default="",
        validators=[URLValidator()],
    )

    EXTRACTED_DATA_KEYS = ("Created_By", "Institution_Name", "Institution_ID")

    def __str__(self):
        return f"{self.status}: {self.credentials}, {self.counter_report}"

    def save(self, *args, **kwargs):
        if not self.credentials_version_hash and self.credentials:
            self.credentials_version_hash = self.credentials.version_hash
        super().save(*args, **kwargs)

    @property
    def can_import_data(self):
        return self.check_importable(False)

    def check_importable(self, raise_error=True) -> bool:
        if self.status == AttemptStatus.SUCCESS:
            if raise_error:
                raise ValueError(f"Data already imported (attempt={self.pk})")
            return False

        elif self.status == AttemptStatus.DOWNLOAD_FAILED:
            if raise_error:
                raise ValueError(f"Trying to import data when download failed (attempt={self.pk})")
            return False

        elif self.status == AttemptStatus.NO_DATA:
            if raise_error:
                raise ValueError(f"Attempt contains no data (attempt={self.pk})")
            return False

        elif self.status == AttemptStatus.IMPORT_FAILED:
            if raise_error:
                raise ValueError(f"Import of data already crashed (attempt={self.pk})")
            return False

        elif self.status != AttemptStatus.IMPORTING:
            if raise_error:
                raise ValueError(f"Could not import data (attempt={self.pk})")
            return False

        if self.import_batch:
            # Can't import when there is and existing import batch
            logger.warning(
                "Attempt #%d is in IMPORTING state and it already contains an ImportBatch #%d",
                self.pk,
                self.import_batch.pk,
            )

            if raise_error:
                raise ValueError(
                    f"Attempt already contains data (attempt={self.pk},ib={self.import_batch.pk})"
                )
            return False

        return True

    @property
    def time_gap(self):
        """
        The amount of time between the end of the harvested month and the time of the attempt.
        """
        if self.end_date and self.timestamp:
            return self.timestamp.date() - self.end_date
        return None

    def mark_processed(self):
        if self.status in AttemptStatus.terminated() and not self.when_processed:
            self.when_processed = now()
            self.save()

    @property
    def ok(self):
        return self.status not in AttemptStatus.errors()

    @staticmethod
    def file_is_json_s(data_file) -> bool:
        """
        Returns True if the file seems to be a JSON file.
        """
        char = data_file.read(1)
        while char and char.isspace():
            char = data_file.read(1)
        data_file.seek(0)
        if char and not isinstance(char, bytes):
            char = char.encode("utf-8", errors="ignore")
        return char in b"[{"

    def file_is_json(self) -> Optional[bool]:
        """
        Returns True if the `data_file` seems to be a JSON file.
        """
        if not self.data_file:
            return None
        return SushiFetchAttempt.file_is_json_s(self.data_file)

    def conflicting(self, fully_enclosing: bool = False) -> Iterable["SushiFetchAttempt"]:
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
            self.log += "\n"
        self.log += str(exception)
        self.status = AttemptStatus.IMPORT_FAILED
        self.processing_info["import_crash_traceback"] = traceback.format_exc()
        if isinstance(exception, DataAlreadyPresent):
            self.clashing_import_batch = exception.import_batch
        self.save()

    @atomic
    def reimport(self) -> Optional[dict]:
        """
        Changes the sushi attempt to undo changes of it being processed. This includes:
        * deleting any data related to the import_batch
        * deleting the import_batch itself
        * and mark attempt as if it didn't crashed
        * update attempt state so it can be imported
        """
        if self.status not in AttemptStatus.reimportable():
            return None

        stats = {}

        if self.import_batch:
            stats = self.import_batch.delete()  # deletes the access logs as well
            self.import_batch = None
        self.status = AttemptStatus.IMPORTING
        self.log = ""
        self.extracted_data = {}
        if "import_crash_traceback" in self.processing_info:
            del self.processing_info["import_crash_traceback"]
        self.save()
        return stats

    @atomic
    def update_broken(self):
        if self.credentials.version_hash != self.credentials_version_hash:
            # credentials changed -> result of this fetch attempt is irrelevant
            return

        if self.status == AttemptStatus.DOWNLOAD_FAILED:
            if not self.update_broken_credentials():
                # entire sushi credentials were not marked as broken
                # lets check whether is can't be marked as broken per report type
                if self.update_broken_report_type():
                    Event.create_for_users(
                        self.credentials.organization.admins(include_superusers=True),
                        title=f"The {self.counter_report.code} report was marked as broken",
                        description=f"The COUNTER {self.credentials.counter_version} report "
                        f"{self.counter_report.code} for credentials for "
                        f"{self.credentials.organization} / {self.credentials.platform} was marked "
                        f"as broken as a result of a harvesting error.",
                        importance=EventImportance.HIGH,
                        category=EventCategory.SUSHI,
                    )
            else:
                Event.create_for_users(
                    self.credentials.organization.admins(include_superusers=True),
                    title="SUSHI credentials were marked as broken",
                    description=f"COUNTER {self.credentials.counter_version} credentials for "
                    f"{self.credentials.organization} / {self.credentials.platform} were marked "
                    f"as broken as a result of a harvesting error.",
                    importance=EventImportance.HIGH,
                    category=EventCategory.SUSHI,
                )

    def any_success_lately(self, days: int = 15) -> bool:
        return self.credentials.current_successful_attempts.filter(
            when_processed__gte=now() - timedelta(days=days)
        ).exists()

    def update_broken_credentials(self) -> bool:
        """updates broken status of credentials

        return True if the credetials become broken, False otherwise
        """
        # Check http status code
        if self.http_status_code in (401, 403):
            self.credentials.set_broken(self, SushiCredentials.BROKEN_HTTP)
            return True

        if self.http_status_code in (500, 400):
            if not self.any_success_lately():
                # some error occurs with 400 http status, but it should not break
                # the entire credentials and are handled when update_broken_report_type
                # is triggered
                if str(self.error_code) not in (str(ErrorCode.INVALID_REPORT_FILTER.value),):
                    self.credentials.set_broken(self, SushiCredentials.BROKEN_HTTP)
                    return True

        # Check for sushi error
        if str(self.error_code) in (
            str(ErrorCode.NOT_AUTHORIZED.value),
            str(ErrorCode.NOT_AUTHORIZED_INSTITUTION.value),
            str(ErrorCode.INVALID_API_KEY.value),
            str(ErrorCode.INSUFFICIENT_DATA.value),
        ):
            self.credentials.set_broken(self, SushiCredentials.BROKEN_SUSHI)
            return True

        return False

    def update_broken_report_type(self) -> bool:
        def mark_broken(broken_type: str) -> bool:
            # try to get the report
            try:
                cr2c = CounterReportsToCredentials.objects.get(
                    credentials=self.credentials, counter_report=self.counter_report
                )
                cr2c.set_broken(self, broken_type)
                return True
            except CounterReportsToCredentials.DoesNotExist:
                # Counter report was removed from credentials
                return False

        if self.http_status_code in (404,):
            return mark_broken(SushiCredentials.BROKEN_HTTP)

        if str(self.error_code) in (
            str(ErrorCode.REPORT_NOT_SUPPORTED.value),
            str(ErrorCode.REPORT_VERSION_NOT_SUPPORTED.value),
            str(ErrorCode.INVALID_REPORT_FILTER.value),
        ):
            return mark_broken(SushiCredentials.BROKEN_SUSHI)
        return False

    def extract_header_data(self, header: dict) -> bool:
        """
        Takes supported header data from `header` and loads them into `extracted_data`.
        Does not save the instance!
        Returns true if something was extracted, false otherwise
        """
        ext_data = {key: header.get(key) for key in self.EXTRACTED_DATA_KEYS if key in header}
        if ext_data:
            self.extracted_data = ext_data
            return True
        return False

    def get_nibbler_poop(self, json_format: bool = False) -> Poop:
        nibbler_parser = self.counter_report.get_nibbler_parser(json_format=self.file_is_json())

        path = Path(settings.MEDIA_ROOT) / self.data_file.name
        logger.debug("Processing file: %s; time: %.3f", self.data_file.name, time())
        poops = counter_format_poops(path, self.credentials.platform, nibbler_parser)
        # Check the output note that poops.extras should countain counter header
        poop = output_to_poops(poops)[0]
        logger.debug("Records parsed; time: %.3f", time())
        return poop

    def any_import_batch_lately(self, days: int = 3 * 30):
        return SushiFetchAttempt.objects.filter(
            credentials=self.credentials,
            credentials__version_hash=F("credentials_version_hash"),
            when_processed__gte=now() - timedelta(days=days),
            import_batch__isnull=False,
        ).exists()

    @property
    def broken_credentials(self):
        """Credentials of this attempt are currently broken"""
        return (
            self.credentials.is_broken()
            or CounterReportsToCredentials.objects.filter(
                credentials=self.credentials,
                counter_report=self.counter_report,
                broken__isnull=False,
            ).exists()
        )


class CounterReportsToCredentials(BrokenCredentialsMixin):
    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    last_harvestable_month = models.DateField(
        help_text="When we know that data before this date are not available", null=True
    )
    last_harvestable_month_attempt = models.ForeignKey(
        SushiFetchAttempt,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cr2c_last_harvestable_month",
        blank=True,
    )
    last_harvestable_month_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        constraints = (
            CheckConstraint(
                check=~(
                    models.Q(last_harvestable_month_attempt__isnull=False)
                    & models.Q(last_harvestable_month_user__isnull=False)
                ),
                name="last_harvestable_month_by_attempt_vs_user",
            ),
            UniqueConstraint(fields=["credentials", "counter_report"], name="unique_creds_to_cr"),
        )
        verbose_name_plural = "Counter reports to credentials"

    def update_last_harvestable_month_by_attempt(self, attempt: SushiFetchAttempt) -> bool:
        """Update last_harvestable_month by attempt which reports that it no longer contains data
        (3032)"""
        if not self.last_harvestable_month or self.last_harvestable_month <= attempt.start_date:
            self.last_harvestable_month_user = None
            self.last_harvestable_month_attempt = attempt
            self.last_harvestable_month = month_start(attempt.start_date) + relativedelta(months=1)
            self.save()
            return True
        return False

    def update_last_harvestable_month_by_user(self, user: User, date: Optional[date]) -> bool:
        """Update last_harvestable_month by user"""
        if self.last_harvestable_month != date or self.last_harvestable_month_user != user:
            self.last_harvestable_month_attempt = None
            self.last_harvestable_month_user = user
            self.last_harvestable_month = date
            self.save()
            return True
        return False
