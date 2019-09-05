from django.db import models
from django.utils.translation import gettext_lazy as _


class Platform(models.Model):

    ext_id = models.PositiveIntegerField(unique=True)
    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    provider = models.CharField(max_length=250)
    url = models.URLField(blank=True)
    interest_reports = models.ManyToManyField('logs.ReportType')

    class Meta:
        ordering = ('short_name',)

    def __str__(self):
        return self.short_name


class Title(models.Model):

    PUB_TYPE_BOOK = 'B'
    PUB_TYPE_JOURNAL = 'J'
    PUB_TYPE_UNKNOWN = 'U'
    PUB_TYPE_DATABASE = 'D'
    PUB_TYPE_OTHER = 'O'
    PUB_TYPE_REPORT = 'R'
    PUB_TYPE_NEWSPAPER = 'N'
    PUB_TYPE_MULTIMEDIA = 'M'
    PUB_TYPE_CHOICES = (
        (PUB_TYPE_BOOK, _('Book')),
        (PUB_TYPE_JOURNAL, _('Journal')),
        (PUB_TYPE_UNKNOWN, _('Unknown')),
        (PUB_TYPE_DATABASE, _('Database')),
        (PUB_TYPE_OTHER, _('Other')),
        (PUB_TYPE_REPORT, _('Report')),
        (PUB_TYPE_NEWSPAPER, _('Newspaper')),
        (PUB_TYPE_MULTIMEDIA, _('Multimedia')),
    )
    PUB_TYPE_MAP = dict(PUB_TYPE_CHOICES)

    name = models.TextField()
    pub_type = models.CharField(max_length=1, choices=PUB_TYPE_CHOICES,
                                verbose_name='Publication type')
    isbn = models.CharField(max_length=20, blank=True, default='')
    issn = models.CharField(max_length=9, blank=True, default='')
    eissn = models.CharField(max_length=9, blank=True, default='',
                             help_text="ISSN of electronic version")
    doi = models.CharField(max_length=250, blank=True, default='')

    class Meta:
        ordering = ('name', 'pub_type')
        unique_together = (('name', 'isbn', 'issn', 'eissn', 'doi'),)

    def __str__(self):
        return self.name
