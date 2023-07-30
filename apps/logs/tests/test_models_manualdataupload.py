import pytest
from organizations.fake_data import OrganizationAltNameFactory, OrganizationFactory

from logs.fake_data import (
    AccessLogFactory,
    ImportBatchFactory,
    ImportBatchFullFactory,
    ManualDataUploadFactory,
    MduState,
)
from logs.logic.clickhouse import (
    sync_accesslogs_with_clickhouse_superfast,
    sync_import_batch_with_clickhouse,
)
from logs.logic.custom_import import custom_import_preflight_check
from logs.models import AccessLog, ManualDataUpload
from logs.tasks import prepare_preflight
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    metrics,
    organizations,
    platforms,
    report_types,
    users,
)


@pytest.mark.django_db
class TestManualUpload:
    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_mdu_related_months_data(
        self, report_types, organizations, platforms, metrics, clickhouse_on_off
    ):
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
        if clickhouse_on_off:
            sync_accesslogs_with_clickhouse_superfast()

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

    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_mdu_related_months_data_with_organization_in_data(
        self, report_types, organizations, platforms, metrics, clickhouse_on_off
    ):
        org = organizations["standalone"]
        org2 = organizations["root"]
        platform = platforms["standalone"]

        DATA = f"""\
Title,Metric,Organization,Jun 2021, Jul 2021, Aug 2021, Jan 2022
A,Metric1,{org.short_name},0,5,9,13
A,Metric2,{org.short_name},1,0,0,14
B,Metric1,{org.short_name},0,0,0,15
B,Metric3,{org.short_name},2,6,10,16
C,Metric3,{org.short_name},3,7,11,17
C,Metric2,{org.short_name},4,8,12,18
A,Metric1,{org2.short_name},0,0,0,19
A,Metric1,unresolved,0,0,0,20
""".encode(
            "utf-8"
        )

        # prepare some import batches 2020
        for i in range(1, 13):
            ib = ImportBatchFactory(
                date=f"2020-{i:02d}-01",
                organization=org,
                report_type=report_types["tr"],
                platform=platform,
            )
            AccessLogFactory.create_batch(
                size=i, import_batch=ib, metric=metrics["metric1"], value=i
            )
            AccessLogFactory.create_batch(
                size=i + 1, import_batch=ib, metric=metrics["metric2"], value=i * 2
            )
            if clickhouse_on_off:
                sync_import_batch_with_clickhouse(ib)

        # prepare half of 2021
        for i in range(1, 7):
            ib = ImportBatchFactory(
                date=f"2021-{i:02d}-01",
                organization=org,
                report_type=report_types["tr"],
                platform=platform,
            )
            AccessLogFactory.create_batch(
                size=i + 2, import_batch=ib, metric=metrics["metric1"], value=i * 3
            )
            AccessLogFactory.create_batch(
                size=i + 3, import_batch=ib, metric=metrics["metric2"], value=i * 5
            )
            if clickhouse_on_off:
                # ImportBatchFullFactory takes care of clickhouse sync, but the above
                # approach does not, so we need to do it manually
                sync_import_batch_with_clickhouse(ib)

            # add some data for org2 organization
            ImportBatchFullFactory(
                organization=org2,
                platform=platform,
                report_type=report_types["tr"],
                date=f"2021-{i:02d}-01",
                create_accesslogs__metrics=[metrics["metric1"]],
                create_accesslogs__value=i,
            )
            # add some data for a completely unrelated organization
            ImportBatchFullFactory(
                organization=organizations["branch"],
                platform=platform,
                report_type=report_types["tr"],
                date=f"2021-{i:02d}-01",
                create_accesslogs__metrics=[metrics["metric1"]],
                create_accesslogs__value=i,
            )
            assert (
                AccessLog.objects.filter(
                    date=f"2021-{i:02d}-01", organization=org, platform=platform
                ).count()
                == 2 * i + 5
            )
            assert (
                AccessLog.objects.filter(
                    date=f"2021-{i:02d}-01", organization=org2, platform=platform
                ).count()
                == 10
            ), '10 titles for org2'

        # prepare MDU
        mdu = ManualDataUploadFactory(
            organization=None,
            report_type=report_types["tr"],
            platform=platform,
            data_file__data=DATA,
            data_file__filename="something.csv",
            state=MduState.INITIAL,
        )

        prepare_preflight(mdu.pk)
        mdu.refresh_from_db()

        months, metrics = mdu.related_months_data()
        assert months == {
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
            "2021-01-01": {'count': 7 + 10, 'sum': 29 + 10},  # 10 titles for org2
            "2021-02-01": {'count': 9 + 10, 'sum': 74 + 10 * 2},
            "2021-03-01": {'count': 11 + 10, 'sum': 135 + 10 * 3},
            "2021-04-01": {'count': 13 + 10, 'sum': 212 + 10 * 4},
            "2021-05-01": {'count': 15 + 10, 'sum': 305 + 10 * 5},
            "2021-06-01": {'count': 17 + 10, 'sum': 414 + 10 * 6},
        }
        assert metrics == ["metric1", "metric2"]

        # Generate preflight
        preflight = custom_import_preflight_check(mdu)
        assert len(preflight['organizations']) == 3

        # Compare month data
        assert preflight["months"] == {
            '2021-06-01': {
                'new': {'count': 8, 'sum': 10},
                'this_month': {'count': 17 + 10, 'sum': 414 + 10 * 6},
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 13, 'sum': 120},
            },
            '2021-07-01': {
                'new': {'count': 8, 'sum': 26},
                'this_month': None,
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 15, 'sum': 161},
            },
            '2021-08-01': {
                'new': {'count': 8, 'sum': 42},
                'this_month': None,
                'prev_year_avg': {'sum': 176, 'count': 14},
                'prev_year_month': {'count': 17, 'sum': 208},
            },
            '2022-01-01': {
                'new': {'count': 8, 'sum': 93 + 19 + 20},
                'this_month': None,
                'prev_year_avg': None,
                'prev_year_month': {'count': 7 + 10, 'sum': 29 + 10},
            },
        }

        assert preflight["used_metrics"] == ["metric1", "metric2"]

        assert preflight["organizations"]["unresolved"] == {
            "pk": None,
            "count": 4,
            "sum": 20,
        }, "check that preflight is properly generated even when some organization is not resolved"

    def test_organization_from_data(self):
        org1 = OrganizationFactory(
            name_en="C Z C U", name_cs="Č Ž Č Ú", short_name_en="CZCU", short_name_cs="ČŽČÚ"
        )
        org2 = OrganizationFactory(
            name_en="C", name_cs="Č", short_name_en="C Z C U", short_name_cs="Č Ž Č Ú"
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

    def test_data_file_names(self, platforms, basic1, report_types, users):
        DATA = """\
Title,Metric,Jun 2021, Jul 2021, Aug 2021, Jan 2022
A,Metric1,0,5,9,13
A,Metric2,1,0,0,14
B,Metric1,0,0,0,15
B,Metric3,2,6,10,16
C,Metric3,3,7,11,17
C,Metric2,4,8,12,18
""".encode(
            "utf-8"
        )

        mdu = ManualDataUploadFactory(
            user=users["admin1"],
            organization=None,
            report_type=report_types["tr"],
            platform=platforms["shared"],
            data_file__data=DATA,
            data_file__filename="something.csv",
            state=MduState.INITIAL,
        )
        assert "/tr-shared_" in mdu.data_file.name

        mdu = ManualDataUploadFactory(
            user=users["admin1"],
            organization=None,
            report_type=report_types["tr"],
            platform=platforms["standalone"],
            data_file__data=DATA,
            data_file__filename="something.csv",
            state=MduState.INITIAL,
        )
        assert "/tr-standalone.standalone" in mdu.data_file.name
