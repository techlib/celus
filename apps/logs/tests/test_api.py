import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from core.logic.dates import month_end, month_start
from core.tests.conftest import admin_identity  # noqa - fixtures
from core.tests.conftest import (
    authenticated_client,
    authentication_headers,
    invalid_identity,
    master_admin_client,
    master_admin_identity,
    valid_identity,
)
from django.db.models import Max, Min
from django.urls import reverse
from logs.models import AccessLog, Dimension, DimensionText, MduMethod, Metric, ReportType
from organizations.models import UserOrganization
from publications.models import Platform
from publications.tests.conftest import interest_rt  # noqa - fixtures
from sushi.models import AttemptStatus, CounterReportsToCredentials
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFullFactory, ManualDataUploadFullFactory
from test_fixtures.scenarios.basic import basic1  # noqa - fixtures
from test_fixtures.scenarios.basic import (
    client_by_user_type,
    clients,
    counter_report_types,
    data_sources,
    identities,
    interests,
    metrics,
    organizations,
    platforms,
    report_types,
    users,
)

from ..logic.data_import import import_counter_records
from ..logic.materialized_interest import sync_interest_for_import_batch


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
        organization = organizations["branch"]
        report_type = report_type_nd(0)  # type: ReportType
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        resp = authenticated_client.get(
            reverse('chart_data_raw', args=(report_type.pk,)),
            {
                'organization': organization.pk,
                'metric': metric.pk,
                'platform': platform.pk,
                'prim_dim': 'date',
            },
        )
        assert resp.status_code == 200
        assert 'data' in resp.json()

    def test_api_simple_data_0d_with_recache(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        organization = organizations["branch"]
        report_type = report_type_nd(0)  # type: ReportType
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
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
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
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
            ['organization', None, [{'organization': 'branch', 'count': 3}]],
            ['organization', 'metric', [{'organization': 'branch', 'metric': 'Hits', 'count': 3}]],
            ['metric', 'organization', [{'organization': 'branch', 'metric': 'Hits', 'count': 3}]],
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
        master_admin_client,
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
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
        resp = master_admin_client.get(reverse('chart_data_raw', args=(report_type.pk,)), params)
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
        import_counter_records(report_type, organizations["branch"], platform1, crs1)
        import_counter_records(report_type, organizations["branch"], platform2, crs1)
        import_counter_records(report_type, organizations["standalone"], platform1, crs1)
        import_counter_records(report_type, organizations["standalone"], platform2, crs2)
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
        recs = get_data({'organization': organizations["branch"].pk, 'prim_dim': 'date'})
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
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
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
        organization = organizations["branch"]
        report_type = report_type_nd(1)
        import_counter_records(report_type, organization, platform, crs)
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
        self, organizations, master_admin_client, report_type_nd, tmp_path, settings
    ):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(0)
        file = StringIO('Source,2019-01\naaaa,9\n')
        settings.MEDIA_ROOT = tmp_path
        response = master_admin_client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organizations["branch"].pk,
                'report_type_id': report_type.pk,
                'data_file': file,
                'method': MduMethod.CELUS,
            },
        )
        assert response.status_code == 201

    def test_manual_upload_data_disabled(self, master_admin_client, settings):
        settings.ALLOW_MANUAL_UPLOAD = False
        response = master_admin_client.get(reverse('manual-data-upload-list'))
        assert response.status_code == 403


@pytest.mark.django_db
class TestReportTypeAPI:
    def test_create_report_type_400(self, organizations, authenticated_client):
        organization = organizations["branch"]
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
        organization = organizations["branch"]
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
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, 'a new ReportType was created'
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 0, 'no extra dimensions for ReportType'

    def test_create_report_type_with_dimension(self, organizations, authenticated_client):
        organization = organizations["branch"]
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
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, 'a new ReportType was created'
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 2

    def test_create_report_type_with_invalid_dimension(self, organizations, authenticated_client):
        organization = organizations["branch"]
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
            ['master_admin', True],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_raw_export_start_organization_access(self, user_type, can_access, client_by_user_type):
        client, org = client_by_user_type(user_type)
        url = reverse('raw_data_export')
        with patch('logs.views.export_raw_data_task') as export_task:
            resp = client.post(url + f'?organization={org.pk}', content_type='application/json')
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
            ['master_admin', True],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_raw_export_start_no_organization_access(
        self, user_type, can_access, client_by_user_type
    ):
        client, org = client_by_user_type(user_type)
        url = reverse('raw_data_export')
        with patch('logs.views.export_raw_data_task') as export_task:
            resp = client.post(url, content_type='application/json')
            expected_status_code = (200,) if can_access else (401, 403)
            assert resp.status_code in expected_status_code
            if can_access:
                export_task.delay.assert_called()
            else:
                export_task.delay.assert_not_called()


