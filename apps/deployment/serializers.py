from django.contrib.sites.models import Site
from rest_framework.serializers import ModelSerializer

from deployment.models import FooterImage, SiteLogo


class FooterImageSerializer(ModelSerializer):
    class Meta:
        model = FooterImage
        fields = ('pk', 'site', 'position', 'img', 'alt_text', 'created', 'last_modified')


class SiteLogoSerializer(ModelSerializer):
    class Meta:
        model = SiteLogo
        fields = ('pk', 'site', 'img', 'alt_text', 'created', 'last_modified')


class SiteSerializer(ModelSerializer):
    class Meta:
        model = Site
        fields = ('pk', 'domain', 'name')
