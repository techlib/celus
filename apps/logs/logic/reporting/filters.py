from abc import ABC, abstractmethod
from datetime import datetime, date

from django.db import models

from core.logic.type_conversion import to_list
from logs.models import DimensionText, AccessLog


class DimensionFilter(ABC):
    def __init__(self, dimension: str):
        self.dimension: str = dimension

    def __str__(self):
        return f'{self.dimension}: {self.value_str}'

    @property
    def value_str(self) -> str:
        return ''

    @abstractmethod
    def query_params(self, primary_filter=False) -> dict:
        """
        When `primary_filter` is False, the filter params should be returned for the AccessLog model
        if `primary_filter` is True, it should be for the dimension model itself.

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

    def query_params(self, primary_filter=False) -> dict:
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

    def query_params(self, primary_filter=False) -> dict:
        if primary_filter:
            return {'pk__in': self.values}
        return {f'{self.dimension}_id__in': self.values}

    def config(self):
        return {
            'dimension': self.dimension,
            'values': self.values,
        }


class ExplicitDimensionFilter(DimensionFilter):
    def __init__(self, dimension, values):
        super().__init__(dimension)
        self.values = to_list(values)

    @property
    def value_str(self):
        return '; '.join(val.text for val in DimensionText.objects.filter(pk__in=self.values))

    def query_params(self, primary_filter=False) -> dict:
        return {f'{self.dimension}__in': self.values}

    def config(self):
        return {
            'dimension': self.dimension,
            'values': self.values,
        }
