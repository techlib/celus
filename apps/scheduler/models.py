import typing
import logging

from collections import Counter

from datetime import datetime, timedelta, date
from enum import Enum, auto

from celery import states
from dateutil.relativedelta import relativedelta
from django.db import models, transaction, DatabaseError
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.db.models.functions import Coalesce
from django.conf import settings
from django.db.models import TextField, Max, IntegerField, F, Q
from django.utils import timezone
from django.utils.functional import cached_property
from django_celery_results.models import TaskResult

from core.models import User
from core.logic.dates import month_start, month_end
from nigiri.error_codes import ErrorCode
from organizations.models import Organization
from publications.models import Platform
from sushi.models import (
    SushiCredentials,
    SushiFetchAttempt,
    CounterReportType,
    CounterReportsToCredentials,
    CreatedUpdatedMixin,
)
from logs.tasks import import_one_sushi_attempt_task


logger = logging.getLogger(__name__)


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
    BROKEN = auto()  # Credentials of FetchIntention are marked as broken
    DUPLICATE = auto()  # FetchIntention was marked as duplicate


# TODO scheduler cleanup (to many invalid urls)
class Scheduler(models.Model):
    """ Represents attempt scheduling based on remote URL """

    DEFAULT_COOLDOWN_DELAY = 5  # in seconds
    DEFAULT_TOO_MANY_REQUESTS_DELAY = 60 * 60  # in seconds
    DEFAULT_SERVICE_NOT_AVAILABLE_DELAY = 60 * 60  # in seconds
    DEFAULT_SERVICE_BUSY_DELAY = 60  # in seconds

    JOB_TIME_LIMIT = 60 * 60  # in seconds

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

    current_intention = models.OneToOneField(
        'scheduler.FetchIntention',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='current_scheduler',
    )
    current_celery_task_id = models.UUIDField(null=True, blank=True)
    current_start = models.DateTimeField(null=True, blank=True)

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

    def run_next(self, celery_task_id: typing.Optional[str] = None) -> RunResponse:
        """
        This function can take a while so it should be run only in celery.
        And should not be run within transaction.
        """
        # Check whether scheduler is in cooldown period
        if self.last_time:
            last_plus_cooldown = self.last_time + timedelta(seconds=self.cooldown)
            if last_plus_cooldown > timezone.now():
                self.when_ready = last_plus_cooldown
                self.save()
                return RunResponse.COOLDOWN

        # Locking scheduler
        with transaction.atomic():
            try:
                # lock this instance by evaluating select_for_update query
                Scheduler.objects.select_for_update(nowait=True).get(
                    pk=self.pk, current_intention__isnull=True, current_celery_task_id__isnull=True,
                )
            except (Scheduler.DoesNotExist, DatabaseError):
                # Locked - currently processing data
                return RunResponse.BUSY

            with transaction.atomic():
                # Takes the first intention
                intention = (
                    FetchIntention.objects.select_for_update(skip_locked=True)
                    .filter(
                        models.Q(
                            scheduler__isnull=True,
                            duplicate_of__isnull=True,
                            credentials__url=self.url,
                            credentials__broken__isnull=True,
                            when_processed__isnull=True,
                            not_before__lte=timezone.now(),
                        )
                        & models.Q(
                            models.Exists(
                                CounterReportsToCredentials.objects.filter(
                                    counter_report=models.OuterRef('counter_report'),
                                    credentials=models.OuterRef('credentials'),
                                    broken__isnull=True,
                                )
                            )
                        )
                    )
                    .order_by('-priority', 'not_before')
                    .first()
                )

                if not intention:
                    return RunResponse.IDLE

                # Check whether scheduler is ready or has sufficient priority
                if self.when_ready <= timezone.now() or intention.priority_now:
                    # Assign intention to scheduler which will cause that the scheduler
                    # would become "locked" (unable to process other fetch intentions)
                    intention.scheduler = self
                    intention.save()
                    self.current_intention = intention
                    self.current_celery_task_id = celery_task_id
                    self.current_start = timezone.now()
                    self.save()
                else:
                    return RunResponse.IDLE

        # processing fetch intention
        with transaction.atomic(savepoint=True):

            # It may take so time to process the intetion
            # (download the data)
            process_response = intention.process()

            # lock scheduler
            Scheduler.objects.select_for_update().get(pk=self.pk)

            # There is a slight chance that this scheduler
            # was unlocked using cron job at this point
            self.refresh_from_db()
            if str(self.current_celery_task_id) != str(celery_task_id):
                # Discard results of this this run,
                # another celery task might be already running to process the intention
                logger.warning(
                    "Unlocked Scheduler's FetchIntention was finished; Performing rollback"
                )
                transaction.set_rollback(True)
                return RunResponse.PROCESSED

            # Analyze the process result
            if process_response == ProcessResponse.BROKEN:
                # Credentials are broken
                res = RunResponse.BROKEN
            else:
                # Update cooldown delay
                self.when_ready = timezone.now() + timedelta(seconds=self.cooldown)
                res = RunResponse.PROCESSED

            self.unassign_intention()
            self.save()

        return res

    def unassign_intention(self):
        self.current_intention = None
        self.current_celery_task_id = None
        self.current_start = None
        self.save()

    @classmethod
    def unlock_stucked_schedulers(cls):
        with transaction.atomic():

            def update_intention(scheduler: 'Scheduler'):
                # Remove scheduler for unprocessed intention
                # so it can be rescheduled
                if (
                    scheduler.current_intention
                    and scheduler.current_intention.when_processed is None
                ):
                    scheduler.current_intention.scheduler = None
                    # put intention back in the intention queue
                    scheduler.current_intention.not_before = max(
                        timezone.now(), scheduler.current_intention.not_before
                    )
                    scheduler.current_intention.save()

            # unlock based on celery task id
            for scheduler in cls.objects.select_for_update().filter(
                Q(current_celery_task_id__isnull=False)
            ):
                if TaskResult.objects.filter(
                    task_id__iexact=str(scheduler.current_celery_task_id),
                    status__in=states.READY_STATES,
                ).exists():
                    update_intention(scheduler)
                    scheduler.unassign_intention()
                logger.info("Scheduler %s was unlocked (task finished)", scheduler)

            # unlocked based on time
            for scheduler in cls.objects.select_for_update().filter(
                Q(current_start__lt=timezone.now() - timedelta(seconds=cls.JOB_TIME_LIMIT))
            ):
                update_intention(scheduler)
                scheduler.unassign_intention()
                logger.info("Scheduler %s was unlocked (timeout)", scheduler)


