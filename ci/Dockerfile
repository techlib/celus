FROM ubuntu:24.04 as celus-test

ARG DEBIAN_FRONTEND=noninteractive

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


# install poetry - used by legacy pre-uv jobs
RUN curl -sSL https://install.python-poetry.org | python - --version "${POETRY_VERSION}"
ENV PATH="${PATH}:/root/.local/bin"
RUN poetry --version

# create virtualenv and make sure it is used
RUN virtualenv env
ENV VIRTUAL_ENV /env
ENV PATH "/env/bin:${PATH}"

# install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="${PATH}:/root/.local/bin"
RUN uv --version

# install dependencies
COPY uv.lock uv.lock
COPY pyproject.toml pyproject.toml
RUN uv sync --active
