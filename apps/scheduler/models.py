import typing

from uuid import uuid4, UUID

from datetime import datetime, timedelta
from enum import Enum, auto

from django.db import models, transaction, DatabaseError
from django.conf import settings
from django.utils import timezone

from core.models import User
from nigiri.error_codes import ErrorCode
from sushi.models import SushiCredentials, SushiFetchAttempt, CounterReportType, CreatedUpdatedMixin

from core.models import User
from logs.tasks import import_one_sushi_attempt_task


NO_DATA_RETRY_PERIOD = timedelta(days=45)  # cca month and half
SERVICE_NOT_AVAILABLE_MAX_RETRY_TIME = timedelta(days=1)
SERVICE_BUSY_MAX_RETRY_TIME = timedelta(days=1)
DATA_NOT_READY_RETRY_PERIOD = timedelta(days=1)


class RunResponse(Enum):
    IDLE = auto()  # no FetchIntention to be processed
    COOLDOWN = auto()  # triggered too soon (make sense to replan in celery)
    BUSY = auto()  # is currently processing a request
    PROCESSED = auto()  # FetchIntention was processed


# TODO scheduler cleanup (to many invalid urls)
class Scheduler(models.Model):
    """ Represents attempt scheduling based on remote URL """

    DEFAULT_COOLDOWN_DELAY = 5  # in seconds
    DEFAULT_TOO_MANY_REQUESTS_DELAY = 60 * 60  # in seconds
    DEFAULT_SERVICE_NOT_AVAILABLE_DELAY = 60 * 60  # in seconds
    DEFAULT_SERVICE_BUSY_DELAY = 60  # in seconds

    url = models.URLField(unique=True)
    when_ready = models.DateTimeField(default=timezone.now)

    cooldown = models.PositiveSmallIntegerField(
        default=DEFAULT_COOLDOWN_DELAY,
        help_text="Required number of seconds before between queries "
        "(to be sure that the queries are not run in parallel)",
    )
    too_many_requests_delay = models.IntegerField(default=DEFAULT_TOO_MANY_REQUESTS_DELAY)
    service_not_available_delay = models.IntegerField(default=DEFAULT_SERVICE_NOT_AVAILABLE_DELAY)
    service_busy_delay = models.IntegerField(default=DEFAULT_SERVICE_BUSY_DELAY)

    @property
    def last_time(self) -> typing.Optional[datetime]:
        intetion = (
            self.intentions.filter(when_processed__isnull=False).order_by('when_processed').last()
        )
        if not intetion:
            return None
        return intetion.when_processed

    # TODO it would be nice to display some kind of scheduler statistics

    def run_next(self) -> RunResponse:
        """ This function can take a while so it should be run only in celery """

        # Check whether scheduler is in cooldown period
        if self.last_time:
            last_plus_cooldown = self.last_time + timedelta(seconds=self.cooldown)
            if last_plus_cooldown > timezone.now():
                self.when_ready = last_plus_cooldown
                self.save()
                return RunResponse.COOLDOWN

        with transaction.atomic():
            try:
                # lock this instance by evaluating select_for_update query
                sch_lock = Scheduler.objects.select_for_update(nowait=True).get(pk=self.pk)  # noqa
            except DatabaseError:
                # Locked - currently processing data
                return RunResponse.BUSY

            with transaction.atomic():
                # Takes the first intention
                intention = (
                    FetchIntention.objects.select_for_update(skip_locked=True)
                    .filter(
                        credentials__url=self.url,
                        when_processed__isnull=True,
                        not_before__lte=timezone.now(),
                    )
                    .order_by('-priority', 'not_before')
                    .first()
                )
                if not intention:
                    return RunResponse.IDLE

                # Check whether scheduler is ready or has sufficient priority
                if self.when_ready <= timezone.now() or intention.priority_now:
                    intention.scheduler = self
                    intention.save()

                    # Process the intetion
                    intention.process()

                    # Add cooldown period to when_ready
                    self.when_ready = timezone.now() + timedelta(seconds=self.cooldown)
                    self.save()

                    return RunResponse.PROCESSED

        return RunResponse.IDLE


