import collectd

from .. import protocol
from . import aggregator
from ..client import internal_types

import logging
log = logging.getLogger(__name__)


summarizers = {}


def summarizes(protocol_type):
    def decorate(fn):
        summarizers[protocol_type] = fn
        return fn

    return decorate


class Receiver(object):
    def __init__(self, plugin="sqlalchemy"):
        self.plugin = plugin
        self.internal_types = [
            internal_types.pool,
            internal_types.totals
        ]
        self.message_receiver = protocol.MessageReceiver(*self.internal_types)

        self.aggregator = aggregator.Aggregator(
            [type_.name for type_ in self.internal_types]
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
        for type_ in self.internal_types:
            summarizer = summarizers.get(type_, None)
            if summarizer:
                summarizer(self, type_, timestamp)


@summarizes(internal_types.pool)
def _summarize_pool_stats(receiver, type_, timestamp):
    values = collectd.Values(
        type="count",
        plugin=receiver.plugin,
        time=timestamp,
        interval=receiver.aggregator.interval
    )
    for hostname, progname, numrecs, stats in \
            receiver.aggregator.get_stats_by_progname(
                type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname, plugin_instance=progname,
                type_instance=name,
                values=[value]
            )

        values.dispatch(
            host=hostname, plugin_instance=progname,
            type_instance="numprocs", values=[numrecs])

    for hostname, numrecs, stats in receiver.aggregator.get_stats_by_hostname(
            type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname, plugin_instance="host",
                type_instance=name,
                values=[value]
            )
        values.dispatch(
            host=hostname, plugin_instance="host",
            type_instance="numprocs", values=[numrecs])


@summarizes(internal_types.totals)
def _summarize_totals(receiver, type_, timestamp):
    values = collectd.Values(
        type="derive",
        plugin=receiver.plugin,
        time=timestamp,
        interval=receiver.aggregator.interval
    )

    for hostname, progname, numrecs, stats in \
            receiver.aggregator.get_stats_by_progname(
                type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname, plugin_instance=progname,
                type_instance=name,
                values=[value]
            )

    for hostname, numrecs, stats in receiver.aggregator.get_stats_by_hostname(
            type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname, plugin_instance="host",
                type_instance=name,
                values=[value]
            )

