import itertools

from .. import internal_types
from .. import stream


class Aggregator(object):
    def __init__(self, bucket_names, include_pids, num_buckets=4):
        self.bucket_names = bucket_names
        self.buckets = {
            name: stream.TimeBucket(4) for name in self.bucket_names
        }
        self.include_pids = include_pids
        self.ready = False

    def set_stats(self, values):
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
        self.ready = True

    def get_stats_by_progname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for (hostname, progname), keys in itertools.groupby(
            sorted(records), key=lambda rec: (rec[0], rec[1])
        ):
            recs = [records[key] for key in keys]
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
