FROM ubuntu:20.04 as celus-test

ARG DEBIAN_FRONTEND=noninteractive
ARG POETRY_VERSION

# install basic packages
RUN \
	apt-get update && \
	apt-get -y upgrade && \
	apt-get -y install --no-install-recommends \
		ca-certificates git cmake make pkg-config gcc g++ openssh-client \
		python3-dev python3-pip python3-venv \
		python3-wheel curl locales libmagic-dev \
		python3-virtualenv \
		&& \
	rm -rf /var/lib/apt/lists/*

# update python paths
RUN \
	update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
	update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# generate locales
RUN \
	echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
	locale-gen
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

# install poetry
RUN curl -sSL https://install.python-poetry.org | python - --version "${POETRY_VERSION}"
ENV PATH="${PATH}:/root/.local/bin"
RUN poetry --version

# create virtualenv and make sure it is used
RUN virtualenv env
ENV VIRTUAL_ENV /env
ENV PATH "/env/bin:${PATH}"

# install latest pip
RUN pip install --upgrade pip

# install dependencies
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
RUN poetry install
