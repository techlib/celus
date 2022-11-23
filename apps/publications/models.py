from collections import Counter

from core.models import DataSource
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _


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
