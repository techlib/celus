import pytest
from django.core.management import call_command

from core.models import UL_ORG_ADMIN
from sushi.models import SushiCredentials, SushiFetchAttempt


@pytest.mark.now
@pytest.mark.django_db
class TestFindMissingAttemptFiles(object):
    """
    Tests the `find_missing_attempt_files` management command
    """

    COMMAND_NAME = 'find_missing_attempt_files'

    def test_no_delete(self, credentials, counter_report_type_named):
        """
        Test without deleting anything
        """
        new_rt1 = counter_report_type_named('new1')
        # the following will have the file missing
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            data_file='test/file.txt',
        )
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 2
        call_command(self.COMMAND_NAME)
        assert SushiFetchAttempt.objects.count() == 2

    def test_delete(self, credentials, counter_report_type_named):
        """
        Test this deleting the attempt with missing file
        """
        new_rt1 = counter_report_type_named('new1')
        # the following will have the file missing
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            data_file='test/file.txt',
        )
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 2
        call_command(self.COMMAND_NAME, '-d')
        assert SushiFetchAttempt.objects.count() == 1
