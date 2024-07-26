import re
import typing
import uuid
from datetime import date, datetime, timedelta

import pytest
import requests_mock
from celus_nigiri.error_codes import ErrorCode
from django.utils import timezone
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory
from logs.logic.attempt_import import import_one_sushi_attempt
from logs.models import ImportBatch, OrganizationPlatform
from logs.tasks import import_one_sushi_attempt_task
from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiCredentials

from scheduler import tasks
from scheduler.fake_data import (
    AutomaticFactory,
    FetchIntentionFactory,
    HarvestFactory,
    SchedulerFactory,
)
from scheduler.models import (
    Automatic,
    FetchIntention,
    FetchIntentionQueue,
    Harvest,
    ProcessResponse,
    RunResponse,
    Scheduler,
)
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    credentials,
    data_sources,
    harvests,
    import_batches,
    organizations,
    platforms,
    report_types,
    schedulers,
    users,
    verified_credentials,
)

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
            credentials=creds1, scheduler=sch, counter_report=counter_report_types["tr"]
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

    def test_process_with_planned_duplicates(self, counter_report_types, credentials, monkeypatch):
        scheduler = SchedulerFactory()

        def mocked_fetch_report(self, counter_report, start_date, end_date):
            return FetchAttemptFactory(
                error_code="",
                credentials=self,
                counter_report=counter_report,
                start_date=start_date,
                end_date=end_date,
                status=AttemptStatus.IMPORTING,
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)
        monkeypatch.setattr(import_one_sushi_attempt_task, "delay", lambda x: None)

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
            (ErrorCode.SERVICE_NOT_AVAILABLE.value, 20 * 2**3, 20 * 2**3),
            (ErrorCode.SERVICE_BUSY.value, 30 * 2**4, 30 * 2**4),
            (ErrorCode.PREPARING_DATA.value, 30 * 2**4, 30 * 2**4),
            (ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value, 60 * 60 * 24 * 2**2, 0),
            (ErrorCode.NO_DATA_FOR_DATE_ARGS.value, 60 * 60 * 24 * 2**2, 0),
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

        def mocked_fetch_report(*args, **kwargs):
            return FetchAttemptFactory(
                error_code=error_code,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)

        fi = FetchIntentionFactory(
            harvest=AutomaticFactory(harvest__last_updated_by=users["admin1"]).harvest,
            not_before=timezone.now(),
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            data_not_ready_retry=2,
            service_not_available_retry=3,
            service_busy_retry=4,
            harvest__last_updated_by=users["admin1"],
        )
        assert fi.process() == ProcessResponse.SUCCESS
        assert fi.attempt.triggered_by == users["admin1"]
        assert fi.when_processed == datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz)

        # test not_before for newly created FetchIntentions
        last = FetchIntention.objects.order_by("pk").last()
        if seconds_not_before:
            assert last.pk != fi.pk
            assert (last.not_before - fi.not_before).total_seconds() == seconds_not_before
            assert last.queue_id == fi.pk
            assert fi.queue_id == fi.pk
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
        new_sch = Scheduler.objects.order_by("pk").last()

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
        "error_code,status,recent_success,automatic,empty_ib,delays,last_canceled",
        (
            pytest.param(
                ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value,  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    None,
                ],  # delays
                False,  # last_canceled
                id="not_ready",
            ),
            pytest.param(
                ErrorCode.NO_DATA_FOR_DATE_ARGS.value,  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                True,  # automatic
                True,  # empty_ib
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    None,
                ],  # delays
                False,  # last_canceled
                id="no_data",
            ),
            pytest.param(
                ErrorCode.PREPARING_DATA.value,  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(minutes=1),
                    timedelta(minutes=2),
                    timedelta(minutes=4),
                    timedelta(minutes=8),
                    timedelta(minutes=16),
                    timedelta(minutes=32),
                    timedelta(minutes=64),
                    timedelta(minutes=128),
                    timedelta(minutes=256),
                    timedelta(minutes=512),
                    timedelta(minutes=1024),
                    None,
                ],  # delays
                True,  # last_canceled
                id="preparing_data",
            ),
            pytest.param(
                ErrorCode.SERVICE_BUSY.value,  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(minutes=1),
                    timedelta(minutes=2),
                    timedelta(minutes=4),
                    timedelta(minutes=8),
                    timedelta(minutes=16),
                    timedelta(minutes=32),
                    timedelta(minutes=64),
                    timedelta(minutes=128),
                    timedelta(minutes=256),
                    timedelta(minutes=512),
                    timedelta(minutes=1024),
                    None,
                ],  # delays
                True,  # last_canceled
                id="service_busy",
            ),
            pytest.param(
                ErrorCode.TOO_MANY_REQUESTS.value,  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                    timedelta(seconds=10),
                ],  # delays
                True,  # last_canceled
                id="too_many_requests",
            ),
            pytest.param(
                ErrorCode.SERVICE_NOT_AVAILABLE.value,  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(minutes=60),
                    timedelta(minutes=120),
                    timedelta(minutes=240),
                    timedelta(minutes=480),
                    timedelta(minutes=960),
                    None,
                ],  # delays
                True,  # last_canceled
                id="service_not_available",
            ),
            pytest.param(
                "",  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                True,  # automatic
                True,  # empty_ib
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    None,
                ],  # delays
                False,  # last_canceled
                id="empty",
            ),
            pytest.param(
                "",  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [None],  # delays
                False,  # last_canceled
                id="error",
            ),
            pytest.param(
                "",  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                True,  # recent_success
                True,  # automatic
                False,  # empty_ib
                [
                    timedelta(days=1),
                    timedelta(days=2),
                    timedelta(days=4),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    timedelta(days=8),
                    None,
                ],  # delays
                False,  # last_canceled
                id="success_then_error",
            ),
            pytest.param(
                ErrorCode.PREPARING_DATA.value,  # error_code
                AttemptStatus.DOWNLOAD_FAILED,  # status
                False,  # recent_success
                False,  # automatic
                False,  # empty_ib
                [
                    timedelta(minutes=1),
                    timedelta(minutes=2),
                    timedelta(minutes=4),
                    timedelta(minutes=8),
                    timedelta(minutes=16),
                    timedelta(minutes=32),
                    timedelta(minutes=64),
                    timedelta(minutes=128),
                    timedelta(minutes=256),
                    timedelta(minutes=512),
                    timedelta(minutes=1024),
                    None,
                ],  # delays
                True,  # last_canceled
                id="preparing_data_no_automatic",
            ),
            pytest.param(
                ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value,  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                False,  # automatic
                False,  # empty_ib
                [None],  # delays
                False,  # last_canceled
                id="not_ready_manual",
            ),
            pytest.param(
                ErrorCode.NO_DATA_FOR_DATE_ARGS.value,  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                False,  # automatic
                True,  # empty_ib
                [None],  # delays
                False,  # last_canceled
                id="no_data_manual",
            ),
            pytest.param(
                "",  # error_code
                AttemptStatus.NO_DATA,  # status
                False,  # recent_success
                False,  # automatic
                True,  # empty_ib
                [None],  # delays
                False,  # last_canceled
                id="no_data_no_error_manual",
            ),
        ),
    )
    def test_process_retry_chain(
        self,
        credentials,
        counter_report_types,
        monkeypatch,
        error_code,
        status,
        recent_success,
        automatic,
        empty_ib,
        delays,
        last_canceled,
        settings,
    ):
        settings.QUEUED_SUSHI_MAX_RETRY_COUNT = 7
        scheduler = SchedulerFactory(url=credentials["standalone_tr"].url)

        start = datetime(2020, 1, 2, 0, 0, 0, 0, tzinfo=current_tz)

        if recent_success:
            with freeze_time(start - timedelta(days=30)):
                FetchAttemptFactory(
                    when_processed=timezone.now() + timedelta(minutes=5),
                    status=AttemptStatus.SUCCESS,
                    start_date=date(2020, 1, 1),
                    end_date=date(2020, 1, 31),
                    credentials=credentials["standalone_tr"],
                    counter_report=counter_report_types["tr"],
                    error_code="",
                    import_batch=ImportBatchFactory(
                        report_type=counter_report_types["tr"].report_type
                    ),
                )

        def mocked_fetch_report(*args, **kwargs):
            return FetchAttemptFactory(
                status=status,
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 31),
                error_code=error_code,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                data_file__data=b'{"Report_Items": [],"Report_Header": '
                b'{"Report_ID": "TR", "Customer_ID":"C1"}}',
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)

        def check_retry(
            fi: FetchIntention,
            expected: typing.Optional[datetime],
            queue: typing.Optional[FetchIntentionQueue],
        ) -> FetchIntention:
            with freeze_time(fi.not_before):
                fi.scheduler = scheduler
                assert fi.process() == ProcessResponse.SUCCESS
                if not expected:
                    if error_code == ErrorCode.PARTIAL_DATA_RETURNED.value:
                        assert (
                            fi.attempt.import_batch is None
                        ), "last partial data should not contain ib"
                        assert fi.attempt.can_import_data, "last partial data should be importable"
                        import_one_sushi_attempt(fi.attempt)
                        assert (
                            fi.attempt.import_batch is not None
                        ), "last partial data should contain ib after import"

                    if empty_ib:
                        assert (
                            fi.attempt.import_batch is not None
                        ), "there should be import batch at the end of a chain"
                        assert (
                            fi.attempt.import_batch.accesslog_set.count() == 0
                        ), "import batch should be empty if partial_data is not returned"
                        assert OrganizationPlatform.objects.filter(
                            organization=fi.credentials.organization,
                            platform=fi.credentials.platform,
                        ).exists(), "OrganizationPlatform should have been created"

                    else:
                        assert (
                            fi.attempt.import_batch is None
                        ), "no ib should be present so it can be retried later"

                else:
                    assert fi.attempt.import_batch is None
            new_fi = FetchIntention.objects.order_by("pk").last()
            assert new_fi is not None

            if expected:
                assert fi.pk != new_fi.pk, "new intention created"
                assert new_fi.not_before == expected, "new planned date matches"
                assert not new_fi.is_processed, "new intention is not processed"
                assert new_fi.canceled is False, "fetch not canceled"
                assert new_fi.queue is not None, "New intetions is a part of a queue"
                if queue:
                    assert new_fi.queue == queue, "Queue equals queue of prev intention"
            else:
                if last_canceled:
                    assert fi.pk != new_fi.pk, "new intention created"
                    assert new_fi.canceled is True
                else:
                    assert new_fi.canceled is False
                assert new_fi.is_processed, "marked as processed"

            return new_fi

        with freeze_time(start):
            if automatic:
                harvest = AutomaticFactory().harvest
            else:
                harvest = HarvestFactory(automatic=None)
            fi = FetchIntentionFactory(
                attempt=None,
                harvest=harvest,
                not_before=timezone.now(),
                scheduler=scheduler,
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                data_not_ready_retry=0,
                when_processed=None,
            )

        queue_to_check = None
        for delay in delays:
            fi = check_retry(fi, start + delay if delay else None, None)
            queue_to_check = queue_to_check if queue_to_check else fi.queue
            if delay:
                start += delay

    @pytest.mark.parametrize(
        ["automatic", "retry_exception", "data_replaced"],
        [
            (True, None, True),  # data without 3040 replaces the old one
            (True, "3040", False),  # data with 3040 does not replace the old one
            (False, None, True),  # data without 3040 replaces the old one
            (False, "3040", False),  # data with 3040 does not replace the old one
        ],
    )
    def test_3040_retry_chain(
        self,
        credentials,
        counter_report_types,
        monkeypatch,
        settings,
        automatic,
        retry_exception,
        data_replaced,
    ):
        """
        Test that when a fetch attempt fails with 3040, the data will be accepted and imported
        but a new fetch intention will be created with a delay of 1 day for automatic harvests.
        If the new intention is processed without 3040, the data will replace the old one.
        """

        settings.QUEUED_SUSHI_MAX_RETRY_COUNT = 7
        # prepare the content of the responses
        with open("test-data/counter5/C5_PR_with_3040.json", "r") as f:
            data_with_3040 = f.read()
        with open("test-data/counter5/C5_PR_test.json", "r") as f:
            data_wo_3040 = f.read()

        scheduler = SchedulerFactory(url=credentials["branch_pr"].url)
        start = datetime(2019, 5, 2, 0, 0, 0, 0, tzinfo=current_tz)

        def create_fetch_intention(when) -> FetchIntention:
            with freeze_time(when):
                if automatic:
                    harvest = AutomaticFactory().harvest
                else:
                    harvest = HarvestFactory(automatic=None)
                return FetchIntentionFactory(
                    attempt=None,
                    start_date="2019-04-01",
                    end_date="2019-04-30",
                    harvest=harvest,
                    not_before=timezone.now(),
                    scheduler=scheduler,
                    credentials=credentials["branch_pr"],
                    counter_report=counter_report_types["pr"],
                    data_not_ready_retry=0,
                    when_processed=None,
                )

        # first attempt
        fi = create_fetch_intention(start)
        with freeze_time(start + timedelta(minutes=5)), requests_mock.Mocker() as m:
            m.get(re.compile(f"^{fi.credentials.url}.*"), text=data_with_3040)
            assert fi.process() == ProcessResponse.SUCCESS
            assert fi.attempt.status == AttemptStatus.IMPORTING
            import_one_sushi_attempt(fi.attempt)
            assert fi.attempt.import_batch is not None
            assert fi.attempt.import_batch.accesslog_set.count() > 0
            assert fi.attempt.status == AttemptStatus.SUCCESS
            assert fi.attempt.partial_data is True
            if automatic:
                assert fi.queue.end != fi, "new intention is planned"
                assert fi.queue.end.duplicate_of is None, "new intention is not a duplicate"

        # second attempt
        start2 = start + timedelta(days=1)
        # we use the planned fi if it was created automatically or create a new one
        fi2 = fi.queue.end if automatic else create_fetch_intention(start2)
        fi2.scheduler = scheduler
        with freeze_time(start2 + timedelta(minutes=5)), requests_mock.Mocker() as m:
            m.get(
                re.compile(f"^{fi2.credentials.url}.*"),
                text=data_with_3040 if retry_exception == "3040" else data_wo_3040,
            )
            if data_replaced:
                # a new import batch with the complete data should be created replacing the old one
                assert fi2.process() == ProcessResponse.SUCCESS
                assert fi2.attempt.status == AttemptStatus.IMPORTING
                import_one_sushi_attempt(fi2.attempt)
                assert fi2.attempt.import_batch is not None
                assert fi2.attempt.import_batch.accesslog_set.count() > 0
                assert fi2.attempt.status == AttemptStatus.SUCCESS
                assert fi2.attempt.partial_data is False
                assert fi2.attempt.import_batch_id != fi.attempt.import_batch_id
                assert ImportBatch.objects.filter(pk=fi.attempt.import_batch_id).exists() is False
                if automatic:
                    assert fi2.queue.end == fi2, "new intention is not planned"
            else:
                # data should not be replaced because there is still the same exception
                # but we reschedule the intention when automatic
                assert fi2.process() == ProcessResponse.SUCCESS
                assert fi2.attempt.status == AttemptStatus.NOT_USED
                assert fi2.attempt.import_batch is None
                assert ImportBatch.objects.filter(pk=fi.attempt.import_batch_id).exists() is True
                if automatic:
                    assert fi2.queue.end != fi2, "new intention is planned"

    @pytest.mark.parametrize(
        [
            "first_exception",
            "first_status",
            "first_partial",
            "second_exception",
            "second_has_data",
            "second_status",
            "second_partial",
        ],
        [
            pytest.param(
                "3040",
                AttemptStatus.IMPORTING,
                True,
                "3040",
                False,
                AttemptStatus.NOT_USED,
                True,
                id="3040 not replaced by 3040",
            ),
            pytest.param(
                "3030",
                AttemptStatus.NO_DATA,
                False,
                "3040",
                True,
                AttemptStatus.IMPORTING,
                True,
                id="3030 replaced with 3040",
            ),
            pytest.param(
                "3040",
                AttemptStatus.IMPORTING,
                True,
                "3030",
                False,
                AttemptStatus.NO_DATA,
                False,
                id="3040 replaced with 3030",
            ),
            pytest.param(
                "3030",
                AttemptStatus.NO_DATA,
                False,
                None,
                True,
                AttemptStatus.IMPORTING,
                False,
                id="3030 replaced with no exception",
            ),
            pytest.param(
                "3040",
                AttemptStatus.IMPORTING,
                True,
                None,
                True,
                AttemptStatus.IMPORTING,
                False,
                id="3040 replaced with no exception",
            ),
        ],
    )
    def test_data_replacement(
        self,
        credentials,
        counter_report_types,
        monkeypatch,
        settings,
        first_exception,
        first_status,
        first_partial,
        second_exception,
        second_has_data,
        second_status,
        second_partial,
    ):
        """
        Test how subsequent harvests with already existing attempt behaves depending on exceptions
        present in individual harvests.
        """

        settings.QUEUED_SUSHI_MAX_RETRY_COUNT = 7

        scheduler = SchedulerFactory(url=credentials["branch_pr"].url)
        # start should ensure that the first attempt is final and empty ib is created for 3030
        start = datetime(2019, 7, 2, 0, 0, 0, 0, tzinfo=current_tz)

        def create_fetch_intention(when) -> FetchIntention:
            with freeze_time(when):
                harvest = HarvestFactory(automatic=None)
                return FetchIntentionFactory(
                    attempt=None,
                    start_date="2019-04-01",
                    end_date="2019-04-30",
                    harvest=harvest,
                    not_before=timezone.now(),
                    scheduler=scheduler,
                    credentials=credentials["branch_pr"],
                    counter_report=counter_report_types["pr"],
                    data_not_ready_retry=0,
                    when_processed=None,
                )

        def exception_to_fname(exc):
            return "C5_PR_" + (f"with_{exc}" if exc else "test") + ".json"

        # first attempt
        fi = create_fetch_intention(start)
        fname = exception_to_fname(first_exception)
        with freeze_time(start + timedelta(minutes=5)), requests_mock.Mocker() as m:
            with open(f"test-data/counter5/{fname}", "r") as f:
                m.get(re.compile(f"^{fi.credentials.url}.*"), text=f.read())
            assert fi.process() == ProcessResponse.SUCCESS
            assert fi.attempt.status == first_status
            if fi.attempt.status == AttemptStatus.IMPORTING:
                import_one_sushi_attempt(fi.attempt)
            assert fi.attempt.import_batch is not None, "import batch created"
            assert (
                fi.attempt.status == AttemptStatus.SUCCESS
                if first_status == AttemptStatus.IMPORTING
                else first_status
            ), "importing status should be replaced with success"
            assert fi.attempt.partial_data is first_partial

        # second attempt
        fi2 = create_fetch_intention(start + timedelta(minutes=10))
        fname = exception_to_fname(second_exception)
        with freeze_time(start + timedelta(minutes=15)), requests_mock.Mocker() as m:
            with open(f"test-data/counter5/{fname}", "r") as f:
                m.get(re.compile(f"^{fi2.credentials.url}.*"), text=f.read())
            assert fi2.process() == ProcessResponse.SUCCESS
            assert fi2.attempt.status == second_status
            if fi2.attempt.status == AttemptStatus.IMPORTING:
                import_one_sushi_attempt(fi2.attempt)
            assert bool(fi2.attempt.import_batch) is second_has_data
            assert (
                fi2.attempt.status == AttemptStatus.SUCCESS
                if second_status == AttemptStatus.IMPORTING
                else second_status
            )
            assert fi2.attempt.partial_data is second_partial

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_cancel(self, harvests):
        processed = harvests["anonymous"].intentions.order_by("pk")[0]
        assert processed.is_processed
        assert processed.cancel() is False
        assert processed.canceled is False
        assert processed.is_processed

        unprocessed = harvests["anonymous"].intentions.latest_intentions()[2]
        assert not unprocessed.is_processed
        assert unprocessed.cancel() is True
        assert unprocessed.canceled is True
        assert unprocessed.is_processed
        assert unprocessed.cancel() is False
        assert unprocessed.canceled is True
        assert unprocessed.is_processed

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

    def test_queue(self, credentials, counter_report_types):
        sch = SchedulerFactory()
        hr = HarvestFactory()
        fi1 = FetchIntentionFactory.build(
            when_processed=datetime(2020, 1, 2, 0, 0, 0, tzinfo=current_tz),
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["jr1"],
            harvest=hr,
            attempt=None,
        )
        fi1.save()
        fi1.refresh_from_db()
        assert fi1.queue.id == fi1.pk
        fi2 = FetchIntentionFactory.build(
            scheduler=sch,
            credentials=credentials["standalone_tr"],
            queue=fi1.queue,
            counter_report=counter_report_types["jr1"],
            harvest=hr,
            attempt=None,
        )
        fi2.save()
        fi2.refresh_from_db()
        assert fi2.queue.id == fi1.pk


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
        def mocked_fetch_report(*args, **kwargs):
            return FetchAttemptFactory(
                error_code="",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)

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

    def test_unlock_stuck_schedulers(self, credentials, counter_report_types):
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

        Scheduler.unlock_stuck_schedulers()

        # First is unlocked
        scheduler1.refresh_from_db()
        intention1.refresh_from_db()
        assert scheduler1.current_intention is None
        assert scheduler1.current_start is None
        assert scheduler1.current_celery_task_id is None
        assert intention1.scheduler == scheduler1
        with pytest.raises(Scheduler.DoesNotExist):
            intention1.current_scheduler  # noqa: B018

        # Seconds is unlocked
        scheduler2.refresh_from_db()
        intention2.refresh_from_db()
        assert scheduler2.current_intention is None
        assert scheduler2.current_start is None
        assert scheduler2.current_celery_task_id is None
        assert intention2.scheduler is None
        with pytest.raises(Scheduler.DoesNotExist):
            intention2.current_scheduler  # noqa: B018

        # Third doesn't need to be unlocked
        scheduler3.refresh_from_db()
        intention3.refresh_from_db()
        assert scheduler3.current_intention == intention3
        assert scheduler3.current_start is not None
        assert scheduler3.current_celery_task_id is not None
        assert intention3.scheduler == scheduler3
        assert intention3.current_scheduler == scheduler3

    def test_last_harvestable_month(self, monkeypatch, credentials, counter_report_types):
        """Test workflow when 3032 error occurs"""
        scheduler = SchedulerFactory()

        def mocked_fetch_report(*args, **kwargs):
            return FetchAttemptFactory(
                start_date=date(2020, 2, 1),
                error_code="3032",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
                status=AttemptStatus.DOWNLOAD_FAILED,
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)

        common_fi_attrs = {
            "not_before": timezone.now() - timedelta(minutes=1),
            "scheduler": scheduler,
            "credentials": credentials["standalone_tr"],
            "counter_report": counter_report_types["tr"],
            "harvest": AutomaticFactory().harvest,
            "attempt": None,
        }

        fi1 = FetchIntentionFactory(start_date=date(2020, 1, 1), **common_fi_attrs)

        fi2 = FetchIntentionFactory(start_date=date(2020, 2, 1), **common_fi_attrs)

        fi3 = FetchIntentionFactory(start_date=date(2020, 3, 1), **common_fi_attrs)

        assert fi2.process() == ProcessResponse.SUCCESS
        fi2.refresh_from_db()
        assert fi2.when_processed is not None, "Second intention was processed"
        assert fi2.canceled is False
        assert fi2.attempt is not None

        fi1.refresh_from_db()
        assert fi1.canceled is True, "First intention was canceled"
        assert fi1.when_processed is not None, "First intentions is marked as processed"
        assert fi1.attempt is None

        fi3.refresh_from_db()
        assert fi3.canceled is False, "Third intention is not canceled"
        assert fi3.when_processed is None, "Third intention is not processed"
        assert fi3.attempt is None

        cr2c = CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["tr"], credentials=credentials["standalone_tr"]
        )
        assert cr2c.last_harvestable_month == date(2020, 3, 1)
        assert cr2c.last_harvestable_month_attempt == fi2.attempt
        assert cr2c.last_harvestable_month_user is None

    def test_run_next_ordering(self, monkeypatch, credentials, counter_report_types):
        def mocked_fetch_report(*args, **kwargs):
            return FetchAttemptFactory(
                error_code="",
                credentials=credentials["standalone_tr"],
                counter_report=counter_report_types["tr"],
            )

        monkeypatch.setattr(SushiCredentials, "fetch_report", mocked_fetch_report)

        scheduler = SchedulerFactory(
            url=credentials["standalone_tr"].url,
            cooldown=10,
            when_ready=datetime(2020, 1, 1, 0, 0, 0, tzinfo=current_tz),
        )
        with freeze_time(datetime(2022, 1, 1, 0, 0, 0, 0, tzinfo=current_tz)):
            intentions = [
                FetchIntention(
                    credentials=credentials["standalone_tr"],
                    counter_report=counter_report_types["tr"],
                    start_date=date(2020, 1, 1),
                    end_date=date(2020, 1, 31),
                ),
                FetchIntention(
                    credentials=credentials["standalone_tr"],
                    counter_report=counter_report_types["tr"],
                    start_date=date(2020, 3, 1),
                    end_date=date(2020, 3, 31),
                ),
                FetchIntention(
                    credentials=credentials["standalone_tr"],
                    counter_report=counter_report_types["tr"],
                    start_date=date(2020, 2, 1),
                    end_date=date(2020, 2, 28),
                ),
            ]
            Harvest.plan_harvesting(intentions)

        # intentsions should be planned in intentions[1], intentions[2], intentions[0]
        # order

        assert intentions[0].when_processed is None
        assert intentions[1].when_processed is None
        assert intentions[2].when_processed is None

        with freeze_time(datetime(2022, 1, 1, 0, 5, 0, 0, tzinfo=current_tz)):
            assert scheduler.run_next() == RunResponse.PROCESSED

        for i in intentions:
            i.refresh_from_db()
        assert intentions[0].when_processed is None
        assert intentions[1].when_processed is not None
        assert intentions[2].when_processed is None

        with freeze_time(datetime(2022, 1, 1, 0, 10, 0, 0, tzinfo=current_tz)):
            assert scheduler.run_next() == RunResponse.PROCESSED

        for i in intentions:
            i.refresh_from_db()
        assert intentions[0].when_processed is None
        assert intentions[1].when_processed is not None
        assert intentions[2].when_processed is not None

        with freeze_time(datetime(2022, 1, 1, 0, 15, 0, 0, tzinfo=current_tz)):
            assert scheduler.run_next() == RunResponse.PROCESSED

        for i in intentions:
            i.refresh_from_db()
        assert intentions[0].when_processed is not None
        assert intentions[1].when_processed is not None
        assert intentions[2].when_processed is not None


