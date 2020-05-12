import logging
from collections import Counter
from datetime import timedelta
from time import time

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.transaction import atomic

from logs.models import ReportType, AccessLog, DimensionText
from publications.models import Title


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Go over all titles and set their publication_type from Data_Type in corresponding '
        'AccessLogs'
    )

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        # prepare the report_types that have Data_Type dimension and store its attribute name
        # to make things faster later on
        report_types = []
        dim_name = 'Data_Type'
        for report_type in (
            ReportType.objects.all().annotate(rec_count=Count('accesslog')).order_by('-rec_count')
        ):
            if dim_name in report_type.dimension_short_names:
                data_type_idx = report_type.dimension_short_names.index(dim_name)
                report_type.data_type_attr_ = f'dim{data_type_idx + 1}'
                report_types.append(report_type)
        logger.info('Report types: %s', report_types)
        stats = Counter()
        pub_type_stats = Counter()
        result_stats = Counter()
        dim_value_to_text = {
            dt.pk: dt.text for dt in DimensionText.objects.filter(dimension__short_name=dim_name)
        }
        # process titles one by one even though it is slow - we don't care, this is one-off script
        start = time()
        title_count = Title.objects.count()
        logger.info('Found %d titles', title_count)
        for i, title in enumerate(Title.objects.all().iterator()):
            final_pub_type = Title.PUB_TYPE_UNKNOWN
            # we try all possible report types to see if we get publication type from Data_Type
            for report_type in report_types:
                data_types = (
                    AccessLog.objects.filter(target_id=title.pk, report_type=report_type)
                    .exclude(**{report_type.data_type_attr_ + '__isnull': True})
                    .values(report_type.data_type_attr_)
                    .annotate(log_count=Count('pk'))
                    .order_by('-log_count')
                )
                if data_types:
                    stats[len(data_types)] += 1
                    # we sorted by occurrence, so we can use the first one as the most widely used
                    dim_value = data_types[0][report_type.data_type_attr_]
                    data_type_name = dim_value_to_text[dim_value]
                    pub_type = Title.data_type_to_pub_type(data_type_name)
                    pub_type_stats[pub_type] += 1
                    final_pub_type = pub_type
                    if final_pub_type != Title.PUB_TYPE_UNKNOWN:
                        break
            # if we get nothing from Data_Types, we try to guess from other data, like isbn
            if final_pub_type == Title.PUB_TYPE_UNKNOWN:
                final_pub_type = title.guess_pub_type()
            # finally we save it
            if final_pub_type != title.pub_type:
                # if final_pub_type in 'OU':
                #     print(final_pub_type, title, 'isbn:', title.isbn, 'issn:', title.issn)
                result_stats['update'] += 1
                result_stats[f'{title.pub_type}->{final_pub_type}'] += 1
                title.pub_type = final_pub_type
                title.save(update_fields=['pub_type'])
            else:
                result_stats['keep'] += 1
            if i and i % 100 == 0:
                delta = time() - start
                eta = timedelta(seconds=delta * (title_count - i) / i)
                logger.info(
                    'Titles: %d/%d; %.1f s; %.1f tps; ETA: %s',
                    i,
                    title_count,
                    delta,
                    i / delta,
                    eta,
                )
                logger.info(
                    'Stats: %s, pub_types: %s, result_stats: %s',
                    stats,
                    pub_type_stats,
                    result_stats,
                )
