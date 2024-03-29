FROM node:10.5.0 as celus-node-build

WORKDIR /root/build/

ENV BUILD=yes
ARG GIT_VERSION
ARG GIT_COMMITHASH
ARG GIT_BRANCH

COPY design design/

RUN \
	sed -i -e "s/outputDir: .*$/outputDir: 'static\/',/" design/ui/vue.config.js && \
	cd design/ui/ && \
	npm install && \
	npm run build

FROM ubuntu:18.04 as celus-django

WORKDIR /var/www/celus/

# install basic packages
RUN \
	apt-get update && \
	apt-get -y upgrade && \
	apt-get -y install --no-install-recommends \
		ca-certificates git cmake pkg-config gcc g++ openssh-client \
		python3-dev python3-setuptools python3-pip python3-virtualenv \
		python3-wheel curl locales libmagic-dev wait-for-it libcap-dev \
		&& \
	apt-get clean

# update python paths
RUN \
	update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
	update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# generate locales
RUN \
	echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
	locale-gen

# install dependencies
# install poetry
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
RUN \
	poetry install
	pip install python-prctl uvicorn==0.11.3

ENV DJANGO_SETTINGS_MODULE=config.settings.docker

# copy sources
COPY apps/ apps/
COPY config/ config/
COPY data/ data/
COPY manage.py ./
COPY --from=celus-node-build /root/build/design/ui/static static

# collect statics
RUN \
	cp config/settings/secret_settings.json.example config/settings/secret_settings.json && \
	yes yes | env PROMETHEUS_EXPORT_MIGRATIONS=0 python manage.py collectstatic

COPY docker/entrypoint-celery.py docker/entrypoint-celery-beat.sh docker/entrypoint-web.sh ./

ENV LC_ALL="en_US.UTF-8"
ENV LANG="en_US.UTF-8"

FROM nginx as celus-nginx

WORKDIR /var/www/celus/

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=celus-django /var/www/celus/static /var/www/celus/static

# static hack TODO fix
RUN cd static && ln -s . static
