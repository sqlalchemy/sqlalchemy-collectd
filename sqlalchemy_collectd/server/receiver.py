from __future__ import absolute_import

import itertools
import logging
from typing import cast
from typing import Dict
from typing import Tuple

from .. import collectd_types
from .. import protocol
from .. import stream

log = logging.getLogger(__name__)


class Receiver:
    buckets: Dict[
        str, stream.TimeBucket[Tuple[str, str, str], protocol.Values]
    ]

    def __init__(
        self, host, port, log, plugin=collectd_types.COLLECTD_PLUGIN_NAME
    ):
        self.log = log
        self.plugin = plugin
        self.collectd_types = [
            collectd_types.pool_internal,
            collectd_types.totals_internal,
            collectd_types.process_internal,
        ]
        self.network_receiver = protocol.NetworkReceiver(
            protocol.ServerConnection(host, port, log), self.collectd_types
        )
        self.translator = stream.StreamTranslator(*self.collectd_types)
        self.bucket_names = [t.name for t in self.collectd_types]
        self.buckets = {
            name: cast(
                stream.TimeBucket[Tuple[str, str, str], protocol.Values],
                stream.TimeBucket(),
            )
            for name in self.bucket_names
        }

    def receive(self):
        values_obj = self.network_receiver.receive()
        if values_obj is not None:
            self._set_stats(values_obj)

    def summarize(self, collectd, timestamp):
        for type_ in self.collectd_types:
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

    def _set_stats(self, values: protocol.Values):
        bucket_name = values.type
        timestamp = values.time
        hostname = values.host
        progname = values.plugin_instance
        process_token = values.type_instance
        interval = values.interval

        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp, interval=interval * 2)

        records[(hostname, progname, process_token)] = values

        if process_token:
            # manufacture a record for that is a single process count for this
            # process_token (which is roughly the pid plus a unique key
            # generated by the client plugin).   we also use a larger interval
            # for this value so that the process count changes more slowly
            process_bucket = self.buckets[collectd_types.process_internal.name]
            process_records = process_bucket.get_data(
                timestamp, interval=interval * 5
            )
            process_records[
                (hostname, progname, process_token)
            ] = values.build(
                type=collectd_types.process_internal.name, values=[1]
            )

    def get_stats_by_progname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)

        for (hostname, progname), keys in itertools.groupby(
            sorted(records), key=lambda rec: (rec[0], rec[1])
        ):
            recs = [records[key] for key in keys]
            interval = recs[0].interval
            # summation here is across process_tokens.
            # if records are process_token-less, then there would be one record
            # per host/program name.
            values_obj = agg_func(recs).build(
                time=timestamp, interval=interval
            )
            yield values_obj

    def get_stats_by_hostname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for hostname, keys in itertools.groupby(
            sorted(records), key=lambda rec: rec[0]
        ):
            recs = [records[key] for key in keys]
            interval = recs[0].interval
            values_obj = agg_func(recs).build(
                plugin_instance="host", time=timestamp, interval=interval
            )
            yield values_obj
