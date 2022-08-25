from typing import Iterable, List

from django.db.models import QuerySet


def to_list(values: Iterable) -> List:
    if isinstance(values, QuerySet):
        return list(values)
    elif type(values) not in (list, set, tuple):
        return [values]
    return list(values)


def to_bool(value) -> bool:
    return value in (True, 'true', 'True', '1', 1)
