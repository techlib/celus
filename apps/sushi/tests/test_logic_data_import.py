import tempfile
from copy import deepcopy

import pytest
from core.fake_data import DataSourceFactory
from core.models import DataSource
from django.db.models import F, Q
from faker import Faker
from openpyxl import Workbook
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory
from publications.models import Platform

from sushi.logic.data_import import (
    Perform,
    import_sushi_credentials_from_xlsx,
    import_sushi_credentials_new,
    import_sushi_credentials_old,
)
from sushi.models import AttemptStatus, CounterReportsToCredentials
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    data_sources,
    organizations,
    report_types,
)

from ..fake_data import FetchAttemptFactory
from ..models import SushiCredentials

fake = Faker()
Faker.seed(0)


@pytest.mark.django_db
class TestLogicDataImportXLSX:
    @staticmethod
    def create_xlsx_file(tmp_file, records, counter_version):
        counter_version_str = counter_version.short
        wb = Workbook()
        headers = list(records[0].keys())
        ws1 = wb.active
        ws1.append(headers)
        ws2 = wb.create_sheet(f"Credentials-COUNTER{counter_version_str}")
        ws2.append(headers)
        for row in records:
            ws2.append([row[header] for header in headers])
        wb.save(tmp_file.name)
        return tmp_file.name

    @pytest.fixture
    def knowledgebases(self):
        return [
            {
                "providers": [
                    {
                        "counter_version": 5,
                        "provider": {"url": fake.url()},
                        "assigned_report_types": [
                            {"not_valid_after": None, "not_valid_before": None, "report_type": "TR"}
                        ],
                    },
                    {
                        "counter_version": 51,
                        "provider": {"url": fake.url()},
                        "assigned_report_types": [
                            {"not_valid_after": None, "not_valid_before": None, "report_type": "IR"}
                        ],
                    },
                ]
            },
            {
                "providers": [
                    {
                        "counter_version": 5,
                        "provider": {"url": fake.url()},
                        "assigned_report_types": [
                            {
                                "not_valid_after": None,
                                "not_valid_before": None,
                                "report_type": "TR",
                            },
                            {
                                "not_valid_after": None,
                                "not_valid_before": None,
                                "report_type": "DR",
                            },
                        ],
                    },
                    {
                        "counter_version": 51,
                        "provider": {"url": fake.url()},
                        "assigned_report_types": [
                            {"not_valid_after": None, "not_valid_before": None, "report_type": "IR"}
                        ],
                    },
                ]
            },
        ]

    @pytest.fixture
    def platforms(self, knowledgebases):
        p1 = PlatformFactory.create(knowledgebase=knowledgebases[0])
        p2 = PlatformFactory.create(knowledgebase=knowledgebases[1])
        return [p1, p2]

    @pytest.fixture
    def local_organizations(self):
        return OrganizationFactory.create_batch(3)

    @pytest.fixture
    def records_wo_org(self, platforms):
        return [
            {
                "title": fake.company(),
                "publisher/vendor/platform": platforms[0].name_en,
                "requestor id": fake.isbn13(),
                "customer id": fake.isbn10(),
                "api key": "",
                "platform filter": "",
            },
            {
                "title": fake.company(),
                "publisher/vendor/platform": platforms[1].name_en,
                "requestor id": fake.isbn13(),
                "customer id": fake.isbn10(),
                "api key": fake.uuid4(),
                "platform filter": fake.company(),
            },
            {
                # considered an empty line
                "title": fake.company(),
                "publisher/vendor/platform": platforms[1].name_en,
                "requestor id": fake.isbn13(),
                "customer id": "",
                "api key": fake.uuid4(),
                "platform filter": fake.company(),
            },
        ]

    @pytest.fixture
    def records(self, records_wo_org, local_organizations):
        rec = deepcopy(records_wo_org)
        rec[0]["organization"] = local_organizations[0].name_en
        rec[1]["organization"] = local_organizations[1].name_en
        rec[2]["organization"] = local_organizations[2].name_en
        return rec

    @pytest.fixture
    def updated_records(self, records):
        rec = deepcopy(records)
        rec[0]["title"] = fake.company()
        rec[0]["requestor id"] = fake.isbn13()
        rec[0]["api key"] = fake.uuid4()
        rec[1]["title"] = fake.company()
        rec[1]["requestor id"] = fake.isbn13()
        rec[1]["api key"] = fake.uuid4()
        return rec

    def test_sheet_empty_and_test_sheet_out_of_range(self, records, counter5_version):
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, records, counter5_version)
            stats = import_sushi_credentials_from_xlsx(file_name, sheet_no=2)
            assert stats["added"] == 2
            # test sheet empty
            stats = import_sushi_credentials_from_xlsx(file_name, sheet_no=1)
            assert stats["added"] == 0
            # test sheet out of range
            with pytest.raises(ValueError):
                import_sushi_credentials_from_xlsx(file_name, sheet_no=3)

    @pytest.mark.parametrize("header", ["customer id", "publisher/vendor/platform"])
    def test_essential_headers(self, records, header, counter5_version):
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, [records[0]], counter5_version)
            stats = import_sushi_credentials_from_xlsx(file_name)
            assert stats["added"] == 1

            records[0].pop(header)
            file_name = self.create_xlsx_file(tmp_file, [records[0]], counter5_version)
            with pytest.raises(ValueError):
                import_sushi_credentials_from_xlsx(file_name)

    @pytest.mark.parametrize(
        ["single_org_arg", "org_colum", "value_error"],
        [[False, True, False], [True, False, False], [False, False, True], [True, True, False]],
    )
    def test_single_org_arg_and_organization_column(
        self,
        single_org_arg,
        org_colum,
        value_error,
        records,
        records_wo_org,
        local_organizations,
        counter5_version,
    ):
        org = OrganizationFactory()
        single_org = org.name_en if single_org_arg else None
        records = records if org_colum else records_wo_org
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, records, counter5_version)

            if value_error:
                with pytest.raises(ValueError):
                    import_sushi_credentials_from_xlsx(file_name, single_org=single_org)
            else:
                import_sushi_credentials_from_xlsx(file_name, single_org=single_org)

                crs = SushiCredentials.objects.all()
                for cr in crs:
                    if single_org_arg:
                        assert cr.organization == org
                    else:
                        assert cr.organization in local_organizations

    def test_sushi_import(self, knowledgebases, records, counter_report_types, counter5_version):
        assert SushiCredentials.objects.count() == 0
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, records, counter5_version)
            stats = import_sushi_credentials_from_xlsx(file_name)
            assert stats["added"] == 2
            assert SushiCredentials.objects.count() == 2
            credentials = SushiCredentials.objects.all().order_by("pk")

            for cr, rec, kb in zip(credentials, records, knowledgebases):
                assert cr.title == rec["title"]
                assert cr.organization.name_en == rec["organization"]
                assert cr.platform.name_en == rec["publisher/vendor/platform"]
                assert cr.requestor_id == rec["requestor id"]
                assert cr.customer_id == rec["customer id"]
                assert cr.api_key == rec["api key"]
                assert cr.extra_params == (
                    {"platform": rec["platform filter"]} if rec["platform filter"] else {}
                )
                assert cr.counter_version == counter5_version
                provider = [e for e in kb["providers"] if e["counter_version"] == counter5_version][
                    0
                ]
                assert cr.url == provider["provider"]["url"].replace("http://", "https://", 1)
                expected_reports = {rec["report_type"] for rec in provider["assigned_report_types"]}
                assert expected_reports == {rt.code for rt in cr.counter_reports.all()}

            # retry
            stats = import_sushi_credentials_new(records, counter_version=counter5_version)
            assert (
                CounterReportsToCredentials.objects.filter(
                    ~Q(credentials__counter_version=F("counter_report__counter_version"))
                ).count()
                == 0
            ), "Counter version of credentials and report types has to be the same"
            assert stats["skipped"] == 2
        assert SushiCredentials.objects.count() == 2

    @pytest.mark.parametrize(
        "update_credentials, cr_not_verified_updated, cr_verified_updated, skipped, updated",
        [
            (Perform.UPDATE_NONE, False, False, 2, 0),
            (Perform.UPDATE_NOT_VERIFIED, True, False, 1, 1),
            (Perform.UPDATE_ALL, True, True, 0, 2),
        ],
    )
    def test_sushi_reimport(
        self,
        update_credentials,
        cr_not_verified_updated,
        cr_verified_updated,
        skipped,
        updated,
        records,
        updated_records,
        counter5_version,
    ):
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, records, counter5_version)
            assert SushiCredentials.objects.count() == 0
            stats = import_sushi_credentials_from_xlsx(file_name)
            assert stats["added"] == 2
            assert SushiCredentials.objects.count() == 2

            cr_not_verified = SushiCredentials.objects.get(customer_id=records[0]["customer id"])
            cr_verified = SushiCredentials.objects.get(customer_id=records[1]["customer id"])
            assert cr_not_verified.is_verified is False
            FetchAttemptFactory(
                credentials=cr_verified,
                status=AttemptStatus.SUCCESS,
                credentials_version_hash=cr_verified.version_hash,
            )
            cr_verified.refresh_from_db()
            assert cr_verified.is_verified is True
            file_name = self.create_xlsx_file(tmp_file, updated_records, counter5_version)
            stats = import_sushi_credentials_from_xlsx(
                file_name, update_credentials=update_credentials
            )
            assert stats["diff_updated"] == updated
            assert stats["diff_skipped"] == skipped
            assert SushiCredentials.objects.count() == 2
            for cr, updated_rec, updated, rec in zip(
                [cr_not_verified, cr_verified],
                updated_records,
                [cr_not_verified_updated, cr_verified_updated],
                records,
            ):
                cr.refresh_from_db()
                assert cr.title == (updated_rec["title"] if updated else rec["title"])
                assert cr.requestor_id == (
                    updated_rec["requestor id"] if updated else rec["requestor id"]
                )
                assert cr.api_key == (updated_rec["api key"] if updated else rec["api key"])

    def test_existing_sushi_reimport(
        self, records, platforms, local_organizations, counter5_version
    ):
        SushiCredentials.objects.create(
            title=fake.company(),
            organization=local_organizations[0],
            platform=platforms[0],
            counter_version=counter5_version,
        )
        SushiCredentials.objects.create(
            title=fake.company(),
            organization=local_organizations[0],
            platform=platforms[0],
            counter_version=counter5_version,
        )

        assert SushiCredentials.objects.count() == 2
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp_file:
            file_name = self.create_xlsx_file(tmp_file, records, counter5_version)
            stats = import_sushi_credentials_from_xlsx(file_name)
            assert stats["added"] == 1
            assert stats["duplicates_skipped"] == 1
            assert SushiCredentials.objects.count() == 3

    @pytest.mark.parametrize(["name_is_identical", "error", "added"], [[False, 0, 1], [True, 1, 0]])
    def test_conflicting_platform_names(
        self, local_organizations, knowledgebases, name_is_identical, error, added, counter5_version
    ):
        ds_type_org = DataSourceFactory.create(
            type=DataSource.TYPE_ORGANIZATION, organization=local_organizations[0]
        )
        ds_type_kb = DataSourceFactory.create(
            type=DataSource.TYPE_KNOWLEDGEBASE, url=fake.url(), token=fake.uuid4()
        )
        name = fake.company()
        name2 = name if name_is_identical else fake.company()
        PlatformFactory.create(source=ds_type_org, name_en=name, knowledgebase=knowledgebases[0])
        PlatformFactory.create(source=ds_type_kb, name_en=name2, knowledgebase=knowledgebases[0])
        records = [
            {
                "title": fake.company(),
                "organization": local_organizations[0].name_en,
                "publisher/vendor/platform": name,
                "customer id": fake.isbn10(),
            }
        ]
        stats = import_sushi_credentials_new(records, counter_version=counter5_version)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["error"] == error
        assert stats["added"] == added


