import pytest
from django.urls import reverse

from logs.models import ImportBatch

from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ManualDataUploadFactory, ImportBatchFullFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory

from test_fixtures.scenarios.basic import (
    users,
    report_types,
    counter_report_types,
    organizations,
    platforms,
    data_sources,
    clients,
    identities,
    credentials,
)  # noqa


@pytest.mark.django_db
class TestImportBatchesAPI:
    lookup_url = reverse('import-batch-lookup')
    purge_url = reverse('import-batch-purge')

    @pytest.fixture()
    def data(
        self, report_types, counter_report_types, organizations, platforms, clients, credentials
    ):
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
                ),
                ImportBatchFullFactory(
                    date="2020-04-01",
                    organization=organizations["standalone"],
                    platform=platforms["standalone"],
                    report_type=report_types["tr"],
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
                ),
                ImportBatchFullFactory(
                    date="2020-03-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                ),
                ImportBatchFullFactory(
                    date="2020-04-01",
                    organization=organizations["branch"],
                    platform=platforms["branch"],
                    report_type=report_types["pr"],
                ),
            ),
        )

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
        assert resp.data == {"batches": 1, "sushi": 1}, "remove ib with fetch attempt"
        assert ImportBatch.objects.count() == len(batches) - 1

        resp = clients["su"].post(self.purge_url, {"batches": [batches[0]]}, format="json")
        assert resp.data == {}, "retry same request - nothing deleted"
        assert ImportBatch.objects.count() == len(batches) - 1

        resp = clients["su"].post(self.purge_url, {"batches": [batches[-1]]}, format="json")
        assert resp.status_code == 200
        assert resp.data == {"batches": 1}, "remove ib from mdu"
        assert ImportBatch.objects.count() == len(batches) - 2

        resp = clients["su"].post(self.purge_url, {"batches": batches[-3:]}, format="json")
        assert resp.status_code == 200
        assert resp.data == {"manual": 1, "batches": 2}, "remove last ibs from mdu"
        assert ImportBatch.objects.count() == len(batches) - 4

        resp = clients["su"].post(self.purge_url, {"batches": batches}, format="json")
        assert resp.status_code == 200
        assert resp.data == {"manual": 1, "batches": 5, "sushi": 3}, "remove rest"
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
        assert resp.data["batches"] == len(data), "number of deleted ibs"
        assert ImportBatch.objects.count() == count - len(data), "all ibs were deleted"