@pytest.fixture
def dimension_texts():
    dim1 = Dimension.objects.create(short_name='dim1')
    dim2 = Dimension.objects.create(short_name='dim2')
    dt1 = DimensionText.objects.create(text='test1', dimension=dim1)
    dt2 = DimensionText.objects.create(text='test2', dimension=dim1)
    dt3 = DimensionText.objects.create(text='test3', dimension=dim2)
    return {dt1.text: dt1, dt2.text: dt2, dt3.text: dt3}


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
class TestImportBatchViewSet:
    def test_data_presence(self, admin_client, counter_report_types):
        # create a manual data upload which is one of the things that enter into the data presence
        # calculation
        mdu = ManualDataUploadFullFactory.create()
        assert AccessLog.objects.count() == 20
        mdu_date_range = AccessLog.objects.aggregate(min=Min('date'), max=Max('date'))
        start_date_mdu = mdu_date_range['min']
        end_date_mdu = mdu_date_range['max']

        # create fetch attempts - these are used for detecting data from SUSHI
        cr = CredentialsFactory.create(organization=mdu.organization, platform=mdu.platform)
        # the credentials from factory are not connected to the counter report type, do it here

        CounterReportsToCredentials.objects.create(
            credentials=cr, counter_report=counter_report_types['tr']
        )
        # the counter_report_type should match the report_type created for the mdu
        end_date_fa = month_start(end_date_mdu + timedelta(days=40))
        FetchAttemptFactory.create(
            credentials=cr,
            status=AttemptStatus.SUCCESS,
            start_date=end_date_fa,
            end_date=month_end(end_date_fa),
            import_batch=ImportBatchFullFactory(
                date=end_date_fa,
                organization=cr.organization,
                platform=cr.platform,
                report_type=counter_report_types['tr'].report_type,
            ),
        )

        # test without params
        resp = admin_client.get(reverse('import-batch-data-presence'))
        assert resp.status_code == 400

        # test with params
        resp = admin_client.get(
            reverse('import-batch-data-presence'),
            {'start_date': str(start_date_mdu), 'end_date': str(end_date_fa), 'credentials': cr.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, 'two months, the same organization, platform and report_type'

    @pytest.mark.parametrize('import_batch', ((True,), (False,)))
    def test_data_presence_attempt_ib(self, admin_client, import_batch):
        cr = CredentialsFactory.create()
        start_date = '2021-10-01'
        fa = FetchAttemptFactory.create(
            credentials=cr,
            status=AttemptStatus.SUCCESS,
            start_date=start_date,
            end_date='2021-10-31',
        )
        if import_batch:
            ib = ImportBatchFullFactory(
                date=start_date,
                platform=cr.platform,
                organization=cr.organization,
                report_type=fa.counter_report.report_type,
            )
            fa.import_batch = ib
            fa.save()

        # the credentials from factory are not connected to the counter report type, do it here
        CounterReportsToCredentials.objects.create(credentials=cr, counter_report=fa.counter_report)

        resp = admin_client.get(
            reverse('import-batch-data-presence'),
            {'start_date': start_date, 'end_date': start_date, 'credentials': cr.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        if import_batch:
            assert len(data) == 1, 'import_batch present'
        else:
            assert len(data) == 0, 'no import_batch => no data'


@pytest.mark.django_db
class TestReportInterestMetricAPI:
    def test_get_report_interest_metric(
        self, authenticated_client, platforms, report_types, metrics, interests
    ):
        url = reverse("reporttype-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == 200
        data = {e["short_name"]: e for e in resp.json()}
        assert len(data["TR"]["interest_metric_set"]) == 2
        assert len(data["DR"]["interest_metric_set"]) == 0
        assert len(data["JR1"]["interest_metric_set"]) == 2
        assert len(data["BR2"]["interest_metric_set"]) == 1


@pytest.mark.django_db
class TestRawDataAPI:
    def test_raw_data_ib(
        self, authenticated_client, report_types, interests, interest_rt, platforms
    ):
        # we need to use the right rt, platform and metric so that interest is defined
        ib = ImportBatchFullFactory.create(
            report_type=report_types['jr1'],
            platform=platforms['branch'],
            create_accesslogs__metrics=[Metric.objects.get(short_name='metric1')],
        )
        resp = authenticated_client.get(reverse('raw_data'), {'ib': ib.pk, 'format': 'json'})
        assert resp.status_code == 200
        data = resp.json()
        log_count = ib.accesslog_set.count()
        assert len(data) == log_count
        sync_interest_for_import_batch(ib, interest_rt)
        assert ib.accesslog_set.count() > log_count, 'ib should have extra interest records'
        # recheck that there is no interest in the data
        resp = authenticated_client.get(
            reverse('raw_data'), {'import_batch': ib.pk, 'format': 'json'}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert log_count == len(data), 'interest data is not in the output'
