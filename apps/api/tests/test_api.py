import pytest
from api.models import OrganizationAPIKey
from django.urls import reverse


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

    def test_platform_report_view_response(self, client, flexible_slicer_test_data):
        org = flexible_slicer_test_data['organizations'][0]
        platform = flexible_slicer_test_data['platforms'][0]
        report = flexible_slicer_test_data['report_types'][0]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name='test')
        resp = client.get(
            reverse(
                'api_platform_report_data',
                kwargs={'platform_id': platform.pk, 'report_type': report.short_name},
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
            ('Title 1', 'm1', 'A', 4),
            ('Title 1', 'm1', 'B', 5),
            ('Title 1', 'm1', 'C', 6),
            ('Title 1', 'm2', 'A', 40),
            ('Title 1', 'm2', 'B', 41),
            ('Title 1', 'm2', 'C', 42),
            ('Title 1', 'm3', 'A', 76),
            ('Title 1', 'm3', 'B', 77),
            ('Title 1', 'm3', 'C', 78),
            ('Title 2', 'm1', 'A', 16),
            ('Title 2', 'm1', 'B', 17),
            ('Title 2', 'm1', 'C', 18),
            ('Title 2', 'm2', 'A', 52),
            ('Title 2', 'm2', 'B', 53),
            ('Title 2', 'm2', 'C', 54),
            ('Title 2', 'm3', 'A', 88),
            ('Title 2', 'm3', 'B', 89),
            ('Title 2', 'm3', 'C', 90),
            ('Title 3', 'm1', 'A', 28),
            ('Title 3', 'm1', 'B', 29),
            ('Title 3', 'm1', 'C', 30),
            ('Title 3', 'm2', 'A', 64),
            ('Title 3', 'm2', 'B', 65),
            ('Title 3', 'm2', 'C', 66),
            ('Title 3', 'm3', 'A', 100),
            ('Title 3', 'm3', 'B', 101),
            ('Title 3', 'm3', 'C', 102),
        }
        assert {
            (rec['title'], rec['metric'], rec['dim1name'], rec['hits']) for rec in records
        } == expected

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
            ('Title 1', 'm1', 'A', 2976),
            ('Title 1', 'm1', 'XX', 2967),
            ('Title 1', 'm1', 'YY', 2970),
            ('Title 1', 'm1', 'ZZ', 2973),
            ('Title 1', 'm2', 'A', 3408),
            ('Title 1', 'm2', 'XX', 3399),
            ('Title 1', 'm2', 'YY', 3402),
            ('Title 1', 'm2', 'ZZ', 3405),
            ('Title 1', 'm3', 'A', 3840),
            ('Title 1', 'm3', 'XX', 3831),
            ('Title 1', 'm3', 'YY', 3834),
            ('Title 1', 'm3', 'ZZ', 3837),
            ('Title 2', 'm1', 'A', 3120),
            ('Title 2', 'm1', 'XX', 3111),
            ('Title 2', 'm1', 'YY', 3114),
            ('Title 2', 'm1', 'ZZ', 3117),
            ('Title 2', 'm2', 'A', 3552),
            ('Title 2', 'm2', 'XX', 3543),
            ('Title 2', 'm2', 'YY', 3546),
            ('Title 2', 'm2', 'ZZ', 3549),
            ('Title 2', 'm3', 'A', 3984),
            ('Title 2', 'm3', 'XX', 3975),
            ('Title 2', 'm3', 'YY', 3978),
            ('Title 2', 'm3', 'ZZ', 3981),
            ('Title 3', 'm1', 'A', 3264),
            ('Title 3', 'm1', 'XX', 3255),
            ('Title 3', 'm1', 'YY', 3258),
            ('Title 3', 'm1', 'ZZ', 3261),
            ('Title 3', 'm2', 'A', 3696),
            ('Title 3', 'm2', 'XX', 3687),
            ('Title 3', 'm2', 'YY', 3690),
            ('Title 3', 'm2', 'ZZ', 3693),
            ('Title 3', 'm3', 'A', 4128),
            ('Title 3', 'm3', 'XX', 4119),
            ('Title 3', 'm3', 'YY', 4122),
            ('Title 3', 'm3', 'ZZ', 4125),
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
