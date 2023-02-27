import codecs
import csv
import os
import tempfile
from collections import Counter
from typing import BinaryIO, Callable, Optional

import magic
from core.models import CreatedUpdatedMixin, DataSource
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization


class PlatformInterestReport(models.Model):

    report_type = models.ForeignKey('logs.ReportType', on_delete=models.CASCADE)
    platform = models.ForeignKey('Platform', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)


class Platform(models.Model):

    ext_id = models.PositiveIntegerField(blank=True, null=True)
    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    provider = models.CharField(max_length=250)
    url = models.URLField(blank=True)
    interest_reports = models.ManyToManyField(
        'logs.ReportType', through=PlatformInterestReport, related_name='interest_platforms'
    )
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

    class Meta:
        ordering = ('short_name',)
        verbose_name = _('Platform')
        constraints = [
            UniqueConstraint(fields=['ext_id', 'source'], name='ext_id_source_not_null'),
            UniqueConstraint(
                fields=['ext_id'], condition=Q(source=None), name='ext_id_source_null'
            ),
            UniqueConstraint(
                fields=('short_name',),
                condition=models.Q(source__isnull=True),
                name='platform_unique_global_shortname',
            ),
            UniqueConstraint(
                fields=('short_name', 'source'),
                name='platform_unique_short_name_source',
                condition=models.Q(
                    ext_id__isnull=True
                ),  # external platforms might have empty short_name
            ),
            UniqueConstraint(fields=['counter_registry_id'], name='unique_counter_registry_id'),
        ]

    def __str__(self):
        return self.short_name

    def create_default_interests(self) -> Counter:
        from logs.models import ReportType

        stats: Counter = Counter()

        for report_type in ReportType.objects.filter(default_platform_interest=True):
            _, created = PlatformInterestReport.objects.get_or_create(
                platform=self, report_type=report_type
            )
            if created:
                stats['created'] += 1
            else:
                stats['existing'] += 1

        return stats


class Title(models.Model):

    PUB_TYPE_BOOK = 'B'
    PUB_TYPE_JOURNAL = 'J'
    PUB_TYPE_UNKNOWN = 'U'
    PUB_TYPE_DATABASE = 'D'
    PUB_TYPE_OTHER = 'O'
    PUB_TYPE_REPORT = 'R'
    PUB_TYPE_NEWSPAPER = 'N'
    PUB_TYPE_MULTIMEDIA = 'M'
    PUB_TYPE_ARTICLE = 'A'
    PUB_TYPE_BOOK_SEGMENT = 'S'
    PUB_TYPE_DATASET = 'T'
    PUB_TYPE_PLATFORM = 'P'
    PUB_TYPE_REPOSITORY_ITEM = 'I'
    PUB_TYPE_THESIS_OR_DISSERTATION = 'H'

    PUB_TYPE_CHOICES = (
        (PUB_TYPE_BOOK, _('Book')),
        (PUB_TYPE_JOURNAL, _('Journal')),
        (PUB_TYPE_UNKNOWN, _('Unknown')),
        (PUB_TYPE_DATABASE, _('Database')),
        (PUB_TYPE_OTHER, _('Other')),
        (PUB_TYPE_REPORT, _('Report')),
        (PUB_TYPE_NEWSPAPER, _('Newspaper')),
        (PUB_TYPE_MULTIMEDIA, _('Multimedia')),
        (PUB_TYPE_ARTICLE, _('Article')),
        (PUB_TYPE_BOOK_SEGMENT, _('Book segment')),
        (PUB_TYPE_DATASET, _('Dataset')),
        (PUB_TYPE_PLATFORM, _('Platform')),
        (PUB_TYPE_REPOSITORY_ITEM, _('Repository item')),
        (PUB_TYPE_THESIS_OR_DISSERTATION, _('Thesis or dissertation')),
    )
    PUB_TYPE_MAP = dict(PUB_TYPE_CHOICES)

    data_type_to_pub_type_map = {
        'journal': PUB_TYPE_JOURNAL,
        'book': PUB_TYPE_BOOK,
        'database': PUB_TYPE_DATABASE,
        'other': PUB_TYPE_OTHER,
        'report': PUB_TYPE_REPORT,
        'newspaper_or_newsletter': PUB_TYPE_NEWSPAPER,
        'multimedia': PUB_TYPE_MULTIMEDIA,
        'article': PUB_TYPE_ARTICLE,
        'book_segment': PUB_TYPE_BOOK_SEGMENT,
        'dataset': PUB_TYPE_DATASET,
        'platform': PUB_TYPE_PLATFORM,
        'repository_item': PUB_TYPE_REPOSITORY_ITEM,
        'thesis_or_dissertation': PUB_TYPE_THESIS_OR_DISSERTATION,
    }

    name = models.TextField()
    pub_type = models.CharField(
        max_length=1,
        choices=PUB_TYPE_CHOICES,
        default=PUB_TYPE_UNKNOWN,
        verbose_name='Publication type',
    )
    isbn = models.CharField(max_length=20, blank=True, default='')
    issn = models.CharField(max_length=9, blank=True, default='')
    eissn = models.CharField(
        max_length=9, blank=True, default='', help_text="ISSN of electronic version"
    )
    doi = models.CharField(max_length=250, blank=True, default='')
    proprietary_ids = models.JSONField(default=list)
    uris = models.JSONField(default=list)

    class Meta:
        ordering = ('name', 'pub_type')
        verbose_name = _('Title/Database')
        unique_together = (('name', 'isbn', 'issn', 'eissn', 'doi', 'proprietary_ids'),)

    def __str__(self):
        return self.name

    @classmethod
    def data_type_to_pub_type(cls, data_type: str) -> str:
        """
        Takes a Data_Type value as it could appear in COUNTER data and translate it to
        the pub_type value as would be stored in the database for the title.
        Does some string manipulation for greater flexibility
        """
        data_type = data_type.replace(' ', '_').lower()
        return cls.data_type_to_pub_type_map.get(data_type, cls.PUB_TYPE_UNKNOWN)

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


