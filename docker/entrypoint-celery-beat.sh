#!/bin/bash

celery beat -A config --loglevel=info --pidfile /tmp/celery-beat.pid
