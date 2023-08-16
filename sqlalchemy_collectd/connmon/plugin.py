from __future__ import annotations

import asyncio
import logging
from typing import Awaitable
from typing import Sequence

from .. import collectd_types
from .. import networking
from .. import protocol
from ..server.logging import CollectdHandler
from ..util import AsyncWorker


log = logging.getLogger(__name__)


message_sender_fn = None  # type: ignore


class CollectdAsyncSenderQueue(AsyncWorker):
    def __init__(
        self,
        senders_fn: Awaitable[Sequence[networking.AsyncNetworkSender]],
        log: logging.Logger,
    ):
        super().__init__(log)
        self.loop = None
        self.senders_fn = senders_fn

    async def _init_service_awaitable(self):
        self.senders = await self.senders_fn
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue()

    async def _run_service_awaitable(self):
        msg = await self.queue.get()
        for sender in self.senders:
            await sender.send_async(msg)

    def send(self, message):
        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, message)


def start_plugin(config):
    config_dict = {elem.key: tuple(elem.values) for elem in config.children}

    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])

    types = [collectd_types.derive_external, collectd_types.count_external]

    async def _run_connmon_service():
        senders = []

        if "listen" in config_dict:
            listen_host, listen_port = config_dict["listen"]
            sender = networking.AsyncNetworkSender(
                (
                    await (
                        networking.UDPServerSender
                    ).listen_for_receive_clients(
                        listen_host, int(listen_port), log
                    )
                ),
                types,
            )
            senders.append(sender)

            log.info(
                "sqlalchemy.collectd receiving listening for connmon "
                "clients on %s %d",
                listen_host,
                listen_port,
            )

        if "monitor" in config_dict:
            monitor_host, monitor_port = config_dict["monitor"]

            sender = networking.AsyncNetworkSender(
                (
                    networking.UDPClientSender(
                        monitor_host, int(monitor_port), log
                    )
                ),
                types,
            )
            senders.append(sender)

            log.info(
                "sqlalchemy.collectd forwarding stats to connmon "
                "listeners on %s %d",
                monitor_host,
                monitor_port,
            )
        return senders

    q = CollectdAsyncSenderQueue(_run_connmon_service(), log)
    q.start()
    global message_sender_fn
    message_sender_fn = q.send


def write(cd_values_obj):
    """Receive values from the collectd server and forward out on UDP
    for connmon listeners to receive.

    The values are received as "external" types, meaning they use the
    "derive" and "count" types in collectd types.db.  The connmon client
    now receives and interprets these objects directly.

    """

    if cd_values_obj.plugin == collectd_types.COLLECTD_PLUGIN_NAME:
        values_obj = protocol.Values.from_collectd_values(cd_values_obj, log)
        if message_sender_fn is not None:
            message_sender_fn(values_obj)


def run_collectd_plugin():
    import collectd  # type: ignore[import]

    collectd.register_config(start_plugin)
    collectd.register_write(write)


run_collectd_plugin()
