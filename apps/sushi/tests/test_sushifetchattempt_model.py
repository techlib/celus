from datetime import date, timedelta
from pathlib import Path

import pytest
from celus_nigiri.error_codes import ErrorCode
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from django.utils import timezone
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory

from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiFetchAttempt
from sushi.models import BrokenCredentialsMixin as BC
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    counter_report_types,
    credentials,
    data_sources,
    organizations,
    platforms,
    report_types,
    users,
)


@pytest.mark.django_db
class TestFileName:
    """Test class for checking whether setting the file name
    work as expected
    """

    @pytest.mark.parametrize(
        ("internal_id", "platform_name", "code", "ext"),
        (
            ("internal1", "platform_1", "tr", "json"),
            (None, "platform_2", "tr", "json"),
            (None, "platform_1", "jr1", "tsv"),
            ("internal2", "platform_1", "jr1", "tsv"),
        ),
    )
    def test_file_name(self, internal_id, platform_name, code, ext, counter_report_types):
        platform = PlatformFactory(short_name=platform_name, name=platform_name)

        organization = OrganizationFactory(internal_id=internal_id)
        counter_report_type = counter_report_types[code]

        credentials = CredentialsFactory(
            organization=organization,
            platform=platform,
            counter_version=counter_report_type.counter_version,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        data_file = ContentFile("b")
        data_file.name = f"report.{ext}"

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date="2020-01-01",
            end_date="2020-02-01",
            data_file=data_file,
            checksum="foo",
            file_size=1,
            credentials_version_hash=credentials.compute_version_hash(),
        )

        assert fetch_attempt.data_file.name.startswith(
            f"counter/{internal_id or organization.pk}/{platform_name}/"
            f"{counter_report_type.counter_version}_{counter_report_type.code.upper()}"
        )


