import pytest
from django.urls import reverse

from charts.models import ReportDataView
from logs.logic.materialized_interest import sync_interest_by_import_batches
from logs.models import ImportBatch, ReportInterestMetric, Metric, InterestGroup
from publications.models import PlatformInterestReport
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import (
    ManualDataUploadFactory,
    ImportBatchFullFactory,
    MetricFactory,
)
from test_fixtures.entities.scheduler import FetchIntentionFactory

from test_fixtures.scenarios.basic import (  # noqa
    users,
    report_types,
    counter_report_types,
    organizations,
    platforms,
    data_sources,
    clients,
    identities,
    credentials,
)
from publications.tests.conftest import interest_rt  # noqa - fixture


@pytest.mark.django_db
class TestImportBatchesAPI:
    lookup_url = reverse('import-batch-lookup')
    purge_url = reverse('import-batch-purge')

    @pytest.fixture()
    def data(
        self, report_types, counter_report_types, organizations, platforms, clients, credentials
    ):
        """
        The created data from IB perspective are

        date    | RT  | platform   | organization | source
        --------+-----+------------+--------------+-------
        2020-01 | TR  | standalone | standalone   | fa
        2020-02 | TR  | standalone | standalone   | fa
        2020-03 | TR  | standalone | standalone   | mdu
        2020-04 | TR  | standalone | standalone   | mdu
        2020-02 | BR1 | standalone | standalone   | fa
        2020-01 | PR  | branch     | branch       | fa
        2020-02 | PR  | branch     | branch       | mdu
        2020-03 | PR  | branch     | branch       | mdu
        2020-04 | PR  | branch     | branch       | mdu
        """
        metric1 = MetricFactory.create()
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
                ),
                ImportBatchFullFactory(
                    date="2020-04-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
                    create_accesslogs__metrics=[metric1],
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
        return {'metric1': metric1}

    def test_lookup(self, data, clients, organizations, platforms, report_types):
        # empty lookup
        resp = clients["su"].post(self.lookup_url, data=[], format="json")
        assert resp.status_code == 200
        assert resp.data == []

        resp = clients["su"].post(
            f"{self.lookup_url}?order_by=date",
            [
                {
                    "organization": organizations["standalone"].pk,
                    "platform": platforms["standalone"].pk,
                    "report_type": report_types["tr"].pk,
                    "months": ["2020-02-01", "2020-03-01"],
                }
            ],
            format="json",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 2
        assert resp.data[0]["date"] == "2020-02-01"
        assert resp.data[0]["report_type"]["pk"] == report_types["tr"].pk
        assert resp.data[0]["organization"]["pk"] == organizations["standalone"].pk
        assert resp.data[0]["platform"]["pk"] == platforms["standalone"].pk
        assert not resp.data[0]["mdu"]
        assert resp.data[0]["sushifetchattempt"]
        assert resp.data[1]["date"] == "2020-03-01"
        assert resp.data[1]["report_type"]["pk"] == report_types["tr"].pk
        assert resp.data[1]["organization"]["pk"] == organizations["standalone"].pk
        assert resp.data[1]["platform"]["pk"] == platforms["standalone"].pk
        assert resp.data[1]["mdu"]
        assert not resp.data[1]["sushifetchattempt"]

        resp = clients["su"].post(
            f"{self.lookup_url}?order_by=date",
            [
                {
                    "organization": organizations["standalone"].pk,
                    "platform": platforms["standalone"].pk,
                    "report_type": report_types["br1"].pk,
                    "months": ["2020-01-02", "2020-02-01", "2020-03-01"],
                },
                {
                    "organization": organizations["branch"].pk,
                    "platform": platforms["branch"].pk,
                    "report_type": report_types["pr"].pk,
                    "months": ["2020-03-01"],
                },
            ],
            format="json",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 2
        assert resp.data[0]["date"] == "2020-02-01"
        assert resp.data[0]["report_type"]["pk"] == report_types["br1"].pk
        assert resp.data[0]["organization"]["pk"] == organizations["standalone"].pk
        assert resp.data[0]["platform"]["pk"] == platforms["standalone"].pk
        assert not resp.data[0]["mdu"]
        assert resp.data[0]["sushifetchattempt"]
        assert resp.data[1]["date"] == "2020-03-01"
        assert resp.data[1]["report_type"]["pk"] == report_types["pr"].pk
        assert resp.data[1]["organization"]["pk"] == organizations["branch"].pk
        assert resp.data[1]["platform"]["pk"] == platforms["branch"].pk
        assert resp.data[1]["mdu"]
        assert not resp.data[1]["sushifetchattempt"]

    def test_purge(self, data, clients):
        # simple delete
        batches = list(ImportBatch.objects.all().order_by('pk').values_list("pk", flat=True))
        resp = clients["su"].post(self.purge_url, {"batches": [batches[0]]}, format="json")

        assert resp.status_code == 200
        assert resp.data == {
            'logs.AccessLog': 10,
            'sushi.SushiFetchAttempt': 2,
            'scheduler.FetchIntention': 2,
            'logs.ImportBatch': 1,
        }, "remove ib with fetch attempt (second is 3031)"
        assert ImportBatch.objects.count() == len(batches) - 1

        resp = clients["su"].post(self.purge_url, {"batches": [batches[0]]}, format="json")
        assert resp.data == {}, "retry same request - nothing deleted"
        assert ImportBatch.objects.count() == len(batches) - 1

        resp = clients["su"].post(self.purge_url, {"batches": [batches[-1]]}, format="json")
        assert resp.status_code == 200
        assert resp.data == {
            'logs.AccessLog': 10,
            'logs.ImportBatch': 1,
            'logs.ManualDataUploadImportBatch': 1,
        }, "remove ib from mdu"
        assert ImportBatch.objects.count() == len(batches) - 2

        resp = clients["su"].post(self.purge_url, {"batches": batches[-3:]}, format="json")
        assert resp.status_code == 200
        assert resp.data == {
            'logs.AccessLog': 20,
            'logs.ImportBatch': 2,
            'logs.ManualDataUpload': 1,
            'logs.ManualDataUploadImportBatch': 2,
        }, "remove last ibs from mdu"
        assert ImportBatch.objects.count() == len(batches) - 4

        resp = clients["su"].post(self.purge_url, {"batches": batches}, format="json")
        assert resp.status_code == 200
        assert resp.data == {
            'logs.AccessLog': 50,
            'logs.ImportBatch': 5,
            'logs.ManualDataUpload': 1,
            'logs.ManualDataUploadImportBatch': 2,
            'scheduler.FetchIntention': 3,
            'sushi.SushiFetchAttempt': 3,
        }, "remove rest"
        assert ImportBatch.objects.count() == 0

    def test_lookup_and_purge(self, data, clients, organizations, platforms, report_types):
        # lookup
        resp = clients["su"].post(
            f"{self.lookup_url}?order_by=date",
            [
                {
                    "organization": organizations["standalone"].pk,
                    "platform": platforms["standalone"].pk,
                    "report_type": report_types["br1"].pk,
                    "months": ["2020-01-01", "2020-02-01", "2020-03-01"],
                },
                {
                    "organization": organizations["branch"].pk,
                    "platform": platforms["branch"].pk,
                    "report_type": report_types["pr"].pk,
                    "months": ["2020-01-01", "2020-02-01", "2020-03-01"],
                },
            ],
            format="json",
        )
        assert resp.status_code == 200
        data = resp.data

        count = ImportBatch.objects.count()
        resp = clients["su"].post(
            self.purge_url, {"batches": [e["pk"] for e in data]}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data['logs.ImportBatch'] == len(data), "number of deleted ibs"
        assert ImportBatch.objects.count() == count - len(data), "all ibs were deleted"

    @pytest.mark.parametrize(
        ['rt', 'ib_counts'],
        [('TR', [1, 1, 1]), ('BR1', [0, 1, 0]), ('PR', [1, 1, 1]), ('DR', [0, 0, 0])],
    )
    def test_data_coverage(
        self, data, clients, organizations, platforms, report_types, rt, ib_counts
    ):
        """
        The created data from IB perspective are

        date    | RT  | platform   | organization | source
        --------+-----+------------+--------------+-------
        2020-01 | TR  | standalone | standalone   | fa
        2020-02 | TR  | standalone | standalone   | fa
        2020-03 | TR  | standalone | standalone   | mdu
        2020-02 | BR1 | standalone | standalone   | fa
        2020-01 | PR  | branch     | branch       | fa
        2020-02 | PR  | branch     | branch       | mdu
        2020-03 | PR  | branch     | branch       | mdu
        """

        resp = clients['su'].get(
            reverse('import-batch-list') + "data-coverage/",
            {
                'start_date': '2020-01',
                'end_date': '2020-03',
                'report_type': report_types[rt.lower()].pk,
            },
        )
        assert resp.status_code == 200
        assert 'date' in resp.json()[0]
        assert 'organization_id' not in resp.json()[0]
        assert ib_counts == [rec['ib_count'] for rec in resp.json()]

    @pytest.mark.parametrize(
        ['split_by_org', 'split_by_platform', 'record_count', 'ib_counts'],
        # sorting in ib_counts should be month, organization_id, platform_id
        [
            (False, False, 3, [1, 2, 1]),
            (False, True, 3 * 2, [0, 1, 1, 1, 0, 1]),  # two platforms
            (True, False, 3, [1, 2, 1]),  # only one org anyway
            (True, True, 3 * 2, [0, 1, 1, 1, 0, 1]),  # two platforms, one org
        ],
    )
    def test_data_coverage_splitting(
        self,
        data,
        clients,
        organizations,
        platforms,
        report_types,
        counter_report_types,
        split_by_org,
        split_by_platform,
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
        """
        # create extra IB with different platform
        ImportBatchFullFactory.create(
            platform=platforms['branch'],
            organization=organizations['standalone'],
            date='2020-02-01',
            report_type=report_types['tr'],
        )
        extra_cr = CredentialsFactory.create(
            platform=platforms['branch'],
            organization=organizations['standalone'],
            counter_version=5,
        )
        extra_cr.counter_reports.add(counter_report_types['tr'])

        extra_params = {}
        if split_by_org:
            extra_params['split_by_org'] = 1
        if split_by_platform:
            extra_params['split_by_platform'] = 1
        resp = clients['su'].get(
            reverse('import-batch-list') + "data-coverage/",
            {
                'start_date': '2020-01',
                'end_date': '2020-03',
                'report_type': report_types['tr'].pk,
                **extra_params,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # check record counts
        assert len(data) == record_count
        assert ib_counts == [rec['ib_count'] for rec in data]
        rec1 = data[0]
        # check record structure
        assert 'date' in rec1
        if split_by_org:
            assert 'organization_id' in rec1
        else:
            assert 'organization_id' not in rec1
        if split_by_platform:
            assert 'platform_id' in rec1
        else:
            assert 'platform_id' not in rec1

    def test_data_coverage_no_dates(self, data, clients, organizations, platforms, report_types):
        resp = clients['su'].get(
            reverse('import-batch-list') + "data-coverage/", {'report_type': report_types['tr'].pk},
        )
        assert resp.status_code == 200
        assert {rec['date'] for rec in resp.json()} == {
            '2020-01-01',
            '2020-02-01',
            '2020-03-01',
            '2020-04-01',
        }

    def test_data_coverage_with_report_view(
        self, data, clients, organizations, platforms, report_types
    ):
        rv = ReportDataView.objects.create(base_report_type=report_types['tr'], name='TR')
        resp = clients['su'].get(
            reverse('import-batch-list') + "data-coverage/", {'report_view': rv.pk},
        )
        assert resp.status_code == 200
        assert {rec['date'] for rec in resp.json()} == {
            '2020-01-01',
            '2020-02-01',
            '2020-03-01',
            '2020-04-01',
        }

    @pytest.mark.parametrize(
        ['rts_to_connect', 'superseding', 'ib_counts', 'ib_max_counts'],
        [
            (['tr'], False, [1, 1, 1], [1, 1, 1]),
            (['br1'], False, [0, 1, 0], [1, 1, 1]),
            (['tr', 'br1'], False, [1, 2, 1], [2, 2, 2]),
            # for month #2 only 1 because one supersedes the other
            (['tr', 'br1'], True, [1, 1, 1], [1, 1, 1]),
        ],
    )
    def test_data_coverage_interest(
        self,
        data,
        clients,
        organizations,
        platforms,
        report_types,
        interest_rt,
        rts_to_connect,
        superseding,
        ib_counts,
        ib_max_counts,
        settings,
    ):
        """
        The created data from IB perspective are

        date    | RT  | platform   | organization | source
        --------+-----+------------+--------------+-------
        2020-01 | TR  | standalone | standalone   | fa
        2020-02 | TR  | standalone | standalone   | fa
        2020-03 | TR  | standalone | standalone   | mdu
        2020-02 | BR1 | standalone | standalone   | fa
        2020-01 | PR  | branch     | branch       | fa
        2020-02 | PR  | branch     | branch       | mdu
        2020-03 | PR  | branch     | branch       | mdu
        """
        # make sure interest is not among the excluded report types
        settings.REPORT_TYPES_WITHOUT_COVERAGE = []
        # set up some interest
        ig = InterestGroup.objects.create(name='XXX', position=1)
        last_tr = None
        metric1 = data['metric1']
        for rt_name in rts_to_connect:
            PlatformInterestReport.objects.create(
                platform=platforms['standalone'], report_type=report_types[rt_name]
            )
            ReportInterestMetric.objects.create(
                report_type=report_types[rt_name], metric=metric1, interest_group=ig
            )
            if last_tr and superseding:
                # superseding was requested - we make the last_tr superseding current RT
                last_tr.superseeded_by = report_types[rt_name]
                last_tr.save()
            last_tr = report_types[rt_name]
        sync_interest_by_import_batches()

        resp = clients['su'].get(
            reverse('import-batch-list') + "data-coverage/",
            {'start_date': '2020-01', 'end_date': '2020-03', 'report_type': interest_rt.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert [rec['ib_max'] for rec in data] == ib_max_counts, "ib_max should match"
        assert [rec['ib_count'] for rec in data] == ib_counts, "ib_count should match"