class FetchIntentionQuerySet(models.QuerySet):
    def annotate_credentials_state(self) -> models.QuerySet:
        return self.annotate(
            broken_creds=F('credentials__broken'),
            broken_mapping=models.Exists(
                CounterReportsToCredentials.objects.filter(
                    counter_report=models.OuterRef('counter_report'),
                    credentials=models.OuterRef('credentials'),
                    broken__isnull=False,
                )
            ),
            missing_mapping=~models.Exists(
                CounterReportsToCredentials.objects.filter(
                    counter_report=models.OuterRef('counter_report'),
                    credentials=models.OuterRef('credentials'),
                )
            ),
        )

    def annotate_unique(self) -> models.QuerySet:
        return self.annotate(
            unique_field=models.functions.Concat(
                models.F('credentials_id'),
                models.F('credentials__version_hash'),
                models.F('counter_report__code'),
                models.F('start_date'),
                models.F('end_date'),
                output_field=TextField(),
            )
        )

    def aggregate_stats(self) -> typing.Dict[str, int]:
        qs = self.annotate_unique()

        res = qs.aggregate(
            total=Coalesce(models.Count('unique_field', distinct=True), 0),
            unprocessed=Coalesce(
                models.Count(
                    'unique_field',
                    distinct=True,
                    filter=models.Q(when_processed__isnull=True)
                    & models.Q(duplicate_of__isnull=True),
                ),
                0,
            ),
        )
        res['finished'] = res['total'] - res['unprocessed']

        return res

    def schedulers_to_trigger(self) -> typing.List[Scheduler]:
        res: typing.Set[Scheduler] = set()
        for fi in self.filter(
            not_before__lt=timezone.now(), scheduler__isnull=True, duplicate_of__isnull=True
        ):
            (scheduler, _) = Scheduler.objects.get_or_create(url=fi.credentials.url)
            if (
                scheduler.current_celery_task_id is None
                and scheduler.current_intention is None
                and (scheduler.when_ready < timezone.now() or fi.priority_now)
            ):
                res.add(scheduler)

        return list(res)

    def latest_intentions(self, within_harvest=False) -> models.QuerySet:
        """ Only latest intentions, retried intentions are skipped """

        extra_filters = {"harvest": models.OuterRef('harvest')} if within_harvest else {}

        return (
            self.annotate_unique()
            .annotate(
                max_pk=models.Subquery(
                    self.annotate_unique()
                    .filter(unique_field=models.OuterRef('unique_field'), **extra_filters)
                    .values('unique_field')
                    .annotate(max_pk=models.Max('pk'))
                    .values("max_pk")[:1],
                    output_field=IntegerField(),
                )
            )
            .filter(pk=models.F('max_pk'))
        )


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
        Scheduler, related_name="intentions", on_delete=models.CASCADE, null=True, blank=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    when_processed = models.DateTimeField(
        help_text="When fetch intention was processed", null=True, blank=True
    )
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
            self.current_scheduler
            return True
        except Scheduler.DoesNotExist:
            return False

    @property
    def priority_now(self) -> bool:
        return self.priority >= FetchIntention.PRIORITY_NOW

    @property
    def is_processed(self):
        return self.when_processed is not None

    @property
    def broken_credentials(self) -> bool:
        if (
            hasattr(self, 'broken_creds')
            and hasattr(self, 'broken_mapping')
            and hasattr(self, 'missing_mapping')
        ):
            return self.broken_creds or self.broken_mapping or self.missing_mapping

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
            # transaction.on_commit(lambda: import_one_sushi_attempt_task.delay(attempt.pk))

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


