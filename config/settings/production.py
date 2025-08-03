from .base import *  # noqa F403 F401

# Set clickhouse_driver to DEBUG for production
# it may provide useful information for debugging on servers
LOGGING["loggers"]["clickhouse_driver"]["level"] = "DEBUG"  # noqa F405
