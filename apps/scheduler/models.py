import typing

from collections import Counter

from datetime import datetime, timedelta, date
from enum import Enum, auto

from dateutil.relativedelta import relativedelta
from django.db import models, transaction, DatabaseError
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.conf import settings
from django.db.models import TextField
from django.utils import timezone

from core.models import User
from core.logic.dates import month_start, month_end
from nigiri.error_codes import ErrorCode
from organizations.models import Organization
from sushi.models import (
    SushiCredentials,
    SushiFetchAttempt,
    CounterReportType,
    CounterReportsToCredentials,
    CreatedUpdatedMixin,
)
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
    BROKEN = auto()  # FetchIntention credentials are broken


class ProcessResponse(Enum):
    SUCCESS = auto()  # Downloading was triggered
    ALREADY_PROCESSED = auto()  # FetchIntention was already processed
    BROKEN = auto()  # Credentials of FetchIntetion are marked as broken
    DUPLICATE = auto()  # FetchIntention was marked as duplicate


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

    def __repr__(self):
        return f'Scheduler #{self.pk} for "{self.url}"'

    def __str__(self):
        return self.url

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
                        duplicate_of__isnull=True,
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
                    # Not than intention can't be `PROCESSED` because
                    # it was selected with when_processed__isnull=True
                    if intention.process() == ProcessResponse.BROKEN:
                        # Credentials are broken
                        return RunResponse.BROKEN

                    # Add cooldown period to when_ready
                    self.when_ready = timezone.now() + timedelta(seconds=self.cooldown)
                    self.save()

                    return RunResponse.PROCESSED

        return RunResponse.IDLE


class FetchIntentionQuerySet(models.QuerySet):
    def schedulers_to_trigger(self) -> typing.List[Scheduler]:
        res: typing.Set[Scheduler] = set()
        for fi in self.filter(
            not_before__lt=timezone.now(), scheduler__isnull=True, duplicate_of__isnull=True
        ):
            (scheduler, _) = Scheduler.objects.get_or_create(url=fi.credentials.url)
            if scheduler.when_ready < timezone.now() or fi.priority_now:
                res.add(scheduler)

        return list(res)


