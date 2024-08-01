from typing import Iterable, List

from django.db.models import QuerySet


def to_list(values: Iterable) -> List:
    if isinstance(values, QuerySet):
        return list(values)
    elif type(values) not in (list, set, tuple):
        return [values]
    return list(values)


def to_bool(value) -> bool:
    return value in (True, "true", "True", "1", 1)


# The following is a copy of the strtobool function from Python 3.11 distutils.util
# as it was removed from Python 3.12
def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
