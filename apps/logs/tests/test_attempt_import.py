import pytest

from pathlib import Path
from django.core.files.base import ContentFile

from core.models import UL_ORG_ADMIN
from organizations.tests.conftest import organizations
from sushi.tests.conftest import counter_report_type_named
from sushi.models import SushiFetchAttempt, SushiCredentials

from ..logic.attempt_import import import_one_sushi_attempt


@pytest.mark.django_db
class TestAttemptImport:
    """
    Test functionality for import attempts
    """

    def test_counter4_import(self, organizations, counter_report_type_named, platform):
        counter_report_type = counter_report_type_named('BR2', version=4)

        credentials = SushiCredentials.objects.create(
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
            credentials=credentials,
            counter_report=counter_report_type,
            start_date="2018-01-01",
            end_date="2018-12-31",
            data_file=data_file,
            credentials_version_hash=credentials.compute_version_hash(),
        )

        import_one_sushi_attempt(fetch_attempt)

        assert fetch_attempt.import_crashed is False
        assert fetch_attempt.import_batch is not None
        assert fetch_attempt.import_batch.accesslog_set.count() == 60
