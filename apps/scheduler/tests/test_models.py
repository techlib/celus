from uuid import uuid4
from datetime import datetime, timedelta, date

from django.utils import timezone

import pytest

from freezegun import freeze_time

from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory, SchedulerFactory
from test_fixtures.scenarios.basic import (
    counter_report_types,
    report_types,
    credentials,
    platforms,
    organizations,
    data_sources,
    users,
)

from scheduler import tasks
from scheduler.models import FetchIntention, Scheduler, RunResponse
from sushi.models import SushiCredentials
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
        fi.process()
        assert when_processed == fi.when_processed

    def test_process_without_scheduler(self):
        fi = FetchIntentionFactory(when_processed=None, scheduler=None, attempt=None)
        with pytest.raises(ValueError):
            fi.process()

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
            last_updated_by=users["user1"],
        )
        fi.process()
        assert fi.attempt.triggered_by == users["user1"]
        assert fi.when_processed == datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz)

        # test not_before for newly created FetchIntentions
        last = FetchIntention.objects.order_by('pk').last()
        if seconds_not_before:
            assert last.pk != fi.pk
            assert (last.not_before - fi.not_before).total_seconds() == seconds_not_before
        else:
            assert last.pk == fi.pk
        assert last.last_updated_by == users["user1"]

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

    def test_stats(self, counter_report_types, credentials):
        uuid1 = uuid4()
        uuid2 = uuid4()

        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            group_id=uuid1,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            group_id=uuid1,
        )

        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            group_id=uuid2,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=None,
            group_id=uuid2,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            group_id=uuid2,
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            group_id=uuid2,
        )

        assert FetchIntention.objects.stats() == (3, 5)
        assert FetchIntention.objects.filter(group_id=uuid1).stats() == (1, 2)
        assert FetchIntention.objects.filter(group_id=uuid2).stats() == (2, 3)

    def test_plan_fetching(self, counter_report_types, credentials, monkeypatch, users):
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
        group_id = FetchIntention.plan_fetching(intentions)
        assert FetchIntention.objects.filter(group_id=group_id).count() == 3

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
            FetchIntention.plan_fetching(
                intentions,
                group_id=group_id,
                priority=FetchIntention.PRIORITY_NOW,
                user=users["user1"],
            )
            == group_id
        )
        assert FetchIntention.objects.filter(group_id=group_id).count() == 6
        assert (
            FetchIntention.objects.filter(group_id=group_id, last_updated_by=users["user1"]).count()
            == 3
        )

        assert urls == {credentials["standalone_tr"].url, credentials["standalone_br1_jr1"].url}


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
            FetchIntentionFactory(
                not_before=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
                scheduler=None,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                priority=FetchIntention.PRIORITY_NOW,
            )
            assert scheduler.run_next() == RunResponse.PROCESSED
