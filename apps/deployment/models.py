from django.contrib.sites.models import Site
from django.db import models


class SiteImage(models.Model):

    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    img = models.FileField(upload_to='deployment')
    alt_text = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.alt_text


class FooterImage(SiteImage):

    position = models.PositiveSmallIntegerField(help_text='influences sorting of images on page')

    class Meta:
        unique_together = (('site', 'position'),)


class SiteLogo(SiteImage):
    class Meta:
        unique_together = (('site',),)
