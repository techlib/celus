"""
This module contains some tests for the `PlatformReportView` which require a different set of
fixtures which clash with those for other tests of this view.
"""

import pytest
from api.models import OrganizationAPIKey
from django.urls import reverse
from django.utils.timezone import now
from sushi.models import CounterReportsToCredentials
from sushi.tests.conftest import counter_report_type, credentials, organizations, platforms  # noqa

from test_fixtures.entities.scheduler import FetchIntentionFactory


@pytest.mark.django_db
class TestPlatformReportApiView:
    def test_platform_report_view_no_data_with_sushi_no_attempts(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period but there is SUSHI active for this
        combination of platform, organization and report
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'Data not yet harvested'

    def test_platform_report_view_no_data_with_inactive_sushi(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period and there is SUSHI which is inactive for this
        combination of platform, organization and report
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        credentials.enabled = False
        credentials.save()
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'SUSHI credentials are not automatically harvested'

    def test_platform_report_view_no_data_with_broken_sushi(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period and there is SUSHI which is broken for this
        combination of platform, organization and report
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        credentials.broken = True
        credentials.save()
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'SUSHI credentials are incorrect'

    def test_platform_report_view_no_data_with_sushi_with_queued_attempt(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period but there is SUSHI active for this
        combination of platform, organization and report.
        There is a fetch attempt which is still running.
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        fi = FetchIntentionFactory(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
            when_processed=now(),
        )
        FetchIntentionFactory(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
            queue=fi.queue,
            attempt=None,
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'Harvesting ongoing'

    def test_platform_report_view_no_data_with_sushi_with_3030_attempt(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period but there is SUSHI active for this
        combination of platform, organization and report.
        The last attempt ended with 3030 which means valid empty data result.
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        FetchIntentionFactory(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
            attempt__error_code='3030',
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is True
        assert data['status'] == 'Empty data'

    def test_platform_report_view_no_data_with_sushi_with_unsuccessfull_attempt(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period but there is SUSHI active for this
        combination of platform, organization and report.
        The last attempt ended without any indication of empty data, so the harvesing was not
        successfull.
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        credentials.counter_reports.add(counter_report_type)
        FetchIntentionFactory(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'Harvesting error'

    def test_platform_report_view_no_data_with_sushi_with_broken_report(
        self, client, counter_report_type, organizations, credentials
    ):
        """
        Report has no data for the requested period but there is SUSHI active for this
        combination of platform, organization and report, but the report is marked as broken
        for these credentials.
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=credentials.organization, name='test'
        )
        CounterReportsToCredentials.objects.create(
            credentials=credentials, counter_report=counter_report_type, broken=True
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={
                    'platform_id': credentials.platform.pk,
                    'report_type': counter_report_type.report_type.short_name,
                },
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'Report marked as broken for existing credentials'
