import logging

from . import aggregator
from .. import internal_types
from .. import protocol

log = logging.getLogger(__name__)

COLLECTD_PLUGIN_NAME = "sqlalchemy"


class Receiver(object):
    def __init__(self, plugin=COLLECTD_PLUGIN_NAME):
        self.plugin = plugin
        self.internal_types = [
            internal_types.pool_internal,
            internal_types.totals_internal,
        ]
        self.message_receiver = protocol.MessageReceiver(*self.internal_types)

        self.aggregator = aggregator.Aggregator(
            [type_.name for type_ in self.internal_types]
        )

        self.monitors = []

    def receive(self, connection):
        data, host_ = connection.receive()
        for monitor in self.monitors:
            monitor.forward(data)

        values_obj = self.message_receiver.receive(data)
        self.aggregator.set_stats(values_obj)
