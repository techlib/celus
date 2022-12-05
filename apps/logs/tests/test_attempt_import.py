from pathlib import Path
from unittest.mock import patch

import pytest

from core.logic.dates import month_end, parse_date
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from django.db.models import Sum
from sushi.models import SushiCredentials, SushiFetchAttempt, AttemptStatus
from sushi.tests.conftest import counter_report_type, counter_report_type_named  # noqa
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.scenarios.basic import (
    data_sources,
    organizations,
    platforms,
    counter_report_types,
    report_types,
)  # noqa

from ..models import Metric
from ..logic.attempt_import import import_one_sushi_attempt, check_importable_attempt
from ..exceptions import UnknownMetric


@pytest.mark.django_db
class TestAttemptImport:
    """
    Test functionality for import attempts
    """

    @pytest.mark.parametrize(['hash_matches'], [(True,), (False,)])
    def test_counter4_br2_import(
        self, organizations, counter_report_type_named, platforms, hash_matches
    ):
        cr_type = counter_report_type_named('BR2', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=4,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        correct_checkum = 'c6135b6b06065a572e18c3cf8a8b4ab643d906385c8cc10fcdd120a4e798d4d8'
        with (Path(__file__).parent / "data/counter4/counter4_br2_one_month.tsv").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = f"something.tsv"

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-02-01",
            end_date="2018-02-28",
            data_file=data_file,
            file_size=1285,
            checksum=correct_checkum if hash_matches else 'foobarbaz',
            credentials_version_hash=creds.compute_version_hash(),
            status=AttemptStatus.IMPORTING,
        )

        with patch('core.models.SourceFileMixin._send_error_mail') as mail_mock:
            import_one_sushi_attempt(fetch_attempt)

        if hash_matches:
            assert fetch_attempt.status == AttemptStatus.SUCCESS
            assert fetch_attempt.import_batch.accesslog_set.count() == 5
            assert not mail_mock.called, 'email to admin was not sent'
        else:
            assert fetch_attempt.status == AttemptStatus.IMPORT_FAILED
            assert fetch_attempt.import_batch is None
            assert mail_mock.called, 'email to admin was sent'

    def test_counter4_jr2_import(self, organizations, counter_report_type_named, platforms):
        cr_type = counter_report_type_named('JR2', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=4,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter4/4_JR2_denials.tsv").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = "something.tsv"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.SUCCESS
        assert fetch_attempt.import_batch.accesslog_set.count() == 2
        assert fetch_attempt.import_batch.accesslog_set.aggregate(total=Sum('value'))['total'] == 5

    def test_counter4_jr1_empty_import(self, organizations, counter_report_type_named, platforms):
        cr_type = counter_report_type_named('JR1', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=4,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter4/counter4_jr1_empty.tsv").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = f"something.tsv"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2020-01-01",
            end_date="2020-01-31",
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.NO_DATA

    @pytest.mark.parametrize(
        "status, passed",
        (
            (AttemptStatus.INITIAL, False),
            (AttemptStatus.DOWNLOADING, False),
            (AttemptStatus.IMPORTING, True),
            (AttemptStatus.SUCCESS, False),
            (AttemptStatus.UNPROCESSED, True),
            (AttemptStatus.NO_DATA, False),
            (AttemptStatus.IMPORT_FAILED, False),
            (AttemptStatus.PARSING_FAILED, False),
            (AttemptStatus.DOWNLOAD_FAILED, False),
            (AttemptStatus.CANCELED, False),
        ),
    )
    def test_import_precondition_error(
        self, status, passed, counter_report_type, organizations, platforms,
    ):

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=counter_report_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=ContentFile('{}', name="something.tsv"),
            file_size=2,
            checksum='235f39119e6330a32dca23b58e651fcc477c1918f75a100093eee91cf3e9f345',
            credentials_version_hash=creds.compute_version_hash(),
            status=status,
        )

        if passed:
            check_importable_attempt(fetch_attempt)
        else:
            with pytest.raises(ValueError):
                check_importable_attempt(fetch_attempt)

    def test_counter5_tr_warning(self, organizations, counter_report_type_named, platforms):
        cr_type = counter_report_type_named('TR', version=5)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter5/5_TR_with_warning.json").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = "something.json"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-11-01",
            end_date="2018-11-30",
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.SUCCESS
        assert fetch_attempt.import_batch.accesslog_set.count() == 8
        assert (
            fetch_attempt.log
            == "Warnings: Warning #3032: Usage No Longer Available for Requested Dates"
        )

    @pytest.mark.parametrize(
        ['filename', 'start_date', 'expected', 'status'],
        [
            (
                '5_TR_ProQuestEbookCentral.json',
                '2019-11-01',
                {
                    'Institution_Name': 'Hidden',
                    'Institution_ID': [{"Type": "Proprietary", "Value": "EBC:hidden"}],
                    'Created_By': 'ProQuest Ebook Central',
                },
                AttemptStatus.SUCCESS,
            ),
            (
                '5_TR_ProQuestEbookCentral_exception.json',
                '2017-01-01',
                {
                    "Institution_Name": "Hidden",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "EBC:hidden"}],
                    "Created_By": "ProQuest Ebook Central",
                },
                AttemptStatus.IMPORT_FAILED,
            ),
            (
                '5_TR_with_warning.json',
                '2018-11-01',
                {
                    "Created_By": "Someone",
                    "Institution_Name": "My Institution",
                    "Institution_ID": [{"Type": "Proprietary", "Value": "XXX:9999999"}],
                },
                AttemptStatus.SUCCESS,
            ),
        ],
    )
    def test_counter5_extracted_data(
        self,
        organizations,
        counter_report_type_named,
        platforms,
        filename,
        start_date,
        expected,
        status,
    ):
        cr_type = counter_report_type_named('TR', version=5)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / f"data/counter5/{filename}").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = "something.json"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=creds,
            counter_report=cr_type,
            start_date=start_date,
            end_date=month_end(parse_date(start_date)),
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == status, 'check status'
        assert fetch_attempt.extracted_data == expected, 'check extracted_data matches'

    @pytest.mark.parametrize(
        "autocreate", (True, False),
    )
    def test_auto_create_metrics(
        self, organizations, counter_report_types, platforms, autocreate, settings
    ):
        settings.AUTOMATICALLY_CREATE_METRICS = autocreate

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter5/C5_PR_test.json").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = f"C5_PR_test.json"

        fetch_attempt = FetchAttemptFactory.create(
            credentials=creds,
            counter_report=counter_report_types["pr"],
            start_date="2019-04-01",
            end_date="2019-04-30",
            data_file=data_file,
            status=AttemptStatus.IMPORTING,
        )

        if autocreate:
            metric_count = Metric.objects.count()
            import_one_sushi_attempt(fetch_attempt)
            assert metric_count + 7 == Metric.objects.count(), "7 new metrics created"
        else:
            metric_count = Metric.objects.count()
            with pytest.raises(UnknownMetric):
                import_one_sushi_attempt(fetch_attempt)
            assert metric_count == Metric.objects.count(), "no new metric created"
