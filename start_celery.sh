#!/bin/sh
celery -A config worker -Q celery,interest,sushi,import,normal -l DEBUG
