import typing
import uuid

from datetime import datetime, timedelta, date

from django.utils import timezone

import pytest

from freezegun import freeze_time

from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory, HarvestFactory, SchedulerFactory
from test_fixtures.scenarios.basic import (
    counter_report_types,
    report_types,
    credentials,
    platforms,
    import_batches,
    organizations,
    data_sources,
    users,
    harvests,
    schedulers,
)

from logs.tasks import import_one_sushi_attempt_task
from nigiri.error_codes import ErrorCode
from scheduler import tasks
from scheduler.models import (
    Automatic,
    FetchIntention,
    Harvest,
    ProcessResponse,
    RunResponse,
    Scheduler,
)
from scheduler import signals
from sushi.models import SushiCredentials, CounterReportsToCredentials
from sushi.tasks import import_one_sushi_attempt_task
from nigiri.error_codes import ErrorCode


current_tz = timezone.get_current_timezone()


@pytest.mark.django_db
class TestFetchIntention:
    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_next_exponential(self):
        assert FetchIntention.next_exponential(0, 30) == (
            datetime(2020, 1, 1, 0, 0, 30, 0, tzinfo=current_tz),
            False,
        )
        assert FetchIntention.next_exponential(0, 30, max_delay=20) == (
            datetime(2020, 1, 1, 0, 0, 20, 0, tzinfo=current_tz),
            True,
        )
        assert FetchIntention.next_exponential(1, 30) == (
            datetime(2020, 1, 1, 0, 1, 0, 0, tzinfo=current_tz),
            False,
        )
        assert FetchIntention.next_exponential(1, 30, max_delay=50) == (
            datetime(2020, 1, 1, 0, 0, 50, 0, tzinfo=current_tz),
            True,
        )
        assert FetchIntention.next_exponential(1, 30, max_delay=70) == (
            datetime(2020, 1, 1, 0, 1, 0, 0, tzinfo=current_tz),
            False,
        )
        assert FetchIntention.next_exponential(2, 20) == (
            datetime(2020, 1, 1, 0, 1, 20, 0, tzinfo=current_tz),
            False,
        )
        assert FetchIntention.next_exponential(2, 20, max_delay=80) == (
            datetime(2020, 1, 1, 0, 1, 20, 0, tzinfo=current_tz),
            True,
        )

    def test_already_processed(self):
        sch = SchedulerFactory()

        when_processed = datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz)
        fi = FetchIntentionFactory(when_processed=when_processed, scheduler=sch)
        assert fi.process() == ProcessResponse.ALREADY_PROCESSED
        assert when_processed == fi.when_processed

    def test_process_broken(self, counter_report_types):
        sch = SchedulerFactory()

        # credentials broken
        creds1 = CredentialsFactory()
        creds1.set_broken(
            FetchAttemptFactory(counter_report=counter_report_types["tr"], credentials=creds1),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )
        CounterReportsToCredentials.objects.create(
            broken=None, credentials=creds1, counter_report=counter_report_types["tr"]
        )
        fi1 = FetchIntentionFactory(
            credentials=creds1, scheduler=sch, counter_report=counter_report_types["tr"],
        )
        assert fi1.process() == ProcessResponse.BROKEN

        # missing mapping
        creds2 = CredentialsFactory(broken=None)
        fi2 = FetchIntentionFactory(
            credentials=creds2, scheduler=sch, counter_report=counter_report_types["tr"]
        )
        assert fi2.process() == ProcessResponse.BROKEN

        # mapping broken
        creds3 = CredentialsFactory(broken=SushiCredentials.BROKEN_HTTP)
        CounterReportsToCredentials.objects.create(
            broken=SushiCredentials.BROKEN_SUSHI,
            credentials=creds3,
            counter_report=counter_report_types["tr"],
        )
        fi3 = FetchIntentionFactory(
            credentials=creds3, scheduler=sch, counter_report=counter_report_types["tr"]
        )
        assert fi3.process() == ProcessResponse.BROKEN

    def test_process_without_scheduler(self):
        fi = FetchIntentionFactory(when_processed=None, scheduler=None, attempt=None)
        with pytest.raises(ValueError):
            fi.process()

    def test_process_with_planned_duplicates(
        self, counter_report_types, credentials, monkeypatch,
    ):
        scheduler = SchedulerFactory()

        def mocked_fetch_report(
            self, counter_report, start_date, end_date, fetch_attemp=None, use_url_lock=True,
        ):
            return FetchAttemptFactory(
                error_code="",
                credentials=self,
                counter_report=counter_report,
                start_date=start_date,
                end_date=end_date,
                contains_data=True,
                is_processed=False,
                download_success=True,
                import_crashed=False,
            )

        monkeypatch.setattr(SushiCredentials, 'fetch_report', mocked_fetch_report)
        monkeypatch.setattr(import_one_sushi_attempt_task, 'delay', lambda x: None)

        fi1 = FetchIntentionFactory(
            not_before=timezone.now() - timedelta(minutes=1),
            scheduler=scheduler,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
        )
        fi2 = FetchIntentionFactory(
            not_before=timezone.now() + timedelta(minutes=1),
            scheduler=scheduler,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
        )
        assert fi1.process() == ProcessResponse.SUCCESS
        fi2.refresh_from_db()
        assert fi2.duplicate_of == fi1
        assert fi2.process() == ProcessResponse.DUPLICATE

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    @pytest.mark.parametrize(
        "error_code,seconds_not_before,seconds_when_ready",
        (
            ("", 0, 0),
            (ErrorCode.SERVICE_NOT_AVAILABLE.value, 20 * 2 ** 3, 20 * 2 ** 3),
            (ErrorCode.SERVICE_BUSY.value, 30 * 2 ** 4, 30 * 2 ** 4),
            (ErrorCode.PREPARING_DATA.value, 30 * 2 ** 4, 30 * 2 ** 4),
            (ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value, 60 * 60 * 24 * 2 ** 2, 0),
            (ErrorCode.NO_DATA_FOR_DATE_ARGS.value, 60 * 60 * 24 * 2 ** 2, 0),
            (ErrorCode.TOO_MANY_REQUESTS.value, 10, 10),
        ),
        ids=(
            "SUCCESS",
            ErrorCode.SERVICE_NOT_AVAILABLE.name,
            ErrorCode.SERVICE_BUSY.name,
            ErrorCode.PREPARING_DATA.name,
            ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.name,
            ErrorCode.NO_DATA_FOR_DATE_ARGS.name,
            ErrorCode.TOO_MANY_REQUESTS.name,
        ),
    )
    def test_process(
        self,
        error_code,
        seconds_not_before,
        seconds_when_ready,
        monkeypatch,
        counter_report_types,
        credentials,
        users,
    ):
        error_code = str(error_code)
        sch = SchedulerFactory(
            cooldown=0,
            too_many_requests_delay=10,
            service_not_available_delay=20,
            service_busy_delay=30,
        )

        def mocked_fetch_report(
            self, counter_report, start_date, end_date, fetch_attemp=None, use_url_lock=True,
        ):
            return FetchAttemptFactory(
                error_code=error_code,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, 'fetch_report', mocked_fetch_report)

        fi = FetchIntentionFactory(
            not_before=timezone.now(),
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            data_not_ready_retry=2,
            service_not_available_retry=3,
            service_busy_retry=4,
            harvest__last_updated_by=users["user1"],
        )
        assert fi.process() == ProcessResponse.SUCCESS
        assert fi.attempt.triggered_by == users["user1"]
        assert fi.when_processed == datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz)

        # test not_before for newly created FetchIntentions
        last = FetchIntention.objects.order_by('pk').last()
        if seconds_not_before:
            assert last.pk != fi.pk
            assert (last.not_before - fi.not_before).total_seconds() == seconds_not_before
            assert last.queue_id == fi.pk
            assert fi.queue_id == fi.pk
            assert fi.attempt.queue_id == fi.pk
        else:
            assert last.pk == fi.pk

        # test scheduler's when_ready updates
        assert sch.when_ready == datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz) + timedelta(
            seconds=seconds_when_ready
        )

    def test_schedulers_to_trigger(self, credentials, counter_report_types):
        old_sch = SchedulerFactory(
            when_ready=timezone.now() + timedelta(minutes=1), url=credentials["standalone_tr"].url
        )
        FetchIntentionFactory(
            not_before=timezone.now(),
            scheduler=None,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            data_not_ready_retry=2,
            service_not_available_retry=3,
            service_busy_retry=4,
        )

        FetchIntentionFactory(
            not_before=timezone.now() + timedelta(minutes=1),
            scheduler=None,
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            data_not_ready_retry=2,
            service_not_available_retry=3,
            service_busy_retry=4,
        )
        FetchIntentionFactory(
            not_before=timezone.now() - timedelta(minutes=1),
            scheduler=None,
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            data_not_ready_retry=2,
            service_not_available_retry=3,
            service_busy_retry=4,
        )

        to_trigger = FetchIntention.objects.schedulers_to_trigger()

        # Created scheduler
        new_sch = Scheduler.objects.order_by('pk').last()

        assert len(to_trigger) == 1
        assert to_trigger[0] == new_sch

        # adding FetchIntention with higher priority for old_sch
        FetchIntentionFactory(
            not_before=timezone.now(),
            scheduler=None,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            priority=FetchIntention.PRIORITY_NOW,
        )
        assert {new_sch.pk, old_sch.pk} == {
            e.pk for e in FetchIntention.objects.schedulers_to_trigger()
        }

    @pytest.mark.parametrize(
        "error_code,delays",
        (
            (
                ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value,
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=16),
                    timedelta(days=32),
                    timedelta(days=64),
                    None,
                ],
            ),
            (
                ErrorCode.NO_DATA_FOR_DATE_ARGS.value,
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=16),
                    timedelta(days=32),
                    None,
                ],
            ),
        ),
        ids=("not_ready", "no_data",),
    )
    def test_process_retry_chain(
        self, credentials, counter_report_types, monkeypatch, error_code, delays, settings,
    ):
        settings.QUEUED_SUSHI_MAX_RETRY_COUNT = 7
        scheduler = SchedulerFactory(url=credentials["standalone_tr"].url)

        def mocked_fetch_report(
            self, counter_report, start_date, end_date, fetch_attemp=None, use_url_lock=True,
        ):

            return FetchAttemptFactory(
                error_code=error_code,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, 'fetch_report', mocked_fetch_report)

        def check_retry(fi: FetchIntention, expected: typing.Optional[datetime]) -> FetchIntention:
            with freeze_time(fi.not_before):
                fi.scheduler = scheduler
                assert fi.process() == ProcessResponse.SUCCESS
            new_fi = FetchIntention.objects.order_by('pk').last()
            assert new_fi is not None

            if expected:
                assert fi.pk != new_fi.pk, "new intention created"
                assert new_fi.not_before == expected, "new planned date matches"
            else:
                assert fi.pk == fi.pk, "no new intention created"

            return new_fi

        start = datetime(2020, 1, 2, 0, 0, 0, 0, tzinfo=current_tz)

        with freeze_time(start):
            fi = FetchIntentionFactory(
                not_before=timezone.now(),
                scheduler=scheduler,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                data_not_ready_retry=0,
                when_processed=None,
            )

        for delay in delays:
            fi = check_retry(fi, start + delay if delay else None)
            if delay:
                start += delay

    def test_fetching_data(self, credentials, counter_report_types):
        scheduler1 = SchedulerFactory(
            url=credentials["standalone_tr"].url,
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            current_celery_task_id=uuid.uuid4(),
        )
        intention1 = FetchIntentionFactory(
            not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
            scheduler=scheduler1,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            priority=FetchIntention.PRIORITY_NOW,
            when_processed=datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz),
        )
        scheduler1.current_intention = intention1
        scheduler1.current_start = datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz)
        scheduler1.save()
        assert intention1.fetching_data is True

        scheduler1.unassign_intention()
        intention1.refresh_from_db()

        assert intention1.fetching_data is False

    def test_queue_id(self, credentials, counter_report_types):
        sch = SchedulerFactory()
        hr = HarvestFactory()
        fi1 = FetchIntentionFactory.build(
            when_processed=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["jr1"],
            harvest=hr,
        )
        fi1.save()
        assert fi1.queue_id == fi1.pk
        fi2 = FetchIntentionFactory.build(
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            queue_id=fi1.queue_id,
            counter_report=counter_report_types["jr1"],
            harvest=hr,
        )
        fi2.save()
        assert fi2.queue_id == fi1.pk


