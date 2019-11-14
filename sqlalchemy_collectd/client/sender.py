from . import internal_types
from .. import protocol


senders = []


def sends(protocol_type):
    def decorate(fn):
        senders.append((protocol_type, fn))
        return fn

    return decorate


class Sender(object):
    def __init__(self, hostname, stats_name, plugin="sqlalchemy"):
        self.hostname = hostname
        self.stats_name = stats_name
        self.plugin = plugin
        self.message_sender = protocol.MessageSender(
            *[protocol_type for protocol_type, sender in senders]
        )

    def send(self, connection, collection_target, timestamp, interval, pid):
        values = protocol.Values(
            host=self.hostname,
            plugin=self.plugin,
            plugin_instance=self.stats_name,
            type_instance=str(pid),
            interval=interval,
            time=timestamp,
        )
        for protocol_type, sender in senders:
            self.message_sender.send(
                connection, sender(values, collection_target)
            )


@sends(internal_types.pool)
def _send_pool(values, collection_target):
    return values.build(
        type=internal_types.pool.name,
        values=[
            collection_target.num_pools,
            collection_target.num_checkedout,
            collection_target.num_checkedin,
            collection_target.num_detached,
            # collection_target.num_invalidated,
            collection_target.num_connections,
            collection_target.num_processes,
        ],
    )


@sends(internal_types.totals)
def _send_connection_totals(values, collection_target):
    return values.build(
        type=internal_types.totals.name,
        values=[
            collection_target.total_checkouts,
            collection_target.total_invalidated,
            collection_target.total_connects,
            collection_target.total_disconnects,
        ],
    )
