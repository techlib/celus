from pathlib import Path

import pytest
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from django.db.models import Sum
from sushi.models import SushiCredentials, SushiFetchAttempt, AttemptStatus
from sushi.tests.conftest import counter_report_type, counter_report_type_named  # noqa
from test_fixtures.scenarios.basic import data_sources, organizations, platforms  # noqa

from ..logic.attempt_import import import_one_sushi_attempt, check_importable_attempt


@pytest.mark.django_db
class TestAttemptImport:
    """
    Test functionality for import attempts
    """

    def test_counter4_br2_import(self, organizations, counter_report_type_named, platforms):
        cr_type = counter_report_type_named('BR2', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=4,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter4/counter4_br2.tsv").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = f"something.tsv"

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=data_file,
            credentials_version_hash=creds.compute_version_hash(),
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.SUCCESS
        assert fetch_attempt.import_batch.accesslog_set.count() == 60

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

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=data_file,
            credentials_version_hash=creds.compute_version_hash(),
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

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2020-01-01",
            end_date="2020-01-31",
            data_file=data_file,
            credentials_version_hash=creds.compute_version_hash(),
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
            (AttemptStatus.CREDENTIALS_BROKEN, False),
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

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-11-01",
            end_date="2018-11-30",
            data_file=data_file,
            credentials_version_hash=creds.compute_version_hash(),
            status=AttemptStatus.IMPORTING,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.status == AttemptStatus.SUCCESS
        assert fetch_attempt.import_batch.accesslog_set.count() == 12
        assert (
            fetch_attempt.log
            == "Warnings: Warning #3032: Usage No Longer Available for Requested Dates"
        )
