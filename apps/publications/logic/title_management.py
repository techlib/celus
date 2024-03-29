import logging
import operator
from functools import reduce
from itertools import combinations
from time import time
from typing import Generator, List, Set, Union

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count
from django.db.models.functions import Lower
from logs.logic.clickhouse import resync_import_batch_with_clickhouse
from logs.logic.data_import import TitleManager
from logs.models import AccessLog, ImportBatch
from publications.models import PlatformTitle, Title

logger = logging.getLogger(__name__)


def find_mergeable_titles(batch_size: int = 100) -> Generator[List[Title], None, None]:
    """
    Goes over all titles and identifies those that could be merged.
    :return: List of lists of titles - first title in a list is the one that should be preserved
    """
    # the order_by('lname') replaces the default ordering which would mess up the grouping
    start = time()
    qs = (
        Title.objects.all()
        .annotate(lname=Lower('name'))
        .values('lname')
        .order_by('lname')
        .annotate(title_count=Count('pk'), title_ids=ArrayAgg('pk'))
        .filter(title_count__gt=1)
    )
    logger.info('Found %d potentially mergeable title groups', qs.count())
    logger.info('Query took %f seconds', time() - start)
    start = time()

    # because there may be a large number of candidates (tens of thousands), we do not want
    # to make a db query for each group. Therefor we use a buffer to group several groups
    # together for query. It makes the code more complicated, but much faster
    buffer = []

    def process_buffer():
        buffer_ids = reduce(operator.add, [buf_rec['title_ids'] for buf_rec in buffer])
        buffer_titles = {t.pk: t for t in Title.objects.filter(pk__in=buffer_ids)}
        for record in buffer:
            titles = [buffer_titles[t_id] for t_id in record['title_ids']]
            for group in titles_to_matching_groups(titles):
                yield sort_mergeable_titles(group)

    for i, rec in enumerate(qs):
        buffer.append(rec)
        if len(buffer) == batch_size:
            for grp in process_buffer():
                yield grp
            buffer = []
        if i % 1000 == 0:
            logger.info('Processed %d groups in %f seconds', i, time() - start)
    if buffer:
        for grp in process_buffer():
            yield grp


def titles_to_matching_groups(titles: List[Title]) -> List[List[Title]]:
    """
    Takes a list of possibly matching titles and returns a list of groups where the titles
    really match. The groups are disjunct
    """
    id_groups = []
    for t1, t2 in combinations(titles, 2):
        t1rec = TitleManager.title_to_titlerec(t1)
        t1cand = TitleManager.title_to_titlecomparerec(t2)
        # we only use one candidate for selection, so if something returns, there is a match
        if TitleManager.select_best_candidate(t1rec, [t1cand]):
            id_groups.append({t1.pk, t2.pk})
    # we have all the tuples as sets in id_groups
    # now we need to merge the groups together if there is an overlap
    # we go over the groups and if there is an overlap, we join them together
    # we do it as long as there are no changes anymore
    new_groups = []
    while id_groups:
        grp = id_groups.pop(0)
        change = True
        while change:
            # we try while there is some change because the last group we merge into grp
            # may cause it to overlap with some it did not match before
            unmatched_groups = []
            change = False
            for other in id_groups:
                if grp & other:
                    grp |= other
                    change = True
                else:
                    unmatched_groups.append(other)
            id_groups = unmatched_groups
        new_groups.append(grp)

    # now recode and return
    id_to_obj = {t.pk: t for t in titles}
    return [[id_to_obj[pk] for pk in grp] for grp in new_groups]


def sort_mergeable_titles(titles: List[Title]) -> List[Title]:
    """
    Sorts the titles so that the first one will be the one to be kept when merging titles.
    It tries to determine which of the titles is used the most and keep it, so that the
    changes in the database will be as small as possible.
    """
    return list(
        Title.objects.filter(pk__in=[t.pk for t in titles])
        .annotate(pt_count=Count('platformtitle'))
        .order_by('-pt_count')
    )


def merge_titles(titles: List[Title], skip_ch_sync=False) -> (Title, Set[int]):
    """
    Joins data from given titles under the first title and changes other data
    (AccessLogs, PlatformTitles) to match the new title and deletes the other titles.

    if `skip_ch_sync` is given, no sync with Clickhouse will be performed. It is up to the
    calling code to do it for all the import batches involved (their ids are returned as part 2).

    :return: (remaining title, set of import batch ids modified by the merge)
    """
    dest, *to_remove = titles
    save = False
    # these import batches should be resynced with CH after the merge because AccessLogs inside
    # have been modified
    ibs_to_resync = set()
    for title in to_remove:
        for attr in ('issn', 'eissn', 'isbn', 'doi'):
            if not getattr(dest, attr) and (update := getattr(title, attr)):
                setattr(dest, attr, update)
                save = True
        if pid_extra := set(title.proprietary_ids) - set(dest.proprietary_ids):
            dest.proprietary_ids += list(pid_extra)
            save = True
        if uris_extra := set(title.uris) - set(dest.uris):
            dest.uris += list(uris_extra)
            save = True
        ibs_to_resync |= replace_title(title, dest)
    logger.debug(
        'Deleting merged titles: %s',
        Title.objects.filter(pk__in=[t.pk for t in to_remove]).delete(),
    )
    if save:
        dest.save()
    # deal with clickhouse
    if settings.CLICKHOUSE_SYNC_ACTIVE:
        for ib in ImportBatch.objects.filter(pk__in=ibs_to_resync):
            resync_import_batch_with_clickhouse(ib)
    return dest, ibs_to_resync


def replace_title(source: Title, dest: Union[Title, int]) -> Set[int]:
    """
    Replaces the `source` title with the `dest` title in all related models. `dest` may be either
    a Title instance or a pk of one.

    Returns a set of IDs of import batches touched by the change
    """
    dest_pk = dest.pk if isinstance(dest, Title) else dest
    ibs_to_resync = set(
        AccessLog.objects.filter(target=source).values_list('import_batch_id', flat=True).distinct()
    )
    logger.debug(
        'AccessLog title update: %s',
        AccessLog.objects.filter(target=source).update(target_id=dest_pk),
    )
    logger.debug(
        'PlatformTitle title update: %d',
        len(
            PlatformTitle.objects.bulk_create(
                [
                    PlatformTitle(title_id=dest_pk, **rec)
                    for rec in PlatformTitle.objects.filter(title=source).values(
                        'platform_id', 'organization_id', 'date'
                    )
                ],
                ignore_conflicts=True,  # PlatformTitles may already exist, so ignore conflicts
            )
        ),
    )
    return ibs_to_resync
