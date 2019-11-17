import itertools
import logging

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
        self.bucket_names = [t.name for t in self.internal_types]
        self.buckets = {
            name: stream.TimeBucket(4) for name in self.bucket_names
        }
        self.include_pids = include_pids

    def receive(self):
        values_obj = self.network_receiver.receive()
        self._set_stats(values_obj)

    def summarize(self, collectd, timestamp):
        for type_ in self.internal_types:
            for values_obj in self.get_stats_by_progname(
                type_.name, timestamp
            ):
                for (
                    external_values_obj
                ) in self.translator.break_into_individual_values(values_obj):
                    external_values_obj.send_to_collectd(collectd, self.log)

            for values_obj in self.get_stats_by_hostname(
                type_.name, timestamp
            ):
                for (
                    external_values_obj
                ) in self.translator.break_into_individual_values(values_obj):
                    external_values_obj.send_to_collectd(collectd, self.log)

    def _set_stats(self, values):
        bucket_name = values.type
        timestamp = values.time
        hostname = values.host
        progname = values.plugin_instance
        pid = values.type_instance
        interval = values.interval

        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp, interval=interval * 2)
        records[(hostname, progname, pid)] = values

        if self.include_pids and pid:
            # manufacture a record for that is a single process count for this
            # pid.   we also use a larger interval for this value so that the
            # process count changes more slowly
            process_bucket = self.buckets[internal_types.process_internal.name]
            process_records = process_bucket.get_data(
                timestamp, interval=interval * 5
            )
            process_records[(hostname, progname, pid)] = values.build(
                type=internal_types.process_internal.name, values=[1]
            )

    def get_stats_by_progname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for (hostname, progname), keys in itertools.groupby(
            sorted(records), key=lambda rec: (rec[0], rec[1])
        ):
            recs = [records[key] for key in keys]
            # summation here is across pids.
            # if records are pid-less, then there would be one record
            # per host/program name.
            values_obj = agg_func(recs).build(
                time=timestamp, interval=bucket.interval
            )
            yield values_obj

    def get_stats_by_hostname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for hostname, keys in itertools.groupby(
            sorted(records), key=lambda rec: rec[0]
        ):
            recs = [records[key] for key in keys]
            values_obj = agg_func(recs).build(
                plugin_instance="host",
                time=timestamp,
                interval=bucket.interval,
            )
            yield values_obj