class HarvestQuerySet(models.QuerySet):
    def annotate_stats(self):
        return self.annotate(
            unprocessed=Coalesce(
                models.Subquery(
                    FetchIntention.objects.filter(harvest=models.OuterRef('pk'))
                    .annotate_unique()
                    .values('harvest')
                    .annotate(
                        count=models.Count(
                            'unique_field',
                            distinct=True,
                            filter=models.Q(when_processed__isnull=True)
                            & models.Q(duplicate_of__isnull=True),
                        )
                    )
                    .values('count')
                ),
                0,
            ),
            total=Coalesce(
                models.Subquery(
                    FetchIntention.objects.filter(harvest=models.OuterRef('pk'))
                    .annotate_unique()
                    .values('harvest')
                    .annotate(count=models.Count('unique_field', distinct=True))
                    .values('count')
                ),
                0,
            ),
            finished=F('total') - F('unprocessed'),
        )


class Harvest(CreatedUpdatedMixin):

    objects = HarvestQuerySet.as_manager()

    def __str__(self):
        return f'Harvest #{self.pk}'

    def stats(self) -> typing.Tuple[int, int]:
        """ Returns how many intentions are finished.
        Note that it considers replaned intentions as one

        :returns: unprocessed, total
        """

        # Harvest obtained via annotated query
        # No need to perform extra query
        if hasattr(self, 'total') and hasattr(self, 'unprocessed'):
            return self.unprocessed, self.total

        # query for stats
        qs = self.intentions.aggregate_stats()
        return qs["unprocessed"], qs["total"]

    def organizations(self) -> typing.List[Organization]:
        if hasattr(self, 'intentions_credentials'):
            organizations = list({i.credentials.organization for i in self.intentions_credentials})
            organizations.sort(key=lambda e: e.pk)
            return organizations

        return list(
            Organization.objects.filter(
                pk__in=self.intentions.all().values('credentials__organization_id')
            )
            .order_by()
            .distinct()
        )

    def platforms(self) -> typing.List[Platform]:
        if hasattr(self, 'intentions_credentials'):
            platforms = list({i.credentials.platform for i in self.intentions_credentials})
            platforms.sort(key=lambda e: e.pk)
            return platforms

        return (
            Platform.objects.filter(pk__in=self.intentions.all().values('credentials__platform_id'))
            .order_by()
            .distinct()
        )

    @cached_property
    def max_not_before(self):
        return self.intentions.aggregate(max=Max('not_before'))['max']

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

        if hasattr(self, 'prefetched_latest_intentions'):
            return self.prefetched_latest_intentions

        return (
            self.intentions.latest_intentions(within_harvest=True)
            .annotate_credentials_state()
            .select_related(
                'attempt',
                'attempt__counter_report',
                'attempt__credentials',
                'attempt__credentials__organization',
                'attempt__credentials__platform',
                'attempt__import_batch',
                'counter_report',
                'credentials',
                'credentials__platform',
                'credentials__organization',
                'duplicate_of',
            )
        )


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
