import collectd

from ..client import internal_types


_summarizers = {}


def summarize(receiver, timestamp):
    if receiver.aggregator.interval is None:
        return

    for type_ in receiver.internal_types:
        summarizer = _summarizers.get(type_, None)
        if summarizer:
            summarizer(receiver, type_, timestamp)


def summarizes(protocol_type):
    def decorate(fn):
        _summarizers[protocol_type] = fn
        return fn

    return decorate


@summarizes(internal_types.pool)
def _summarize_pool_stats(receiver, type_, timestamp):
    values = collectd.Values(
        type="count",
        plugin=receiver.plugin,
        time=timestamp,
        interval=receiver.aggregator.interval,
    )
    for (
        hostname,
        progname,
        numrecs,
        stats,
    ) in receiver.aggregator.get_stats_by_progname(type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname,
                plugin_instance=progname,
                type_instance=name,
                values=[value],
            )

        values.dispatch(
            host=hostname,
            plugin_instance=progname,
            type_instance="numprocs",
            values=[numrecs],
        )

    for hostname, numrecs, stats in receiver.aggregator.get_stats_by_hostname(
        type_.name, timestamp, sum
    ):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname,
                plugin_instance="host",
                type_instance=name,
                values=[value],
            )
        values.dispatch(
            host=hostname,
            plugin_instance="host",
            type_instance="numprocs",
            values=[numrecs],
        )


@summarizes(internal_types.totals)
def _summarize_totals(receiver, type_, timestamp):
    values = collectd.Values(
        type="derive",
        plugin=receiver.plugin,
        time=timestamp,
        interval=receiver.aggregator.interval,
    )

    for (
        hostname,
        progname,
        numrecs,
        stats,
    ) in receiver.aggregator.get_stats_by_progname(type_.name, timestamp, sum):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname,
                plugin_instance=progname,
                type_instance=name,
                values=[value],
            )

    for hostname, numrecs, stats in receiver.aggregator.get_stats_by_hostname(
        type_.name, timestamp, sum
    ):
        for name, value in zip(type_.names, stats):
            values.dispatch(
                host=hostname,
                plugin_instance="host",
                type_instance=name,
                values=[value],
            )
