#!/bin/bash

set -e

wait-for-it -p 5432 -h "${POSTGRES_HOST:-celus-postgres}"
wait-for-it -p 6379 -h "${REDIS_HOST:-celus-redis}"

python manage.py migrate
python manage.py loaddata data/initial-data.json

uvicorn --host 0.0.0.0 config.wsgi:application --interface wsgi