@pytest.mark.django_db
class TestHarvest:
    @pytest.mark.django_db(transaction=True)
    def test_plan_harvesting(self, counter_report_types, credentials, monkeypatch, users):
        urls = set()

        def mocked_trigger_scheduler(url, finish):
            urls.add(url)

        monkeypatch.setattr(tasks.trigger_scheduler, "delay", mocked_trigger_scheduler)

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
                user=users["admin1"],
            )
            == harvest
        )
        assert harvest.last_updated_by == users["admin1"]
        assert FetchIntention.objects.filter(harvest=harvest).count() == 6

        assert urls == {credentials["standalone_tr"].url, credentials["standalone_br1_jr1"].url}

    def test_stats(self, counter_report_types, credentials, settings):
        harvest1 = HarvestFactory(automatic=None)
        harvest2 = HarvestFactory(automatic=None)
        harvest3 = HarvestFactory(automatic=None)
        harvest4 = HarvestFactory(automatic=None)
        harvest5 = HarvestFactory(automatic=None)

        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            harvest=harvest1,
            duplicate_of=None,
            attempt=FetchAttemptFactory(
                counter_report=counter_report_types["tr"],
                credentials=credentials["standalone_tr"],
                status="importing",
            ),
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest1,
            duplicate_of=None,
            attempt=None,
        )

        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest2,
            duplicate_of=None,
            attempt=None,
        )
        last = FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=None,
            harvest=harvest2,
            duplicate_of=None,
            attempt=None,
        )
        queue = last.queue
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest2,
            duplicate_of=None,
            queue=queue,
            attempt=FetchAttemptFactory(
                counter_report=counter_report_types["tr"],
                credentials=credentials["standalone_tr"],
                status="success",
            ),
        )
        FetchIntentionFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            start_date="2020-02-01",
            end_date="2020-02-29",
            when_processed=None,
            harvest=harvest2,
            duplicate_of=None,
            attempt=None,
        )

        original_fi = FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=timezone.now(),
            harvest=harvest3,
            duplicate_of=None,
            attempt=FetchAttemptFactory(
                counter_report=counter_report_types["pr"], credentials=credentials["branch_pr"]
            ),
        )
        working_intention = FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date="2020-01-01",
            end_date="2020-01-31",
            when_processed=None,
            harvest=harvest4,
            duplicate_of=original_fi,
            attempt=None,
        )
        SchedulerFactory(current_intention=working_intention)

        assert harvest1.stats() == {
            "finished": 1,
            "planned": 1,
            "total": 2,
            "attempt_count": 1,
            "working": 1,
        }
        assert harvest2.stats() == {
            "finished": 1,
            "planned": 2,
            "total": 3,
            "attempt_count": 1,
            "working": 0,
        }
        assert harvest3.stats() == {
            "finished": 1,
            "planned": 0,
            "total": 1,
            "attempt_count": 1,
            "working": 0,
        }
        assert harvest4.stats() == {
            "finished": 1,
            "planned": 0,
            "total": 1,
            "attempt_count": 0,
            "working": 1,
        }
        assert harvest5.stats() == {
            "finished": 0,
            "planned": 0,
            "total": 0,
            "attempt_count": 0,
            "working": 0,
        }

        assert list(
            Harvest.objects.annotate_stats().order_by("pk").values_list("pk", "planned", "total")
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
        assert harvests["admin1"].intentions.count() == 2
        assert harvests["admin1"].latest_intentions.count() == 2

    def test_wipe(self, harvests):
        assert Harvest.objects.filter(pk=harvests["admin1"].pk).wipe() == {
            "fetch_attemtps_deleted": (1, {"sushi.SushiFetchAttempt": 1}),
            "harvests_deleted": (3, {"scheduler.FetchIntention": 2, "scheduler.Harvest": 1}),
            "import_batches_deleted": (1, {"logs.ImportBatch": 1}),
        }


@pytest.mark.django_db
class TestAutomatic:
    @freeze_time(datetime(2020, 2, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_update_for_last_month(
        self, credentials, organizations, counter_report_types, verified_credentials
    ):
        start_date = date(2020, 2, 1)

        # all empty
        assert FetchIntention.objects.count() == 0
        assert Automatic.update_for_last_month() == {"added": 4, "deleted": 0}
        last = Automatic.objects.order_by("pk").last()
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

        assert Automatic.update_for_last_month() == {
            "deleted": 0,
            "added": 0,
        }, "updated using signals"
        assert FetchIntention.objects.count() == 1
        remained = FetchIntention.objects.last()
        assert remained.counter_report == counter_report_types["br1"]
        # create mapping
        CounterReportsToCredentials.objects.create(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["pr"]
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

        assert Automatic.update_for_last_month() == {
            "deleted": 0,
            "added": 0,
        }, "updated using signals"
        assert FetchIntention.objects.count() == 2

        # make cred1 verified
        FetchAttemptFactory(
            credentials=creds1,
            status=AttemptStatus.NO_DATA,
            credentials_version_hash=creds1.version_hash,
        )

        assert Automatic.update_for_last_month() == {"deleted": 0, "added": 1}
        assert FetchIntention.objects.count() == 3

        assert all(e.not_before.date() > start_date for e in FetchIntention.objects.all())

    @freeze_time(datetime(2020, 2, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_update_for_last_month_rerun(
        self, credentials, organizations, counter_report_types, verified_credentials
    ):
        # all empty
        assert FetchIntention.objects.count() == 0
        assert Automatic.update_for_last_month() == {"added": 4, "deleted": 0}
        # try again
        assert Automatic.update_for_last_month() == {"added": 0, "deleted": 0}
        # try again after the intentions were processed
        for fi in FetchIntention.objects.all():
            fi.when_processed = datetime(2020, 2, 1, 10, 0, 0)
            fi.save()
        assert Automatic.update_for_last_month() == {"added": 0, "deleted": 0}, "no new intentions"
        # now break some credentials and check that processed were not deleted
        for fi in FetchIntention.objects.all():
            fi.credentials.broken = True
            fi.credentials.save()
        assert Automatic.update_for_last_month() == {
            "added": 0,
            "deleted": 0,
        }, "no intentions deleted"

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_credentials_signals(
        self, counter_report_types, credentials, verified_credentials, monkeypatch
    ):
        """Test whether automatic harvests are update when
        credentials or credentails to counter report mapping
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

        fi.attempt.refresh_from_db()
        assert "assuming a 3030 exception" in fi.attempt.log

    @freeze_time(datetime(2020, 1, 1, 0, 0, 0, 0, tzinfo=current_tz))
    def test_same_queue_reenabled_intentions(
        self, counter_report_types, credentials, verified_credentials
    ):
        # Clear all harvests
        Harvest.objects.all().delete()

        # And delete some credentials
        credentials["standalone_br1_jr1"].delete()
        credentials["branch_pr"].delete()

        # Prepare intention
        assert FetchIntention.objects.all().count() == 0
        assert Automatic.objects.all().count() == 0

        Automatic.update_for_last_month()

        assert FetchIntention.objects.all().count() == 1
        assert Automatic.objects.all().count() == 1

        # Create 3030 fetch attempt and replan next
        fi = FetchIntention.objects.order_by("pk").last()
        assert fi.queue is not None
        queue = fi.queue
        fi.attempt = FetchAttemptFactory(
            start_date=fi.start_date,
            end_date=fi.end_date,
            credentials=credentials["standalone_tr"],
            error_code="3030",
            status=AttemptStatus.NO_DATA,
            import_batch=None,
        )
        fi.when_processed = timezone.now()
        fi.save()

        # Call hanlder to replan
        fi.get_handler()()

        assert FetchIntention.objects.all().count() == 2, "new FI is created"
        assert FetchIntention.objects.order_by("pk").last().queue == queue

        # Disable credentials
        credentials["standalone_tr"].enabled = False
        credentials["standalone_tr"].save()

        assert FetchIntention.objects.all().count() == 1, "new FI is deleted"
        Automatic.update_for_last_month()
        assert FetchIntention.objects.all().count() == 1, "nothing updated"

        # Reenable credentials
        credentials["standalone_tr"].enabled = True
        credentials["standalone_tr"].save()

        # Replan
        Automatic.update_for_last_month()

        assert FetchIntention.objects.all().count() == 2, "new FI is recreated"
        assert (
            FetchIntention.objects.order_by("pk").last().queue == queue
        ), "queue matches the one which was interrupted"
