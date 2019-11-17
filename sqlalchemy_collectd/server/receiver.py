import logging

from . import aggregator
from .. import internal_types
from .. import protocol
from .. import stream

log = logging.getLogger(__name__)


class Receiver(object):
    def __init__(
        self,
        host,
        port,
        log,
        plugin=internal_types.COLLECTD_PLUGIN_NAME,
        include_pids=True,
    ):
        self.log = log
        self.plugin = plugin
        self.internal_types = [
            internal_types.pool_internal,
            internal_types.totals_internal,
            internal_types.process_internal,
        ]
        self.network_receiver = protocol.NetworkReceiver(
            protocol.ServerConnection(host, port, log), self.internal_types
        )
        self.translator = stream.StreamTranslator(*self.internal_types)
        # TODO: why not have aggreagtor be part of receiver to simplify
        # things, this becomes a server-specific receiver.  connmon
        # should have its own receiver
        self.aggregator = aggregator.Aggregator(
            [t.name for t in self.internal_types], include_pids=include_pids
        )

    def receive(self):
        values_obj = self.network_receiver.receive()
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
                    external_values_obj.send_to_collectd(collectd, self.log)

            for values_obj in self.aggregator.get_stats_by_hostname(
                type_.name, timestamp
            ):
                for (
                    external_values_obj
                ) in self.translator.break_into_individual_values(values_obj):
                    external_values_obj.send_to_collectd(collectd, self.log)
