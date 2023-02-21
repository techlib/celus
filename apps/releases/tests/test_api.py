import json
import re

import pytest
from django.urls import reverse
from releases.logic.releases import get_releases_entries

from test_fixtures.scenarios.basic import *  # noqa - fixtures

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

    def test_current_releases_file(self, clients, settings):
        if data := get_releases_entries():
            serialized_source_data = ReleaseSerializer(data=data, many=True)
            assert serialized_source_data.is_valid(raise_exception=True)
        url = reverse('releases-list')
        response = clients['user1'].get(url)
        assert response.status_code == 200
        with open(settings.RELEASES_SOURCEFILE, 'r') as f:
            text = f.read()
            if any(char for char in text if not char.isspace()):
                # if the file contains anything but whitespace, it should produce at least one record
                assert len(response.data) > 0
            else:
                assert len(response.data) == 0

    def test_releases_list_creation(self, clients, settings, releases_source):
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_filled_releases.yaml'
        url = reverse('releases-list')
        response = clients["user1"].get(url)
        assert response.status_code == 200
        # response.data automagically deserializes date ISO strings to datetime objects
        # which we don't want, so we need to deserialize the response content manually
        response_data = json.loads(response.content.decode(response.charset))
        assert [list(e.items()) for e in response_data] == [
            list(e.items()) for e in releases_source
        ]

    def test_latest_release(self, clients, settings, releases_source):
        url = reverse('releases-latest')
        settings.RELEASES_SOURCEFILE = 'test-data/releases/test_filled_releases.yaml'
        response = clients["user1"].get(url)
        assert response.status_code == 200
        # response.data automagically deserializes date ISO strings to datetime objects
        # which we don't want, so we need to deserialize the response content manually
        response_data = json.loads(response.content.decode(response.charset))
        assert list(response_data.items()) == list(releases_source[0].items())


@pytest.mark.django_db
class TestChangelogAPI:
    def test_changelog(self, clients, settings):
        url = reverse('changelog')
        response = clients['user1'].get(url)
        assert response.status_code == 200
        for release in response.data:
            assert release.get("version")
            assert release.get("markdown")
            assert 'date' in release, 'date must be present, even if it is "None"'
            assert (
                re.search(r"^[0-9]+\.[0-9]+\.[0-9]+", release["version"]) is not None
                or release["version"] == "Unreleased"
            )
