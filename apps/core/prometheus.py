from prometheus_client import Counter, Summary, Gauge

report_access_total_counter = Counter(
    'celus_report_access_total',
    'The number of times a report type was accessed from a specific type of view. Also '
    'split by report type',
    ['view_type', 'report_type'],
)

report_access_time_summary = Summary(
    'celus_report_access_time_seconds',
    'The time it took to process request for data for each report type. Also ' 'split by view_type',
    ['view_type', 'report_type'],
)

celus_version_num = Gauge(
    'celus_version_num', 'CELUS version converted to int. For example 4.1.2 => 412', []
)

celus_sentry_release = Gauge(
    'celus_git_hash',
    'In production this is a git hash of deployed commit. It is stored in the hash dimension. '
    'Value is always 1',
    ['hash'],
)
