import os
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO, Callable, List, Optional

from celus_nigiri.record import Author as NigiriAuthor
from core.models import CreatedUpdatedMixin, DataSource
from core.validators import validate_mime_type_csv as validate_mime_type
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.files import File
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.db.transaction import atomic
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization

from .logic import knowledgebase as kb
from .logic.validation import (
    AUTHOR_ID_LEN,
    AUTHOR_NAME_LEN,
    normalize_author_id,
    normalize_author_name,
)

# the following curve was obtained as a generic curve from the production data on K1
# and slightly modified to make it more generic.
# It will be used in case there are not enough attempts in a CELUS installation to create a
# generic curve
DEFAULT_ARRIVAL_STATS = {
    "count": 0,
    "curve": [1.90, 1.95, 2.00, 2.05, 2.90, 3.00, 5.00, 9.00, 17.00, 18.00, 25.00, 30.00, 44.00],
    "probabs": [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
    "source": "generic",
}


def default_stats():
    return DEFAULT_ARRIVAL_STATS.copy()


class CounterReportSource(models.TextChoices):
    KNOWLEDGEBASE = "knowledgebase", _("Knowledgebase")
    MANUAL = "manual", _("Manual")


DEFAULT_COUNTER_REPORT_TYPES = {
    4: ["BR1", "BR2", "BR3", "DB1", "DB2", "JR1", "JR2", "PR1"],
    5: ["TR", "DR", "PR"],
    51: ["TR", "DR", "PR"],
}


class PlatformQuerySet(models.QuerySet):
    @atomic
    def update_counter_reports_from_knowledgebase(self) -> int:
        """Updates CounterReportPlatform structs based on knowledgebase"""
        from sushi.models import CounterReportPlatform, CounterReportType

        platforms = self.filter(counter_reports_source=CounterReportSource.KNOWLEDGEBASE)
        crp_map = {e.pk: [] for e in platforms}
        for crp in CounterReportPlatform.objects.filter(platform__in=platforms):
            crp_map[crp.platform.pk].append(crp)

        crt_map = {(e.counter_version, e.code): e for e in CounterReportType.objects.all()}

        modified = 0
        for platform in platforms:
            crps = crp_map[platform.pk]
            modified = False
            for version, code in kb.get_counter_reports(platform.knowledgebase):
                # make sure that all links exists
                if crt := crt_map.get((version, code)):
                    _, created = CounterReportPlatform.objects.get_or_create(
                        platform=platform, counter_report=crt
                    )
                    if created:
                        modified = True
                    crps = [
                        e
                        for e in crps
                        if (version, code)
                        != (e.counter_report.counter_version, e.counter_report.code)
                    ]

            # Remove extras
            CounterReportPlatform.objects.filter(pk__in=[e.pk for e in crps]).delete()

            modified += 1 if modified or crps else 0

        return modified


class Platform(models.Model):
    ext_id = models.PositiveIntegerField(blank=True, null=True)
    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    provider = models.CharField(max_length=250)
    url = models.URLField(blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    knowledgebase = models.JSONField(blank=True, null=True)
    counter_registry_id = models.UUIDField(blank=True, null=True)
    duplicates = ArrayField(
        models.PositiveIntegerField(),
        default=list,
        help_text="Links to other platform's ext_id",
        blank=True,
    )
    sushi_arrival_stats = models.JSONField(
        default=default_stats,
        blank=True,
        help_text="Stats about when a specific percentage of reports are typically available",
    )
    counter_reports_source = models.CharField(
        max_length=20,
        choices=CounterReportSource.choices,
        default=CounterReportSource.KNOWLEDGEBASE,
    )
    counter_reports = models.ManyToManyField(
        "sushi.CounterReportType",
        through="sushi.CounterReportPlatform",
        related_name="sushicredentials_via_platform",
    )

    objects = PlatformQuerySet.as_manager()

    class Meta:
        ordering = ("short_name",)
        verbose_name = _("Platform")
        constraints = [
            UniqueConstraint(fields=["ext_id", "source"], name="ext_id_source_not_null"),
            CheckConstraint(
                check=(Q(source=None) & Q(ext_id=None)) | ~Q(source=None),
                name="if_source_is_null_ext_id_should_be_null",
            ),
            UniqueConstraint(
                fields=("short_name",),
                condition=models.Q(source__isnull=True),
                name="platform_unique_global_shortname",
            ),
            UniqueConstraint(
                fields=("short_name", "source"),
                name="platform_unique_short_name_source",
                condition=models.Q(
                    ext_id__isnull=True
                ),  # external platforms might have empty short_name
            ),
            UniqueConstraint(fields=["counter_registry_id"], name="unique_counter_registry_id"),
        ]

    def __str__(self):
        return self.short_name

    def _find_probability_on_curve(self, curve_day: float) -> Optional[float]:
        curve = self.sushi_arrival_stats.get("curve", DEFAULT_ARRIVAL_STATS["curve"])
        probabs = self.sushi_arrival_stats.get("probabs", DEFAULT_ARRIVAL_STATS["probabs"])
        min_day = 0.0
        min_probab = 0.0
        for day, probab in zip(curve, probabs):
            # Exact match
            if day == curve_day:
                return probab
            elif day < curve_day:
                min_day = day
                min_probab = probab
            elif day > curve_day:
                # Gap found
                # calcualte probability
                return (probab - min_probab) / (day - min_day) * (curve_day - min_day) + min_probab
        return None

    def _find_days_on_curve(self, curve_probab: float) -> Optional[float]:
        curve = self.sushi_arrival_stats.get("curve", DEFAULT_ARRIVAL_STATS["curve"])
        probabs = self.sushi_arrival_stats.get("probabs", DEFAULT_ARRIVAL_STATS["probabs"])
        min_day = 0.0
        min_probab = 0.0
        for day, probab in zip(curve, probabs):
            # Exact match
            if probab == curve_probab:
                return day
            elif probab < curve_probab:
                min_day = day
                min_probab = probab
            elif probab > curve_probab:
                # Gap found
                # calcualte days
                return (day - min_day) / (probab - min_probab) * (
                    curve_probab - min_probab
                ) + min_day

        return None

    def calculate_next_arrival(
        self, harvest_start: datetime, current_date: datetime
    ) -> Optional[datetime]:
        current_day = (current_date - harvest_start) / timedelta(days=1)

        current_prob = self._find_probability_on_curve(current_day)
        if current_prob is None:
            # Beyond curve -> skip calculation
            return None

        for prob in settings.AUTO_HARVESTING_PROBABILITIES:
            if prob > current_prob:
                new_prob = prob
                break
        else:
            # No next prob found
            return None

        if next_days := self._find_days_on_curve(new_prob):
            min_start = current_day + 1
            # convert date to datetime
            return harvest_start + timedelta(days=max(next_days, min_start))

        return None

    @property
    def slugified_name(self):
        # make short name slugified => this makes sure that it e.g.
        # doesn't contain `/` which would be a problem for file names

        platform_slug = slugify(self, allow_unicode=True)
        if source := self.source:
            if org := source.organization:
                return f"{slugify(org.short_name, allow_unicode=True)}.{platform_slug}"
        return platform_slug

    def update_related_credentials_url(self) -> int:
        count = 0
        for creds in self.sushicredentials_set.filter(auto_update_url=True):
            if url := kb.get_url(self.knowledgebase, creds.counter_version):
                if creds.perform_auto_update(url):
                    count += 1

        return count

    def get_counter_reports(self, counter_version: int) -> List["models.CounterReportType"]:
        if counter_reports := self.counter_reports.filter(counter_version=counter_version):
            return list(counter_reports)
        else:
            return []


class PubTypeMixin(models.Model):
    PUB_TYPE_BOOK = "B"
    PUB_TYPE_JOURNAL = "J"
    PUB_TYPE_UNKNOWN = "U"
    PUB_TYPE_DATABASE = "D"
    PUB_TYPE_OTHER = "O"
    PUB_TYPE_REPORT = "R"
    PUB_TYPE_NEWSPAPER = "N"
    PUB_TYPE_MULTIMEDIA = "M"
    PUB_TYPE_ARTICLE = "A"
    PUB_TYPE_BOOK_SEGMENT = "S"
    PUB_TYPE_DATASET = "T"
    PUB_TYPE_PLATFORM = "P"
    PUB_TYPE_REPOSITORY_ITEM = "I"
    PUB_TYPE_THESIS_OR_DISSERTATION = "H"

    PUB_TYPE_CHOICES = (
        (PUB_TYPE_BOOK, _("Book")),
        (PUB_TYPE_JOURNAL, _("Journal")),
        (PUB_TYPE_UNKNOWN, _("Unknown")),
        (PUB_TYPE_DATABASE, _("Database")),
        (PUB_TYPE_OTHER, _("Other")),
        (PUB_TYPE_REPORT, _("Report")),
        (PUB_TYPE_NEWSPAPER, _("Newspaper")),
        (PUB_TYPE_MULTIMEDIA, _("Multimedia")),
        (PUB_TYPE_ARTICLE, _("Article")),
        (PUB_TYPE_BOOK_SEGMENT, _("Book segment")),
        (PUB_TYPE_DATASET, _("Dataset")),
        (PUB_TYPE_PLATFORM, _("Platform")),
        (PUB_TYPE_REPOSITORY_ITEM, _("Repository item")),
        (PUB_TYPE_THESIS_OR_DISSERTATION, _("Thesis or dissertation")),
    )
    PUB_TYPE_MAP = dict(PUB_TYPE_CHOICES)

    data_type_to_pub_type_map = {
        "journal": PUB_TYPE_JOURNAL,
        "book": PUB_TYPE_BOOK,
        "database": PUB_TYPE_DATABASE,
        "other": PUB_TYPE_OTHER,
        "report": PUB_TYPE_REPORT,
        "newspaper_or_newsletter": PUB_TYPE_NEWSPAPER,
        "multimedia": PUB_TYPE_MULTIMEDIA,
        "article": PUB_TYPE_ARTICLE,
        "book_segment": PUB_TYPE_BOOK_SEGMENT,
        "dataset": PUB_TYPE_DATASET,
        "platform": PUB_TYPE_PLATFORM,
        "repository_item": PUB_TYPE_REPOSITORY_ITEM,
        "thesis_or_dissertation": PUB_TYPE_THESIS_OR_DISSERTATION,
    }

    pub_type = models.CharField(
        max_length=1,
        choices=PUB_TYPE_CHOICES,
        default=PUB_TYPE_UNKNOWN,
        verbose_name="Publication type",
    )

    class Meta:
        abstract = True

    @classmethod
    def data_type_to_pub_type(cls, data_type: str) -> str:
        """
        Takes a Data_Type value as it could appear in COUNTER data and translate it to
        the pub_type value as would be stored in the database for the title.
        Does some string manipulation for greater flexibility
        """
        data_type = data_type.replace(" ", "_").lower()
        return cls.data_type_to_pub_type_map.get(data_type, cls.PUB_TYPE_UNKNOWN)


class Title(CreatedUpdatedMixin, PubTypeMixin, models.Model):
    name = models.TextField()
    isbn = models.CharField(max_length=20, blank=True, default="")
    issn = models.CharField(max_length=9, blank=True, default="", db_index=True)
    eissn = models.CharField(
        max_length=9, blank=True, default="", db_index=True, help_text="ISSN of electronic version"
    )
    doi = models.CharField(max_length=250, blank=True, default="")
    proprietary_ids = models.JSONField(default=list)
    uris = models.JSONField(default=list)

    class Meta:
        ordering = ("name", "pub_type")
        verbose_name = _("Title/Database")

    def __str__(self):
        return self.name

    def guess_pub_type(self):
        """
        Based on presence of isbn, issn and eissn attrs, guess what type of publication this is
        :return:
        """
        if self.isbn and not self.issn:
            return self.PUB_TYPE_BOOK
        if (self.issn or self.eissn) and not self.isbn:
            return self.PUB_TYPE_JOURNAL
        return self.PUB_TYPE_UNKNOWN


class Author(CreatedUpdatedMixin, models.Model):
    # limit length to 250 characters - some sources have very long author names
    # (e.g. 1000+ characters) and this then messes up the unique constraint because the data
    # does not fit into the index
    name = models.CharField(max_length=AUTHOR_NAME_LEN, blank=True)
    # ISNI contains 16 characters
    isni = models.CharField(max_length=AUTHOR_ID_LEN, blank=True, default="")
    # ORCID contains 16 charactes
    orcid = models.CharField(max_length=AUTHOR_ID_LEN, blank=True, default="")

    items = models.ManyToManyField(
        "publications.Item", through="publications.AuthorToItem", related_name="authors"
    )

    class Meta:
        unique_together = (("name", "isni", "orcid"),)

    def __str__(self):
        if self.isni and self.orcid:
            return f"{self.name} (ISNI:{self.isni}|ORCID:{self.orcid})"
        elif self.isni:
            return f"{self.name} (ISNI:{self.isni})"
        elif self.orcid:
            return f"{self.name} (ORCID:{self.orcid})"
        else:
            return self.name

    def save(self, *args, **kwargs):
        self.isni = normalize_author_id(self.isni)
        self.orcid = normalize_author_id(self.orcid)
        self.name = normalize_author_name(self.name)
        return super().save(*args, **kwargs)

    @classmethod
    def from_nigiri_author(cls, author: NigiriAuthor) -> "Author":
        # Need to normalize identifiers
        # (this function may be used with batch_create which doesn't perform save
        return cls(
            name=normalize_author_name(author.name),
            isni=normalize_author_id(author.ISNI),
            orcid=normalize_author_id(author.ORCID),
        )


class Item(CreatedUpdatedMixin, PubTypeMixin, models.Model):
    name = models.TextField()
    publication_date = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=250, blank=True, default="")
    isbn = models.CharField(max_length=20, blank=True, default="")
    issn = models.CharField(max_length=9, blank=True, default="", db_index=True)
    eissn = models.CharField(
        max_length=9, blank=True, default="", db_index=True, help_text="ISSN of electronic version"
    )
    uris = models.JSONField(default=list, blank=True)
    proprietary_ids = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("name", "publication_date")
        verbose_name = _("Item")

    def __str__(self):
        return self.name


class AuthorToItem(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(help_text="Used for per title author ordering")

    class Meta:
        unique_together = (("author", "item"),)
        ordering = ("item_id", "author_id", "position")


class PlatformTitle(models.Model):
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    date = models.DateField(help_text="Month for which title was available on platform")

    class Meta:
        unique_together = (("title", "platform", "organization", "date"),)

    def __str__(self):
        return f"{self.platform} - {self.title}: {self.date}"


def where_to_store(instance: "TitleOverlapBatch", filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime("%Y%m%d-%H%M%S.%f")
    return f"overlap_batch/{root}-{ts}{ext}"


class TitleOverlapBatchState(models.TextChoices):
    INITIAL = "initial", _("Initial")
    PROCESSING = "processing", _("Processing")
    FAILED = "failed", _("Import failed")
    DONE = "done", _("Done")


class TitleOverlapBatch(CreatedUpdatedMixin, models.Model):
    source_file = models.FileField(
        upload_to=where_to_store,
        blank=True,
        null=True,
        max_length=256,
        validators=[validate_mime_type],
    )
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Titles will only be looked up for this organization",
    )
    annotated_file = models.FileField(
        upload_to="overlap_batch/",
        blank=True,
        null=True,
        max_length=256,
        help_text="File with additional data added during processing",
    )
    processing_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Information gathered during processing of the source file",
    )
    state = models.CharField(
        max_length=20,
        choices=TitleOverlapBatchState.choices,
        default=TitleOverlapBatchState.INITIAL,
    )

    class Meta:
        verbose_name_plural = "Title overlap batches"

    def file_row_count(self):
        from publications.logic.title_list_overlap import CsvTitleListOverlapReader

        orig_pos = self.source_file.tell()
        self.source_file.seek(0)
        total = CsvTitleListOverlapReader().record_count(self.source_file)
        self.source_file.seek(orig_pos)
        return total

    def process_source_file(
        self,
        dump_file: Optional[BinaryIO] = None,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        """
        :param dump_file: opened file where a copy of input will be written with extra data from
                          the processing
        :param title_id_formatter: converter of title id into string
        :param progress_monitor: callback to report progress, should send (current, total) ints
        :return:
        """
        from publications.logic.title_list_overlap import CsvTitleListOverlapReader

        reader = CsvTitleListOverlapReader(
            organization=self.organization, dump_id_formatter=title_id_formatter
        )
        stats = Counter()
        unique_title_ids = set()
        total = self.file_row_count()
        for rec in reader.process_source(self.source_file, dump_file=dump_file):
            stats["row_count"] += 1
            unique_title_ids |= rec.title_ids
            if not rec.title_ids:
                stats["no_match"] += 1
            if progress_monitor:
                progress_monitor(stats["row_count"], total)
        stats["unique_matched_titles"] = len(unique_title_ids)
        return {
            "stats": stats,
            "recognized_columns": sorted(reader.column_names.values(), key=lambda x: x.lower()),
        }

    def process(
        self,
        title_id_formatter: Callable[[int], str] = str,
        progress_monitor: Optional[Callable[[int, int], None]] = None,
    ):
        """
        :param title_id_formatter: converts title ids to string in the annotated file
        :param progress_monitor: callback to report progress, should send (current, total) ints
        :return:
        """
        self.state = TitleOverlapBatchState.PROCESSING
        self.save()
        try:
            with tempfile.NamedTemporaryFile("r+b") as dump_file:
                self.processing_info = self.process_source_file(
                    dump_file=dump_file,
                    title_id_formatter=title_id_formatter,
                    progress_monitor=progress_monitor,
                )
                dump_file.seek(0)
                self.annotated_file = File(dump_file, name=self.create_annotated_file_name())
                self.state = TitleOverlapBatchState.DONE
                self.save()
        except Exception as e:
            self.processing_info["error"] = str(e)
            self.state = TitleOverlapBatchState.FAILED
            self.save()

        self.create_processing_events()

    def create_annotated_file_name(self) -> str:
        if not self.source_file:
            raise ValueError("source_file must be filled in")
        path = Path(self.source_file.name)
        return path.stem + "-annotated" + path.suffix

    def create_processing_events(self):
        """
        Based on `self.state` creates events either about failure or success of the processing
        """
        if not self.last_updated_by:
            return
        from events.models import Event, EventCategory, EventImportance

        if self.state == TitleOverlapBatchState.FAILED:
            Event.create_for_users(
                [self.last_updated_by],
                title="Title list overlap analysis failed",
                description="An error occurred while processing the title list: {error}".format(
                    **self.processing_info
                ),
                importance=EventImportance.HIGH,
                category=EventCategory.OVERLAP,
            )

        else:
            Event.create_for_users(
                [self.last_updated_by],
                title="Title list overlap analysis finished successfully",
                description=(
                    "Number of rows processed: {row_count}\n"
                    "Number of unique titles matched: {unique_matched_titles}"
                ).format(**self.processing_info["stats"]),
                importance=EventImportance.NORMAL,
                category=EventCategory.OVERLAP,
            )
