#!/usr/bin/env bash


# dump data for all the stuff the database definitions that it is useful to preserve
# in form of fixtures for easy replication and/or restoration

# apps.charts - all models

python manage.py dumpdata --indent 2 charts > apps/charts/fixtures/charts.json

# apps.core - nothing needed

# apps.logs - selected models
# - ReportType
# - InterestGroup
# - Metric
# - ReportInterestMetric
# - Dimension
# - ReportTypeToDimension

python manage.py dumpdata --indent 2 logs.reporttype logs.interestgroup logs.metric logs.reportinterestmetric logs.dimension logs.reporttypetodimension > apps/logs/fixtures/logs.json

# apps.organizations - nothing needed

# apps.publications - nothing needed

# apps.sushi - model CounterReportType

python manage.py dumpdata --indent 2 sushi.counterreporttype > apps/sushi/fixtures/sushi.json

