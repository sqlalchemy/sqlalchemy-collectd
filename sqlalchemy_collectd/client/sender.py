from .. import protocol
from .. import types


senders = []


def sends(protocol_type):
    def decorate(fn):
        senders.append((protocol_type, fn))
        return fn

    return decorate


class Sender(object):
    def __init__(self, hostname, stats_name):
        self.hostname = hostname
        self.stats_name = stats_name

    def send(self, connection, collection_target, timestamp, interval, pid):
        for protocol_type, sender in senders:
            message_sender = protocol.MessageSender(
                protocol_type, self.hostname, "sqlalchemy",
                plugin_instance=self.stats_name, type_instance=str(pid),
                interval=interval
            )
            sender(message_sender, connection, collection_target, timestamp)


@sends(types.pool)
def _send_pool(message_sender, connection, collection_target, timestamp):
    message_sender.send(
        connection, timestamp,
        collection_target.num_pools,
        collection_target.num_checkedout,
        collection_target.num_checkedin,
        collection_target.num_detached,
        collection_target.num_invalidated,
        collection_target.num_connections
    )
