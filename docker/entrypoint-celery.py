#!/usr/bin/env python3

import subprocess
import os
import re
import signal
import socket
import sys
import typing

import prctl

worker_config: typing.Dict[str, dict] = {}

OPTION_CONVERTOR: typing.Dict[str, typing.Callable[[str], typing.Any]] = {
    "CONCURRENCY": int,
    "QUEUES": lambda n: [i for i in [e.strip() for e in n.split(",")] if i],
    "TIMELIMIT": int,
}

DEFAULT_CONCURRENCY = 1
DEFAULT_TIMELIMIT = 300


def convert_option(option: str, value: str) -> typing.Optional[typing.Any]:
    if option not in OPTION_CONVERTOR:
        print(f"Unknow option { option }", file=sys.stderr)
        return None
    try:
        return OPTION_CONVERTOR[option](value)
    except Exception:
        print(f"Failed to convert option { option } - '{ value }'", file=sys.stderr)
        return None


def config_to_program(worker_name, options: dict) -> typing.List[str]:
    res = ["celery", "worker", "-A", "config", "--loglevel", "info"]

    queues = ','.join(options['QUEUES'])
    res.extend(
        [
            f"--time-limit={options['TIMELIMIT']}",
            f"--concurrency={options['CONCURRENCY']}",
            "-Ofair",
            f"--queues={queues}",
            f"--hostname={worker_name}@{socket.gethostname()}",
            "--pool=threads",
        ]
    )

    print(" ".join(res))
    return res


# Converts celery related env vars into
for k, v in [(k, v) for k, v in os.environ.items() if k.startswith("CELERY_WORKER_")]:

    # extract env variable
    match = re.match(r"^CELERY_WORKER_(.*)_([^_]+)$", k)
    if not match:
        continue
    worker_name, option = match.groups()
    worker_name = worker_name.lower()

    # skip unmatched options
    value = convert_option(option, v)
    if not value:
        print(f"Skipping setting { option } for worker { worker_name }", file=sys.stderr)
        continue

    options: typing.Dict[str, typing.Any] = worker_config.get(worker_name, {})
    options[option] = value
    worker_config[worker_name] = options

# Fill in the default
for worker_name, options in worker_config.items():
    options["CONCURRENCY"] = options.get("CONCURRENCY", DEFAULT_CONCURRENCY)
    options["TIMELIMIT"] = options.get("TIMELIMIT", DEFAULT_TIMELIMIT)
    if "QUEUES" not in options:
        print(f"QUEUES not defined for worker { worker_name }", file=sys.stderr)
        sys.exit(1)

print("Using worker configuration:", worker_config)

print("Starting workers")
processes: typing.List[subprocess.Popen] = []
for worker_name, options in worker_config.items():
    process = subprocess.Popen(
        config_to_program(worker_name, options),
        preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL),
    )
    processes.append(process)

for process in processes:
    process.wait()