@pytest.mark.django_db
class TestScheduler:
    def test_last_time(self, credentials, counter_report_types):
        scheduler = SchedulerFactory(url=credentials["standalone_br1_jr1"].url)
        assert scheduler.last_time is None

        FetchIntentionFactory(
            not_before=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            scheduler=scheduler,
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            when_processed=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
        )

        FetchIntentionFactory(
            not_before=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            scheduler=scheduler,
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            when_processed=datetime(2020, 2, 1, 0, 0, 0, tzinfo=current_tz),
        )

        assert scheduler.last_time == datetime(2020, 2, 1, 0, 0, 0, tzinfo=current_tz)

    def test_run_next(self, monkeypatch, credentials, counter_report_types):
        def mocked_fetch_report(
            self, counter_report, start_date, end_date, fetch_attemp=None, use_url_lock=True,
        ):
            return FetchAttemptFactory(
                error_code="",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, 'fetch_report', mocked_fetch_report)

        scheduler = SchedulerFactory(
            url=credentials["standalone_tr"].url,
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
        )

        with freeze_time("2020-01-01"):
            assert scheduler.run_next() == RunResponse.IDLE

            FetchIntentionFactory(
                not_before=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )
            assert scheduler.run_next() == RunResponse.PROCESSED
            assert scheduler.run_next() == RunResponse.COOLDOWN

        with freeze_time("2020-01-02"):
            # not fetch intention ready
            FetchIntentionFactory(
                not_before=datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )
            assert scheduler.run_next() == RunResponse.IDLE

            # Trigger immediatelly
            scheduler.when_ready = datetime(2020, 1, 5, 0, 0, 0, tzinfo=current_tz)
            scheduler.save()
            FetchIntentionFactory(
                not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )
            assert scheduler.run_next() == RunResponse.IDLE

            # Test broken
            credentials["standalone_tr"].set_broken(
                FetchAttemptFactory(
                    counter_report=counter_report_types["tr"],
                    credentials=credentials["standalone_tr"],
                ),
                broken_type=SushiCredentials.BROKEN_HTTP,
            )
            FetchIntentionFactory(
                not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                priority=FetchIntention.PRIORITY_NOW,
            )
            # broken should not be run
            assert scheduler.run_next() == RunResponse.IDLE

            # unbreak and process
            credentials["standalone_tr"].unset_broken()
            FetchIntentionFactory(
                not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                priority=FetchIntention.PRIORITY_NOW,
            )
            assert scheduler.run_next() == RunResponse.PROCESSED

    def test_unlock_stucked_schedulers(self, credentials, counter_report_types):

        scheduler1 = SchedulerFactory(
            url="https://scheduler1.example.com",
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            current_celery_task_id=uuid.uuid4(),
        )
        intention1 = FetchIntentionFactory(
            not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
            scheduler=scheduler1,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            priority=FetchIntention.PRIORITY_NOW,
            when_processed=datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz),
        )
        scheduler1.current_intention = intention1
        scheduler1.current_start = datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz)
        scheduler1.save()
        assert intention1.current_scheduler == scheduler1
        assert intention1.scheduler == scheduler1

        scheduler2 = SchedulerFactory(
            url="https://scheduler2.example.com",
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            current_celery_task_id=uuid.uuid4(),
        )
        intention2 = FetchIntentionFactory(
            not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
            scheduler=scheduler2,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            priority=FetchIntention.PRIORITY_NOW,
            when_processed=None,
        )
        scheduler2.current_intention = intention2
        scheduler2.current_start = datetime(2020, 1, 3, 0, 0, 0, tzinfo=current_tz)
        scheduler2.save()
        assert intention2.current_scheduler == scheduler2
        assert intention2.scheduler == scheduler2

        scheduler3 = SchedulerFactory(
            url="https://scheduler3.example.com",
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
            current_celery_task_id=uuid.uuid4(),
        )
        intention3 = FetchIntentionFactory(
            not_before=datetime.now(),
            scheduler=scheduler3,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            priority=FetchIntention.PRIORITY_NOW,
            when_processed=None,
        )
        scheduler3.current_intention = intention3
        scheduler3.current_start = timezone.now()
        scheduler3.save()
        assert intention3.current_scheduler == scheduler3
        assert intention3.scheduler == scheduler3

        Scheduler.unlock_stucked_schedulers()

        # First is unlocked
        scheduler1.refresh_from_db()
        intention1.refresh_from_db()
        assert scheduler1.current_intention is None
        assert scheduler1.current_start is None
        assert scheduler1.current_celery_task_id is None
        assert intention1.scheduler == scheduler1
        with pytest.raises(Scheduler.DoesNotExist):
            intention1.current_scheduler

        # Seconds is unlocked
        scheduler2.refresh_from_db()
        intention2.refresh_from_db()
        assert scheduler2.current_intention is None
        assert scheduler2.current_start is None
        assert scheduler2.current_celery_task_id is None
        assert intention2.scheduler is None
        with pytest.raises(Scheduler.DoesNotExist):
            intention2.current_scheduler

        # Third doesn't need to be unlocked
        scheduler3.refresh_from_db()
        intention3.refresh_from_db()
        assert scheduler3.current_intention == intention3
        assert scheduler3.current_start is not None
        assert scheduler3.current_celery_task_id is not None
        assert intention3.scheduler == scheduler3
        assert intention3.current_scheduler == scheduler3


