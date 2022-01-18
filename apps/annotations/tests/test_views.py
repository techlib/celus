from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from freezegun import freeze_time

from test_fixtures.entities.annotations import AnnotationFactory
from test_fixtures.entities.users import UserFactory

User = get_user_model()


class GlobalAnnotationFactory(AnnotationFactory):
    organization = None


@freeze_time("2022-01-01")
@pytest.mark.django_db
class TestViews:
    @pytest.mark.parametrize(
        ["params", "count"],
        [({}, 8), ({"search": "needle"}, 7), ({"search": "xyz"}, 0)],
        ids=["all", "needle", "not-found"],
    )
    def test_annotation_search(self, params, count, authenticated_client):
        GlobalAnnotationFactory()
        GlobalAnnotationFactory(subject="needle")
        GlobalAnnotationFactory(subject_en="needle")
        GlobalAnnotationFactory(short_message="needle")
        GlobalAnnotationFactory(message="needle")
        GlobalAnnotationFactory(author=UserFactory(first_name="needle"))
        GlobalAnnotationFactory(author=UserFactory(last_name="needle"))
        GlobalAnnotationFactory(author=UserFactory(email="needle@bdd.tld"))

        url = reverse('annotations-list')
        assert authenticated_client.get(url, params).json()["count"] == count

    @pytest.mark.parametrize(
        ["params", "count"],
        [
            ({}, 6),
            ({"validity": "valid"}, 3),
            ({"validity": "outdated"}, 2),
            ({"validity": "future"}, 1),
        ],
        ids=["all", "valid", "outdated", "future"],
    )
    def test_annotation_filter_dates(self, params, count, authenticated_client):

        GlobalAnnotationFactory(subject='valid1'),
        GlobalAnnotationFactory(subject='valid2', start_date=date(2021, 8, 1)),
        GlobalAnnotationFactory(subject='valid3', end_date=date(2022, 12, 1)),
        GlobalAnnotationFactory(
            subject='outdated1', start_date=date(2021, 8, 1), end_date=date(2021, 12, 1)
        ),
        GlobalAnnotationFactory(subject='outdated2', end_date=date(2021, 12, 1)),
        GlobalAnnotationFactory(subject='future1', start_date=date(2022, 8, 1)),

        url = reverse('annotations-list')
        resp = authenticated_client.get(url, params)
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == count
        for result in results:
            assert result["subject"].startswith(params.get("validity", ""))

    def test_annotation_filter_platforms(self, platforms, authenticated_client):
        pl1, pl2 = platforms
        a0 = GlobalAnnotationFactory(subject="no_pl", platform=None)
        a1 = GlobalAnnotationFactory(subject="pl1", platform=pl1)
        a2 = GlobalAnnotationFactory(subject="pl2", platform=pl2)
        all_annot = [a0.subject, a1.subject, a2.subject]
        url = reverse('annotations-list')

        results = authenticated_client.get(url).json()["results"]
        assert [a["subject"] for a in results] == all_annot

        results = authenticated_client.get(url, {"platform[]": [pl1.pk, pl2.pk]}).json()["results"]
        assert len(results) == 3
        assert [a["subject"] for a in results] == all_annot

        results = authenticated_client.get(url, {"platform[]": pl1.pk}).json()["results"]
        assert len(results) == 2
        assert results[0]["subject"] == a0.subject
        assert results[1]["subject"] == a1.subject

        results = authenticated_client.get(url, {"platform[]": pl2.pk}).json()["results"]
        assert len(results) == 2
        assert results[0]["subject"] == a0.subject
        assert results[1]["subject"] == a2.subject
