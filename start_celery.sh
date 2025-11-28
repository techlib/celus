#!/bin/sh
export PYTHONBREAKPOINT=celery.contrib.rdb.set_trace
export DJANGO_SETTINGS_MODULE=config.settings.devel
# watchmedo auto-restart -d apps/ -d config/  -p '*.py' -R -- celery -A config worker -Q export,celery,interest,sushi,import,normal,preflight -l DEBUG
uv run celery -A config worker -Q export,celery,interest,sushi,import,normal,preflight,ch_export --concurrency=1 -l DEBUG
