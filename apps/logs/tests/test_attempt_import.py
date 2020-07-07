import pytest

from pathlib import Path
from django.core.files.base import ContentFile
from django.db.models import Sum

from core.models import UL_ORG_ADMIN
from organizations.tests.conftest import organizations
from publications.tests.conftest import platforms
from sushi.tests.conftest import counter_report_type_named, credentials, counter_report_type
from sushi.models import SushiFetchAttempt, SushiCredentials

from ..logic.attempt_import import import_one_sushi_attempt


@pytest.mark.django_db
class TestAttemptImport:
    """
    Test functionality for import attempts
    """

    def test_counter4_br2_import(self, organizations, counter_report_type_named, platform):
        cr_type = counter_report_type_named('BR2', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platform,
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
            download_success=True,
            is_processed=False,
            import_crashed=False,
            contains_data=True,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.import_crashed is False
        assert fetch_attempt.import_batch is not None
        assert fetch_attempt.import_batch.accesslog_set.count() == 60

    def test_counter4_jr2_import(self, organizations, counter_report_type_named, platform):
        cr_type = counter_report_type_named('JR2', version=4)

        creds = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platform,
            counter_version=4,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )

        with (Path(__file__).parent / "data/counter4/4_JR2_denials.tsv").open() as f:

            data_file = ContentFile(f.read())
            data_file.name = f"something.tsv"

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=creds,
            counter_report=cr_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=data_file,
            credentials_version_hash=creds.compute_version_hash(),
            download_success=True,
            is_processed=False,
            import_crashed=False,
            contains_data=True,
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.import_crashed is False
        assert fetch_attempt.import_batch is not None
        assert fetch_attempt.import_batch.accesslog_set.count() == 2
        assert fetch_attempt.import_batch.accesslog_set.aggregate(total=Sum('value'))['total'] == 5

    @pytest.mark.parametrize(
        "download_success,is_processed,contains_data,import_crashed",
        (
            (False, False, True, False),
            (True, True, True, False),
            (True, False, False, False),
            (True, False, True, True),
        ),
    )
    def test_import_precondition_error(
        self,
        download_success,
        is_processed,
        contains_data,
        import_crashed,
        credentials,
        counter_report_type,
    ):
        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=None,
            credentials_version_hash=credentials.compute_version_hash(),
            download_success=download_success,
            is_processed=is_processed,
            contains_data=contains_data,
            import_crashed=import_crashed,
        )

        with pytest.raises(ValueError):
            import_one_sushi_attempt(fetch_attempt)
