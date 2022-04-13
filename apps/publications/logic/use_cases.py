import typing
from functools import reduce

from django.conf import settings
from django.db.models import Count, F, Max, Q, QuerySet
from publications.models import Platform
from sushi.models import AttemptStatus, SushiFetchAttempt


def get_use_cases(platforms: QuerySet[Platform]) -> typing.List[dict]:
    # Exclude fake urls
    fake_cond = reduce(
        lambda x, y: x | Q(url__icontains=y.rstrip("/")), settings.FAKE_SUSHI_URLS, Q()
    )
    return (
        SushiFetchAttempt.objects.filter(
            credentials_version_hash=F('credentials__version_hash'),
            status=AttemptStatus.SUCCESS,
            credentials__platform__in=platforms,
        )
        .annotate(
            url=F('credentials__url'),
            organization=F('credentials__organization'),
            platform=F('credentials__platform'),
            counter_version=F('credentials__counter_version'),
        )
        .exclude(fake_cond)
        .values("url", "organization", "platform", "counter_report", "counter_version")
        .annotate(latest=Max('timestamp'), count=Count('pk'))
    )
