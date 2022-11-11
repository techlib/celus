import pytest
from logs.logic.custom_import import custom_import_preflight_check
from logs.models import ManualDataUpload
from logs.tasks import prepare_preflight
from test_fixtures.entities.logs import (
    AccessLogFactory,
    ImportBatchFactory,
    ManualDataUploadFactory,
    MduState,
    MetricFactory,
)
from test_fixtures.entities.organizations import OrganizationAltNameFactory, OrganizationFactory
from test_fixtures.scenarios.basic import (
    data_sources,
    metrics,
    organizations,
    platforms,
    report_types,
)


@pytest.mark.django_db
class TestManualUpload:
    def test_mdu_related_months_data(self, report_types, organizations, platforms, metrics):
        DATA = b"""\
Title,Metric,Jun 2021, Jul 2021, Aug 2021, Jan 2022
A,Metric1,0,5,9,13
A,Metric2,1,0,0,14
B,Metric1,0,0,0,15
B,Metric3,2,6,10,16
C,Metric3,3,7,11,17
C,Metric2,4,8,12,18
"""

        # prepare some import batches 2020
        for i in range(1, 13):
            ib = ImportBatchFactory(
                date=f"2020-{i:02d}-01",
                organization=organizations["standalone"],
                report_type=report_types["tr"],
                platform=platforms["standalone"],
            )
            AccessLogFactory.create_batch(
                size=i, import_batch=ib, metric=metrics["metric1"], value=i
            )
            AccessLogFactory.create_batch(
                size=i + 1, import_batch=ib, metric=metrics["metric2"], value=i * 2
            )

        # prepare half of 2021
        for i in range(1, 7):
            ib = ImportBatchFactory(
                date=f"2021-{i:02d}-01",
                organization=organizations["standalone"],
                report_type=report_types["tr"],
                platform=platforms["standalone"],
            )
            AccessLogFactory.create_batch(
                size=i + 2, import_batch=ib, metric=metrics["metric1"], value=i * 3
            )
            AccessLogFactory.create_batch(
                size=i + 3, import_batch=ib, metric=metrics["metric2"], value=i * 5
            )

        # prepare MDU
        mdu = ManualDataUploadFactory(
            organization=organizations["standalone"],
            report_type=report_types["tr"],
            platform=platforms["standalone"],
            data_file__data=DATA,
            data_file__filename="something.csv",
            state=MduState.INITIAL,
        )

        assert mdu.related_months_data() == (
            {
                "2020-01-01": {'count': 3, 'sum': 5},
                "2020-02-01": {'count': 5, 'sum': 16},
                "2020-03-01": {'count': 7, 'sum': 33},
                "2020-04-01": {'count': 9, 'sum': 56},
                "2020-05-01": {'count': 11, 'sum': 85},
                "2020-06-01": {'count': 13, 'sum': 120},
                "2020-07-01": {'count': 15, 'sum': 161},
                "2020-08-01": {'count': 17, 'sum': 208},
                "2020-09-01": {'count': 19, 'sum': 261},
                "2020-10-01": {'count': 21, 'sum': 320},
                "2020-11-01": {'count': 23, 'sum': 385},
                "2020-12-01": {'count': 25, 'sum': 456},
                "2021-01-01": {'count': 7, 'sum': 29},
                "2021-02-01": {'count': 9, 'sum': 74},
                "2021-03-01": {'count': 11, 'sum': 135},
                "2021-04-01": {'count': 13, 'sum': 212},
                "2021-05-01": {'count': 15, 'sum': 305},
                "2021-06-01": {'count': 17, 'sum': 414},
            },
            ["metric1", "metric2"],
        )

        # Generate preflight
        preflight = custom_import_preflight_check(mdu)

        # Compare month data
        assert preflight["months"] == {
            '2021-06-01': {
                'new': {'count': 6, 'sum': 10},
                'this_month': {'count': 17, 'sum': 414},
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 13, 'sum': 120},
            },
            '2021-07-01': {
                'new': {'count': 6, 'sum': 26},
                'this_month': None,
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 15, 'sum': 161},
            },
            '2021-08-01': {
                'new': {'count': 6, 'sum': 42},
                'this_month': None,
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 17, 'sum': 208},
            },
            '2022-01-01': {
                'new': {'count': 6, 'sum': 93},
                'this_month': None,
                'prev_year_avg': None,
                'prev_year_month': {'count': 7, 'sum': 29},
            },
        }

        assert preflight["used_metrics"] == ["metric1", "metric2"]

    def test_organization_from_data(self):
        org1 = OrganizationFactory(
            name_en="C Z C U", name_cs="Č Ž Č Ú", short_name_en="CZCU", short_name_cs="ČŽČÚ",
        )
        org2 = OrganizationFactory(
            name_en="C", name_cs="Č", short_name_en="C Z C U", short_name_cs="Č Ž Č Ú",
        )
        OrganizationAltNameFactory(name="X", organization=org1)
        OrganizationAltNameFactory(name="y", organization=org2)
        assert ManualDataUpload.organizations_from_data_cls([]) == []
        assert ManualDataUpload.organizations_from_data_cls(None) == []
        assert ManualDataUpload.organizations_from_data_cls(
            ["not_found", "czcu", "čžčú", "c z c u", "č ž č ú", "c", "č", "x", "Y"]
        ) == [
            ("not_found", None),
            ("czcu", org1),
            ("čžčú", org1),
            ("c z c u", org1),
            ("č ž č ú", org1),
            ("c", org2),
            ("č", org2),
            ("x", org1),
            ("Y", org2),
        ]