class FetchIntention(models.Model):

    PRIORITY_NOW = 100
    PRIORITY_NORMAL = 50

    objects = FetchIntentionQuerySet.as_manager()

    duplicate_of = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
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
    attempt = models.OneToOneField(SushiFetchAttempt, null=True, on_delete=models.SET_NULL)
    harvest = models.ForeignKey(
        'scheduler.Harvest', on_delete=models.CASCADE, related_name="intentions"
    )
    retry_id = models.IntegerField(null=True, blank=True, help_text='Identifier of retry queue',)

    # Retry counters
    data_not_ready_retry = models.SmallIntegerField(default=0)
    service_not_available_retry = models.SmallIntegerField(default=0)
    service_busy_retry = models.SmallIntegerField(default=0)

    class Meta:
        constraints = (
            CheckConstraint(check=models.Q(start_date__lt=models.F('end_date')), name='timeline'),
        )

    @property
    def fetching_data(self) -> bool:
        try:
            FetchIntention.objects.select_for_update(nowait=True).get(pk=self.pk)  # noqa
            return False
        except DatabaseError:
            return True

    @property
    def priority_now(self) -> bool:
        return self.priority >= FetchIntention.PRIORITY_NOW

    @property
    def is_processed(self):
        return self.when_processed is not None

    @property
    def broken_credentials(self) -> bool:
        return (
            self.credentials.broken
            or not CounterReportsToCredentials.objects.filter(
                broken__isnull=True,
                credentials=self.credentials,
                counter_report=self.counter_report,
            ).exists()  # skip broken or non existing counter report to credentials mapping
        )

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

    def process(self) -> ProcessResponse:
        """ Should be run only from celery

        :returns: None if processed, False if credentials are broken, True on success
        """
        if not self.scheduler:
            raise ValueError("Trying to process intetion without configured scheduler")

        if self.is_processed:
            return ProcessResponse.ALREADY_PROCESSED

        if self.broken_credentials:
            return ProcessResponse.BROKEN

        if self.duplicate_of:
            return ProcessResponse.DUPLICATE

        # fetch attempt
        attempt: SushiFetchAttempt = self.credentials.fetch_report(
            self.counter_report, self.start_date, self.end_date
        )
        attempt.triggered_by = self.harvest.last_updated_by
        attempt.queue_id = self.retry_id
        attempt.save()

        self.attempt = attempt
        self.when_processed = timezone.now()
        self.save()

        handler = self.get_handler(attempt.error_code)
        if handler:
            handler(self)

        # plan data import
        if attempt.can_import_data:
            # Mark planned fetch intention with the same requirements as
            # processed
            FetchIntention.objects.filter(
                when_processed__isnull=True,
                credentials=self.credentials,
                counter_report=self.counter_report,
                start_date=self.start_date,
                end_date=self.end_date,
            ).update(duplicate_of=self)

            # Plan data synchronization
            transaction.on_commit(lambda: import_one_sushi_attempt_task.delay(attempt.pk))

        return ProcessResponse.SUCCESS

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

        with transaction.atomic():
            if not self.retry_id:
                self.retry_id = self.pk
                self.save()
                self.attempt.queue_id = self.retry_id
                self.attempt.save()

        return FetchIntention.objects.create(
            not_before=not_before,
            priority=self.priority,
            credentials=self.credentials,
            counter_report=self.counter_report,
            start_date=self.start_date,
            end_date=self.end_date,
            harvest=self.harvest,
            retry_id=self.retry_id,
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

    @property
    def platform_name(self):
        return self.credentials.platform.name

    @property
    def organization_name(self):
        return self.credentials.organization.name

    @property
    def counter_report_code(self):
        return self.counter_report.code


class Harvest(CreatedUpdatedMixin):
    def __str__(self):
        return f'Harvest #{self.pk}'

    def stats(self) -> typing.Tuple[int, int]:
        """ Returns how many intentions are finished.
        Note that it considers replaned intentions as one

        :returns: unprocessed, total
        """

        qs = self.intentions.annotate(
            unique_field=models.functions.Concat(
                models.F('credentials_id'),
                models.F('credentials__version_hash'),
                models.F('counter_report__code'),
                models.F('start_date'),
                models.F('end_date'),
                output_field=TextField(),
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

    @classmethod
    @transaction.atomic
    def plan_harvesting(
        cls,
        intentions: typing.List['FetchIntention'],
        harvest: typing.Optional['Harvest'] = None,
        priority: int = FetchIntention.PRIORITY_NORMAL,
        user: typing.Optional[User] = None,
    ) -> 'Harvest':
        """  Plans fetching of FetchIntentions

        :param intentions: unsaved FetchIntentions (for batch_create)
        :param harvest: id of harvest which is used to fetch groups of fetch intentions
        :param priority: priority of planned tasks
        :param user: user who triggered the fetching (or None if planned by e.g. cron)

        :returns: releated harvest
        """
        harvest = harvest or Harvest.objects.create()
        harvest.last_updated_by = user
        harvest.save()
        urls = set()

        for intention in intentions:
            urls.add(intention.credentials.url)
            intention.harvest = harvest
            intention.priority = priority

        FetchIntention.objects.bulk_create(intentions)

        if priority >= FetchIntention.PRIORITY_NOW:
            from .tasks import trigger_scheduler

            # We need to plan to trigger the schedulers
            # after this transaction is terminated
            def plan_schedulers():
                for url in urls:
                    trigger_scheduler.delay(url, True)

            transaction.on_commit(plan_schedulers)

        return harvest

    @property
    def latest_intentions(self):
        """ Only latest intentions, retried intentions are skipped """

        latest_pks = (
            self.intentions.annotate(
                unique_field=models.functions.Concat(
                    models.F('credentials_id'),
                    models.F('credentials__version_hash'),
                    models.F('counter_report__code'),
                    models.F('start_date'),
                    models.F('end_date'),
                    output_field=models.CharField(),
                ),
            )
            .values('unique_field')
            .annotate(max_pk=models.Max('pk'))
            .values_list('max_pk', flat=True)
        )

        return self.intentions.filter(pk__in=latest_pks)


class Automatic(models.Model):
    month = models.DateField()
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='automatic_harvest'
    )
    harvest = models.OneToOneField(Harvest, on_delete=models.CASCADE)

    class Meta:
        constraints = (
            CheckConstraint(check=models.Q(month__day=1), name='fist_month_day'),
            UniqueConstraint(fields=['month', 'organization'], name='unique_month_organization'),
        )

    @staticmethod
    def _cmp_intentions(
        new: typing.List[FetchIntention], existing: typing.List[FetchIntention]
    ) -> typing.Tuple[typing.List[FetchIntention], typing.List[FetchIntention]]:
        """
        Compares intentions from existing to those which are
        supposed to be created

        :returns: intentions which need to be added, deleted and stats
        """
        new_map = {
            (e.start_date, e.end_date, e.counter_report.pk, e.credentials.pk): e for e in new
        }
        existing_map = {
            (e.start_date, e.end_date, e.counter_report.pk, e.credentials.pk): e for e in existing
        }

        # remove those which were e.g. disabled (no in new list)
        to_delete: typing.List[FetchIntention] = []
        for ekey, intention in existing_map.items():
            if ekey not in new_map:
                to_delete.append(intention)

        # add those which are not in list
        to_add: typing.List[FetchIntention] = []
        for nkey, intention in new_map.items():
            if nkey not in existing_map:
                to_add.append(intention)

        return (to_add, to_delete)

    @classmethod
    def next_month_trigger_time(cls):
        return datetime.combine(
            cls.next_month(), datetime.min.time(), tzinfo=timezone.get_current_timezone(),
        ) + timedelta(
            days=2
        )  # TODO customizable delta per scheduler

    @classmethod
    @transaction.atomic
    def update_for_next_month(cls) -> Counter:
        """ Updates automatic harvesting for next month """
        counter = Counter({"added": 0, "deleted": 0})

        next_month = cls.next_month()
        next_month_end = month_end(next_month)

        new_intentions: typing.List[FetchIntention] = []
        for cr2c in CounterReportsToCredentials.objects.filter(
            credentials__enabled=True, broken__isnull=True, credentials__broken__isnull=True
        ):
            new_intentions.append(
                FetchIntention(
                    not_before=cls.next_month_trigger_time(),
                    priority=FetchIntention.PRIORITY_NORMAL,
                    credentials=cr2c.credentials,
                    counter_report=cr2c.counter_report,
                    start_date=next_month,
                    end_date=next_month_end,
                )
            )

        # group by organization
        organization_to_intentions = {
            e.organization: []
            for e in Automatic.objects.filter(month=next_month)  # prefill with allready planned
        }

        for intention in new_intentions:
            org_intentions = organization_to_intentions.get(intention.credentials.organization, [])
            org_intentions.append(intention)
            organization_to_intentions[intention.credentials.organization] = org_intentions

        # compare and unschedule disabled
        for organization, intentions in organization_to_intentions.items():
            try:
                automatic = Automatic.objects.get(month=next_month, organization=organization)
            except Automatic.DoesNotExist:
                automatic = None
            if automatic:
                # delete missing
                existing_intentions = list(
                    FetchIntention.objects.select_for_update().filter(
                        start_date=next_month,
                        end_date=next_month_end,
                        credentials__organization=organization,
                        when_processed__isnull=True,
                    )
                )
                to_add, to_delete = cls._cmp_intentions(intentions, existing_intentions)
                counter.update({"added": len(to_add), "deleted": len(to_delete)})
                # Delete extra intentions
                FetchIntention.objects.filter(pk__in=[e.pk for e in to_delete]).delete()

                # Extends harvest with new intentions
                Harvest.plan_harvesting(to_add, automatic.harvest)

            else:
                # plan right away
                harvest = Harvest.plan_harvesting(intentions)
                counter.update({"added": len(intentions)})
                Automatic.objects.create(
                    month=next_month, organization=organization, harvest=harvest
                )

        return counter

    @classmethod
    def get_or_create(cls, month: date, organization: Organization) -> 'Automatic':
        month = month.replace(day=1)  # normalize month
        try:
            return cls.objects.get(month=month, organization=organization)
        except cls.DoesNotExist:
            return cls.objects.create(
                month=month, organization=organization, harvest=Harvest.objects.create()
            )

    @property
    def month_end(self):
        return month_end(self.month)

    @staticmethod
    def next_month():
        return month_start(timezone.now()) + relativedelta(months=1)
