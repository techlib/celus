#!/bin/sh
watchmedo auto-restart -d apps/ -d config/  -p '*.py' -R -- celery -A config worker -Q export,celery,interest,sushi,import,normal,preflight -l DEBUG
