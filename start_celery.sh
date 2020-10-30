#!/bin/sh
celery -A config -Q celery,interest,sushi,import,normal worker -l DEBUG