@pytest.mark.django_db
class TestLogicDataImportCSV:
    def test_sushi_import(self, counter_report_types):
        organizations = OrganizationFactory.create_batch(2)
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                "platform": "XXX",
                "organization": organizations[0].internal_id,
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
                "version": "4",
            },
            {
                "platform": "XXX",
                "organization": organizations[1].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRX",
                "URL": "http://this.is/test/2",
                "version": 5,
                "extra_attrs": f"auth=un,pass;api_key={'key' * 100};foo=bar",
                "counter_reports": "TR, DR",
            },
            {
                "platform": "XXX",
                "organization": organizations[1].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRY",
                "URL": "http://this.is/test/3",
                "version": 51,
                "extra_attrs": f"api_key={'key' * 100};foot=ball",
                "counter_reports": "IR",
            },
            {
                # missing organization and counter version
                "platform": "XXX",
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
            },
        ]
        Platform.objects.create(short_name="XXX", name="XXXX")
        stats = import_sushi_credentials_old(data)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["added"] == 3
        assert stats["error"] == 1, "the last record is missing organization"
        assert SushiCredentials.objects.count() == 3
        credentials = SushiCredentials.objects.all().order_by("pk")
        # check individual objects
        cr1 = credentials[0]
        assert cr1.counter_version == 4
        assert cr1.url == "https://this.is/test/"
        assert cr1.organization == organizations[0]
        cr2 = credentials[1]
        assert cr2.counter_version == 5
        assert cr2.url == "https://this.is/test/2"
        assert cr2.organization == organizations[1]
        assert cr2.http_username == "un"
        assert cr2.http_password == "pass"
        assert cr2.api_key == "key" * 100
        assert cr2.extra_params == {"foo": "bar"}
        assert cr2.counter_reports.count() == 2
        assert {crt.code for crt in cr2.counter_reports.all()} == {"TR", "DR"}
        cr3 = credentials[2]
        assert cr3.counter_version == 51
        assert cr3.url == "https://this.is/test/3"
        assert cr3.organization == organizations[1]
        assert cr3.api_key == "key" * 100
        assert cr3.extra_params == {"foot": "ball"}
        assert cr3.counter_reports.count() == 1
        assert {crt.code for crt in cr3.counter_reports.all()} == {"IR"}
        # retry
        stats = import_sushi_credentials_old(data)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["skipped"] == 3
        assert SushiCredentials.objects.count() == 3

    def test_sushi_reimport(self):
        organizations = OrganizationFactory.create_batch(2)
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                "platform": "XXX",
                "organization": organizations[0].internal_id,
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
                "version": 4,
            },
            {
                "platform": "XXX",
                "organization": organizations[1].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRX",
                "URL": "http://this.is/test/2",
                "version": 5,
                "extra_attrs": "auth=un,pass;api_key=kekekeyyy;foo=bar",
            },
            {
                "platform": "XXX",
                "organization": organizations[1].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRY",
                "URL": "http://this.is/test/3",
                "version": 51,
                "extra_attrs": f"api_key={'key' * 100};foot=ball",
                "counter_reports": "IR",
            },
        ]
        Platform.objects.create(short_name="XXX", name="XXXX")
        stats = import_sushi_credentials_old(data)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["added"] == 3
        assert SushiCredentials.objects.count() == 3
        # retry
        data[1]["URL"] = "http://new.url/"
        data[1]["extra_attrs"] = "api_key=kekekeyyy;foo=bar"
        data[2]["extra_attrs"] = "foot=ball"
        stats = import_sushi_credentials_old(data)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["skipped"] == 1
        assert stats["synced"] == 2
        assert SushiCredentials.objects.count() == 3
        credentials = SushiCredentials.objects.get(url="https://new.url/")
        assert credentials.http_password == ""
        assert credentials.http_username == ""
        credentials = SushiCredentials.objects.get(url="https://this.is/test/3")
        assert not credentials.api_key
        assert credentials.extra_params == {"foot": "ball"}

    @pytest.mark.parametrize("organization_idx", [0, 1])
    def test_sushi_import_with_custom_platforms(self, organization_idx):
        organizations = OrganizationFactory.create_batch(2)
        assert SushiCredentials.objects.count() == 0
        pl_global = PlatformFactory.create(short_name="pl-global")
        s1, _ = DataSource.objects.get_or_create(
            short_name="s1", organization=organizations[0], type=DataSource.TYPE_ORGANIZATION
        )
        s2, _ = DataSource.objects.get_or_create(
            short_name="s2", organization=organizations[1], type=DataSource.TYPE_ORGANIZATION
        )
        pl_org1 = PlatformFactory.create(short_name="pl-org1", source=s1)
        pl_org2 = PlatformFactory.create(short_name="pl-org2", source=s2)
        data = [
            {
                "platform": pl_global.short_name,
                "organization": organizations[organization_idx].internal_id,
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
                "version": 4,
            },
            {
                "platform": pl_org1.short_name,
                "organization": organizations[organization_idx].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRX",
                "URL": "http://this.is/test/2",
                "version": 5,
            },
            {
                "platform": pl_org2.short_name,
                "organization": organizations[organization_idx].internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRX",
                "URL": "http://this.is/test/2",
                "version": 5,
            },
        ]
        stats = import_sushi_credentials_old(data)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["added"] == 2, "one global and one for org specific platform"
        assert stats["error"] == 1, "one org specific platform not matching"
        assert SushiCredentials.objects.count() == 2, "one global and one for org specific platform"
        used_pl_names = [sc.platform.short_name for sc in SushiCredentials.objects.all()]
        used_pl_names.sort()
        if organization_idx == 0:
            assert used_pl_names == ["pl-global", "pl-org1"]
        else:
            assert used_pl_names == ["pl-global", "pl-org2"]

    def test_sushi_import_override_organization(self, counter_report_types):
        org1, org2, org3 = OrganizationFactory.create_batch(3)
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                "platform": "XXX",
                "organization": org1.internal_id,
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
                "version": 4,
            },
            {
                "platform": "XXX",
                "organization": org2.internal_id,
                "customer_id": "BBB",
                "requestor_id": "RRRX",
                "URL": "http://this.is/test/2",
                "version": 5,
                "extra_attrs": f"auth=un,pass;api_key={'key' * 100};foo=bar",
                "counter_reports": "TR, DR",
            },
        ]
        Platform.objects.create(short_name="XXX", name="XXXX")
        stats = import_sushi_credentials_old(data, override_organization=org3)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["added"] == 2
        assert SushiCredentials.objects.count() == 2
        assert SushiCredentials.objects.filter(organization=org3).count() == 2
        assert SushiCredentials.objects.filter(organization=org1).count() == 0
        assert SushiCredentials.objects.filter(organization=org2).count() == 0

    @pytest.mark.parametrize("default_version", [4, 5, None])
    def test_sushi_import_default_version(self, counter_report_types, default_version):
        organization = OrganizationFactory.create()
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                "platform": "XXX",
                "organization": organization.name,
                "customer_id": "AAA",
                "requestor_id": "RRR",
                "URL": "http://this.is/test/",
            }
        ]
        Platform.objects.create(short_name="XXX", name="XXXX")
        extra = {"default_version": default_version} if default_version is not None else {}
        stats = import_sushi_credentials_old(data, **extra)
        assert (
            CounterReportsToCredentials.objects.filter(
                ~Q(credentials__counter_version=F("counter_report__counter_version"))
            ).count()
            == 0
        ), "Counter version of credentials and report types has to be the same"
        assert stats["added"] == 1
        cr1 = SushiCredentials.objects.first()
        assert cr1.counter_version == (5 if default_version is None else default_version)
