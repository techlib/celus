import json
import logging
import hashlib
import requests
import traceback
import typing

from collections import Counter
from enum import Enum, auto
from urllib.parse import urljoin, urlparse

from django.db import models, transaction
from django.contrib.postgres.fields import JSONField
from django.utils import timezone

from core.models import DataSource
from logs.models import ReportType
from publications.models import Platform, PlatformInterestReport


logger = logging.getLogger(__name__)


class ImportAttempt(models.Model):
    class State(Enum):
        QUEUE = auto()
        DOWNLOADING = auto()
        PROCESSING = auto()
        SKIPPED = auto()
        SUCCESS = auto()
        FAILED = auto()

    class MergeStrategy(Enum):
        NONE = auto()  # No merging is performed
        EMPTY_SOURCE = auto()  # Merges by short_name only when source is empty
        ALL = auto()  # Merges by short_name regardless of the source

    KIND_PLATFORM = 'platform'

    KINDS = ((KIND_PLATFORM, 'Platform',),)

    URL_MAP = {
        KIND_PLATFORM: '/knowledgebase/platforms/',
    }

    url = models.URLField()
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=KINDS)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    started_timestamp = models.DateTimeField(null=True, blank=True)
    downloaded_timestamp = models.DateTimeField(null=True, blank=True)
    processing_timestamp = models.DateTimeField(null=True, blank=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)
    data_hash = models.CharField(
        max_length=64, help_text="SHA-256 hash of attempt", null=True, blank=True
    )
    stats = JSONField(null=True, blank=True)
    error = models.TextField(blank=True, null=True)

    @property
    def status(self) -> 'ImportAttempt.State':
        if self.error is not None:
            return ImportAttempt.State.FAILED

        if self.started_timestamp is None:
            return ImportAttempt.State.QUEUE

        if not self.data_hash:
            return ImportAttempt.State.DOWNLOADING

        if self.end_timestamp is None:
            return ImportAttempt.State.PROCESSING

        if self.processing_timestamp is None:
            return ImportAttempt.State.SKIPPED

        return ImportAttempt.State.SUCCESS

    @property
    def failed(self) -> bool:
        """ attempt failed """
        return self.status == ImportAttempt.State.FAILED

    @property
    def success(self) -> bool:
        return self.status in (ImportAttempt.State.SUCCESS, ImportAttempt.State.SKIPPED)

    @property
    def running(self):
        """ running or to be run """
        return not self.failed and not self.success

    def save(self, *args, **kwargs):
        self.kind = self.required_kind
        self.url = urljoin(self.source.url, ImportAttempt.URL_MAP[self.kind])

        return super().save(*args, **kwargs)

    @property
    def request_headers_extra(self) -> dict:
        return {}

    @property
    def request_headers(self) -> dict:
        res = {
            'Authorization': f'Token {self.source.token}',
            'Content-Type': 'application/json',
        }
        res.update(self.request_headers_extra)
        return res

    def perform(self, merge=MergeStrategy.NONE):
        """ Downloads data from knowledgebase and imports it

        :param merge: Try to merge with existing platforms without a source (should be used rarely)
        """
        self.started_timestamp = timezone.now()
        self.save()

        try:
            # find lastest digest
            latest_download = (
                ImportAttempt.objects.filter(
                    source=self.source,
                    kind=self.required_kind,
                    downloaded_timestamp__isnull=False,
                    data_hash__isnull=False,
                )
                .exclude(data_hash__exact="")
                .order_by('-downloaded_timestamp')
                .first()
            )

            # donwload
            resp = requests.get(self.url, headers=self.request_headers)
            resp.raise_for_status()

            # store hash
            data = resp.json()
            sha256 = hashlib.sha256()
            sha256.update(json.dumps(data).encode())
            self.downloaded_timestamp = timezone.now()
            self.data_hash = sha256.hexdigest()
            self.save()

            # process data
            if not latest_download or latest_download.data_hash != self.data_hash:
                self.processing_timestamp = timezone.now()
                self.save()
                self.process(data, merge)

        except Exception as e:
            logger.warning("An error occured: %s", e)
            logger.debug(traceback.print_exc())

            self.error = str(e)

        finally:
            self.end_timestamp = timezone.now()
            self.save()


class PlatformImportAttempt(ImportAttempt):
    class Meta:
        proxy = True

    def plan(self):
        from .tasks import update_platforms

        update_platforms.delay(self.pk)

    @transaction.atomic
    def process(self, data: typing.List[dict], merge=ImportAttempt.MergeStrategy.NONE):
        counter: typing.Counter[str] = Counter()

        counter["total"] = len(data)

        UPDATABLE_FIELDS = ('short_name', 'name', 'provider', 'url', 'knowledgebase')

        for record in data:
            updatable = dict(
                short_name=record["short_name"],
                name=record["name"],
                provider=record["provider"],
                url=record["url"],
                knowledgebase={"providers": record["providers"]},
            )

            if merge == ImportAttempt.MergeStrategy.NONE:
                # Only new or existing with the same soure
                platform, created = Platform.objects.get_or_create(
                    defaults=updatable, ext_id=record["pk"], source=self.source,
                )
            elif merge in [
                ImportAttempt.MergeStrategy.EMPTY_SOURCE,
                ImportAttempt.MergeStrategy.ALL,
            ]:
                try:
                    # Try to get existing record (non-knowledgebase) record
                    query_args = models.Q(short_name=record["short_name"]) & ~models.Q(
                        source__type=DataSource.TYPE_KNOWLEDGEBASE,
                    )
                    if merge == ImportAttempt.MergeStrategy.EMPTY_SOURCE:
                        query_args = query_args & models.Q(source__isnull=True)
                    platform = Platform.objects.get(query_args)

                    # update existing platform
                    platform.source = self.source
                    platform.ext_id = record["pk"]
                    platform.save()
                    created = False

                except Platform.DoesNotExist:
                    platform, created = Platform.objects.get_or_create(
                        defaults=updatable, ext_id=record["pk"], source=self.source,
                    )
                except Platform.MultipleObjectsReturned:
                    # if multiple objects are returned we are not sure which one to merge
                    # so lets skip it and don't update platform
                    logger.warning(
                        "Multiple platforms with '%s' in db. Not sure which one to merge => skip",
                        record["short_name"],
                    )
                    counter["skipped"] += 1
                    continue

            else:
                raise ValueError(f'Unsupported value for "merge": {merge}')

            needs_update = any(updatable[e] != getattr(platform, e) for e in UPDATABLE_FIELDS)
            if created:
                logger.info("Platform '%s' created", record["short_name"])
                platform.create_default_interests()
                counter["created"] += 1

            elif needs_update:
                for e in UPDATABLE_FIELDS:
                    setattr(platform, e, updatable[e])
                platform.save()
                logger.info("Platform '%s' updated", record["short_name"])
                counter["updated"] += 1

            else:
                logger.info("Platform '%s' remained the same", record["short_name"])
                counter["same"] += 1

        self.stats = dict(counter)

        self.save()

    @property
    def required_kind(self):
        return ImportAttempt.KIND_PLATFORM