class PlatformTitle(models.Model):

    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    date = models.DateField(help_text='Month for which title was available on platform')

    class Meta:
        unique_together = (('title', 'platform', 'organization', 'date'),)

    def __str__(self):
        return f'{self.platform} - {self.title}: {self.date}'


def where_to_store(instance: 'TitleOverlapBatch', filename):
    root, ext = os.path.splitext(filename)
    ts = now().strftime('%Y%m%d-%H%M%S.%f')
    return f'overlap_batch/{root}-{ts}{ext}'


class TitleOverlapBatchState(models.TextChoices):

    INITIAL = 'initial', _("Initial")
    PROCESSING = 'processing', _("Processing")
    FAILED = 'failed', _("Import failed")
    DONE = 'done', _('Done')


def validate_mime_type(fileobj):
    pos = fileobj.tell()
    fileobj.seek(0)
    try:
        detected_type = magic.from_buffer(fileobj.read(16384), mime=True)
    finally:
        fileobj.seek(pos)
    # there is not one type to rule them all - magic is not perfect and we need to consider
    # other possibilities that could be detected - for example the text/x-Algol68 seems
    # to be returned for some CSV files with some version of libmagic
    # (the library magic uses internally)
    if detected_type not in ('text/csv', 'text/plain', 'application/csv', 'text/x-Algol68'):
        raise ValidationError(
            _(
                "The uploaded file does not seem to be a CSV file. "
                "The file type seems to be '{detected_type}'. "
                "Please upload a CSV file."
            ).format(detected_type=detected_type)
        )


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
        help_text='Titles will only be looked up for this organization',
    )
    annotated_file = models.FileField(
        upload_to='overlap_batch/',
        blank=True,
        null=True,
        max_length=256,
        help_text='File with additional data added during processing',
    )
    processing_info = models.JSONField(
        default=dict,
        blank=True,
        help_text='Information gathered during processing of the source file',
    )
    state = models.CharField(
        max_length=20,
        choices=TitleOverlapBatchState.choices,
        default=TitleOverlapBatchState.INITIAL,
    )

    class Meta:
        verbose_name_plural = 'Title overlap batches'

    def file_row_count(self):
        orig_pos = self.source_file.tell()
        self.source_file.seek(0)
        check_reader = csv.reader(codecs.getreader('utf-8')(self.source_file))
        total = sum(1 for _ in check_reader) - 1  # -1 because of header
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
        for rec in reader.process_source(
            codecs.getreader('utf-8')(self.source_file), dump_file=dump_file
        ):
            stats['row_count'] += 1
            unique_title_ids |= rec.title_ids
            if not rec.title_ids:
                stats['no_match'] += 1
            if progress_monitor:
                progress_monitor(stats['row_count'], total)
        stats['unique_matched_titles'] = len(unique_title_ids)
        return {
            'stats': stats,
            'recognized_columns': list(
                sorted(reader.column_names.values(), key=lambda x: x.lower())
            ),
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
            with tempfile.NamedTemporaryFile('r+b') as dump_file:
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
            self.processing_info['error'] = str(e)
            self.state = TitleOverlapBatchState.FAILED
            self.save()

    def create_annotated_file_name(self) -> str:
        if not self.source_file:
            raise ValueError('source_file must be filled in')
        _folder, fname = os.path.split(self.source_file.name)
        base, ext = os.path.splitext(fname)
        return base + '-annotated' + ext
