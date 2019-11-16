# TODO: most of this should be replaced by protocol.Values and generic
# translation functions set up in types.py for "internal types" vs.
# "external types"; this will be one of the stream translators


from .. import internal_types
from .. import protocol
from .. import stream

_summarizers = {}


def summarize(collectd, receiver, timestamp):
    if not receiver.aggregator.ready:
        return

    for type_ in receiver.internal_types:
        summarizer = _summarizers.get(type_, None)
        if summarizer:
            summarizer(collectd, receiver, type_, timestamp)


def summarizes(protocol_type):
    def decorate(fn):
        _summarizers[protocol_type] = fn
        return fn

    return decorate


@summarizes(internal_types.pool_internal)
def _summarize_pool_stats(collectd, receiver, type_, timestamp):
    #    values = collectd.Values(
    #        type="count", plugin=receiver.plugin, time=timestamp
    #    )
    translator = stream.StreamTranslator(type_)
    for (
        hostname,
        progname,
        stats,
    ) in receiver.aggregator.get_stats_by_progname(type_.name, timestamp, sum):
        #        print("Summarize values by progname: %s" % stats)
        # for value in translator.break_into_individual_values(stats):
        #    value.send_to_collectd(collectd)

        for name, stat_value, value in zip(
            type_.names,
            stats.values,
            translator.break_into_individual_values(stats),
        ):
            vv = protocol.Values(
                type="count",
                plugin=receiver.plugin,
                time=timestamp,
                interval=stats.interval,
                host=hostname,
                plugin_instance=progname,
                type_instance=name,
                values=[stat_value],
            )
            assert value.time is not None
            assert value == vv, "%r != %r" % (value, vv)
            value.send_to_collectd(collectd)

    #        for name, value in zip(type_.names, stats.values):
    #            values.dispatch(
    #                interval=stats.interval,
    #                host=hostname,
    #                plugin_instance=progname,
    #                type_instance=name,
    #                values=[value],
    #            )

    for hostname, stats in receiver.aggregator.get_stats_by_hostname(
        type_.name, timestamp, sum
    ):
        #        print("Summarize values by hostname: %s" % stats)
        # for value in translator.break_into_individual_values(stats):
        #    value.send_to_collectd(collectd)

        for name, stat_value, value in zip(
            type_.names,
            stats.values,
            translator.break_into_individual_values(stats),
        ):
            vv = protocol.Values(
                type="count",
                plugin=receiver.plugin,
                time=timestamp,
                interval=stats.interval,
                host=hostname,
                plugin_instance="host",
                type_instance=name,
                values=[stat_value],
            )
            assert value.time is not None
            assert value == vv, "%r != %r" % (value, vv)
            value.send_to_collectd(collectd)


#        for name, value in zip(type_.names, stats.values):
#            values.dispatch(
#                interval=stats.interval,
#                host=hostname,
#                plugin_instance="host",
#                type_instance=name,
#                values=[value],
#            )


@summarizes(internal_types.totals_internal)
def _summarize_totals(collectd, receiver, type_, timestamp):
    #    values = collectd.Values(
    #        type="derive", plugin=receiver.plugin, time=timestamp
    #    )
    translator = stream.StreamTranslator(type_)

    for (
        hostname,
        progname,
        stats,
    ) in receiver.aggregator.get_stats_by_progname(type_.name, timestamp):
        #        print("Summarize totals by progname: %s" % stats)
        for name, stat_value, value in zip(
            type_.names,
            stats.values,
            translator.break_into_individual_values(stats),
        ):
            vv = protocol.Values(
                type="derive",
                plugin=receiver.plugin,
                time=timestamp,
                interval=stats.interval,
                host=hostname,
                plugin_instance=progname,
                type_instance=name,
                values=[stat_value],
            )
            assert value.time is not None
            assert value == vv, "%r != %r" % (value, vv)
            value.send_to_collectd(collectd)
    #        for name, value in zip(type_.names, stats.values):
    #            values.dispatch(
    #                interval=stats.interval,
    #                host=hostname,
    #                plugin_instance=progname,
    #               type_instance=name,
    #                values=[value],
    #            )

    for hostname, stats in receiver.aggregator.get_stats_by_hostname(
        type_.name, timestamp
    ):
        #        print("Summarize totals by hostname: %s" % stats)
        # for value in translator.break_into_individual_values(stats):
        #    value.send_to_collectd(collectd)

        for name, stat_value, value in zip(
            type_.names,
            stats.values,
            translator.break_into_individual_values(stats),
        ):
            vv = protocol.Values(
                type="derive",
                plugin=receiver.plugin,
                time=timestamp,
                interval=stats.interval,
                host=hostname,
                plugin_instance="host",
                type_instance=name,
                values=[stat_value],
            )
            assert value.time is not None
            assert value == vv, "%r != %r" % (value, vv)
            value.send_to_collectd(collectd)


#        for name, value in zip(type_.names, stats.values):
#            values.dispatch(
#                interval=stats.interval,
#                host=hostname,
#                plugin_instance="host",
#                type_instance=name,
#                values=[value],
#            )
