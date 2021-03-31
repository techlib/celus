#!/bin/sh
celery -A config worker -Q export,celery,interest,sushi,import,normal -l DEBUG
