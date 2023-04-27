from unittest import mock

import pytest
from django.urls import reverse
from scheduler.models import FetchIntention
from sushi.models import SushiCredentials

from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory
from test_fixtures.scenarios.basic import *  # noqa


@pytest.mark.django_db
class TestSushiCredentialsAPI:
    @pytest.mark.parametrize(
        [
            'user',
            'delete_credentials',
            'delete_fetchintentions',
            'delete_data',
            'delete_fetchattempts_and_related_importbatches',
            'status_code',
        ],
        [
            ['admin2', True, True, True, True, 204],
            ['admin1', False, False, True, False, 404],
            ['user2', False, False, True, False, 404],
            ['admin2', True, True, False, False, 204],
            ['admin1', False, False, False, False, 404],
        ],
    )
    def test_destroy(
        self,
        credentials,
        clients,
        user,
        basic1,
        delete_fetchattempts_and_related_importbatches,
        delete_credentials,
        delete_fetchintentions,
        delete_data,
        status_code,
    ):

        cr = credentials['standalone_tr']
        fetch_attempts = FetchAttemptFactory.create_batch(2, credentials=cr)
        fi = FetchIntentionFactory(credentials=cr, attempt=fetch_attempts[0])

        cr_queryset = SushiCredentials.objects.filter(pk=cr.pk)
        fi_queryset = FetchIntention.objects.filter(pk=fi.pk)

        assert cr_queryset.exists()
        assert fi_queryset.exists()

        with mock.patch(
            'sushi.views.delete_fetchattempts_and_related_importbatches_task'
        ) as mock_task:
            url = reverse('sushi-credentials-detail', args=[cr.pk])
            url += f'?delete_data={delete_data}'
            res = clients[user].delete(url)
            assert res.status_code == status_code

            if delete_fetchattempts_and_related_importbatches:
                fa_pks = [fa.pk for fa in fetch_attempts]
                mock_task.delay.assert_called_with(fa_pks)
            else:
                mock_task.delay.assert_not_called()

        if delete_credentials:
            assert not cr_queryset.exists()
        else:
            assert cr_queryset.exists()

        if delete_fetchintentions:
            assert not fi_queryset.exists()
        else:
            assert fi_queryset.exists()