@pytest.mark.django_db
class TestHarvest:
    @pytest.mark.django_db(transaction=True)
    def test_plan_harvesting(self, counter_report_types, credentials, monkeypatch, users):
        urls = set()

        def mocked_trigger_scheduler(
            url, fihish,
        ):
            urls.add(url)

        monkeypatch.setattr(tasks.trigger_scheduler, 'delay', mocked_trigger_scheduler)

        intentions = [
            FetchIntention(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["jr1"],
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 31),
            ),
            FetchIntention(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 31),
            ),
            FetchIntention(
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 31),
            ),
        ]
        harvest = Harvest.plan_harvesting(intentions)
        assert FetchIntention.objects.filter(harvest=harvest).count() == 3

        intentions = [
            FetchIntention(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["jr1"],
                start_date=date(2020, 2, 1),
                end_date=date(2020, 2, 29),
            ),
            FetchIntention(
                credentials=credentials["standalone_br1_jr1"],
                counter_report=counter_report_types["br1"],
                start_date=date(2020, 2, 1),
                end_date=date(2020, 2, 29),
            ),
            FetchIntention(
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                start_date=date(2020, 2, 1),
                end_date=date(2020, 2, 29),
            ),
        ]
        assert (
            Harvest.plan_harvesting(
                intentions,
                harvest=harvest,
                priority=FetchIntention.PRIORITY_NOW,
                user=users["user1"],
            )
            == harvest
        )
        assert harvest.last_updated_by == users["user1"]
        assert FetchIntention.objects.filter(harvest=harvest).count() == 6

        assert urls == {credentials["standalone_tr"].url, credentials["standalone_br1_jr1"].url}

    def test_stats(self, counter_report_types, credentials):
        harvest1 = HarvestFactory()
        harvest2 = HarvestFactory()
        harvest3 = HarvestFactory()
        harvest4 = HarvestFactory()
        harvest5 = HarvestFactory()

        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            harvest=harvest1,
            duplicate_of=None,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest1,
            duplicate_of=None,
        )

        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest2,
            duplicate_of=None,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=None,
            harvest=harvest2,
            duplicate_of=None,
            queue_id=1,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest2,
            duplicate_of=None,
            queue_id=1,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            harvest=harvest2,
            duplicate_of=None,
        )

        original_fi = FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest3,
            duplicate_of=None,
        )
        FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=None,
            harvest=harvest4,
            duplicate_of=original_fi,
        )

        assert harvest1.stats() == (1, 2)
        assert harvest2.stats() == (2, 3)
        assert harvest3.stats() == (0, 1)
        assert harvest4.stats() == (0, 1)
        assert harvest5.stats() == (0, 0)

        assert list(
            Harvest.objects.annotate_stats()
            .order_by('pk')
            .values_list('pk', 'unprocessed', 'total')
        ) == [
            (harvest1.pk, 1, 2),
            (harvest2.pk, 2, 3),
            (harvest3.pk, 0, 1),
            (harvest4.pk, 0, 1),
            (harvest5.pk, 0, 0),
        ]

    def test_latest_intentions(self, harvests):
        assert harvests["anonymous"].intentions.count() == 4
        assert harvests["anonymous"].latest_intentions.count() == 3
        assert harvests["user1"].intentions.count() == 2
        assert harvests["user1"].latest_intentions.count() == 2


