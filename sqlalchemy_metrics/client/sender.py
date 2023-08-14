from __future__ import annotations

import threading
from typing import Dict
from typing import List
from typing import Protocol
from typing import Tuple
from typing import TYPE_CHECKING

from .. import collectd_types
from .. import protocol

if TYPE_CHECKING:
    from logging import Logger

    from .collector import CollectionTarget


class _SenderFunction(Protocol):
    def __call__(
        self, values: protocol.Values, collection_target: CollectionTarget
    ) -> protocol.Values:
        ...


senders: List[Tuple[protocol.Type, _SenderFunction]] = []


def sends(protocol_type: protocol.Type):
    def decorate(fn: _SenderFunction):
        senders.append((protocol_type, fn))
        return fn

    return decorate


_SenderKey = Tuple[str, str, str, int]


class Sender:
    senders: Dict[_SenderKey, Sender] = {}
    create_mutex = threading.Lock()

    def __init__(
        self,
        hostname,
        stats_name,
        collectd_host,
        collectd_port,
        log,
        plugin=collectd_types.COLLECTD_PLUGIN_NAME,
    ):
        self.hostname = hostname
        self.stats_name = stats_name
        self.plugin = plugin
        self.message_sender = protocol.NetworkSender(
            protocol.ClientConnection.for_host_port(
                collectd_host, collectd_port, log
            ),
            [protocol_type for protocol_type, sender in senders],
        )

    def send(self, collection_target, timestamp, interval, process_token):
        values = protocol.Values(
            host=self.hostname,
            plugin=self.plugin,
            plugin_instance=self.stats_name,
            type_instance=str(process_token),
            interval=interval,
            time=timestamp,
        )
        for protocol_type, sender in senders:
            self.message_sender.send(sender(values, collection_target))

    @classmethod
    def get_sender(
        cls,
        hostname: str,
        stats_name: str,
        collectd_host: str,
        collectd_port: int,
        log: Logger,
    ):
        cls.create_mutex.acquire()
        try:
            key = (hostname, stats_name, collectd_host, collectd_port)
            if key not in cls.senders:
                sender = cls.senders[key] = Sender(
                    hostname, stats_name, collectd_host, collectd_port, log
                )
                return sender
            else:
                return cls.senders[key]

        finally:
            cls.create_mutex.release()


@sends(collectd_types.pool_internal)
def _send_pool(values, collection_target):
    return values.build(
        type=collectd_types.pool_internal.name,
        values=[
            collection_target.num_pools,
            collection_target.num_checkedout,
            collection_target.num_checkedin,
            collection_target.num_detached,
            # collection_target.num_invalidated,
            collection_target.num_connections,
        ],
    )


@sends(collectd_types.totals_internal)
def _send_connection_totals(values, collection_target):
    return values.build(
        type=collectd_types.totals_internal.name,
        values=[
            collection_target.total_checkouts,
            collection_target.total_invalidated,
            collection_target.total_connects,
            collection_target.total_disconnects,
        ],
    )
