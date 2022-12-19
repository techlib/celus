from abc import ABC, abstractmethod
from datetime import date, datetime

from django.conf import settings
from django.db import models

from core.logic.type_conversion import to_list
from logs.models import AccessLog, DimensionText
from tags.models import Tag


# 10 chars per id should be OK
CLICKHOUSE_ID_COUNT_LIMIT = settings.CLICKHOUSE_QUERY_SIZE_LIMIT // 10


class ClickhouseIncompatibleFilter(ValueError):
    """
    Raised when a filter cannot return query params compatible with Clickhouse.
    """


class DimensionFilter(ABC):
    def __init__(self, dimension: str):
        self.dimension: str = dimension

    def __str__(self):
        return f'{self.dimension}: {self.value_str}'

    @property
    def value_str(self) -> str:
        return ''

    @abstractmethod
    def query_params(self, primary_filter=False, clickhouse_compatible=False) -> dict:
        """
        When `primary_filter` is False, the filter params should be returned for the AccessLog model
        if `primary_filter` is True, it should be for the dimension model itself.

        `clickhouse_compatible` should be set to True if the resulting params should be converted
        for use in ClickHouse queries. Not all filters will need this distinction, but some will.

        The returned dict will be passed as individual kwargs to the `.filter` method of a QuerySet
        """

    @abstractmethod
    def config(self) -> dict:
        """
        Returns a dict describing the filter and suitable for storage.
        """


class DateDimensionFilter(DimensionFilter):
    def __init__(self, dimension: str, start, end):
        super().__init__(dimension)
        self.start = start
        self.end = end

    @property
    def value_str(self) -> str:
        return f'{self.start} - {self.end}'

    def query_params(self, primary_filter=False, clickhouse_compatible=False) -> dict:
        ret = {}
        if self.start:
            ret[f'{self.dimension}__gte'] = self.start
        if self.end:
            ret[f'{self.dimension}__lte'] = self.end
        return ret

    def config(self):
        return {
            'dimension': self.dimension,
            'start': self.serialize_date(self.start),
            'end': self.serialize_date(self.end),
        }

    @classmethod
    def serialize_date(cls, value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        return value


class ForeignKeyDimensionFilter(DimensionFilter):
    def __init__(self, dimension, values):
        super().__init__(dimension)
        values = to_list(values)
        # convert model instances to their primary keys
        values = [val.pk if isinstance(val, models.Model) else val for val in values]
        self.values = values

    @property
    def value_str(self) -> str:
        field, modifier = AccessLog.get_dimension_field(self.dimension)
        objs = field.related_model.objects.filter(pk__in=self.values)
        values = [obj.name or obj.short_name for obj in objs]
        return '; '.join(str(val) for val in values)

    def query_params(self, primary_filter=False, clickhouse_compatible=False) -> dict:
        if primary_filter:
            return {'pk__in': self.values}
        return {f'{self.dimension}_id__in': self.values}

    def config(self):
        return {'dimension': self.dimension, 'values': self.values}


class ExplicitDimensionFilter(DimensionFilter):
    def __init__(self, dimension, values):
        super().__init__(dimension)
        self.values = to_list(values)

    @property
    def value_str(self):
        return '; '.join(val.text for val in DimensionText.objects.filter(pk__in=self.values))

    def query_params(self, primary_filter=False, clickhouse_compatible=False) -> dict:
        return {f'{self.dimension}__in': self.values}

    def config(self):
        return {'dimension': self.dimension, 'values': self.values}


class TagDimensionFilter(DimensionFilter):
    def __init__(self, dimension, tag_ids):
        super().__init__(dimension)
        if dimension not in ['target', 'platform', 'organization']:
            raise ValueError(f'Unsupported dimension for tagging: {dimension}')
        self.tag_ids = [tag.pk if isinstance(tag, Tag) else tag for tag in to_list(tag_ids)]

    @property
    def value_str(self):
        return '; '.join(val.name for val in Tag.objects.filter(pk__in=self.tag_ids))

    def query_params(self, primary_filter=False, clickhouse_compatible=False) -> dict:
        if primary_filter:
            return {'tags__in': self.tag_ids}
        # here we translate the tag ids to related object ids and use it for query,
        # querying tags directly in the query (like `platform__tags__in`) hits a nesting limit
        # inside Django
        field, _modifier = AccessLog.get_dimension_field(self.dimension)
        rel_model = field.remote_field.model

        obj_ids_qs = (
            rel_model.objects.filter(tags__in=self.tag_ids).values_list('pk', flat=True).distinct()
        )
        # By default, we try to convert the queryset to a list of ids.
        #
        # This is necessary when using clickhouse, but I found that it speeds up the query even
        # in Postgres
        #  - for tag with 1000 titles it is 12 s => 2.2 s (5.5x faster)
        #  - for tag with 10000 titles it is 26 s => 2.7 s (9.5x faster)
        #
        # (CH is 2-3x faster than even than the faster Postgres query)
        #
        # On the other hand, if the list is really long, then postgres will get slower
        # and clickhouse will fail with a query string length limit.
        # Therefore, we use this only for tags with less than 20k titles in PG,
        # or `CLICKHOUSE_ID_COUNT_LIMIT` in CH.
        size_limit = CLICKHOUSE_ID_COUNT_LIMIT if clickhouse_compatible else 20_000
        if obj_ids_qs.count() > size_limit:
            if clickhouse_compatible:
                # when clickhouse compatibility is requested, we have to raise an error
                raise ClickhouseIncompatibleFilter('Too many ids to use in query')
            # otherwise we just use the queryset
            obj_ids = obj_ids_qs
        else:
            obj_ids = list(obj_ids_qs)
        return {f'{self.dimension}_id__in': obj_ids}

    def config(self):
        return {'dimension': self.dimension, 'tag_ids': self.tag_ids}
