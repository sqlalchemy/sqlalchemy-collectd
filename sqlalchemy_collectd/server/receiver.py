import collectd

from .. import protocol
from .. import types
from . import aggregator

import logging
log = logging.getLogger(__name__)


class Receiver(object):
    def __init__(self, plugin="sqlalchemy"):
        self.plugin = plugin
        self.types = types_ = [
            types.pool,
            types.checkouts,
            types.commits,
            types.rollbacks,
            types.invalidated,
            types.transactions
        ]
        self.message_receiver = protocol.MessageReceiver(*types_)

        self.aggregator = aggregator.Aggregator(
            [type_.name for type_ in types_]
        )

    def receive(self, connection):
        data, host = connection.receive()
        message = self.message_receiver.receive(data)
        type_name = message[protocol.TYPE_TYPE]
        timestamp = message[protocol.TYPE_TIME]
        host = message[protocol.TYPE_HOST]
        progname = message[protocol.TYPE_PLUGIN_INSTANCE]
        values = message[protocol.TYPE_VALUES]
        pid = message[protocol.TYPE_TYPE_INSTANCE]
        self.aggregator.set_stats(
            type_name, host, progname, pid, timestamp, values
        )

    def summarize(self, timestamp):
        for type_ in self.types:
            self._summarize_for_type(type_, timestamp)

    def _summarize_for_type(self, type_, timestamp):
        values = collectd.Values(
            type=type_.name,
            plugin=self.plugin,
            time=timestamp,
            interval=self.aggregator.interval
        )
        for hostname, progname, stats in \
                self.aggregator.get_stats_by_progname(
                    type_.name, timestamp, sum):
            values.dispatch(
                type_instance="sum", host=hostname, plugin_instance=progname,
                values=stats
            )

        for hostname, stats in self.aggregator.get_stats_by_hostname(
                type_.name, timestamp, sum):
            values.dispatch(
                type_instance="sum", host=hostname, plugin_instance="all",
                values=stats
            )

        for hostname, progname, stats in self.aggregator.get_stats_by_progname(
                type_.name, timestamp, aggregator.avg):
            values.dispatch(
                type_instance="avg", host=hostname, plugin_instance=progname,
                values=stats
            )

        for hostname, stats in self.aggregator.get_stats_by_hostname(
                type_.name, timestamp, aggregator.avg):
            values.dispatch(
                type_instance="avg", host=hostname, plugin_instance="all",
                values=stats
            )

