import collectd

from .. import protocol
from .. import types
from . import aggregator

import logging
log = logging.getLogger(__name__)

receivers = {}
summarizers = []


def receives(protocol_type):
    def decorate(fn):
        receivers[protocol_type.name] = fn
        return fn

    return decorate


def summarizes(protocol_type):
    def decorate(fn):
        summarizers.append(fn)
        return fn

    return decorate


class Receiver(object):
    def __init__(self):
        self.message_receiver = protocol.MessageReceiver(
            types.pool,
            types.checkouts,
            types.commits,
            types.rollbacks,
            types.invalidated,
            types.transactions
        )

    def receive(self, connection, aggregator_):
        data, host = connection.receive()
        message = self.message_receiver.receive(data)
        type_ = message[protocol.TYPE_TYPE]
        timestamp = message[protocol.TYPE_TIME]
        host = message[protocol.TYPE_HOST]
        progname = message[protocol.TYPE_PLUGIN_INSTANCE]
        values = message[protocol.TYPE_VALUES]
        pid = message[protocol.TYPE_TYPE_INSTANCE]
        try:
            receiver = receivers[type_]
        except KeyError:
            log.warn("Don't understand message type %s, skipping" % type_)
        else:
            receiver(
                message, timestamp, host, progname, pid, values, aggregator_)

    def summarize(self, aggregator_, timestamp):
        for summarizer in summarizers:
            summarizer(aggregator_, timestamp)


@receives(types.pool)
def _receive_pool(
        message, timestamp, host, progname, pid, values, aggregator_):
    aggregator_.set_pool_stats(host, progname, pid, timestamp, *values)


@summarizes(types.pool)
def _summarize_pool(aggregator_, timestamp):
    values = collectd.Values(
        type=types.pool.name,
        plugin="sqlalchemy",
        time=timestamp,
        interval=aggregator_.interval
    )
    for hostname, progname, stats in \
            aggregator_.get_pool_stats_by_progname(timestamp, sum):
        values.dispatch(
            type_instance="sum", host=hostname, plugin_instance=progname,
            values=stats
        )

    for hostname, stats in aggregator_.get_pool_stats_by_hostname(
            timestamp, sum):
        values.dispatch(
            type_instance="sum", host=hostname, plugin_instance="all",
            values=stats
        )

    for hostname, progname, stats in aggregator_.get_pool_stats_by_progname(
            timestamp, aggregator.avg):
        values.dispatch(
            type_instance="avg", host=hostname, plugin_instance=progname,
            values=stats
        )

    for hostname, stats in aggregator_.get_pool_stats_by_hostname(
            timestamp, aggregator.avg):
        values.dispatch(
            type_instance="avg", host=hostname, plugin_instance="all",
            values=stats
        )

