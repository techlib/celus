import pytest
from django.urls import reverse
from sushi.fake_data import CounterReportTypeFactory

from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from test_scenarios.basic import (
    basic1,  # noqa
    clients,  # noqa
    data_sources,  # noqa
    identities,  # noqa
    organizations,  # noqa
    platforms,  # noqa
    users,  # noqa
)
from test_scenarios.counter_data import (
    counter_report_types,  # noqa
    dimension_texts,  # noqa
    dimensions,  # noqa
    dr,  # noqa
    dr51,  # noqa
    dr51_dim,  # noqa
    dr51_ibs,  # noqa
    dr_dim,  # noqa
    dr_ibs,  # noqa
    ir,  # noqa
    ir51,  # noqa
    ir51_dim,  # noqa
    ir51_ibs,  # noqa
    ir_dim,  # noqa
    ir_ibs,  # noqa
    ir_m1,  # noqa
    ir_m1_dim,  # noqa
    ir_m1_ibs,  # noqa
    metrics,  # noqa
    pr,  # noqa
    pr51,  # noqa
    pr51_dim,  # noqa
    pr51_ibs,  # noqa
    pr_dim,  # noqa
    pr_ibs,  # noqa
    targets,  # noqa
    tr,  # noqa
    tr51,  # noqa
    tr51_dim,  # noqa
    tr51_ibs,  # noqa
    tr_dim,  # noqa
    tr_ibs,  # noqa
)


def sync_import_batches_with_clickhouse(*ibs):
    for ib in ibs:
        sync_import_batch_with_clickhouse(ib)


@pytest.fixture
def platform(platforms):
    return platforms["standalone"]


@pytest.fixture
def organization(organizations):
    return organizations["standalone"]


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("clickhouse_db")
class TestExportDownloadCounterEndpoint:
    @pytest.mark.parametrize(
        "user,status_code",
        (
            ("su", 200),
            ("master_user", 200),
            ("master_admin", 200),
            ("user2", 200),
            ("admin2", 200),
            ("user1", 404),
            ("admin1", 404),
        ),
    )
    def test_permissions(
        self, basic1, organization, platform, counter_report_types, clients, user, status_code
    ):
        response = clients[user].get(
            reverse("counter-data-export-download", args=(counter_report_types["tr"].pk,)),
            data={"platform": platform.id, "organization": organization.pk},
        )
        assert response.status_code == status_code

    def test_unsupported_report_type(self, basic1, organization, platform, clients):
        counter_report_type1 = CounterReportTypeFactory(code="JR1", counter_version=4)
        counter_report_type2 = CounterReportTypeFactory(code="IR_A1", counter_version=5)

        response = clients["master_user"].get(
            reverse("counter-data-export-download", args=(counter_report_type1.pk,)),
            data={"platform": platform.id, "organization": organization.pk},
        )
        assert response.status_code == 400

        response = clients["master_user"].get(
            reverse("counter-data-export-download", args=(counter_report_type2.pk,)),
            data={"platform": platform.id, "organization": organization.pk},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "counter_report_type,start_date,end_date,output_size",
        (
            ("tr", "2020-02-01", "2020-02-01", 18),
            ("tr", None, None, 20),
            ("dr", "2020-02-01", "2020-02-01", 18),
            ("dr", None, None, 20),
            ("pr", "2020-02-01", "2020-02-01", 18),
            ("pr", None, None, 20),
            ("ir_m1", "2020-02-01", "2020-02-01", 18),
            ("ir_m1", None, None, 20),
        ),
    )
    def test_download(
        self,
        basic1,
        organization,
        platform,
        clients,
        counter_report_types,
        tr_ibs,
        pr_ibs,
        dr_ibs,
        ir_m1_ibs,
        counter_report_type,
        start_date,
        end_date,
        output_size,
    ):
        data = {"platform": platform.id, "organization": organization.pk}
        sync_import_batches_with_clickhouse(*tr_ibs, *dr_ibs, *pr_ibs, *ir_m1_ibs)

        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date

        counter_report_type = counter_report_types[counter_report_type]

        response = clients["master_user"].get(
            reverse("counter-data-export-download", args=(counter_report_type.pk,)), data=data
        )
        assert response.status_code == 200

        content = b"".join(e for e in response.streaming_content).splitlines(False)
        assert len(content) == output_size


@pytest.mark.django_db
@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
class TestExportUsedCounterEndpoint:
    @pytest.mark.parametrize(
        "user,status_code",
        (
            ("su", 200),
            ("master_user", 200),
            ("master_admin", 200),
            ("user2", 200),
            ("admin2", 200),
            ("user1", 200),
            ("admin1", 200),
        ),
    )
    def test_permissions(
        self, basic1, organization, platform, counter_report_types, clients, user, status_code
    ):
        response = clients[user].get(
            reverse("counter-data-export-used"),
            data={"platform": platform.id, "organization": organization.pk},
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        "start_date,end_date,codes",
        (
            (None, None, {"TR", "DR", "PR", "IR_M1"}),
            ("2018-01-01", "2018-01-01", set()),
            ("2020-02-01", "2020-02-01", {"TR", "DR", "PR", "IR_M1"}),
            ("2020-03-01", "2020-03-01", set()),
            ("2020-04-01", "2020-04-01", {"TR", "DR", "PR"}),
        ),
    )
    def test_used(
        self,
        basic1,
        organization,
        platform,
        clients,
        counter_report_types,
        tr_ibs,
        pr_ibs,
        dr_ibs,
        ir_m1_ibs,
        start_date,
        end_date,
        codes,
    ):
        # remove ib with ir_m1 for 2020-04
        for ib in [e for e in ir_m1_ibs if e.date == "2020-04-01"]:
            ib.delete()

        data = {"platform": platform.id, "organization": organization.pk}
        sync_import_batches_with_clickhouse(*tr_ibs, *dr_ibs, *pr_ibs, *ir_m1_ibs)

        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date

        response = clients["master_user"].get(reverse("counter-data-export-used"), data=data)
        assert response.status_code == 200

        assert {e["code"] for e in response.data if e["used"] > 0} == codes
