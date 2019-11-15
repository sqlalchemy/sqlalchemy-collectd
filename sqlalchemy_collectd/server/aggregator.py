import itertools

from .. import stream


class Aggregator(object):
    def __init__(self, bucket_names, num_buckets=4):
        self.bucket_names = bucket_names
        self.buckets = {
            name: stream.TimeBucket(4) for name in self.bucket_names
        }
        self.ready = False

    def set_stats(self, values):
        bucket_name = values.type
        timestamp = values.time
        hostname = values.host
        progname = values.plugin_instance
        pid = values.type_instance
        interval = values.interval

        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp, interval=interval)
        records[(hostname, progname, pid)] = values
        self.ready = True

    def get_stats_by_progname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for (hostname, progname), keys in itertools.groupby(
            sorted(records), key=lambda rec: (rec[0], rec[1])
        ):
            recs = [records[key] for key in keys]
            yield (hostname, progname, agg_func(recs))

    def get_stats_by_hostname(self, bucket_name, timestamp, agg_func=sum):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for hostname, keys in itertools.groupby(
            sorted(records), key=lambda rec: rec[0]
        ):
            recs = [records[key] for key in keys]
            yield hostname, agg_func(recs)