@pytest.mark.django_db
class TestSushiFetchAttemptModel:
    def test_conflicting_fully_enclosing(self, credentials, counter_report_types):
        fa = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        assert fa.conflicting(fully_enclosing=True).count() == 0, "no conflicts"
        fa2 = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-03-31",
        )
        assert fa.conflicting(fully_enclosing=True).count() == 1, "one conflict"
        # results do not have to be symmetrical because of different date ranges
        assert fa.conflicting(fully_enclosing=True).get().pk == fa2.pk
        assert fa2.conflicting(fully_enclosing=True).count() == 0

    def test_conflicting_not_fully_enclosing(self, credentials, counter_report_types):
        fa = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        # fully_enclosing is False by default, so no need to specify it
        assert fa.conflicting().count() == 0, "no conflicts"
        fa2 = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-03-31",
        )
        assert fa.conflicting().count() == 1, "one conflict"
        # results should be symmetrical - fa conflicts with fa2, fa2 conflicts with fa
        assert fa.conflicting().get().pk == fa2.pk
        assert fa2.conflicting().get().pk == fa.pk

    def test_any_success_lately(self, credentials, counter_report_types):
        now = timezone.now()

        with freeze_time(now):
            # add unsuccessful attempt which happened right now
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now,
                status=AttemptStatus.DOWNLOAD_FAILED,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # add unsuccessful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=5),
                status=AttemptStatus.DOWNLOAD_FAILED,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # successful after lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=16),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # successful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=15),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is True

    def test_any_import_batch_lately(self, credentials, counter_report_types):
        now = timezone.now()

        with freeze_time(now):
            # add unsuccessful attempt which happened right now
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now,
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_import_batch_lately() is False

            # add unsuccessful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=5),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_import_batch_lately() is False

            # successful after lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=91),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
            )
            assert attempt.any_import_batch_lately() is False

            # successful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=90),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
            )
            assert attempt.any_import_batch_lately() is True

    def test_broken_credentials(self, credentials, counter_report_types):
        attempt = FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            end_date="2020-01-31",
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["tr"],
            import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
        )
        assert attempt.broken_credentials is False
        credentials["standalone_tr"].set_broken(FetchAttemptFactory(), "http")
        assert attempt.broken_credentials is True

        attempt = FetchAttemptFactory(
            credentials=credentials["branch_pr"],
            end_date="2020-01-31",
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["pr"],
            import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
        )
        assert attempt.broken_credentials is False
        CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["pr"], credentials=credentials["branch_pr"]
        ).set_broken(FetchAttemptFactory(), "sushi")
        assert attempt.broken_credentials is True

    @pytest.mark.parametrize(
        "status,http_status,sushi_status,lately,broken_credentials,broken_cr2c",
        (
            ("NO_DATA", 400, ErrorCode.INVALID_API_KEY, False, None, None),
            ("SUCCESS", 401, ErrorCode.REPORT_NOT_SUPPORTED, False, None, None),
            ("QUEUED", 400, ErrorCode.NOT_AUTHORIZED, False, None, None),
            ("NO_DATA", 400, ErrorCode.NOT_AUTHORIZED_INSTITUTION, False, None, None),
            ("SUCCESS", 400, ErrorCode.INVALID_API_KEY, False, None, None),
            ("NO_DATA", 400, ErrorCode.INSUFFICIENT_DATA, False, None, None),
            # cred broken testing
            ("FAILURE", 401, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 403, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 500, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 400, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 500, ErrorCode.TOO_MANY_REQUESTS, True, None, None),
            ("FAILURE", 400, ErrorCode.TOO_MANY_REQUESTS, True, None, None),
            ("FAILURE", 200, ErrorCode.NOT_AUTHORIZED, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.INVALID_API_KEY, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.NOT_AUTHORIZED_INSTITUTION, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.INSUFFICIENT_DATA, False, BC.BROKEN_SUSHI, None),
            # cred to report type testing
            ("FAILURE", 404, ErrorCode.TOO_MANY_REQUESTS, False, None, BC.BROKEN_HTTP),
            ("FAILURE", 200, ErrorCode.REPORT_NOT_SUPPORTED, False, None, BC.BROKEN_SUSHI),
            ("FAILURE", 200, ErrorCode.REPORT_VERSION_NOT_SUPPORTED, False, None, BC.BROKEN_SUSHI),
            ("FAILURE", 400, ErrorCode.INVALID_REPORT_FILTER, False, None, BC.BROKEN_SUSHI),
        ),
    )
    def test_update_broken(
        self,
        status,
        http_status,
        sushi_status,
        lately,
        broken_credentials,
        broken_cr2c,
        credentials,
        counter_report_types,
    ):
        creds = credentials["standalone_br1_jr1"]
        assert creds.broken is None
        assert creds.first_broken_attempt is None

        cr2c = CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["br1"], credentials=creds
        )
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

        # Different credentials
        FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            end_date="2020-01-31",
            when_processed=timezone.now() - timedelta(days=1),
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["jr1"],
        )

        if lately:
            FetchAttemptFactory(
                credentials=creds,
                end_date="2020-01-31",
                when_processed=timezone.now() - timedelta(days=1),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["br1"],
                http_status_code=200,
            )

        if status == "SUCCESS":
            status = AttemptStatus.SUCCESS
        elif status == "NO_DATA":
            status = AttemptStatus.NO_DATA
        elif status == "QUEUED":
            status = AttemptStatus.DOWNLOADING
        elif status == "FAILURE":
            status = AttemptStatus.DOWNLOAD_FAILED
        else:
            raise NotImplementedError()

        # First broken attempt
        attempt = FetchAttemptFactory(
            credentials=creds,
            end_date="2020-01-31",
            when_processed=timezone.now(),
            counter_report=counter_report_types["br1"],
            error_code=sushi_status.value,
            http_status_code=http_status,
            status=AttemptStatus.DOWNLOAD_FAILED
            if broken_credentials or broken_cr2c
            else AttemptStatus.SUCCESS,
        )
        attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken == broken_credentials
        assert creds.first_broken_attempt == (attempt if broken_credentials else None)
        assert cr2c.broken == broken_cr2c
        assert cr2c.first_broken_attempt == (attempt if broken_cr2c else None)

        # Test whether first_broken_attempt is not overriden
        second_attempt = FetchAttemptFactory(
            credentials=creds,
            end_date="2020-01-31",
            when_processed=timezone.now(),
            counter_report=counter_report_types["br1"],
            error_code=sushi_status.value,
            http_status_code=http_status,
            status=status,
        )
        second_attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken == broken_credentials
        assert creds.first_broken_attempt == (attempt if broken_credentials else None)
        assert cr2c.broken == broken_cr2c
        assert cr2c.first_broken_attempt == (attempt if broken_cr2c else None)

        # Change credentials hash => all will be unbroken
        creds.url += "/something/"
        creds.save()
        cr2c.refresh_from_db()
        assert creds.broken is None
        assert creds.first_broken_attempt is None
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

        # Rerun update broken should keep the creds and cr2c unbroken
        attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken is None
        assert creds.first_broken_attempt is None
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

    def test_data_file_names(self, platforms, credentials):
        with (Path(__file__).parent / "data/counter5/5_TR_ProQuestEbookCentral.json").open(
            "rb"
        ) as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.json"

        fa = FetchAttemptFactory.create(
            data_file=data_file, credentials=credentials["standalone_tr"]
        )
        assert "/standalone.standalone/" in fa.data_file.name

        fa = FetchAttemptFactory.create(
            data_file=data_file, credentials__platform=platforms["shared"]
        )
        assert "/shared/" in fa.data_file.name


