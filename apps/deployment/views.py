from django.contrib.sites.models import Site
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from django.conf import settings
from deployment.models import FooterImage, SiteLogo
from deployment.serializers import FooterImageSerializer, SiteLogoSerializer, SiteSerializer


class FooterImageViewSet(ReadOnlyModelViewSet):

    serializer_class = FooterImageSerializer
    queryset = FooterImage.objects.filter(site_id=settings.SITE_ID)


class SiteLogoViewSet(ReadOnlyModelViewSet):

    serializer_class = SiteLogoSerializer
    queryset = SiteLogo.objects.filter(site_id=settings.SITE_ID)


class SiteViewSet(ReadOnlyModelViewSet):

    serializer_class = SiteSerializer
    queryset = Site.objects.filter(pk=settings.SITE_ID)


class SiteOverview(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        site = Site.objects.get(pk=settings.SITE_ID)
        footer_images = [
            {'img': settings.MEDIA_URL + fim['img'], 'alt_text': fim['alt_text']}
            for fim in FooterImage.objects.filter(site_id=settings.SITE_ID)
            .order_by('position')
            .values('img', 'alt_text')
        ]
        site_logo = SiteLogo.objects.filter(site_id=settings.SITE_ID).values('img', 'alt_text')
        data = {'site_name': site.name, 'site_domain': site.domain, 'footer_images': footer_images}
        if site_logo:
            data['site_logo'] = site_logo[0]  # it is an iterable from the query
            data['site_logo']['img'] = settings.MEDIA_URL + data['site_logo']['img']
        return Response(data)
