import logging
import sys
from statistics import mean
from time import monotonic

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Q, FilteredRelation

from logs.models import AccessLog, ReportType
from publications.models import Title
from tags.models import Tag, TagScope, TitleTag, TagClass

logger = logging.getLogger(__name__)


def print_time_stats(times, title=''):
    print(
        f'{title}: '
        f'avg={1000*mean(times):.1f} ms, '
        f'min={1000*min(times):.1f} ms, '
        f'max={1000*max(times):.1f} ms'
    )


class Command(BaseCommand):

    help = 'Runs some queries using tags and prints out statistics.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        print(
            f'Stats: '
            f'tagclasses={TagClass.objects.count():,}, '
            f'tags={Tag.objects.count():,}, '
            f'titletags={TitleTag.objects.count():,}'
        )
        print('-----------------------------------------------------')
        self.test_count_titles_by_tag()
        self.test_count_titles_by_tagclass()
        self.test_group_by_tag()
        self.test_title_interest_by_title()
        self.test_title_interest_by_tag()
        self.test_title_interest_group_by_tag()

    @classmethod
    def test_count_titles_by_tag(cls):
        times = []
        for tag in Tag.objects.filter(tag_class__scope=TagScope.TITLE):
            start = monotonic()
            tag.titles.count()
            times.append(monotonic() - start)
        print_time_stats(times, 'Title count by tag')
        return times

    @classmethod
    def test_count_titles_by_tagclass(cls):
        times = []
        for tag in TagClass.objects.filter(scope=TagScope.TITLE):
            start = monotonic()
            Title.objects.filter(tags__tag_class=tag).count()
            times.append(monotonic() - start)
        print_time_stats(times, 'Title count by tag class')
        return times

    @classmethod
    def test_group_by_tag(cls):
        start = monotonic()
        list(Tag.objects.filter(tag_class__scope=TagScope.TITLE).annotate(Count('titles')))
        duration = monotonic() - start
        print(f'Titles group by tag: time={1000*duration:.1f} ms')
        return [duration]

    @classmethod
    def test_title_interest_by_tag(cls):
        times = []
        rt = ReportType.objects.get(short_name='interest')
        for tag in Tag.objects.filter(tag_class__scope=TagScope.TITLE)[:20]:
            start = monotonic()
            AccessLog.objects.filter(report_type_id=rt.pk, target__tags=tag).aggregate(
                score=Sum('value')
            )
            times.append(monotonic() - start)
            print('.', end='')
            sys.stdout.flush()
        print('\r', end='')
        print_time_stats(times, 'Interest sum by tag')
        return times

    @classmethod
    def test_title_interest_group_by_tag(cls):
        rt = ReportType.objects.get(short_name='interest')
        qs = (
            Tag.objects.filter(tag_class__scope=TagScope.TITLE)
            .annotate(
                relevant_accesslogs=FilteredRelation(
                    'titles__accesslog', condition=Q(titles__accesslog__report_type_id=rt.pk)
                )
            )
            .annotate(score=Sum('relevant_accesslogs__value'))
        )
        start = monotonic()
        list(qs)
        duration = monotonic() - start
        print(f'Interest group by tag: time={1000*duration:.1f} ms')
        return [duration]

    @classmethod
    def test_title_interest_by_title(cls):
        """
        This is just a baseline without tag use to have some frame of reference for
        `test_title_interest_by_tag`
        :return:
        """
        times = []
        for title in Title.objects.all().order_by('?')[:20]:
            start = monotonic()
            AccessLog.objects.filter(report_type__short_name='interest', target=title).aggregate(
                score=Sum('value')
            )
            times.append(monotonic() - start)
            print('.', end='')
            sys.stdout.flush()
        print('\r', end='')
        print_time_stats(times, '~~ Interest sum by title')
        return times
