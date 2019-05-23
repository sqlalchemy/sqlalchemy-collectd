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

    def send(self, connection, collection_target, timestamp, interval, pid):
        for protocol_type, sender in senders:
            message_sender = protocol.MessageSender(
                protocol_type,
                self.hostname,
                self.plugin,
                plugin_instance=self.stats_name,
                type_instance=str(pid),
                interval=interval,
            )
            sender(message_sender, connection, collection_target, timestamp)


@sends(internal_types.pool)
def _send_pool(message_sender, connection, collection_target, timestamp):
    message_sender.send(
        connection,
        timestamp,
        collection_target.num_pools,
        collection_target.num_checkedout,
        collection_target.num_checkedin,
        collection_target.num_detached,
        # collection_target.num_invalidated,
        collection_target.num_connections,
    )


@sends(internal_types.totals)
def _send_connection_totals(
    message_sender, connection, collection_target, timestamp
):
    message_sender.send(
        connection,
        timestamp,
        collection_target.total_checkouts,
        collection_target.total_invalidated,
        collection_target.total_connects,
        collection_target.total_disconnects,
    )
