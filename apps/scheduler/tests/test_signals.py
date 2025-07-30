from datetime import date, datetime

import pytest
from django.utils import timezone
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory
from sushi.fake_data import FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiCredentials

from scheduler.fake_data import FetchIntentionFactory
from scheduler.models import Automatic, FetchIntention, Harvest
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    credentials,
    data_sources,
    organizations,
    platforms,
    report_types,
    verified_credentials,
)

current_tz = timezone.get_current_timezone()


@pytest.mark.django_db
class TestCredentialsSignals:
    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_credentials_signals(
        self, counter_report_types, credentials, verified_credentials, monkeypatch
    ):
        """Test whether automatic harvests are update when
        credentials or credentials to counter report mapping
        changes
        """
        # Clear all harvests
        Harvest.objects.all().delete()

        start_date = date(2020, 1, 1)

        assert FetchIntention.objects.all().count() == 0
        assert Automatic.objects.all().count() == 0

        # Mock successful report fetching
        def mocked_fetch_report_v5(self, client, counter_report, start_date, end_date, file_data):
            return FetchAttemptFactory.build(
                credentials=credentials["branch_pr"],
                counter_report=counter_report,
                start_date=start_date,
                end_date=end_date,
                status=AttemptStatus.IMPORTING,
                data_file=None,
                checksum="",
                when_processed=timezone.now(),
                http_status_code=200,
            )

        monkeypatch.setattr(SushiCredentials, "_fetch_report_v5", mocked_fetch_report_v5)
        credentials["branch_pr"].fetch_report(
            counter_report_types["pr"], date(2019, 1, 1), date(2019, 1, 31)
        )

        assert FetchIntention.objects.all().count() == 1
        assert Automatic.objects.all().count() == 1
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Altering credentials should cause it to be disabled
        credentials["branch_pr"].customer_id += "X"
        credentials["branch_pr"].save()
        assert FetchIntention.objects.all().count() == 1
        assert Automatic.objects.all().count() == 1
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Save credentials to its previous version should enable automatic again
        credentials["branch_pr"].customer_id = credentials["branch_pr"].customer_id[:-1]
        credentials["branch_pr"].save()
        assert Automatic.objects.all().count() == 1
        automatic_branch = Automatic.objects.first()
        assert automatic_branch.harvest.intentions.count() == 1
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        credentials["standalone_br1_jr1"].save()
        assert Automatic.objects.all().count() == 2
        automatic_standalone = Automatic.objects.order_by("pk").last()
        assert automatic_standalone.harvest.intentions.count() == 2
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Test that no intention is created when there are some clashing data
        ImportBatchFactory(
            report_type=counter_report_types["tr"].report_type,
            organization=credentials["standalone_tr"].organization,
            platform=credentials["standalone_tr"].platform,
            date=date(2019, 12, 1),  # prev month
        )
        credentials["standalone_tr"].save()
        assert (
            automatic_standalone.harvest.intentions.count() == 2
        ), "No intentions is created - clashing data"

        # Create new mapping
        new_mapping = CounterReportsToCredentials.objects.create(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["tr"],
            broken=None,
        )
        assert FetchIntention.objects.all().count() == 4
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Set credentials broken
        credentials["branch_pr"].set_broken(
            FetchAttemptFactory(
                counter_report=counter_report_types["tr"], credentials=credentials["branch_pr"]
            ),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )
        assert automatic_branch.harvest.intentions.count() == 0

        # Unset credentials broken
        credentials["branch_pr"].unset_broken()
        assert automatic_branch.harvest.intentions.count() == 2
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Unset credentials enabled
        credentials["branch_pr"].enabled = False
        credentials["branch_pr"].save()
        assert automatic_branch.harvest.intentions.count() == 0

        # Set credentials enabled
        credentials["branch_pr"].enabled = True
        credentials["branch_pr"].save()
        assert automatic_branch.harvest.intentions.count() == 2
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Set broken mapping
        new_mapping.set_broken(
            FetchAttemptFactory(
                counter_report=counter_report_types["tr"], credentials=credentials["branch_pr"]
            ),
            broken_type=SushiCredentials.BROKEN_SUSHI,
        )
        assert automatic_branch.harvest.intentions.count() == 1

        # Unset broken mapping
        new_mapping.unset_broken()
        assert automatic_branch.harvest.intentions.count() == 2
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Remove mapping
        new_mapping.delete()
        assert automatic_branch.harvest.intentions.count() == 1

        # Remove credentials
        assert automatic_standalone.harvest.intentions.count() == 2
        credentials["standalone_br1_jr1"].delete()
        assert automatic_standalone.harvest.intentions.count() == 0
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_credentials_signals_with_retry_chains(
        self, counter_report_types, credentials, verified_credentials
    ):
        # Clear all harvests
        Harvest.objects.all().delete()

        def mock_3031(intention: FetchIntention):
            intention.attempt = FetchAttemptFactory(
                start_date=intention.start_date,
                end_date=intention.end_date,
                credentials=credentials["standalone_tr"],
                error_code="3031",
                status=AttemptStatus.NO_DATA,
                import_batch=None,
            )
            intention.when_processed = timezone.now()
            intention.save()

        # And delete some credentials
        credentials["standalone_br1_jr1"].delete()
        credentials["branch_pr"].delete()

        assert FetchIntention.objects.all().count() == 0
        assert Automatic.objects.all().count() == 0

        # Trigger signal (update credentials)
        credentials["standalone_tr"].save()

        assert FetchIntention.objects.all().count() == 1
        assert Automatic.objects.all().count() == 1

        fi = FetchIntention.objects.order_by("pk").last()
        mock_3031(fi)
        fi.refresh_from_db()

        # Plan new one
        fi.get_handler()()
        assert FetchIntention.objects.all().count() == 2

        # Make credentials broken
        credentials["standalone_tr"].set_broken(
            FetchAttemptFactory(
                counter_report=counter_report_types["tr"], credentials=credentials["standalone_tr"]
            ),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )
        assert FetchIntention.objects.all().count() == 1

        fi.refresh_from_db()
        assert fi.queue.start == fi, "fi is first in queue"
        assert fi.queue.end is None, "last in queue was deleted"

        # Now unset broken
        credentials["standalone_tr"].unset_broken()

        assert FetchIntention.objects.all().count() == 2

        fi.refresh_from_db()
        assert fi.queue.start == fi, "fi is first in queue"
        assert fi.queue.end is not None, "queue is complete"
        assert fi.queue.end != fi, "new fi at the end of the line"
        assert fi.queue.end.when_processed is None, "last is not finished"

    @pytest.mark.parametrize(["retry_count", "has_ib"], [(0, False), (2, False), (10, True)])
    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_credentials_signals_with_no_error_code(
        self, counter_report_types, credentials, verified_credentials, retry_count, has_ib
    ):
        # Clear all harvests
        Harvest.objects.all().delete()

        # And delete some credentials
        credentials["standalone_br1_jr1"].delete()
        credentials["branch_pr"].delete()

        assert FetchIntention.objects.all().count() == 0
        assert Automatic.objects.all().count() == 0

        # Trigger signal (update credentials)
        credentials["standalone_tr"].save()

        assert FetchIntention.objects.all().count() == 1
        assert Automatic.objects.all().count() == 1

        # Prepare attempt
        fi = FetchIntention.objects.order_by("pk").last()
        fi.data_not_ready_retry = retry_count
        fi.save()
        fi.attempt = FetchAttemptFactory(
            start_date=fi.start_date,
            end_date=fi.end_date,
            credentials=credentials["standalone_tr"],
            error_code="",
            status=AttemptStatus.NO_DATA,
            import_batch=None,
        )
        fi.when_processed = timezone.now()
        fi.save()

        fi.get_handler()()
        fi.refresh_from_db()

        if has_ib:
            assert FetchIntention.objects.all().count() == 1, "FI is updated"
            assert fi.attempt.import_batch is not None
        else:
            assert FetchIntention.objects.all().count() == 2, "new FI is created"
            assert fi.attempt.import_batch is None


@pytest.mark.django_db
class TestFetchIntentionSignals:
    def test_fill_in_queue(self):
        """Test that a queue is linked to FetchIntention
        when the intention is created
        """
        # test create
        intention = FetchIntentionFactory()
        assert intention.queue is not None
