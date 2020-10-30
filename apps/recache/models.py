import pickle
from datetime import timedelta
from hashlib import blake2b
from statistics import mean
from time import monotonic

import django
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, IntegrityError
from django.db.models import F, ExpressionWrapper, DateTimeField
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now

BLAKE_HASH_SIZE = 16
DEFAULT_TIMEOUT = timedelta(seconds=60 * 60)  # 1 hour
DEFAULT_LIFETIME = timedelta(days=30)  # 30 days


class RenewalError(Exception):
    pass


class CachedQueryQuerySet(models.QuerySet):
    def get_for_queryset(self, queryset):
        """
        Gets `CachedQuery` for a query represented by the `queryset` object
        """
        qs_hash = CachedQuery.compute_queryset_hash(queryset)
        return self.get(query_hash=qs_hash, django_version=django.get_version())

    def create_from_queryset(
        self,
        queryset,
        timeout: timedelta = DEFAULT_TIMEOUT,
        lifetime: timedelta = DEFAULT_LIFETIME,
        origin='',
    ):
        qs_hash = CachedQuery.compute_queryset_hash(queryset)
        queryset_pickle = pickle.dumps(queryset)

        return self.create(
            model=ContentType.objects.get_for_model(queryset.model),
            query_hash=qs_hash,
            query_string=str(queryset.query),
            queryset_pickle=queryset_pickle,
            django_version=django.get_version(),
            timeout=timeout,
            lifetime=lifetime,
            origin=origin,
        )

    def past_timeout(self):
        """
        Returns objects that are past timeout (`last_update` + `timeout` is in the past) and have
        to be re-evaluated
        """
        # the name 'valid_until' is used by a property of CachedQuery, so it cannot be used here
        # therefore we use the `valid_until_db` attr
        return self.annotate(
            valid_until_db=ExpressionWrapper(
                F('last_updated') + F('timeout'), output_field=DateTimeField()
            )
        ).filter(valid_until_db__lt=now())

    def past_lifetime(self):
        """
        Returns objects that are past lifetime (`last_queried` + `lifetime` is in the past) and
        have to be removed
        """
        return self.annotate(
            live_until=ExpressionWrapper(
                F('last_queried') + F('lifetime'), output_field=DateTimeField()
            )
        ).filter(live_until__lt=now())


class CachedQuery(models.Model):

    objects = CachedQueryQuerySet.as_manager()

    origin = models.CharField(
        max_length=32,
        blank=True,
        help_text="Optional identifier of the query's origin. "
        "For info only, is not used when querying for cached queries",
    )
    model = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    query_hash = models.CharField(
        max_length=BLAKE_HASH_SIZE * 2, help_text='Hash of the query string',
    )
    query_string = models.TextField()
    queryset_pickle = models.BinaryField(help_text='Pickle of the evaluated queryset with results')
    django_version = models.CharField(
        max_length=16, help_text='Version of Django that created the last pickle'
    )
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(
        default=now, help_text='Last time queryset_pickle was updated'
    )
    last_queried = models.DateTimeField(
        default=now, help_text='Last time someone queried this data - read the queryset'
    )
    timeout = models.DurationField(
        default=DEFAULT_TIMEOUT, help_text='Number of seconds until the queryset it re-evaluated'
    )
    lifetime = models.DurationField(
        default=DEFAULT_LIFETIME,
        help_text='Number of seconds from last querying after which the cache will be removed',
    )
    hit_count = models.PositiveIntegerField(
        default=0, help_text='The number of times cache was successfully used'
    )
    query_durations = ArrayField(
        models.FloatField(),
        default=list,
        help_text='Each item is a duration of the query in seconds. It is updated for each renewal',
    )

    class Meta:
        verbose_name_plural = 'Cached queries'
        unique_together = [('query_hash', 'django_version')]

    def __str__(self):
        return self.query_hash

    @classmethod
    def compute_queryset_hash(cls, queryset):
        return blake2b(str(queryset.query).encode('utf-8'), digest_size=BLAKE_HASH_SIZE).hexdigest()

    @property
    def valid_until(self):
        return self.last_updated + self.timeout

    @property
    def is_valid(self):
        return self.valid_until > now()

    @property
    def is_too_old(self):
        """
        If the object was not updated in twice the `timeout`, it is considered old
        """
        return self.last_updated + 2 * self.timeout < now()

    def renew(self):
        """
        Checks if the query should already be renewed and renews if needed.
        """
        if self.valid_until < now() or self.django_version != django.get_version():
            self.force_renew(catch_refresh_errors=self.django_version != django.get_version())

    def force_renew(self, catch_refresh_errors: bool = False):
        """
        Re-evaluates the stored queryset and stores the new result

        :arg catch_refresh_errors: when True, potential `get_fresh_queryset` exceptions will be caught and re-raised
          as `RenewError`. This is useful when renewing querysets from old Django versions which raise errors due to
          queryset interface changes.
        """
        try:
            queryset = self.get_fresh_queryset()
        except Exception as exc:
            if catch_refresh_errors:
                raise RenewalError(f'Could not renew queryset because of error: {exc}')
            raise

        start = monotonic()
        self.queryset_pickle = pickle.dumps(queryset)
        self.last_updated = now()
        self.query_durations.append(monotonic() - start)
        orig_django_version = self.django_version
        self.django_version = django.get_version()
        try:
            with atomic():
                self.save()
        except IntegrityError:
            # the only reason this can happen now is if there already is cached query
            # for the same hash and the current django version

            # we restore the original django version in order not to pollute the object at hand
            self.django_version = orig_django_version
            raise RenewalError('CachedQuery with current django version already exists')

    def get_fresh_queryset(self):
        """
        Returns a new, unevaluated queryset based on the stored data
        """
        # .all() creates a fresh copy of the queryset
        return self.get_cached_queryset(record_hit=False).all()

    def get_cached_queryset(self, record_hit=True):
        """
        Returns the cached queryset including all results

        :arg record_hit: When true, the `hit_count` field will be increased and `last_queried` updated
        """
        if record_hit:
            self.last_queried = now()
            self.hit_count = F('hit_count') + 1
            self.save(update_fields=('last_queried', 'hit_count'))
        return pickle.loads(self.queryset_pickle)

    @cached_property
    def avg_query_duration(self):
        return mean(self.query_durations) if self.query_durations else None