@pytest.mark.django_db
class TestAutomatic:
    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_update_for_this_month(
        self, credentials, organizations, counter_report_types, disable_automatic_scheduling,
    ):
        start_date = date(2020, 2, 1)

        # all empty
        assert FetchIntention.objects.count() == 0
        assert Automatic.update_for_this_month() == {"added": 4, "deleted": 0}
        last = Automatic.objects.last()
        assert last.month == date(2020, 1, 1)
        assert last.harvest.intentions.count() == 1
        assert last.harvest.intentions.last().not_before.date() > start_date
        assert FetchIntention.objects.count() == 4
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # mark credentials broken
        credentials["branch_pr"].set_broken(
            attempt=FetchAttemptFactory(
                counter_report=counter_report_types["pr"], credentials=credentials["branch_pr"]
            ),
            broken_type=SushiCredentials.BROKEN_SUSHI,
        )

        # mark mapping broken
        CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["jr1"]
        ).set_broken(
            attempt=FetchAttemptFactory(
                counter_report=counter_report_types["pr"], credentials=credentials["branch_pr"]
            ),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )

        # remove mapping
        CounterReportsToCredentials.objects.filter(
            counter_report=counter_report_types["tr"]
        ).delete()

        assert Automatic.update_for_this_month() == {"deleted": 3, "added": 0}
        assert FetchIntention.objects.count() == 1
        remained = FetchIntention.objects.last()
        assert remained.counter_report == counter_report_types["br1"]
        # create mapping
        CounterReportsToCredentials.objects.create(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["pr"],
        )

        # create broken mapping
        CounterReportsToCredentials.objects.create(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["db1"],
        ).set_broken(
            FetchAttemptFactory(
                counter_report=counter_report_types["db1"],
                credentials=credentials["standalone_br1_jr1"],
            ),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )

        # create credentials for other organiation
        creds1 = CredentialsFactory(enabled=True)
        CounterReportsToCredentials.objects.create(
            broken=None, credentials=creds1, counter_report=counter_report_types["tr"]
        )

        # create broken credentials for other organization
        creds2 = CredentialsFactory(enabled=True)
        creds2.set_broken(
            FetchAttemptFactory(counter_report=counter_report_types["tr"], credentials=creds2),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )
        CounterReportsToCredentials.objects.create(
            broken=None, credentials=creds2, counter_report=counter_report_types["tr"]
        )

        # create credentials with broken mapping
        creds3 = CredentialsFactory(enabled=True)
        creds3.set_broken(
            FetchAttemptFactory(counter_report=counter_report_types["tr"], credentials=creds2),
            broken_type=SushiCredentials.BROKEN_HTTP,
        )
        CounterReportsToCredentials.objects.create(
            broken=None, credentials=creds3, counter_report=counter_report_types["tr"]
        ).set_broken(
            FetchAttemptFactory(counter_report=counter_report_types["tr"], credentials=creds2),
            broken_type=SushiCredentials.BROKEN_SUSHI,
        )

        assert Automatic.update_for_this_month() == {"deleted": 0, "added": 2}
        assert FetchIntention.objects.count() == 3
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_credentials_signals(
        self, counter_report_types, credentials, enable_automatic_scheduling
    ):
        """ Test whether automatic harvests are update when
            credentials or credentails to counter report mapping
            changes
        """
        start_date = date(2020, 2, 1)

        # Save credentials
        assert FetchIntention.objects.all().count() == 0
        assert Automatic.objects.all().count() == 0

        credentials["branch_pr"].save()
        assert Automatic.objects.all().count() == 1
        automatic_branch = Automatic.objects.first()
        assert automatic_branch.harvest.intentions.count() == 1
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        credentials["standalone_br1_jr1"].save()
        assert Automatic.objects.all().count() == 2
        automatic_standalone = Automatic.objects.order_by('pk').last()
        assert automatic_standalone.harvest.intentions.count() == 2
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        credentials["standalone_tr"].save()
        assert automatic_standalone.harvest.intentions.count() == 3
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

        # Create new mapping
        new_mapping = CounterReportsToCredentials.objects.create(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["tr"],
            broken=None,
        )
        assert FetchIntention.objects.all().count() == 5
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
        assert automatic_standalone.harvest.intentions.count() == 3
        credentials["standalone_br1_jr1"].delete()
        assert automatic_standalone.harvest.intentions.count() == 1
        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())
