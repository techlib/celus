.PHONY: all update_requirements

all: update_requirements

update_requirements: requirements/develop.txt requirements/production.txt

requirements/production.txt: poetry.lock
	poetry export -q --without-hashes -f requirements.txt -o $@

requirements/develop.txt: poetry.lock
	poetry export -q --dev --without-hashes -f requirements.txt -o $@
