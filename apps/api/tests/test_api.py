import pytest
from django.urls import reverse

from api.models import OrganizationAPIKey
from api.throttling import APIKeyBasedThrottle


@pytest.mark.django_db
class TestAPI:
    def test_apikey_access_report_no_key(self, client, root_platform, tr_report):
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            )
        )
        assert resp.status_code == 401

    def test_apikey_access_report_no_key_with_user(self, admin_client, root_platform, tr_report):
        resp = admin_client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            )
        )
        assert resp.status_code == 403, 'even admin cannot access without a key'

    def test_apikey_access_report_bad_key(self, client, root_platform, tr_report):
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            HTTP_AUTHORIZATION='Api-Key RANDOM.value',
        )
        assert resp.status_code == 401, 'invalid key'

    def test_apikey_access_report_good_key(self, client, root_platform, tr_report, organizations):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 400, 'allowed, but missing arg'

    def test_apikey_access_report_good_key_good_request(
        self, client, root_platform, tr_report, organizations
    ):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200

    def test_apikey_access_report_good_key_good_request_no_dimensions(
        self, client, root_platform, tr_report, organizations
    ):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            {'month': '2020-01'},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize('use_registry_id', [True, False])
    def test_platform_report_view_response(
        self, client, flexible_slicer_test_data, use_registry_id
    ):
        org = flexible_slicer_test_data['organizations'][0]
        platform = flexible_slicer_test_data['platforms'][0]
        report = flexible_slicer_test_data['report_types'][0]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name='test')
        platform_id = str(platform.counter_registry_id) if use_registry_id else platform.pk
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': platform_id, 'report_type': report.short_name},
            ),
            {'month': '2020-01', 'dims': 'dim1name'},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'OK'
        assert data['complete_data'] is True
        records = data['records']
        assert len(records) == 3 * 3 * 3, "3 titles; 3 metrics; 3 dim1 values"
        # the following data was created in a spreadsheet based on flexible_slicer_test_data
        expected = {
            ('Title 1', 'm1', 'A', 28),
            ('Title 1', 'm1', 'B', 29),
            ('Title 1', 'm1', 'C', 30),
            ('Title 1', 'm2', 'A', 37),
            ('Title 1', 'm2', 'B', 38),
            ('Title 1', 'm2', 'C', 39),
            ('Title 1', 'm3', 'A', 46),
            ('Title 1', 'm3', 'B', 47),
            ('Title 1', 'm3', 'C', 48),
            ('Title 2', 'm1', 'A', 31),
            ('Title 2', 'm1', 'B', 32),
            ('Title 2', 'm1', 'C', 33),
            ('Title 2', 'm2', 'A', 40),
            ('Title 2', 'm2', 'B', 41),
            ('Title 2', 'm2', 'C', 42),
            ('Title 2', 'm3', 'A', 49),
            ('Title 2', 'm3', 'B', 50),
            ('Title 2', 'm3', 'C', 51),
            ('Title 3', 'm1', 'A', 34),
            ('Title 3', 'm1', 'B', 35),
            ('Title 3', 'm1', 'C', 36),
            ('Title 3', 'm2', 'A', 43),
            ('Title 3', 'm2', 'B', 44),
            ('Title 3', 'm2', 'C', 45),
            ('Title 3', 'm3', 'A', 52),
            ('Title 3', 'm3', 'B', 53),
            ('Title 3', 'm3', 'C', 54),
        }
        assert {
            (rec['title'], rec['metric'], rec['dim1name'], rec['hits']) for rec in records
        } == expected

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_platform_report_view_excluded_dim(self, client, flexible_slicer_test_data):
        org = flexible_slicer_test_data['organizations'][0]
        platform = flexible_slicer_test_data['platforms'][0]
        report = flexible_slicer_test_data['report_types'][1]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name='test')
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': platform.pk, 'report_type': report.short_name},
            ),
            {'month': '2020-01', 'dims': 'dim2name'},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'OK'
        assert data['complete_data'] is True
        records = data['records']
        assert len(records) == 3 * 3 * 4, "3 titles; 3 metrics; 4 dim2 values"
        # the following data was created in a spreadsheet based on flexible_slicer_test_data
        expected = {
            ('Title 1', 'm1', 'A', 3264),
            ('Title 1', 'm1', 'XX', 3255),
            ('Title 1', 'm1', 'YY', 3258),
            ('Title 1', 'm1', 'ZZ', 3261),
            ('Title 1', 'm2', 'A', 3372),
            ('Title 1', 'm2', 'XX', 3363),
            ('Title 1', 'm2', 'YY', 3366),
            ('Title 1', 'm2', 'ZZ', 3369),
            ('Title 1', 'm3', 'A', 3480),
            ('Title 1', 'm3', 'XX', 3471),
            ('Title 1', 'm3', 'YY', 3474),
            ('Title 1', 'm3', 'ZZ', 3477),
            ('Title 2', 'm1', 'A', 3300),
            ('Title 2', 'm1', 'XX', 3291),
            ('Title 2', 'm1', 'YY', 3294),
            ('Title 2', 'm1', 'ZZ', 3297),
            ('Title 2', 'm2', 'A', 3408),
            ('Title 2', 'm2', 'XX', 3399),
            ('Title 2', 'm2', 'YY', 3402),
            ('Title 2', 'm2', 'ZZ', 3405),
            ('Title 2', 'm3', 'A', 3516),
            ('Title 2', 'm3', 'XX', 3507),
            ('Title 2', 'm3', 'YY', 3510),
            ('Title 2', 'm3', 'ZZ', 3513),
            ('Title 3', 'm1', 'A', 3336),
            ('Title 3', 'm1', 'XX', 3327),
            ('Title 3', 'm1', 'YY', 3330),
            ('Title 3', 'm1', 'ZZ', 3333),
            ('Title 3', 'm2', 'A', 3444),
            ('Title 3', 'm2', 'XX', 3435),
            ('Title 3', 'm2', 'YY', 3438),
            ('Title 3', 'm2', 'ZZ', 3441),
            ('Title 3', 'm3', 'A', 3552),
            ('Title 3', 'm3', 'XX', 3543),
            ('Title 3', 'm3', 'YY', 3546),
            ('Title 3', 'm3', 'ZZ', 3549),
        }
        assert {
            (rec['title'], rec['metric'], rec['dim2name'], rec['hits']) for rec in records
        } == expected

    def test_platform_report_view_no_data_no_sushi(
        self, client, root_platform, tr_report, organizations
    ):
        """
        Report has no data for the requested period and there is no SUSHI active for this
        combination of platform, organization and report
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            {'month': '2020-01', 'dims': ''},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['complete_data'] is False
        assert data['status'] == 'SUSHI credentials not present for this report'

    def test_platform_report_view_incorrect_dims(
        self, client, root_platform, tr_report, organizations
    ):
        """
        User requested dimensions that are not supported by the report type
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
            ),
            {'month': '2020-01', 'dims': 'foo,bar'},
            HTTP_AUTHORIZATION=f'Api-Key {key_val}',
        )
        assert resp.status_code == 400
        assert b'Unknown dimensions' in resp.content

    @pytest.mark.parametrize('throttling', [True, False])
    def test_platform_report_view_throttling(
        self, client, root_platform, tr_report, organizations, throttling
    ):
        """
        Test throttling of the platform report view
        """
        # at this point, it is not possible to adjust the throttling rate via settings
        # so we have to set it on the class directly
        APIKeyBasedThrottle.rate = '1/minute' if throttling else '2/minute'
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations['root'], name='test'
        )

        def make_request():
            return client.get(
                reverse(
                    'api_platform_report_data',
                    kwargs={'platform_id': root_platform.pk, 'report_type': tr_report.short_name},
                ),
                {'month': '2020-01', 'dims': ''},
                HTTP_AUTHORIZATION=f'Api-Key {key_val}',
            )

        # first request should always succeed
        resp = make_request()
        assert resp.status_code == 200
        # second request should fail if throttling is enabled
        resp2 = make_request()
        assert resp2.status_code == (429 if throttling else 200)
        # remove the rate attr from APIKeyBasedThrottle so that it doesn't affect other tests
        del APIKeyBasedThrottle.rate
