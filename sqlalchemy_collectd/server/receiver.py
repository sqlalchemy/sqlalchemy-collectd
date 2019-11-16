import logging

from . import aggregator
from .. import internal_types
from .. import protocol
from .. import stream

log = logging.getLogger(__name__)

COLLECTD_PLUGIN_NAME = "sqlalchemy"


class Receiver(object):
    def __init__(self, plugin=COLLECTD_PLUGIN_NAME):
        self.plugin = plugin
        self.internal_types = [
            internal_types.pool_internal,
            internal_types.totals_internal,
            internal_types.process_internal,
        ]
        self.message_receiver = protocol.MessageReceiver(*self.internal_types)
        self.translator = stream.StreamTranslator(*self.internal_types)

        self.aggregator = aggregator.Aggregator(
            [t.name for t in self.internal_types]
        )

        self.monitors = []

    def receive(self, connection):
        data, host_ = connection.receive()
        for monitor in self.monitors:
            monitor.forward(data)

        values_obj = self.message_receiver.receive(connection, data)
        self.aggregator.set_stats(values_obj)

    def summarize(self, collectd, timestamp):
        if not self.aggregator.ready:
            return

        for type_ in self.internal_types:
            for values_obj in self.aggregator.get_stats_by_progname(
                type_.name, timestamp
            ):
                for (
                    external_values_obj
                ) in self.translator.break_into_individual_values(values_obj):
                    external_values_obj.send_to_collectd(collectd)

            for values_obj in self.aggregator.get_stats_by_hostname(
                type_.name, timestamp
            ):
                for (
                    external_values_obj
                ) in self.translator.break_into_individual_values(values_obj):
                    external_values_obj.send_to_collectd(collectd)