@pytest.mark.django_db
class TestParsing:
    @pytest.mark.parametrize(
        ("filename", "counter_report_type", "header", "count", "sum"),
        (
            ("4_JR2_denials.tsv", "jr2", {"Institution_Name": "Higher Title"}, 2, 5),
            ("counter4_br2.tsv", "br2", {"Institution_Name": "ANONYMOUS"}, 60, 43),
            ("counter4_br2_one_month.tsv", "br2", {"Institution_Name": "ANONYMOUS"}, 5, 12),
            ("counter4_jr1_empty.tsv", "jr1", {"Institution_Name": "Title"}, 0, 0),
        ),
    )
    def test_counter4_parsing(
        self, counter_report_types, filename, counter_report_type, header, count, sum
    ):
        with (Path(__file__).parent / "data/counter4" / filename).open("rb") as f:
            content = f.read()
        fa = FetchAttemptFactory(
            counter_report=counter_report_types[counter_report_type],
            data_file__data=content,
            data_file__filename="input.tsv",
        )

        poop = fa.get_nibbler_poop(fa.file_is_json())
        fa.extract_header_data(poop.extras)
        assert fa.extracted_data == header
        logs = (e[1] for e in poop.records_basic())
        parsed_count = 0
        parsed_sum = 0
        for log in logs:
            parsed_count += 1
            parsed_sum += log.value

        assert parsed_count == count
        assert parsed_sum == sum

    @pytest.mark.parametrize(
        ("filename", "counter_report_type", "header", "count", "sum"),
        (
            (
                "5_TR_ProQuestEbookCentral.json",
                "tr",
                {
                    "Created_By": "ProQuest Ebook Central",
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBC:hidden"}],
                },
                30,
                52,
            ),
            (
                "C5_PR_test.json",
                "pr",
                {
                    "Created_By": "EBSCO Information Services",
                    "Institution_Name": "FOO BAR UNIVERSITY",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBSCOhost:1234567"}],
                },
                25,
                5051,
            ),
            (
                "C5_PR_with_3030.json",
                "pr",
                {
                    "Created_By": "EBSCO Information Services",
                    "Institution_Name": "FOO BAR UNIVERSITY",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBSCOhost:1234567"}],
                },
                25,
                5051,
            ),
            (
                "C5_PR_with_3040.json",
                "pr",
                {
                    "Created_By": "EBSCO Information Services",
                    "Institution_Name": "FOO BAR UNIVERSITY",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBSCOhost:1234567"}],
                },
                25,
                5051,
            ),
            (
                "no_data.json",
                "tr",
                {
                    "Created_By": "Celus LLC.",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "lyb:DDDDDDDDDDDDDD"}],
                },
                0,
                0,
            ),
            (
                "no_data_3050.json",
                "tr",
                {"Created_By": "My provider", "Institution_Name": "My Library"},
                0,
                0,
            ),
            (
                "no_data_3062.json",
                "tr",
                {"Created_By": "Provider", "Institution_Name": "My LIbrary"},
                0,
                0,
            ),
            (
                "some_data_3062.json",
                "tr",
                {"Created_By": "Provider", "Institution_Name": "My LIbrary"},
                20,
                24,
            ),
            (
                "TR-one-title-more-ids.json",
                "tr",
                {
                    "Created_By": "ProQuest",
                    "Institution_Name": "Foo bar baz",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "ProQuest:XXYYZZ"}],
                },
                124,
                12528,
            ),
            (
                "partial_data1.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                12,
                50,
            ),
            (
                "partial_data2.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                12,
                50,
            ),
            (
                "partial_data3.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                12,
                50,
            ),
            (
                "some_data_3050.json",
                "pr",
                {"Created_By": "My provider", "Institution_Name": "My Library"},
                8,
                1422,
            ),
            (
                "5_TR_with_warning.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                8,
                46,
            ),
            (
                "counter5_tr_test1.json",
                "tr",
                {
                    "Created_By": "My Provider",
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:hidden"}],
                },
                16,
                322,
            ),
            (
                "code-zero.json",
                "tr",
                {
                    "Created_By": "Publisher",
                    "Institution_Name": "Celus College",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "SN:8888888888"}],
                },
                0,
                0,
            ),
            (
                "counter5_tr_nature.json",
                "tr",
                {
                    "Created_By": "SpringerNature",
                    "Institution_Name": "PRIVATE",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "SN:XXXXXX"}],
                },
                115,
                231,
            ),
            (
                "null-in-Item_ID.json",
                "tr",
                {
                    "Created_By": "Some Entity",
                    "Institution_Name": "My organization",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "my:1111"}],
                },
                2,
                3,
            ),
            (
                "severity-missing.json",
                "dr",
                {
                    "Created_By": "Provider",
                    "Institution_Name": "My university",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "Provider:1258"}],
                },
                0,
                0,
            ),
            (
                "severity-number.json",
                "dr",
                {
                    "Created_By": "Provider",
                    "Institution_Name": "My university",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "Provider:1258"}],
                },
                0,
                0,
            ),
            (
                "severity-wrong.json",
                "pr",
                {"Created_By": "My provider", "Institution_Name": "My university"},
                0,
                0,
            ),
        ),
    )
    def test_counter5_parsing(
        self, counter_report_types, filename, counter_report_type, header, count, sum
    ):
        with (Path(__file__).parent / "data/counter5" / filename).open("rb") as f:
            content = f.read()
        fa = FetchAttemptFactory(
            counter_report=counter_report_types[counter_report_type],
            data_file__data=content,
            data_file__filename="input.json",
        )

        poop = fa.get_nibbler_poop(fa.file_is_json())
        fa.extract_header_data(poop.extras)
        assert fa.extracted_data == header
        logs = (e[1] for e in poop.records_basic())
        parsed_count = 0
        parsed_sum = 0
        for log in logs:
            parsed_count += 1
            parsed_sum += log.value

        assert parsed_count == count
        assert parsed_sum == sum


