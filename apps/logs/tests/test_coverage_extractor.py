from datetime import date

import pytest
from publications.fake_data import TitleFactory
from scheduler.fake_data import FetchIntentionFactory
from sushi.fake_data import CredentialsFactory, FetchAttemptFactory

from logs.fake_data import ImportBatchFullFactory, ManualDataUploadFactory, MetricFactory
from logs.logic.data_coverage import DataCoverageExtractor
from logs.models import ManualDataUpload
from test_scenarios.basic import (  # noqa
    counter_report_types,
    credentials,
    data_sources,
    organizations,
    platforms,
    report_types,
)


@pytest.mark.django_db
class TestCoverageExtractor:
    @pytest.fixture()
    def data(self, report_types, counter_report_types, organizations, platforms, credentials):
        """
        The created data from IB perspective are

        date    | RT   | platform   | organization | source | titles
        --------+------+------------+--------------+--------+--------
        2020-01 | TR   | standalone | standalone   | fa     | t1
        2020-02 | TR   | standalone | standalone   | fa     | t1,t2
        2020-03 | TR   | standalone | standalone   | mdu    | t2,t3
        2020-04 | TR   | standalone | standalone   | mdu    | t1,t2,t3
        2020-02 | BR1  | standalone | standalone   | fa     | t1
        2020-01 | PR   | branch     | branch       | fa     | t2
        2020-02 | PR   | branch     | branch       | mdu    | random 10
        2020-03 | PR   | branch     | branch       | mdu    | random 10
        2020-04 | PR   | branch     | branch       | mdu    | random 10
        2020-01 | IR51 | standalone | standalone   | fa     | t1
        2020-02 | IR51 | standalone | standalone   | fa     | t1,t2
        2020-03 | IR51 | standalone | standalone   | fa     | t1,t2,t3
        """
        metric1 = MetricFactory.create()
        t1, t2, t3, t4 = TitleFactory.create_batch(4)
        FetchIntentionFactory(
            start_date="2020-01-01",
            end_date="2020-01-31",
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            attempt=FetchAttemptFactory(
                start_date="2020-01-01",
                end_date="2020-01-31",
                error_code="3031",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                import_batch=None,
            ),
        )

        FetchIntentionFactory(
            start_date="2020-01-01",
            end_date="2020-01-31",
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            attempt=FetchAttemptFactory(
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFullFactory(
                    date="2020-01-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-02-01",
            end_date="2020-02-29",
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            attempt=FetchAttemptFactory(
                start_date="2020-02-01",
                end_date="2020-02-29",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFullFactory(
                    date="2020-02-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1, t2],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-02-01",
            end_date="2020-02-29",
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            attempt=FetchAttemptFactory(
                start_date="2020-02-01",
                end_date="2020-02-29",
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                import_batch=ImportBatchFullFactory(
                    date="2020-02-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["br1"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-01-01",
            end_date="2020-01-31",
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            attempt=FetchAttemptFactory(
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials=credentials["branch_pr"],
                counter_report=counter_report_types["pr"],
                import_batch=ImportBatchFullFactory(
                    date="2020-01-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t2],
                ),
            ),
        )
        ManualDataUploadFactory(
            organization=organizations["standalone"],
            platform=platforms["standalone"],
            report_type=report_types["tr"],
            import_batches=(
                ImportBatchFullFactory(
                    date="2020-03-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t2, t3],
                ),
                ImportBatchFullFactory(
                    date="2020-04-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1, t2, t3],
                ),
            ),
        )
        ManualDataUploadFactory(
            organization=organizations["branch"],
            platform=platforms["branch"],
            report_type=report_types["pr"],
            import_batches=(
                ImportBatchFullFactory(
                    date="2020-02-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                    create_accesslogs__metrics=[metric1],
                ),
                ImportBatchFullFactory(
                    date="2020-03-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                    create_accesslogs__metrics=[metric1],
                ),
                ImportBatchFullFactory(
                    date="2020-04-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                    create_accesslogs__metrics=[metric1],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-01-01",
            end_date="2020-01-31",
            credentials=credentials["standalone_ir51"],
            counter_report=counter_report_types["tr51"],
            attempt=FetchAttemptFactory(
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials=credentials["standalone_ir51"],
                counter_report=counter_report_types["tr51"],
                import_batch=ImportBatchFullFactory(
                    date="2020-01-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["ir51"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-02-01",
            end_date="2020-02-29",
            credentials=credentials["standalone_ir51"],
            counter_report=counter_report_types["tr51"],
            attempt=FetchAttemptFactory(
                start_date="2020-02-01",
                end_date="2020-02-29",
                credentials=credentials["standalone_ir51"],
                counter_report=counter_report_types["tr51"],
                import_batch=ImportBatchFullFactory(
                    date="2020-02-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["ir51"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1, t2],
                ),
            ),
        )
        FetchIntentionFactory(
            start_date="2020-03-01",
            end_date="2020-03-31",
            credentials=credentials["standalone_ir51"],
            counter_report=counter_report_types["tr51"],
            attempt=FetchAttemptFactory(
                start_date="2020-03-01",
                end_date="2020-03-31",
                credentials=credentials["standalone_ir51"],
                counter_report=counter_report_types["tr51"],
                import_batch=ImportBatchFullFactory(
                    date="2020-03-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["ir51"],
                    create_accesslogs__metrics=[metric1],
                    create_accesslogs__titles=[t1, t2, t3],
                ),
            ),
        )
        return {"metric1": metric1, "t1": t1, "t2": t2, "t3": t3, "t4": t4}

    @pytest.mark.parametrize(
        ["split_by_org", "split_by_platform", "split_by_date", "record_count", "ib_counts"],
        # sorting in ib_counts should be month, organization_id, platform_id
        [
            (False, False, True, 3, [1, 2, 1]),
            (False, True, True, 3 * 2, [0, 1, 1, 1, 0, 1]),  # two platforms
            (True, False, True, 3, [1, 2, 1]),  # only one org anyway
            (True, True, True, 3 * 2, [0, 1, 1, 1, 0, 1]),  # two platforms, one org
            (True, False, False, 1, [4]),  # two platforms, one org
            (False, False, False, 1, [4]),  # no splitting at all
        ],
    )
    def test_data_coverage_splitting(
        self,
        data,
        organizations,
        platforms,
        report_types,
        counter_report_types,
        split_by_org,
        split_by_platform,
        split_by_date,
        record_count,
        ib_counts,
    ):
        """
        The created data from IB perspective are

        date    | RT  | platform   | organization | source
        --------+-----+------------+--------------+-------
        2020-01 | TR  | standalone | standalone   | fa
        2020-02 | TR  | standalone | standalone   | fa
        2020-03 | TR  | standalone | standalone   | mdu
        2020-02 | TR  | branch     | standalone   | ??
        """
        # create extra IB with different platform
        ImportBatchFullFactory.create(
            platform=platforms["branch"],
            organization=organizations["standalone"],
            date="2020-02-01",
            report_type=report_types["tr"],
        )
        extra_cr = CredentialsFactory.create(
            platform=platforms["branch"],
            organization=organizations["standalone"],
            counter_version=5,
        )
        extra_cr.counter_reports.add(counter_report_types["tr"])

        extra_params = {}
        if split_by_org:
            extra_params["split_by_org"] = 1
        if split_by_platform:
            extra_params["split_by_platform"] = 1
        if not split_by_date:
            # split by date is the default
            extra_params["split_by_date"] = 0

        extractor = DataCoverageExtractor(
            report_type=report_types["tr"],
            start_month=date(2020, 1, 1),
            end_month=date(2020, 3, 31),
            **extra_params,
        )
        data = extractor.get_coverage_data()
        # check record counts
        assert len(data) == record_count
        assert ib_counts == [rec["ib_count"] for _key, rec in sorted(data.items())]
        key1 = sorted(data.keys())[0]
        # check record structure
        if split_by_date:
            assert isinstance(key1[0], date)
        elif split_by_org or split_by_platform:
            assert isinstance(key1[0], int)
        else:
            assert len(key1) == 0, "key1 should be empty - no splitting"

    @pytest.mark.parametrize(
        ["report_type", "fallback_report_type", "exp_max", "exp_ib_count"],
        [
            ("ir51", "tr", 4, 4),  # TR has data for 04 filling the gap
            ("ir51", "br1", 4, 3),  # BR1 cannot fill the gap in 04
            ("ir51", None, 4, 3),  # no fallback, so no data for 04
            ("tr", "br1", 4, 4),  # TR has no gap - no fallback needed
            ("br1", "ir51", 4, 3),  # BR1 has 3 month gap - ir51 fills two of them
        ],
    )
    def test_data_coverage_with_fallback_report_type(
        self, data, report_types, report_type, fallback_report_type, exp_max, exp_ib_count
    ):
        """
        The created data from IB perspective are

        date    | RT   | platform   | organization | source | titles
        --------+------+------------+--------------+--------+--------
        2020-01 | TR   | standalone | standalone   | fa     | t1
        2020-02 | TR   | standalone | standalone   | fa     | t1,t2
        2020-03 | TR   | standalone | standalone   | mdu    | t2,t3
        2020-04 | TR   | standalone | standalone   | mdu    | t1,t2,t3
        2020-02 | BR1  | standalone | standalone   | fa     | t1
        2020-01 | IR51 | standalone | standalone   | fa     | t1
        2020-02 | IR51 | standalone | standalone   | fa     | t1,t2
        2020-03 | IR51 | standalone | standalone   | fa     | t1,t2,t3

        We will use IR51 with fallback to TR or BR1
        """
        extractor = DataCoverageExtractor(
            report_type=report_types[report_type],
            fallback_report_type=report_types.get(fallback_report_type),
            start_month=date(2020, 1, 1),
            end_month=date(2020, 4, 30),
            split_by_date=False,
            split_by_org=False,
            split_by_platform=False,
        )
        data = extractor.get_coverage_data()
        assert len(data) == 1
        result = data[()]
        assert result["ib_count"] == exp_ib_count
        assert result["ib_max"] == exp_max

    @pytest.mark.parametrize(
        ["report_type", "fallback_report_type", "exp_max", "exp_ib_count"],
        [
            ("ir51", "tr", 4, 4),  # TR has data for 04 filling the gap
            ("tr", "ir51", 4, 4),  # TR has no gap - no fallback needed
            # PR has different org, so they should complement each other
            ("pr", "ir51", 8, 7),  # IR51 misses one month
            ("ir51", "pr", 8, 7),  # IR51 misses one month
            ("pr", "tr", 8, 8),  # both complete coverage
            ("tr", "pr", 8, 8),  # both complete coverage
        ],
    )
    def test_data_coverage_with_fallback_report_type_without_main_credentials(
        self,
        data,
        report_types,
        credentials,
        report_type,
        fallback_report_type,
        exp_max,
        exp_ib_count,
    ):
        """
        Test that when there are no credentials for the main report type, the fallback report type
        is used to compute the maximum number of import batches, thus ensuring that
        the coverage does not get over 100 %.
        """
        if report_type.endswith("51"):
            credentials["standalone_ir51"].delete()
        else:
            credentials["standalone_tr"].delete()
            ManualDataUpload.objects.filter(report_type=report_types["tr"]).delete()

        extractor = DataCoverageExtractor(
            report_type=report_types[report_type],
            fallback_report_type=report_types.get(fallback_report_type),
            start_month=date(2020, 1, 1),
            end_month=date(2020, 4, 30),
            split_by_date=False,
            split_by_org=False,
            split_by_platform=False,
        )
        data = extractor.get_coverage_data()
        assert len(data) == 1
        result = data[()]
        assert result["ib_max"] == exp_max
        assert result["ib_count"] == exp_ib_count

    @pytest.mark.parametrize(
        ["report_type", "fallback_report_type", "exp_max", "exp_ib_count"],
        [
            ("ir51", "tr", 3, 3),  # IR has 3 months of data
            ("ir51", "br1", 3, 3),  # IR has 3 months of data
            ("ir51", None, 3, 3),  # no fallback, so no data for 04
            ("tr", "br1", 4, 4),  # TR has 4 months of data
            ("br1", "ir51", 1, 1),  # BR1 has 1 month of data
        ],
    )
    def test_data_coverage_with_fallback_report_type_without_explicit_date_range(
        self, data, report_types, report_type, fallback_report_type, exp_max, exp_ib_count
    ):
        """
        The created data from IB perspective are

        date    | RT   | platform   | organization | source | titles
        --------+------+------------+--------------+--------+--------
        2020-01 | TR   | standalone | standalone   | fa     | t1
        2020-02 | TR   | standalone | standalone   | fa     | t1,t2
        2020-03 | TR   | standalone | standalone   | mdu    | t2,t3
        2020-04 | TR   | standalone | standalone   | mdu    | t1,t2,t3
        2020-02 | BR1  | standalone | standalone   | fa     | t1
        2020-01 | IR51 | standalone | standalone   | fa     | t1
        2020-02 | IR51 | standalone | standalone   | fa     | t1,t2
        2020-03 | IR51 | standalone | standalone   | fa     | t1,t2,t3

        We will use IR51 with fallback to TR or BR1
        """
        extractor = DataCoverageExtractor(
            report_type=report_types[report_type],
            fallback_report_type=report_types.get(fallback_report_type),
            split_by_date=False,
            split_by_org=False,
            split_by_platform=False,
        )
        data = extractor.get_coverage_data()
        assert len(data) == 1
        result = data[()]
        assert result["ib_count"] == exp_ib_count
        assert result["ib_max"] == exp_max
