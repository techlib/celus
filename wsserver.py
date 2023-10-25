#!/usr/bin/env python

import asyncio
import json
import logging
import signal
import socket
import sys
from functools import partial
from typing import Optional

import django
import websockets
from decouple import config
from redis import asyncio as aioredis

django.setup()

from core.models import User  # noqa E402  - needed after django.setup()
from django.db import connection  # noqa E402  - needed after django.setup()
from sesame.utils import get_user  # noqa E402 - needed after django.setup()
from websockets.frames import CloseCode  # noqa E402  - needed after django.setup()

user_id_to_connections = {}
logger = logging.getLogger(__name__)


async def run_in_thread(func, *args, **kwargs):
    if hasattr(asyncio, "to_thread"):
        return await asyncio.to_thread(func, *args, **kwargs)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def handler(websocket):
    data = json.loads(await websocket.recv())
    if data["command"] != "subscribe":
        await websocket.close(CloseCode.INTERNAL_ERROR, "invalid command")
        return

    user = await run_in_thread(get_user, data["data"])
    if user is None:
        await websocket.close(CloseCode.INTERNAL_ERROR, "authentication failed")
        return

    logger.info("received subscribe command for user %d", user.id)
    user_id_to_connections.setdefault(user.id, []).append(websocket)
    try:
        await websocket.wait_closed()
    finally:
        try:
            user_id_to_connections[user.id].remove(websocket)
        except ValueError:
            pass


async def process_events():
    """Listen to events in Redis and process them."""
    redis = aioredis.from_url("redis://127.0.0.1:6379/1")
    pubsub = redis.pubsub()
    await pubsub.subscribe("events")
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        payload = message["data"].decode()
        event = json.loads(payload)
        recipients = user_id_to_connections.get(event["user_id"], [])
        logger.info(
            "broadcasting event for user %s to %d recipients", event["user_id"], len(recipients)
        )
        websockets.broadcast(recipients, payload)


async def main(port: Optional[int] = None):
    """
    :param port: when None, use unix socket
    :return:
    """
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    if port is not None:
        # if port is specified, use TCP socket
        server = partial(websockets.serve, host="localhost", port=port)
    else:
        # otherwise use unix socket
        # it uses file descriptor 3, which is the first socket passed by systemd
        if listen_fds := config("LISTEN_FDS", default=0, cast=int):
            # we are under systemd
            logger.info("using systemd socket activation; listen_fds = %s", listen_fds)
            sock: socket.socket = socket.socket(fileno=3)
            server = partial(websockets.unix_serve, path=None, sock=sock)
        else:
            process_name = config("SUPERVISOR_PROCESS_NAME", default=sys.argv[0])
            server = partial(websockets.unix_serve, path=f"{process_name}.sock")

    async with server(handler):
        await asyncio.wait(
            [asyncio.create_task(process_events()), stop], return_when=asyncio.FIRST_COMPLETED
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    asyncio.run(main(port=args.port))
