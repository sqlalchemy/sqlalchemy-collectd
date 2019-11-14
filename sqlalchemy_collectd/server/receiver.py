import logging

from . import aggregator
from .. import protocol
from ..client import internal_types

log = logging.getLogger(__name__)

COLLECTD_PLUGIN_NAME = "sqlalchemy"


class Receiver(object):
    def __init__(self, plugin=COLLECTD_PLUGIN_NAME):
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

        values_obj = self.message_receiver.receive(data)
        type_name = values_obj.type
        timestamp = values_obj.time
        host = values_obj.host
        progname = values_obj.plugin_instance
        values = values_obj.values
        pid = values_obj.type_instance
        interval = values_obj.interval
        self.aggregator.set_stats(
            type_name, host, progname, pid, timestamp, values, interval
        )
