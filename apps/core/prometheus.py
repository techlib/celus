from prometheus_client import Counter, Summary

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
