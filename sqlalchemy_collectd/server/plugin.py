from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from typing import Awaitable
from typing import Iterator

from . import receiver
from .logging import CollectdHandler
from .. import networking
from .. import protocol
from ..util import AsyncWorker


log = logging.getLogger(__name__)

receiver_: CollectdAsyncReceiverQueue


class CollectdAsyncReceiverQueue(AsyncWorker):
    queue: asyncio.Queue[Any]

    def __init__(
        self, receiver_fn: Awaitable[receiver.Receiver], log: logging.Logger
    ):
        super().__init__(log)
        self.loop = None
        self.queue = asyncio.Queue()
        self.receiver_fn = receiver_fn

    def summarize(self, now) -> Iterator[protocol.Values]:
        if self.receiver_ is not None:
            yield from self.receiver_.summarize(now)

    async def _init_service_awaitable(self):
        self.receiver_ = await self.receiver_fn

    async def _run_service_awaitable(self):
        await self.receiver_.receive()


def start_plugin(config):
    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])

    async def _start_receiver():
        receiver_ = receiver.Receiver(
            networking.AsyncNetworkReceiver(
                await networking.UDPServerReceiver.receive_from_send_clients(
                    host, int(port), log
                ),
                receiver.Receiver.collectd_types,
            )
        )

        log.info(
            "sqlalchemy.collectd server listening for "
            "SQLAlchemy clients on UDP %s %d" % (host, port)
        )

        return receiver_

    q = CollectdAsyncReceiverQueue(_start_receiver(), log)
    q.start()
    global receiver_
    receiver_ = q


def read(data=None):
    """Extract data from received messages periodically and broadcast to
    the collectd server in which we are embedded.

    The values are sent as "external" types, meaning we are using the
    "derive" and "count" types in collectd types.db.

    """
    global receiver_
    import collectd  # type: ignore[import]

    now = time.time()
    for values_obj in receiver_.summarize(now):
        values_obj.send_to_collectd(collectd, log)


def run_collectd_plugin():
    import collectd  # type: ignore[import]

    collectd.register_config(start_plugin)
    collectd.register_read(read)


run_collectd_plugin()
