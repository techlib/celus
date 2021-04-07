import json
from io import StringIO
from itertools import combinations
from unittest.mock import patch

import pytest
from django.urls import reverse

from core.logic.serialization import b64json
from logs.models import (
    ReportType,
    AccessLog,
    Metric,
    ImportBatch,
    Dimension,
    FlexibleReport,
    DimensionText,
)
from organizations.models import UserOrganization
from publications.models import Platform

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import organizations, identity_by_user_type
from core.tests.conftest import (
    valid_identity,
    authenticated_client,
    authentication_headers,
    invalid_identity,
    master_identity,
    master_client,
    admin_identity,
)
from test_fixtures.scenarios.basic import users  # noqa


@pytest.mark.django_db
class TestChartDataAPI:

    """
    Tests functionality of the view chart-data
    """

    def test_api_simple_data_0d(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(
            report_type, organization, platform, counter_records_0d, import_batch
        )
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        with patch('recache.util.renew_cached_query_task') as renewal_task:
            # the following is necessary so that it does not hang in Gitlab
            resp = authenticated_client.get(
                reverse('chart_data_raw', args=(report_type.pk,)),
                {
                    'organization': organization.pk,
                    'metric': metric.pk,
                    'platform': platform.pk,
                    'prim_dim': 'date',
                },
            )
            # make sure recache is not used here
            renewal_task.apply_async.assert_not_called()
        assert resp.status_code == 200
        assert 'data' in resp.json()

    def test_api_simple_data_0d_with_recache(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(
            report_type, organization, platform, counter_records_0d, import_batch
        )
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        # the following is necessary so that it does not hang in Gitlab
        resp = authenticated_client.get(
            reverse('chart_data_raw', args=(report_type.pk,)),
            {
                'organization': organization.pk,
                'metric': metric.pk,
                'platform': platform.pk,
                'prim_dim': 'date',
                'dashboard': True,
            },
        )
        assert resp.status_code == 200
        assert 'data' in resp.json()

    @pytest.mark.parametrize(
        'primary_dim, secondary_dim, count',
        [
            ['date', None, 3],  # three months
            ['date', 1, 4],  # two values in first month
            [1, None, 2],  # two values in first dim
            [2, None, 3],  # three values in first dim
            [2, 3, 4],  # four combinations of dim2 and dim3
            ['platform', None, 1],  # just one platform
        ],
    )
    def test_api_secondary_dim(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        count,
        authenticated_client,
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
            ['Title2', '2018-01-01', '1v2', '2v2', '3v1', 4],
            ['Title1', '2018-02-01', '1v1', '2v1', '3v1', 8],
            ['Title2', '2018-02-01', '1v1', '2v2', '3v2', 16],
            ['Title1', '2018-03-01', '1v1', '2v3', '3v2', 32],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs, import_batch)
        assert AccessLog.objects.count() == 6
        metric = Metric.objects.get(short_name='Hits')
        if type(primary_dim) is int:
            primary_dim = report_type.dimensions_sorted[primary_dim - 1].short_name
        params = {
            'organization': organization.pk,
            'metric': metric.pk,
            'platform': platform.pk,
            'prim_dim': primary_dim,
        }
        if secondary_dim:
            params['sec_dim'] = report_type.dimensions_sorted[secondary_dim - 1].short_name
        resp = authenticated_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        assert len(data['data']) == count

    @pytest.mark.parametrize(
        'primary_dim, secondary_dim, result',
        [
            ['date', None, [{'date': '2018-01-01', 'count': 3}]],
            ['date', 3, [{'date': '2018-01-01', 'dim2': '3v1', 'count': 3}]],
            [
                'date',
                1,
                [
                    {'date': '2018-01-01', 'dim0': '1v1', 'count': 1},
                    {'date': '2018-01-01', 'dim0': '1v2', 'count': 2},
                ],
            ],
            ['platform', None, [{'platform': 'Platform1', 'count': 3}]],
            ['platform', 'metric', [{'platform': 'Platform1', 'metric': 'Hits', 'count': 3}]],
            ['metric', 'platform', [{'platform': 'Platform1', 'metric': 'Hits', 'count': 3}]],
            ['organization', None, [{'organization': 'AAA', 'count': 3}]],
            ['organization', 'metric', [{'organization': 'AAA', 'metric': 'Hits', 'count': 3}]],
            ['metric', 'organization', [{'organization': 'AAA', 'metric': 'Hits', 'count': 3}]],
        ],
    )
    def test_api_values(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        result,
        master_client,
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs, import_batch)
        assert AccessLog.objects.count() == 2
        metric = Metric.objects.get(short_name='Hits')
        params = {
            'organization': organization.pk,
            'metric': metric.pk,
            'platform': platform.pk,
            'prim_dim': primary_dim,
        }
        if secondary_dim:
            if type(secondary_dim) is int:
                params['sec_dim'] = report_type.dimensions_sorted[secondary_dim - 1].short_name
            else:
                params['sec_dim'] = secondary_dim
        resp = master_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        assert data['data'] == result

    def test_api_filtering(
        self, counter_records, organizations, report_type_nd, authenticated_client
    ):
        platform1 = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        platform2 = Platform.objects.create(
            ext_id=1235, short_name='Platform2', name='Platform 2', provider='Provider 2'
        )
        data1 = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title2', '2018-01-01', '1v2', '2v1', '3v1', 2],
            ['Title3', '2018-01-01', '1v2', '2v1', '3v1', 4],
        ]
        data2 = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 8],
            ['Title2', '2018-02-01', '1v1', '2v1', '3v1', 16],
            ['Title3', '2018-02-01', '1v2', '2v2', '3v1', 32],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        crs2 = list(counter_records(data2, metric='Big Hits', platform='Platform2'))
        report_type = report_type_nd(3)
        import_counter_records(
            report_type,
            organizations[0],
            platform1,
            crs1,
            ImportBatch.objects.create(
                organization=organizations[0], platform=platform1, report_type=report_type
            ),
        )
        import_counter_records(
            report_type,
            organizations[0],
            platform2,
            crs1,
            ImportBatch.objects.create(
                organization=organizations[0], platform=platform2, report_type=report_type
            ),
        )
        import_counter_records(
            report_type,
            organizations[1],
            platform1,
            crs1,
            ImportBatch.objects.create(
                organization=organizations[1], platform=platform1, report_type=report_type
            ),
        )
        import_counter_records(
            report_type,
            organizations[1],
            platform2,
            crs2,
            ImportBatch.objects.create(
                organization=organizations[1], platform=platform2, report_type=report_type
            ),
        )
        assert AccessLog.objects.count() == 12
        metric1 = Metric.objects.get(short_name='Hits')
        metric2 = Metric.objects.get(short_name='Big Hits')

        def get_data(params):
            resp = authenticated_client.get(
                reverse('chart_data_raw', args=(report_type.pk,)), params
            )
            assert resp.status_code == 200
            result = json.loads(resp.content)
            assert 'data' in result
            return result['data']

        # no filter
        recs = get_data({'prim_dim': 'date'})
        assert len(recs) == 2
        assert recs[0]['count'] == 3 * (1 + 2 + 4) + 8
        assert recs[1]['count'] == 16 + 32
        # organization filter
        recs = get_data({'organization': organizations[0].pk, 'prim_dim': 'date'})
        assert len(recs) == 1
        assert recs[0]['count'] == 2 * (1 + 2 + 4)
        # organization dim, platform filter
        recs = get_data({'platform': platform2.pk, 'prim_dim': 'organization'})
        assert len(recs) == 2
        assert recs[0]['count'] == 1 + 2 + 4
        assert recs[1]['count'] == 8 + 16 + 32
        # filter by dim1, platform dim
        recs = get_data({'dim0': '1v1', 'prim_dim': 'platform'})
        assert len(recs) == 2
        assert recs[0]['count'] == 2 * 1
        assert recs[1]['count'] == 1 + 8 + 16
        # filter by dim2, platform and title dim
        recs = get_data({'dim0': '1v1', 'prim_dim': 'platform', 'sec_dim': 'target'})
        assert len(recs) == 3
        assert recs[0]['count'] == 2 * 1  # platform 1 and title 1
        assert recs[1]['count'] == 1 + 8  # platform 2 and title 1
        assert recs[2]['count'] == 16  # platform 2 and title 2
        # filter by date
        recs = get_data({'date': '2018-02-01', 'prim_dim': 'target'})
        assert len(recs) == 2
        assert recs[0]['count'] == 16
        assert recs[1]['count'] == 32
        # filter by date range
        recs = get_data({'start': '2018-02', 'end': '2018-02', 'prim_dim': 'target'})
        assert len(recs) == 2
        assert recs[0]['count'] == 16
        assert recs[1]['count'] == 32

    @pytest.mark.parametrize(
        'primary_dim, secondary_dim, count',
        [
            ['date', None, 3],  # three months
            ['date', 1, 4],  # two values in first month
            [1, None, 2],  # two values in first dim
            [2, None, 3],  # three values in first dim
            [2, 3, 4],  # four combinations of dim2 and dim3
            ['platform', None, 1],  # just one platform
        ],
    )
    def test_api_secondary_dim_no_title(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        count,
        authenticated_client,
    ):
        """
        Copy of the same test as test_api_secondary_dim but with title set to None
        """
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            [None, '2018-01-01', '1v1', '2v1', '3v1', 1],
            [None, '2018-01-01', '1v2', '2v1', '3v1', 2],
            [None, '2018-01-01', '1v2', '2v2', '3v1', 4],
            [None, '2018-02-01', '1v1', '2v1', '3v1', 8],
            [None, '2018-02-01', '1v1', '2v2', '3v2', 16],
            [None, '2018-03-01', '1v1', '2v3', '3v2', 32],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs, import_batch)
        assert AccessLog.objects.count() == 6
        metric = Metric.objects.get(short_name='Hits')
        if type(primary_dim) is int:
            primary_dim = report_type.dimensions_sorted[primary_dim - 1].short_name
        params = {
            'organization': organization.pk,
            'metric': metric.pk,
            'platform': platform.pk,
            'prim_dim': primary_dim,
        }
        if secondary_dim:
            params['sec_dim'] = report_type.dimensions_sorted[secondary_dim - 1].short_name
        resp = authenticated_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        assert len(data['data']) == count

    def test_api_date_year_query(
        self, counter_records, organizations, report_type_nd, authenticated_client
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title1', '2018-02-01', '1v1', 2],
            ['Title2', '2018-03-01', '1v2', 4],
            ['Title1', '2019-01-01', '1v1', 8],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(1)
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs, import_batch)
        assert AccessLog.objects.count() == 4
        metric = Metric.objects.get(short_name='Hits')
        # check it without year first
        params = {
            'organization': organization.pk,
            'metric': metric.pk,
            'platform': platform.pk,
            'prim_dim': 'date',
        }
        resp = authenticated_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 4
        # now try years
        params['prim_dim'] = 'date__year'
        resp = authenticated_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['data']) == 2
        assert data['data'][0]['count'] == 7


