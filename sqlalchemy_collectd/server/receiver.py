import logging

from . import aggregator
from .. import protocol
from ..client import internal_types

log = logging.getLogger(__name__)


class Receiver(object):
    def __init__(self, plugin="sqlalchemy"):
        self.plugin = plugin
        self.internal_types = [internal_types.pool, internal_types.totals]
        self.message_receiver = protocol.MessageReceiver(*self.internal_types)

        self.aggregator = aggregator.Aggregator(
            [type_.name for type_ in self.internal_types]
        )

        self.monitors = []

    def receive(self, connection):
        data, host_ = connection.receive()
        for monitor in self.monitors:
            monitor.forward(data)

        message = self.message_receiver.receive(data)
        type_name = message[protocol.TYPE_TYPE]
        timestamp = message[protocol.TYPE_TIME]
        host = message[protocol.TYPE_HOST]
        progname = message[protocol.TYPE_PLUGIN_INSTANCE]
        values = message[protocol.TYPE_VALUES]
        pid = message[protocol.TYPE_TYPE_INSTANCE]
        interval = message[protocol.TYPE_INTERVAL]
        self.aggregator.set_stats(
            type_name, host, progname, pid, timestamp, values, interval
        )
