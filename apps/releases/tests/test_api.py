import json
import re

import pytest
import yaml
from django.urls import reverse
from typing_extensions import Required

from apps.releases.releases_parser import parse_source_of_releases
from apps.releases.tests.conftest import releases_source
from test_fixtures.scenarios.basic import *

from ..serializers import ReleaseSerializer


@pytest.mark.django_db
class TestReleasesAPI:
    def test_filled_releases_file(self, clients, settings):
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_filled_releases.yaml'
        url = reverse('releases-list')
        response = clients['user1'].get(url)
        assert response.status_code == 200

    def test_empty_releases_file(self, clients, settings):
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_empty_releases.yaml'
        url = reverse('releases-list')
        response = clients['user1'].get(url)
        assert response.status_code == 200

    def test_actual_releases_file(self, clients):
        if parse_source_of_releases():
            serialized_source_data = ReleaseSerializer(data=parse_source_of_releases(), many=True)
            assert serialized_source_data.is_valid(raise_exception=True) == True
        url = reverse('releases-list')
        response = clients['user1'].get(url)
        assert response.status_code == 200

    def test_releases_list_creation(self, clients, settings, releases_source):
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_filled_releases.yaml'
        url = reverse('releases-list')
        response = clients["user1"].get(url)
        assert response.status_code == 200
        response_data = json.loads(json.dumps(response.data))
        assert [list(e.items()) for e in response_data] == [
            list(e.items()) for e in releases_source
        ]

    def test_latest_release(self, clients, settings, releases_source):
        url = reverse('releases-latest')
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_filled_releases.yaml'
        response = clients["user1"].get(url)
        assert response.status_code == 200
        assert list(response.data.items()) == list(releases_source[0].items())


@pytest.mark.django_db
class TestChangelogAPI:
    def test_changelog(self, clients, settings):
        url = reverse('changelog-list')
        response = clients['user1'].get(url)
        assert response.status_code == 200
        for release in response.data:
            assert release.get("version")
            assert release.get("markdown")
            assert re.search("^[0-9]+\.[0-9]+\.[0-9]+", release["version"]) is not None