@pytest.mark.django_db
class TestManualDataUpload:
    def test_can_create_manual_data_upload(
        self, organizations, master_client, report_type_nd, tmp_path, settings
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(0)
        file = StringIO('Source,2019-01\naaaa,9\n')
        settings.MEDIA_ROOT = tmp_path
        response = master_client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organizations[0].pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
        )
        assert response.status_code == 201

    def test_manual_upload_data_disabled(self, master_client, settings):
        settings.ALLOW_MANUAL_UPLOAD = False
        response = master_client.get(reverse('manual-data-upload-list'),)
        assert response.status_code == 403


@pytest.mark.django_db
class TestReportTypeAPI:
    def test_create_report_type_400(self, organizations, authenticated_client):
        organization = organizations[0]
        assert ReportType.objects.count() == 0
        response = authenticated_client.post(
            reverse('organization-report-types-list', kwargs={'organization_pk': organization.pk}),
            {
                'short_name': 'TEST',
                'name_cs': 'Test report',
                'name_en': 'Test report',
                'name': 'Test report',
                'dimensions': [],
            },
            content_type='application/json',
        )
        assert response.status_code == 400
        assert b'cannot access' in response.content
        assert ReportType.objects.count() == 0, 'no new ReportType was created'

    def test_create_report_type(self, organizations, authenticated_client):
        organization = organizations[0]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        response = authenticated_client.post(
            reverse('organization-report-types-list', kwargs={'organization_pk': organization.pk}),
            {
                'short_name': 'TEST',
                'name_cs': 'Test report',
                'name_en': 'Test report',
                'name': 'Test report',
                'dimensions': [],
            },
            content_type='application/json',
        )
        print(response.content)
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, 'a new ReportType was created'
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 0, 'no extra dimensions for ReportType'

    def test_create_report_type_with_dimension(self, organizations, authenticated_client):
        organization = organizations[0]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        dim1 = Dimension.objects.create(short_name='dim1', name='Dimension 1')
        dim2 = Dimension.objects.create(short_name='dim2', name='Dimension 2')
        response = authenticated_client.post(
            reverse('organization-report-types-list', kwargs={'organization_pk': organization.pk}),
            {
                'short_name': 'TEST',
                'name_cs': 'Test report',
                'name_en': 'Test report',
                'name': 'Test report',
                'dimensions': [dim1.pk, dim2.pk],
                'public': False,
            },
            content_type='application/json',
        )
        print(response.content)
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, 'a new ReportType was created'
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 2

    def test_create_report_type_with_invalid_dimension(self, organizations, authenticated_client):
        organization = organizations[0]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        dim1 = Dimension.objects.create(short_name='dim1', name='Dimension 1')
        response = authenticated_client.post(
            reverse('organization-report-types-list', kwargs={'organization_pk': organization.pk}),
            {
                'short_name': 'TEST',
                'name_cs': 'Test report',
                'name_en': 'Test report',
                'name': 'Test report',
                'dimensions': [dim1.pk, dim1.pk + 1],
            },
            content_type='application/json',
        )
        assert response.status_code == 400
        assert ReportType.objects.count() == 0
        assert 'object does not exist' in response.json()['dimensions'][0]


