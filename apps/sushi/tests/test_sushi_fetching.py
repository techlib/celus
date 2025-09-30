import re
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import requests_mock
from django.core.files.base import ContentFile
from freezegun import freeze_time
from logs.logic.attempt_import import import_one_sushi_attempt
from publications.models import Item, Title

from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiFetchAttempt
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    data_sources,
    organizations,
    platforms,
    report_types,
)


@pytest.mark.django_db
class TestSushiFetching:
    @pytest.mark.parametrize(
        ("path", "counter_report", "status1", "status2", "log", "breaks", "checksum"),
        (
            (
                "C5_PR_test.json",
                "pr",
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                "",
                False,
                "9f8a4abbfdc601d9a35e0904c896d843ffd488ee2f7ac0f4cd46e2ab61e2549a",
            ),
            (
                "C5_PR_with_3040.json",
                "pr",
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                (
                    "Warnings: Warning #3040: Partial Data Returned. "
                    "(Usage data has not been processed for all requested months.)\n\n"
                ),
                False,
                "634630dea45bde1bd341ffb49ae1baf9ea07088e5ab3d37ebf711712db1171ea",
            ),
            (
                "naked_errors.json",
                "pr",
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                "Warnings: Warning #1011: Report Queued for Processing (Report is currently queued "
                "for processing. Please retry the request after some reasonable time.); "
                "Warning #3060: Invalid Report Filter Value (platform not able to be changed "
                "from its value of jstor)\n\n",
                False,
                "74214e7abef5686360a1533d63e271663a502709d7790bf2bc966d781bf403d6",
            ),
            (
                "naked_error.json",
                "pr",
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                "Warnings: Warning #1011: Report Queued for Processing (Report is currently queued"
                " for processing. Please retry the request after some reasonable time.)\n\n",
                False,
                "f2bf80be20ec7f320482bb1e59c58f4aa203e47c5761325935955233a4a51f19",
            ),
            (
                "5_TR_ProQuestEbookCentral_exception.json",
                "tr",
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                "Errors: Error #3030: No Usage Available for Requested Dates. (Usage data is not "
                "available for all requested months between the begin_date and end_date.)\n\n",
                False,
                "2cff6104b7d2104724425361eeeb5868e99e46b4d663194edcd1813fa4829070",
            ),
            (
                "error-in-root.json",
                "tr",
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                "Errors: Error #2090: Got response code: 404 for request: "
                "https://example.com/path/path\n\n",
                False,
                "498d3539351036335252e99b1d005e79515656299777bcc3f2338f5e257db44c",
            ),
            (
                "no_data.json",
                "tr",
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                "",
                False,
                "9196e290f625163e1cd5d20b0e90ebe5163e93317c91366097ce7414e1b369ce",
            ),
            (
                "invalid-customer.json",
                "dr",
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                "Errors: Error #1030: Invalid Customer Id\n\n",
                True,
                "f53489e656fee489bac7a309c83a2674d1d5079a493a46192fc9f62c8dc5ce5f",
            ),
            (
                "code-zero.json",
                "tr",
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                "Infos: Info #0: Some description\n\n",
                False,
                "b161ed02ef7498aa6ea418525f7b86d561d5e6e57d4ac2f5daf4ae6ca7f7f28f",
            ),
            (
                "no_data_3062.json",
                "tr",
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                "Infos: Info #3062: Invalid ReportAttribute Value (Access_Method is not a "
                "recognized attribute for this report)\n\n",
                False,
                "46c1b2d43465cd53df256b96ae87b770a1a8d2d3aa7837c6de024cf2ebe1502c",
            ),
            (
                "some_data_3062.json",
                "tr",
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                "Infos: Info #3062: Invalid ReportAttribute Value (Access_Method is not a "
                "recognized attribute for this report)\n\n",
                False,
                "21300b16301c0d696e6c8ea986efc14362c54ba21fd633bbdfac9bb1461470e7",
            ),
            (
                "no_data_3050.json",
                "tr",
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                "Infos: Info #3050: Parameter Not Recognized in this Context "
                "(Parameter email is not recognized)\n\n",
                False,
                "38ac8db30e72f965b221004ddd9500acad6b1db0b2fda23c8c718ed45042df3c",
            ),
            (
                "some_data_3050.json",
                "pr",
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                "Infos: Info #3050: Parameter Not Recognized in this Context ([requestor_id]); "
                "Info #0: In order to be consistent with chapter-only COUNTER "
                "metrics available for other publishers, the non-standard "
                "tandfeBooks:Total_Chapter_Requests metric has been included\n\n",
                False,
                "e20be08f4fd0d3a81f37aa6d0a53ee91ec2e5c55d05f8518cae5d858c0a2cb7b",
            ),
        ),
        ids=lambda x: "" if isinstance(x, str) and not x.endswith(".json") else x,
    )
    def test_c5(
        self,
        path,
        counter_report,
        status1,
        status2,
        log,
        breaks,
        counter_report_types,
        organizations,
        platforms,
        checksum,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5
        )
        assert credentials.is_broken() is False
        # in some cases the behavior depends on the time gap between the request and the
        # requested dates, so we freeze the time to a fixed value
        with (
            freeze_time("2019-05-10"),
            requests_mock.Mocker() as m,
            patch("sushi.models.Event") as mock_event,
        ):
            with open(Path(__file__).parent / "data/counter5" / path) as datafile:
                content = datafile.read()
                m.get(re.compile(f"^{credentials.url}.*"), text=content)
                file_size = len(content)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types[counter_report], start_date="2019-04-01", end_date="2019-04-30"
            )
            assert m.called
            assert attempt.status == status1
            assert attempt.log == log

            # import the attempt and check the result
            if attempt.can_import_data:
                import_one_sushi_attempt(attempt)
                assert attempt.status == status2
                assert attempt.http_status_code == 200
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)

            assert attempt.checksum == checksum
            assert attempt.file_size == file_size

            # test that an Event is created when the attempt breaks credentials
            assert mock_event.create_for_users.call_count == (1 if breaks else 0)

        assert credentials.is_broken() == breaks

    @pytest.mark.parametrize("time", ("2020-08-01", "2020-06-15"))
    def test_c4_3030(self, counter_report_types, organizations, platforms, time):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4
        )
        credentials.counter_reports.add(counter_report_types["db1"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(Path(__file__).parent / "data/counter4/sushi_3030.xml") as datafile:
                m.post(re.compile(f"^{credentials.url}.*"), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date="2020-05-01", end_date="2020-05-31"
            )
            assert m.called
            assert attempt.status == AttemptStatus.NO_DATA
            assert (
                attempt.checksum
                == "c5f4a28d70b72005b4e6862a62fe1fb534745c0cc3039688851e312f2622c740"
            )

    def test_c4_wrong_namespaces(self, counter_report_types, organizations, platforms):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4
        )
        credentials.counter_reports.add(counter_report_types["db1"])
        with requests_mock.Mocker() as m, freeze_time("2021-01-01"):
            with open(
                Path(__file__).parent / "data/counter4/sushi_exception-with-extra-attrs.xml"
            ) as datafile:
                m.post(re.compile(f"^{credentials.url}.*"), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date="2020-01-01", end_date="2020-01-31"
            )
            assert m.called
            assert attempt.status == AttemptStatus.DOWNLOAD_FAILED
            assert (
                attempt.checksum
                == "85e1fd64816d7bd022e38c8beec58c952db793e96d727e997802c66177f51eee"
            )

    def test_c4_non_sushi_exception(self, counter_report_types, organizations, platforms):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4
        )
        credentials.counter_reports.add(counter_report_types["jr1"])
        with requests_mock.Mocker() as m, freeze_time("2021-01-01"):
            with open(
                Path(__file__).parent / "data/counter4/4_JR1_missing_reports_tag.xml"
            ) as datafile:
                m.post(re.compile(f"^{credentials.url}.*"), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["jr1"], start_date="2021-10-01", end_date="2021-10-31"
            )
            assert m.called
            assert attempt.status == AttemptStatus.PARSING_FAILED
            assert "Traceback" not in attempt.log, "no raw exception traceback in the log"
            assert "report not found" in attempt.log

    @pytest.mark.parametrize(("path", "error_code", "partial"), (("sushi_3040.xml", "3040", True),))
    def test_c4_partial_data(
        self, path, error_code, partial, counter_report_types, organizations, platforms
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / "data/counter4" / path) as datafile:
                m.post(re.compile(f"^{credentials.url}.*"), text=datafile.read(), status_code=200)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date="2020-05-01", end_date="2020-05-31"
            )
            assert m.called
            assert str(attempt.error_code) == error_code
            assert attempt.partial_data == partial
            assert attempt.status == AttemptStatus.NO_DATA

    @pytest.mark.parametrize("time", ("2017-04-01", "2017-02-15"))
    def test_c5_3030(self, counter_report_types, organizations, platforms, time):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5
        )
        credentials.counter_reports.add(counter_report_types["tr"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(
                Path(__file__).parent / "data/counter5/5_TR_ProQuestEbookCentral_exception.json"
            ) as datafile:
                m.get(re.compile(f"^{credentials.url}.*"), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date="2017-01-01", end_date="2017-01-31"
            )
            assert m.called
            assert attempt.status == AttemptStatus.NO_DATA

    @pytest.mark.parametrize(
        ("path", "http_status", "error_code", "status"),
        (
            ("naked_error_3000.json", 400, "3000", AttemptStatus.DOWNLOAD_FAILED),
            ("naked_error_3000.json", 200, "3000", AttemptStatus.DOWNLOAD_FAILED),
            ("severity-wrong.json", 200, "1011", AttemptStatus.DOWNLOAD_FAILED),
            ("no_json.txt", 400, "non-sushi", AttemptStatus.DOWNLOAD_FAILED),
        ),
    )
    def test_c5_with_http_error_codes(
        self, path, http_status, error_code, status, counter_report_types, organizations, platforms
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / "data/counter5" / path) as datafile:
                m.get(
                    re.compile(f"^{credentials.url}.*"),
                    text=datafile.read(),
                    status_code=http_status,
                )
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date="2019-04-01", end_date="2019-04-30"
            )
            assert m.called
            assert attempt.status == status
            assert attempt.error_code == error_code
            assert attempt.http_status_code == http_status

    @pytest.mark.parametrize(
        ("path", "error_code", "partial"),
        (
            ("partial_data1.json", "3210", True),
            ("partial_data2.json", "3210", True),
            ("partial_data3.json", "3040", True),
            ("5_TR_with_warning.json", "3032", True),
            ("C5_PR_with_3040.json", "3040", True),
        ),
    )
    def test_c5_partial_data(
        self, path, error_code, partial, counter_report_types, organizations, platforms
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5
        )
        # in some cases the behavior depends on the time gap between the request and the
        # requested dates, so we freeze the time to a fixed value
        with freeze_time("2019-05-10"), requests_mock.Mocker() as m:
            with open(Path(__file__).parent / "data/counter5" / path) as datafile:
                m.get(re.compile(f"^{credentials.url}.*"), text=datafile.read(), status_code=200)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date="2019-04-01", end_date="2019-04-30"
            )
            assert m.called
            assert attempt.error_code == error_code
            assert attempt.partial_data == partial
            if attempt.error_code == "3040":
                assert attempt.status == AttemptStatus.IMPORTING

    @pytest.mark.parametrize("delay_days", [1, 20, 50])
    def test_c5_3040_delay(self, counter_report_types, organizations, platforms, delay_days):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5
        )
        path = "C5_PR_with_3040.json"
        with (
            freeze_time(datetime(2019, 5, 1) + timedelta(days=delay_days)),
            requests_mock.Mocker() as m,
        ):
            with open(Path(__file__).parent / "data/counter5" / path) as datafile:
                m.get(re.compile(f"^{credentials.url}.*"), text=datafile.read(), status_code=200)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date="2019-04-01", end_date="2019-04-30"
            )
            assert m.called
            assert attempt.error_code == "3040"
            assert attempt.partial_data is True
            assert attempt.status == AttemptStatus.IMPORTING
            import_one_sushi_attempt(attempt)
            assert attempt.status == AttemptStatus.SUCCESS

    @pytest.mark.parametrize(
        ("path", "counter_report", "extracted_data", "import_passes"),
        (
            ("5_DR_ProQuestEbookCentral_exception.json", "dr", {}, False),
            (
                "5_TR_ProQuestEbookCentral.json",
                "tr",
                {
                    "Created_By": "ProQuest Ebook Central",
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBC:hidden"}],
                },
                True,
            ),
            (
                "5_TR_ProQuestEbookCentral_exception.json",
                "tr",
                {
                    "Created_By": "ProQuest Ebook Central",
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBC:hidden"}],
                },
                False,
            ),
            (
                "5_TR_with_warning.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                True,
            ),
            (
                "C5_PR_test.json",
                "pr",
                {
                    "Created_By": "EBSCO Information Services",
                    "Institution_Name": "FOO BAR UNIVERSITY",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBSCOhost:1234567"}],
                },
                True,
            ),
            (
                "counter5_tr_test1.json",
                "tr",
                {
                    "Created_By": "My Provider",
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:hidden"}],
                },
                True,
            ),
            ("data_incorrect.json", "tr", {}, False),
            (
                "error-in-root.json",
                "tr",
                {"Created_By": "CELUS LLC.", "Institution_Name": "National Library"},
                False,
            ),
            ("naked_error.json", "tr", {}, False),
            ("naked_error_3000.json", "tr", {}, False),
            ("naked_error_lowercase.json", "tr", {}, False),
            ("naked_errors.json", "tr", {}, False),
            (
                "no_data.json",
                "tr",
                {
                    "Created_By": "CELUS LLC.",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "lyb:DDDDDDDDDDDDDD"}],
                },
                False,
            ),
            (
                "partial_data1.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                False,
            ),
            (
                "partial_data2.json",
                "tr",
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                False,
            ),
            (
                "severity-missing.json",
                "dr",
                {
                    "Created_By": "Provider",
                    "Institution_Name": "My university",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "Provider:1258"}],
                },
                False,
            ),
            (
                "severity-number.json",
                "dr",
                {
                    "Created_By": "Provider",
                    "Institution_Name": "My university",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "Provider:1258"}],
                },
                False,
            ),
            (
                "stringified_error.json",
                "tr",
                {"Created_By": "Moogle LLC.", "Institution_Name": "Mekong Honkong"},
                False,
            ),
            (
                "null-in-Item_ID.json",
                "tr",
                {
                    "Created_By": "Some Entity",
                    "Institution_Name": "My organization",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "my:1111"}],
                },
                True,
            ),
            (
                "dr-extra-ids.json",
                "dr",
                {
                    "Created_By": "My services",
                    "Institution_Name": "My institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "IIIIIIIII:88888888"}],
                },
                True,
            ),
            (
                "Sample-IR_M1.json",
                "ir_m1",
                {
                    "Created_By": "Sample Institutional Repository",
                    "Institution_Name": "Client Demo Site",
                    "Institution_ID": [{"Type": "ISNI", "Value": "1234123412341234"}],
                },
                True,
            ),
        ),
    )
    def test_c5_all_cases(
        self,
        path,
        counter_report,
        extracted_data,
        import_passes,
        counter_report_types,
        organizations,
        platforms,
    ):
        """Just test that processing of test data works as excpected"""
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            url="https://example.com/sushi/",
            customer_id="CCCCCCC",
            requestor_id="RRRRRRR",
            api_key="AAAAAAAA",
        )
        # in some cases the behavior depends on the time gap between the request and the
        # requested dates, so we freeze the time to a fixed value
        with freeze_time("2019-05-10"), requests_mock.Mocker() as m:
            with open(Path(__file__).parent / "data/counter5" / path) as datafile:
                m.get(re.compile(f"^{credentials.url}.*"), text=datafile.read(), status_code=200)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types[counter_report], start_date="2019-04-01", end_date="2019-04-30"
            )
            assert attempt.extracted_data == extracted_data
            url = (
                f"https://example.com/sushi/reports/{counter_report}?customer_id=CCCCCCC"
                "&requestor_id=RRRRRRR&api_key=AAAAAAAA"
            )
            assert attempt.used_url.startswith(url)

            if import_passes:
                import_one_sushi_attempt(attempt)
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)

    @pytest.mark.parametrize(
        ("path", "counter_report", "extracted_data", "breaks_report"),
        (
            (
                # even though requested, Parent_Details are not present for some records
                # and we need to crash such an import - otherwise we will get items unconnected
                # to titles, which messes up the interest computation
                "IR_sample_r51.json",
                "ir51",
                {
                    "Created_By": "Sample Publisher",
                    "Institution_Name": "Sample Institution",
                    "Institution_ID": {"ISNI": ["1234123412341234"]},
                },
                True,
            ),
            (
                # this one has parent details where necessary and only lacks it for Multimedia,
                # where parent details are not required
                "IR_sample_r51_no-missing-parent.json",
                "ir51",
                {
                    "Created_By": "Sample Publisher",
                    "Institution_Name": "Sample Institution",
                    "Institution_ID": {"ISNI": ["1234123412341234"]},
                },
                False,
            ),
            (
                # The same author is used twice in the author's list
                "IR_sample_r51_same-authors.json",
                "ir51",
                {
                    "Created_By": "Sample Publisher",
                    "Institution_Name": "Sample Institution",
                    "Institution_ID": {"ISNI": ["1234123412341234"]},
                },
                False,
            ),
        ),
    )
    def test_c51_ir(
        self,
        path,
        counter_report,
        extracted_data,
        breaks_report,
        counter_report_types,
        organizations,
        platforms,
    ):
        """
        Test that processing IR reports without parent details and with article data breaks the
        report if title details are missing.
        """
        # NOTE: Do not remove this test when rebasing IR_M1 migration code, this has been modified
        # to use C51 and is important
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=51,
            url="https://example.com/sushi/",
            customer_id="CCCCCCC",
            requestor_id="RRRRRRR",
            api_key="AAAAAAAA",
        )
        crt = counter_report_types[counter_report]
        cr2c = CounterReportsToCredentials.objects.create(
            credentials=credentials, counter_report=crt
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / "data/counter51" / path) as datafile:
                m.get(re.compile(f"^{credentials.url}.*"), text=datafile.read(), status_code=200)
            attempt: SushiFetchAttempt = credentials.fetch_report(
                crt, start_date="2022-01-01", end_date="2022-01-31"
            )
            assert attempt.extracted_data == extracted_data
            url = (
                "https://example.com/sushi/r51/reports/ir?customer_id=CCCCCCC"
                "&requestor_id=RRRRRRR&api_key=AAAAAAAA"
            )
            assert attempt.used_url.startswith(url)

            cr2c.refresh_from_db()
            assert cr2c.is_broken() is False, "The report should not be broken before import"

            import_one_sushi_attempt(attempt)
            attempt.refresh_from_db()
            cr2c.refresh_from_db()
            assert cr2c.is_broken() == breaks_report

    def test_c51_ir_title_and_item_data_types(self, counter_report_types, organizations, platforms):
        """
        Test that when importing IR reports with title and item data types are properly set -
        the title should be set from the title data, the item should be set from the usage data.
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=51
        )
        crt = counter_report_types["ir51"]
        CounterReportsToCredentials.objects.create(credentials=credentials, counter_report=crt)

        with (
            Path(__file__).parent / "data/counter51/IR_sample_r51_no-missing-parent.json"
        ).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.json"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=credentials,
            counter_report=crt,
            start_date="2022-01-01",
            end_date="2022-01-31",
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.SUCCESS
        t1 = Title.objects.get(name="Title 1")
        assert t1.pub_type == Title.PUB_TYPE_BOOK
        i1 = Item.objects.get(name="Item 3")
        assert i1.pub_type == Item.PUB_TYPE_BOOK_SEGMENT

    def test_user_agent(
        self, counter_report_types, organizations, platforms, settings, monkeypatch
    ):
        """Tests whether HTTP User-Agent is properly set"""
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            url="https://example.com/sushi/",
            customer_id="CCCCCCC",
            requestor_id="RRRRRRR",
            api_key="AAAAAAAA",
        )
        crt = counter_report_types["tr"]
        CounterReportsToCredentials.objects.create(credentials=credentials, counter_report=crt)

        settings.HARVESTER_USER_AGENT = "My-Agent 1.0"

        res = {}

        def get_handler(self, *args, **kwargs):
            res["agent_matches"] = self.headers["User-Agent"] == "My-Agent 1.0"

        monkeypatch.setattr(requests.Session, "get", get_handler)

        credentials.fetch_report(crt, start_date="2016-01-01", end_date="2016-01-31")

        assert res["agent_matches"]
