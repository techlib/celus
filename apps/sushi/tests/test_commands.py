import os
import pytest
import pathlib

from datetime import timedelta, datetime

from django.core.files import File
from django.core.management import call_command
from django.utils.timezone import now

from core.models import UL_ORG_ADMIN
from sushi.models import SushiCredentials, SushiFetchAttempt

from test_fixtures.entities.fetchattempts import FetchAttemptFactory


@pytest.mark.django_db
class TestFindMissingAttemptFiles:
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
            file_size=2,
            checksum="foobarbaz",
        )
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            file_size=0,
            checksum="0",
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
            file_size=2,
            checksum="foobarbaz",
        )
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            file_size=0,
            checksum="0",
        )
        assert SushiFetchAttempt.objects.count() == 2
        call_command(self.COMMAND_NAME, '-d')
        assert SushiFetchAttempt.objects.count() == 1


@pytest.mark.django_db
class TestRemoveOrphanedFiles:
    """
    Tests the `remove_orphaned_files` management command
    """

    COMMAND_NAME = 'remove_orphaned_files'

    @pytest.fixture(scope="function")
    def scenario(self, tmpdir, settings):
        media_dir = pathlib.Path(tmpdir.mkdir("media"))
        settings.MEDIA_ROOT = media_dir

        def prepare_file(path, mod_time, attempt):
            path = media_dir / path
            mtime = mod_time.timestamp()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as f:
                f.write("data")
            os.utime(path, (mtime, mtime))
            if attempt:
                FetchAttemptFactory(data_file=str(path))

        # old file to be deleted
        prepare_file(
            "counter/AA-1234/AAA/5_TR_20200101-111111.222222.json", datetime(2020, 1, 1), False
        )
        # file which should not be deleted
        prepare_file("counter/AA-1234/AAA/5_TR_XXXXXXXX-333333.444444.json", now(), False)

        # file which may be deleted
        prepare_file(
            "counter/BB-4567/BBB/5_TR_YYYYYYYY-555555.666666.json",
            now() - timedelta(days=15),
            False,
        )

        # File with attempts should never be deleted
        prepare_file(
            "counter/AA-1234/AAA/5_TR_20200101-777777.888888.json", datetime(2020, 1, 1), True
        )
        prepare_file("counter/AA-1234/AAA/5_TR_XXXXXXXX-999999.000000.json", now(), True)
        prepare_file(
            "counter/BB-4567/BBB/5_TR_YYYYYYYY-111111.000000.json", now() - timedelta(days=15), True
        )

        yield media_dir

    def test_30_day_commit(self, scenario):
        media_dir = scenario
        call_command(self.COMMAND_NAME, '--older-than', '30', '--do-it')
        assert not (media_dir / "counter/AA-1234/AAA/5_TR_20200101-111111.222222.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-333333.444444.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-555555.666666.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-777777.888888.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-999999.000000.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-111111.000000.json").exists()

    def test_30_day_nocommit(self, scenario):
        media_dir = scenario
        call_command(self.COMMAND_NAME, '--older-than', '30')
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-111111.222222.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-333333.444444.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-555555.666666.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-777777.888888.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-999999.000000.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-111111.000000.json").exists()

    def test_1_day_commit(self, scenario):
        media_dir = scenario
        call_command(self.COMMAND_NAME, '--older-than', '1', '--do-it')
        assert not (media_dir / "counter/AA-1234/AAA/5_TR_20200101-111111.222222.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-333333.444444.json").exists()
        assert not (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-555555.666666.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-777777.888888.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-999999.000000.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-111111.000000.json").exists()

    def test_1_day_nocommit(self, scenario):
        media_dir = scenario
        call_command(self.COMMAND_NAME, '--older-than', '1')
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-111111.222222.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-333333.444444.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-555555.666666.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_20200101-777777.888888.json").exists()
        assert (media_dir / "counter/AA-1234/AAA/5_TR_XXXXXXXX-999999.000000.json").exists()
        assert (media_dir / "counter/BB-4567/BBB/5_TR_YYYYYYYY-111111.000000.json").exists()