class FetchIntentionQuerySet(models.QuerySet):
    def schedulers_to_trigger(self) -> typing.List[Scheduler]:
        res: typing.Set[Scheduler] = set()
        for fi in self.filter(not_before__lt=timezone.now(), scheduler__isnull=True):
            (scheduler, _) = Scheduler.objects.get_or_create(url=fi.credentials.url)
            if scheduler.when_ready < timezone.now() or fi.priority_now:
                res.add(scheduler)

        return list(res)

    def stats(self) -> typing.Tuple[int, int]:
        """ Returns how many intentions are finished.
        Note that it considers replaned intentions as one

        :returns: unprocessed, total
        """

        qs = self.annotate(
            unique_field=models.functions.Concat(
                models.F('credentials__version_hash'),
                models.F('counter_report__code'),
                models.F('start_date'),
                models.F('end_date'),
            )
        )

        total = qs.aggregate(total=models.Count('unique_field', distinct=True))["total"] or 0
        unprocessed = (
            qs.filter(when_processed=None).aggregate(
                total=models.Count('unique_field', distinct=True)
            )["total"]
            or 0
        )
        return unprocessed, total


class FetchIntention(CreatedUpdatedMixin):

    PRIORITY_NOW = 100
    PRIORITY_NORMAL = 50

    objects = FetchIntentionQuerySet.as_manager()

    not_before = models.DateTimeField(help_text="Don't plan before", default=timezone.now)
    priority = models.SmallIntegerField(default=PRIORITY_NORMAL)
    credentials = models.ForeignKey(SushiCredentials, on_delete=models.CASCADE)
    counter_report = models.ForeignKey(CounterReportType, on_delete=models.CASCADE)
    scheduler = models.ForeignKey(
        Scheduler, related_name="intentions", on_delete=models.CASCADE, null=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    when_processed = models.DateTimeField(help_text="When fetch unit was processed", null=True)
    attempt = models.ForeignKey(SushiFetchAttempt, null=True, on_delete=models.SET_NULL)
    group_id = models.UUIDField(help_text="every fetchattempt is planned as a part of a group")

    # Retry counters
    data_not_ready_retry = models.SmallIntegerField(default=0)
    service_not_available_retry = models.SmallIntegerField(default=0)
    service_busy_retry = models.SmallIntegerField(default=0)

    @property
    def priority_now(self) -> bool:
        return self.priority >= FetchIntention.PRIORITY_NOW

    @property
    def is_processed(self):
        return self.when_processed is not None

    @classmethod
    def get_handler(
        cls, error_code_str: typing.Optional[str]
    ) -> typing.Optional[typing.Callable[['FetchIntention'], None]]:

        try:
            error_code = int(error_code_str or "")
        except ValueError:
            return None

        if error_code == ErrorCode.SERVICE_NOT_AVAILABLE:
            return cls.handle_service_not_available
        elif error_code in [ErrorCode.SERVICE_BUSY, ErrorCode.PREPARING_DATA]:
            return cls.handle_service_busy
        elif error_code == ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS:
            return cls.handle_data_not_ready
        elif error_code == ErrorCode.NO_DATA_FOR_DATE_ARGS:
            return cls.handle_no_data
        elif error_code == ErrorCode.TOO_MANY_REQUESTS:
            return cls.handle_too_many_requests

        return None

    def process(self):
        """ Should be run only from celery """
        if self.is_processed:
            return  # already processed

        if not self.scheduler:
            raise ValueError("Trying to process intetion without configured scheduler")

        # fetch attempt
        attempt: SushiFetchAttempt = self.credentials.fetch_report(
            self.counter_report, self.start_date, self.end_date
        )
        attempt.triggered_by = self.last_updated_by
        attempt.save()

        self.attempt = attempt
        self.when_processed = timezone.now()
        self.save()

        handler = self.get_handler(attempt.error_code)
        if handler:
            handler(self)

        # plan data import
        if attempt.can_import_data:
            import_one_sushi_attempt_task.delay(attempt.id)

    @staticmethod
    def next_exponential(
        retry_number: int, initial_delay: int, max_delay: typing.Optional[int] = None
    ) -> typing.Tuple[datetime, bool]:
        """ Calculates next_time as expoential
        :param retry_number: number of retries
        :param initial_delay: delay interval (in seconds)
        :param max_delay: max interval (in newer interval is biger max delay is returned instead)
        :returns: (new interval and max delay was reached indicator)
        """
        now = timezone.now()
        delta = timedelta(seconds=initial_delay * 2 ** retry_number)
        if max_delay:
            max_delta = timedelta(seconds=max_delay)
            if max_delta > delta:
                return now + delta, False
            else:
                return now + max_delta, True
        else:
            return now + delta, False

    def _create_retry(
        self,
        not_before: datetime,
        inc_data_not_ready_retry: bool = False,
        inc_service_not_available_retry: bool = False,
        inc_service_busy_retry: bool = False,
    ) -> 'FetchIntention':

        kwargs = {
            'data_not_ready_retry': self.data_not_ready_retry
            + (1 if inc_data_not_ready_retry else 0)  # always keep data_not_ready counter
        }
        if inc_service_busy_retry:
            kwargs['service_busy_retry'] = self.service_busy_retry + 1
        if inc_service_not_available_retry:
            kwargs['service_not_available_retry'] = self.service_not_available_retry + 1

        return FetchIntention.objects.create(
            not_before=not_before,
            priority=self.priority,
            credentials=self.credentials,
            counter_report=self.counter_report,
            start_date=self.start_date,
            end_date=self.end_date,
            group_id=self.group_id,
            last_updated_by=self.last_updated_by,
            **kwargs,
        )

    def handle_service_not_available(self):
        next_time, max_reached = FetchIntention.next_exponential(
            self.service_not_available_retry,
            self.scheduler.service_not_available_delay,
            SERVICE_NOT_AVAILABLE_MAX_RETRY_TIME.total_seconds(),
        )

        # update scheduler
        self.scheduler.when_ready = next_time
        self.scheduler.save()

        # giving up for the next retry
        if max_reached:
            return

        # prepare retry
        self._create_retry(
            next_time, inc_service_not_available_retry=True,
        )

    def handle_service_busy(self):
        next_time, max_reached = FetchIntention.next_exponential(
            self.service_busy_retry,
            self.scheduler.service_busy_delay,
            SERVICE_BUSY_MAX_RETRY_TIME.total_seconds(),
        )

        # update scheduler
        self.scheduler.when_ready = next_time
        self.scheduler.save()

        # giving up for the next retry
        if max_reached:
            return

        # prepare retry
        self._create_retry(
            self.scheduler.when_ready, inc_service_busy_retry=True,
        )

    def handle_data_not_ready(self):
        next_time, _ = FetchIntention.next_exponential(
            self.data_not_ready_retry, DATA_NOT_READY_RETRY_PERIOD.total_seconds(),
        )

        if self.data_not_ready_retry > settings.QUEUED_SUSHI_MAX_RETRY_COUNT:
            # giving up
            return

        # prepare retry
        self._create_retry(
            next_time, inc_data_not_ready_retry=True,
        )

    def handle_no_data(self):
        """ Some vendors use no_data status as data_not_ready status """
        next_time, _ = FetchIntention.next_exponential(
            self.data_not_ready_retry, DATA_NOT_READY_RETRY_PERIOD.total_seconds(),
        )

        if (
            self.data_not_ready_retry > settings.QUEUED_SUSHI_MAX_RETRY_COUNT
            or next_time
            - datetime.combine(self.end_date, datetime.min.time(), tzinfo=next_time.tzinfo)
            > NO_DATA_RETRY_PERIOD
        ):
            # giving up
            return

        # prepare retry
        self._create_retry(
            next_time, inc_data_not_ready_retry=True,
        )

    def handle_too_many_requests(self):
        # just add a constant delay set in scheduler
        self.scheduler.when_ready = timezone.now() + timedelta(
            seconds=self.scheduler.too_many_requests_delay
        )
        self.scheduler.save()

        # prepare retry
        self._create_retry(self.scheduler.when_ready)

    @classmethod
    @transaction.atomic
    def plan_fetching(
        cls,
        intentions: typing.List['FetchIntention'],
        group_id: typing.Optional[UUID] = None,
        priority: int = PRIORITY_NORMAL,
        user: typing.Optional[User] = None,
    ) -> UUID:
        """  Plans fetching of FetchIntentions

        :param intentions: unsaved FetchIntentions (for batch_create)
        :param group_id: id of fetching group, if not given random uuid will be used
        :param priority: priority of planned tasks
        :param user: user who triggered the fetching (or None if planned by e.g. cron)

        :returns: group_id
        """
        group_id = group_id or uuid4()
        urls = set()

        for intention in intentions:
            urls.add(intention.credentials.url)
            intention.group_id = group_id
            intention.priority = priority
            intention.last_updated_by = user

        FetchIntention.objects.bulk_create(intentions)

        if priority >= cls.PRIORITY_NOW:
            from .tasks import trigger_scheduler

            for url in urls:
                trigger_scheduler.delay(url, True)

        return group_id