@pytest.mark.django_db
class TestRawDataExport:
    @pytest.mark.parametrize(
        ['user_type', 'can_access'],
        [
            ['no_user', False],
            ['invalid', False],
            ['unrelated', False],
            ['related_user', True],
            ['related_admin', True],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_raw_export_start_organization_access(
        self, user_type, can_access, identity_by_user_type, client, authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        url = reverse('raw_data_export')
        with patch('logs.views.export_raw_data_task') as export_task:
            resp = client.post(
                url + f'?organization={org.pk}',
                content_type='application/json',
                **authentication_headers(identity),
            )
            expected_status_code = (200,) if can_access else (401, 403)
            assert resp.status_code in expected_status_code
            if can_access:
                export_task.delay.assert_called()
            else:
                export_task.delay.assert_not_called()

    @pytest.mark.parametrize(
        ['user_type', 'can_access'],
        [
            ['no_user', False],
            ['invalid', False],
            ['unrelated', False],
            ['related_user', False],
            ['related_admin', False],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_raw_export_start_no_organization_access(
        self, user_type, can_access, identity_by_user_type, client, authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        url = reverse('raw_data_export')
        with patch('logs.views.export_raw_data_task') as export_task:
            resp = client.post(
                url, content_type='application/json', **authentication_headers(identity)
            )
            expected_status_code = (200,) if can_access else (401, 403)
            assert resp.status_code in expected_status_code
            if can_access:
                export_task.delay.assert_called()
            else:
                export_task.delay.assert_not_called()


@pytest.mark.django_db
class TestFlexibleReportAPI:
    def test_list_simple(self, admin_client):
        url = reverse('flexible-report-list')
        resp = admin_client.get(url)
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ['user', 'accessible_reports'],
        [
            ['user1', {'public', 'user1 report'}],
            ['user2', {'public', 'org2+user2 report'}],
            ['admin2', {'public', 'org1 report'}],
            ['admin1', {'public', 'org2+user2 report'}],
            ['empty', {'public', 'org2+user2 report', 'org1 report'}],
            ['master', {'public'}],
            ['su', {'public', 'org1 report', 'org2+user2 report'}],  # cannot see private
        ],
    )
    def test_list_access(self, client, users, organizations, user, accessible_reports):
        organization1 = organizations[0]
        organization2 = organizations[1]
        FlexibleReport.objects.create(name='public')
        FlexibleReport.objects.create(name='user1 report', owner=users['user1'])
        FlexibleReport.objects.create(name='org1 report', owner_organization=organization1)
        FlexibleReport.objects.create(
            name='org2+user2 report', owner_organization=organization2, owner=users['user2']
        )
        UserOrganization.objects.create(user=users['admin1'], organization=organization2)
        UserOrganization.objects.create(user=users['admin2'], organization=organization1)
        UserOrganization.objects.create(user=users['empty'], organization=organization2)
        UserOrganization.objects.create(user=users['empty'], organization=organization1)
        url = reverse('flexible-report-list')
        client.force_login(users[user])
        resp = client.get(url)
        assert resp.status_code == 200
        assert accessible_reports == {rec['name'] for rec in resp.json()}

    def test_create(self, admin_client, admin_user):
        resp = admin_client.post(
            reverse('flexible-report-list'),
            {
                'name': 'test report',
                'config': {'primary_dimension': 'platform', 'groups': b64json(['metric'])},
            },
            content_type='application/json',
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()['pk'])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config['primary_dimension'] == 'platform'
        assert report.report_config['group_by'] == ['metric']

    @pytest.fixture()
    def user_organizations(self, users, organizations):
        org1 = organizations[0]
        org2 = organizations[1]
        UserOrganization.objects.create(user=users['user1'], organization=org1)
        UserOrganization.objects.create(user=users['user2'], organization=org2)
        UserOrganization.objects.create(user=users['admin1'], organization=org1, is_admin=True)
        UserOrganization.objects.create(user=users['admin2'], organization=org2, is_admin=True)
        UserOrganization.objects.create(user=users['master'], organization=org1, is_admin=True)
        UserOrganization.objects.create(user=users['master'], organization=org2, is_admin=True)

    @pytest.mark.parametrize(
        ['user', 'can_private', 'can_org1', 'can_org2', 'can_consortium'],
        [
            #         private, org1, org2, consortium
            ['user1', True, False, False, False],  # normal user, connected to org1
            ['user2', True, False, False, False],  # normal user, connected to org2
            ['admin1', True, True, False, False],  # admin of org1
            ['admin2', True, False, True, False],  # admin of org2
            ['master', True, True, True, False],  # admin of org1 and org2
            ['su', True, True, True, True],  # superuser
        ],
    )
    def test_create_accesslevel(
        self,
        client,
        users,
        organizations,
        user_organizations,
        user,
        can_private,
        can_org1,
        can_org2,
        can_consortium,
    ):
        """
        Test that when saving a report the user can/cannot set a specific accesslevel
        and also for specific organization when setting organization level access
        """
        org1 = organizations[0]
        org2 = organizations[1]
        data_base = {
            'name': 'test report',
            'config': {'primary_dimension': 'platform', 'groups': b64json(['metric'])},
        }
        url = reverse('flexible-report-list')
        client.force_login(users[user])

        # private
        resp = client.post(url, data_base, content_type='application/json')
        assert resp.status_code == (201 if can_private else 403)
        assert resp.json()['owner'] == users[user].pk
        assert resp.json()['owner_organization'] is None

        # org1
        resp = client.post(
            url,
            {**data_base, 'owner_organization': org1.pk, 'owner': None},
            content_type='application/json',
        )
        assert resp.status_code == (201 if can_org1 else 403)
        if can_org1:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org1.pk

        # org2
        resp = client.post(
            url,
            {**data_base, 'owner_organization': org2.pk, 'owner': None},
            content_type='application/json',
        )
        assert resp.status_code == (201 if can_org2 else 403)
        if can_org2:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org2.pk

        # consortium
        resp = client.post(url, {**data_base, 'owner': None}, content_type='application/json')
        assert resp.status_code == (201 if can_consortium else 403)
        if can_consortium:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] is None

    @classmethod
    def access_to_code(cls, access, delete=False):
        if access is None:
            return 404
        elif access:
            return 204 if delete else 200
        return 403

    @pytest.fixture(params=["user1", "user2", "org1", "org2", "admin1", "admin2", "consortium"])
    def flexible_report(self, request, organizations, users):
        data = {'report_config': {'primary_dimension': 'platform', 'group_by': ['metric']}}
        if request.param in ('user1', 'user2', 'admin1', 'admin2'):
            # user owned
            data['owner'] = users[request.param]
        elif request.param == 'org1':
            # organization owned
            data['owner_organization'] = organizations[0]
        elif request.param == 'org2':
            # organization owned
            data['owner_organization'] = organizations[1]
        elif request.param == 'consortium':
            # consortium owned
            data['owner'] = None
        return {
            'level': request.param,
            'report': FlexibleReport.objects.create(name=f'test {request.param}', **data),
        }

    @pytest.mark.parametrize(
        ['user', 'can'],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                'user1',  # normal user, connected to org1
                {
                    'user1': (True, True, False, False, False),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (False, False, False, False, False),  # what he can do to report org1
                    'org2': (None, None, None, None, None),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'user2',  # normal user, connected to org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (True, True, False, False, False),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (None, None, None, None, None),  # what he can do to report org1
                    'org2': (False, False, False, False, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'admin1',  # admin of org1
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (True, True, True, False, False),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, False, False),  # what he can do to report org1
                    'org2': (None, None, None, None, None),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'admin2',  # admin of org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (True, True, False, True, False),  # what he can do to report admin2
                    'org1': (None, None, None, None, None),  # what he can do to report org1
                    'org2': (True, True, False, True, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'master',  # admin of org1 and org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, True, False),  # what he can do to report org1
                    'org2': (True, True, True, True, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'su',  # superuser
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, True, True),  # what he can do to report org1
                    'org2': (True, True, True, True, True),  # what he can do to report org2
                    'consortium': (True, True, True, True, True),  # what he can do to cons...
                },
            ],
        ],
    )
    def test_update_accesslevel(
        self, client, users, organizations, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        org1 = organizations[0]
        org2 = organizations[1]
        fr = flexible_report['report']
        url = reverse('flexible-report-detail', args=(fr.pk,))
        client.force_login(users[user])
        can_change_spec, can_private, can_org1, can_org2, can_consortium = can[
            flexible_report['level']
        ]

        # change spec
        resp = client.patch(url, {'name': 'foobar'}, content_type='application/json')
        assert resp.status_code == self.access_to_code(can_change_spec)
        if can_change_spec:
            assert resp.json()['owner'] == fr.owner_id
            assert resp.json()['owner_organization'] == fr.owner_organization_id

        # private
        resp = client.patch(
            url,
            {'owner': users[user].pk, 'owner_organization': None},
            content_type='application/json',
        )
        assert resp.status_code == self.access_to_code(can_private)
        if can_private:
            assert resp.json()['owner'] == users[user].pk
            assert resp.json()['owner_organization'] is None

        # org1
        resp = client.patch(
            url, {'owner_organization': org1.pk, 'owner': None}, content_type='application/json',
        )
        assert resp.status_code == self.access_to_code(can_org1)
        if can_org1:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org1.pk

        # org2
        resp = client.patch(
            url, {'owner_organization': org2.pk, 'owner': None}, content_type='application/json',
        )
        assert resp.status_code == self.access_to_code(can_org2)
        if can_org2:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org2.pk

        # consortium
        resp = client.patch(
            url, {'owner_organization': None, 'owner': None}, content_type='application/json'
        )
        assert resp.status_code == self.access_to_code(can_consortium)
        if can_consortium:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] is None

    @pytest.mark.parametrize(
        ['user', 'can'],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                'user1',  # normal user, connected to org1
                {
                    'user1': True,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': False,  # what he can do to report org1
                    'org2': None,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'user2',  # normal user, connected to org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': True,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': None,  # what he can do to report org1
                    'org2': False,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'admin1',  # admin of org1
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': True,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': None,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'admin2',  # admin of org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': True,  # what he can do to report admin2
                    'org1': None,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'master',  # admin of org1 and org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'su',  # superuser
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': True,  # what he can do to cons...
                },
            ],
        ],
    )
    def test_delete_accesslevel(
        self, client, users, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        fr = flexible_report['report']
        url = reverse('flexible-report-detail', args=(fr.pk,))
        client.force_login(users[user])
        can_delete = can[flexible_report['level']]

        resp = client.delete(url)
        assert resp.status_code == self.access_to_code(can_delete, delete=True)
        if can_delete:
            assert FlexibleReport.objects.count() == 0
        else:
            assert FlexibleReport.objects.count() == 1


@pytest.fixture
def dimension_texts():
    dim1 = Dimension.objects.create(short_name='dim1')
    dim2 = Dimension.objects.create(short_name='dim2')
    dt1 = DimensionText.objects.create(text='test1', dimension=dim1)
    dt2 = DimensionText.objects.create(text='test2', dimension=dim1)
    dt3 = DimensionText.objects.create(text='test3', dimension=dim2)
    return {
        dt1.text: dt1,
        dt2.text: dt2,
        dt3.text: dt3,
    }


@pytest.mark.django_db
class TestDimensionTextAPI:
    def test_list_simple(self, admin_client):
        url = reverse('dimension-text-list')
        resp = admin_client.get(url)
        assert resp.status_code == 200

    def test_list_with_data(self, admin_client, dimension_texts):
        url = reverse('dimension-text-list')
        resp = admin_client.get(url)
        assert resp.status_code == 200
        assert resp.json()['count'] == len(dimension_texts)
        assert len(resp.json()['results']) == len(dimension_texts)

    def test_list_with_selected_pks(self, admin_client, dimension_texts):
        url = reverse('dimension-text-list')
        dt_ids = [dimension_texts['test1'].pk, dimension_texts['test3'].pk]
        resp = admin_client.get(url, {'pks': ','.join(map(str, dt_ids))})
        assert resp.status_code == 200
        assert 'count' not in resp.json(), 'we do not paginate when using list of ids'
        assert set(dt_ids) == {rec['pk'] for rec in resp.json()}

    def test_list_via_post_with_selected_pks(self, admin_client, dimension_texts):
        """
        Test that the post method works the same a GET - we need this to support long lists of
        IDs passed to the endpoint
        """
        url = reverse('dimension-text-list')
        dt_ids = [dimension_texts['test1'].pk, dimension_texts['test3'].pk]
        resp = admin_client.post(url, {'pks': dt_ids}, content_type='application/json')
        assert resp.status_code == 200
        assert set(dt_ids) == {rec['pk'] for rec in resp.json()}
        assert 'count' not in resp.json(), 'we do not paginate POST results'


@pytest.mark.django_db
class TestSlicerAPI:
    def test_primary_dimension_required(self, flexible_slicer_test_data, admin_client):
        url = reverse('flexible-slicer')
        resp = admin_client.get(url)
        assert resp.status_code == 400
        assert 'error' in resp.json()
        assert resp.json()['error']['code'] == 'E104'

    def test_group_by_required(self, flexible_slicer_test_data, admin_client):
        url = reverse('flexible-slicer')
        resp = admin_client.get(url, {'primary_dimension': 'platform'})
        assert resp.status_code == 400
        assert 'error' in resp.json()
        assert resp.json()['error']['code'] == 'E106'
