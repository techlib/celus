#!/bin/sh

set -e

poetry export -q --without-hashes -f requirements.txt -o requirements/base.txt

poetry export -q -E production --without-hashes -f requirements.txt -o requirements/production.txt

poetry export -q -E staging --without-hashes -f requirements.txt -o requirements/staging.txt

poetry export -q -E test --without-hashes -f requirements.txt -o requirements/test.txt

poetry export -q --dev -E devel --without-hashes -f requirements.txt -o requirements/devel.txt
