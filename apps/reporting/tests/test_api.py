from unittest import mock

import pytest
from django.urls import reverse

from test_fixtures.entities.organizations import OrganizationFactory


@pytest.mark.django_db
class TestReportsAPI:
    def test_report_list(self, admin_client):
        response = admin_client.get(reverse('report-list'))
        assert response.status_code == 200
        assert len(response.data) == 2
        assert response.data[0]['name'] == 'Rebiun report'
        assert response.data[1]['name'] == 'ARL Statistics survey'

    @pytest.mark.parametrize('new_organization', [True, False])
    def test_report_output(
        self, admin_client, report_data_tr_jr1, report_def_tr_jr1, new_organization
    ):
        # if new organization is True, we will create a new organization and use it in the request.
        # it will have empty data, but the result structure should be the same
        # - except for the total and the used report type
        if new_organization:
            org = OrganizationFactory()
        else:
            org = report_data_tr_jr1['org']
        with mock.patch('reporting.views.get_report_def_by_name') as mock_get_report_def_by_name:
            # we replace the stored report by our own
            mock_get_report_def_by_name.return_value = report_def_tr_jr1
            response = admin_client.get(
                reverse('report-data', args=['Test report']),
                {'start_date': '2022-01', 'end_date': '2022-03', 'organization': org.pk},
            )
        assert response.status_code == 200
        assert len(response.data) == 2, "2 parts"
        assert response.data[0]['part_name'] == 'PART 1'
        if new_organization:
            assert len(response.data[0]['data']) == 0, 'org not connected to any platform'
        else:
            assert len(response.data[0]['data']) == 2, '2 platforms'
            platform1 = report_data_tr_jr1['platform1']
            platform2 = report_data_tr_jr1['platform2']
            assert {rec['primary_pk'] for rec in response.data[0]['data']} == {
                platform1.pk,
                platform2.pk,
            }
            # get data for platform1 and check it against the expected structure
            pl1_data = next(
                rec for rec in response.data[0]['data'] if rec['primary_pk'] == platform1.pk
            )
            assert set(pl1_data['monthly_data'].keys()) == {'2022-01', '2022-02', '2022-03'}
            assert pl1_data['primary_obj'] == platform1.short_name
            assert pl1_data['used_report_type'] == report_data_tr_jr1['rt_tr'].short_name
            assert pl1_data['total'] > 0

    def test_report_export(self, admin_client, report_data_tr_jr1, report_def_tr_jr1):
        org = report_data_tr_jr1['org']
        with mock.patch('reporting.views.get_report_def_by_name') as mock_get_report_def_by_name:
            # we replace the stored report by our own
            mock_get_report_def_by_name.return_value = report_def_tr_jr1
            response = admin_client.get(
                reverse('report-export', args=['Test report']),
                {'start_date': '2022-01', 'end_date': '2022-03', 'organization': org.pk},
            )
        assert response.status_code == 200
        assert (
            response['Content-Type']
            == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        assert response['Content-Disposition'] == 'attachment; filename="Test report.xlsx"'
