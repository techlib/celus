from django.db import models
from django.utils.translation import gettext_lazy as _


class Platform(models.Model):

    ext_id = models.PositiveIntegerField(unique=True)
    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    provider = models.CharField(max_length=250)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.short_name


class Title(models.Model):

    PUB_TYPE_BOOK = 'B'
    PUB_TYPE_JOURNAL = 'J'
    PUB_TYPE_CHOICES = (
        (PUB_TYPE_BOOK, _('Book')),
        (PUB_TYPE_JOURNAL, _('Journal')),
    )

    name = models.TextField()
    pub_type = models.CharField(max_length=1, choices=PUB_TYPE_CHOICES,
                                verbose_name='Publication type')
    isbn = models.CharField(max_length=20, null=True, blank=True)
    issn = models.CharField(max_length=9, null=True, blank=True)
    eissn = models.CharField(max_length=9, null=True, blank=True,
                             help_text="ISSN of electronic version")
    doi = models.CharField(max_length=250, null=True, blank=True)

    class Meta:
        ordering = ('name', 'pub_type')

    def __str__(self):
        return self.name
