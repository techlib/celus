from .test import *  # noqa

USES_REGISTRY_BACKEND = True

# No need to use clickhouse here
CLICKHOUSE_SYNC_ACTIVE = False
CLICKHOUSE_QUERY_ACTIVE = False

# nor OTP
OTP_ENABLED = False
