#!/bin/sh
export DJANGO_SETTINGS_MODULE=config.settings.devel
watchmedo auto-restart -d apps/ -d config/  -p '*.py' -R -- celery -A config beat -l DEBUG
