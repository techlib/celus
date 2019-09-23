#!/usr/bin/env bash

# this script is intended to bootstrap the system of statistics to fully functional state
# from a fresh installation.

# What needs to be done

# * synchronize platforms, organizations, etc. with ERMS

python manage.py erms_sync_platforms
python manage.py erms_sync_organizations
python manage.py erms_sync_identities_and_users

# * load fixtures for COUNTER report types, report types, chart definitions, etc.

python manage.py loaddata apps/logs/fixtures/logs.json
python manage.py loaddata apps/sushi/fixtures/sushi.json
python manage.py loaddata apps/charts/fixtures/charts.json

# * create superuser account outside ERMS if needed
# * load the list of organization SUSHI credentials

python manage.py load_sushi_credentials "$1"

# * load the table of reports active for each organization credentials
# + load the interest definitions from a table

python manage.py load_platform_report_table "$2"

# * start task to fetch SUSHI data

