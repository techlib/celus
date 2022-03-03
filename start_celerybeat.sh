#!/bin/sh
watchmedo auto-restart -d apps/ -d config/  -p '*.py' -R -- celery -A config beat -l DEBUG