@pytest.mark.django_db
class TestCounterReportsToCredentials:
    def test_last_harvestable_month(
        self,
        users,
        platforms,
        organizations,
        credentials,
        data_sources,
        report_types,
        counter_report_types,
    ):
        cr2c_user_user = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        cr2c_attempt_attempt = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_user_attempt = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        cr2c_attempt_user = CounterReportsToCredentials.objects.get(
            credentials=credentials["branch_pr"], counter_report=counter_report_types["pr"]
        )

        assert cr2c_user_user.last_harvestable_month is None
        assert cr2c_user_user.last_harvestable_month_attempt is None
        assert cr2c_user_user.last_harvestable_month_user is None
        assert cr2c_attempt_attempt.last_harvestable_month is None
        assert cr2c_attempt_attempt.last_harvestable_month_attempt is None
        assert cr2c_attempt_attempt.last_harvestable_month_user is None
        assert cr2c_user_attempt.last_harvestable_month is None
        assert cr2c_user_attempt.last_harvestable_month_attempt is None
        assert cr2c_user_attempt.last_harvestable_month_user is None

        # 1) None - > User
        cr2c_user_user.update_last_harvestable_month_by_user(
            users["master_admin"], date(2020, 1, 1)
        )
        assert cr2c_user_user.last_harvestable_month == date(2020, 1, 1)
        assert cr2c_user_user.last_harvestable_month_attempt is None
        assert cr2c_user_user.last_harvestable_month_user == users["master_admin"]

        # 1) User - > User
        cr2c_user_user.update_last_harvestable_month_by_user(users["su"], date(2019, 1, 1))
        assert cr2c_user_user.last_harvestable_month == date(2019, 1, 1)
        assert cr2c_user_user.last_harvestable_month_attempt is None
        assert cr2c_user_user.last_harvestable_month_user == users["su"]

        # 1) User - > None
        cr2c_user_user.update_last_harvestable_month_by_user(users["master_admin"], None)
        assert cr2c_user_user.last_harvestable_month is None
        assert cr2c_user_user.last_harvestable_month_attempt is None
        assert cr2c_user_user.last_harvestable_month_user == users["master_admin"]

        # 2) None -> Attempt
        fa1 = FetchAttemptFactory.create(
            credentials=cr2c_attempt_attempt.credentials, start_date=date(2021, 1, 1)
        )
        assert cr2c_attempt_attempt.update_last_harvestable_month_by_attempt(fa1) is True
        assert cr2c_attempt_attempt.last_harvestable_month == date(2021, 2, 1)
        assert cr2c_attempt_attempt.last_harvestable_month_attempt == fa1
        assert cr2c_attempt_attempt.last_harvestable_month_user is None

        # 2) Attempt -> Attempt (older)
        fa2 = FetchAttemptFactory.create(
            credentials=cr2c_attempt_attempt.credentials, start_date=date(2020, 1, 1)
        )
        assert cr2c_attempt_attempt.update_last_harvestable_month_by_attempt(fa2) is False
        assert cr2c_attempt_attempt.last_harvestable_month == date(
            2021, 2, 1
        ), "date does not change"
        assert cr2c_attempt_attempt.last_harvestable_month_attempt == fa1
        assert cr2c_attempt_attempt.last_harvestable_month_user is None

        # 2) Attempt -> Attempt (newer)
        fa3 = FetchAttemptFactory.create(
            credentials=cr2c_attempt_attempt.credentials, start_date=date(2022, 1, 1)
        )
        assert cr2c_attempt_attempt.update_last_harvestable_month_by_attempt(fa3) is True
        assert cr2c_attempt_attempt.last_harvestable_month == date(2022, 2, 1)
        assert cr2c_attempt_attempt.last_harvestable_month_attempt == fa3
        assert cr2c_attempt_attempt.last_harvestable_month_user is None

        # 3) None -> User
        cr2c_user_attempt.update_last_harvestable_month_by_user(
            users["master_admin"], date(2021, 1, 1)
        )
        assert cr2c_user_attempt.last_harvestable_month == date(2021, 1, 1)
        assert cr2c_user_attempt.last_harvestable_month_attempt is None
        assert cr2c_user_attempt.last_harvestable_month_user == users["master_admin"]

        # 3) User -> Attempt (older)
        fa4 = FetchAttemptFactory.create(
            credentials=cr2c_user_attempt.credentials, start_date=date(2020, 1, 1)
        )
        assert cr2c_user_attempt.update_last_harvestable_month_by_attempt(fa4) is False
        assert cr2c_user_attempt.last_harvestable_month == date(2021, 1, 1), "date does not change"
        assert cr2c_user_attempt.last_harvestable_month_attempt is None
        assert cr2c_user_attempt.last_harvestable_month_user == users["master_admin"]

        # 3) User -> Attempt (newer)
        fa5 = FetchAttemptFactory.create(
            credentials=cr2c_user_attempt.credentials, start_date=date(2022, 1, 1)
        )
        assert cr2c_user_attempt.update_last_harvestable_month_by_attempt(fa5) is True
        assert cr2c_user_attempt.last_harvestable_month == date(2022, 2, 1)
        assert cr2c_user_attempt.last_harvestable_month_attempt == fa5
        assert cr2c_user_attempt.last_harvestable_month_user is None

        # 4) None -> Attempt
        fa6 = FetchAttemptFactory.create(
            credentials=cr2c_attempt_user.credentials, start_date=date(2021, 1, 1)
        )
        assert cr2c_attempt_user.update_last_harvestable_month_by_attempt(fa6) is True
        assert cr2c_attempt_user.last_harvestable_month == date(2021, 2, 1)
        assert cr2c_attempt_user.last_harvestable_month_attempt == fa6
        assert cr2c_attempt_user.last_harvestable_month_user is None

        # 4) Attempt -> User (older)
        cr2c_attempt_user.update_last_harvestable_month_by_user(
            users["master_admin"], date(2020, 1, 1)
        )
        assert cr2c_attempt_user.last_harvestable_month == date(2020, 1, 1)
        assert cr2c_attempt_user.last_harvestable_month_attempt is None
        assert cr2c_attempt_user.last_harvestable_month_user == users["master_admin"]
