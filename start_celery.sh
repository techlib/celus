#!/bin/sh
celery -A config -Q celery,interest,sushi,import worker -l DEBUG
