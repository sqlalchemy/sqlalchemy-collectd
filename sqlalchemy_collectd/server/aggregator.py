import itertools


def avg(values):
    return sum(values) / len(values)


class Aggregator(object):
    def __init__(self, bucket_names, num_buckets=4):
        self.buckets = None
        self.interval = None
        self.bucket_names = bucket_names

    def _init_buckets(self, interval):
        # the interval at which we bucket the data has to be longer than
        # the interval coming in from the messages, since we want to give
        # enough time for all of them to come in
        self.interval = interval * 2
        self.buckets = {
            name: TimeBucket(4, self.interval) for name in self.bucket_names
        }

    def set_stats(
        self, bucket_name, hostname, progname, pid, timestamp, values, interval
    ):
        if not self.interval:
            self._init_buckets(interval)

        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        records[(hostname, progname, pid)] = values

    def get_stats_by_progname(self, bucket_name, timestamp, agg_func):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for (hostname, progname), keys in itertools.groupby(
            sorted(records), key=lambda rec: (rec[0], rec[1])
        ):
            recs = [records[key] for key in keys]
            yield (
                hostname,
                progname,
                len(recs),
                [agg_func(coll) for coll in zip(*recs)],
            )

    def get_stats_by_hostname(self, bucket_name, timestamp, agg_func):
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(timestamp)
        for hostname, keys in itertools.groupby(
            sorted(records), key=lambda rec: rec[0]
        ):
            recs = [records[key] for key in keys]
            yield hostname, len(recs), [agg_func(coll) for coll in zip(*recs)]


class TimeBucket(object):
    """Store the last N seconds of time-stamped data within
    interval-keyed buckets.

    The idea is we can store and retrieve records that were
    within the last N seconds only, or in the previous
    2N-N seconds, or 3N-2N seconds, including that we can efficiently
    clean up old ranges in O(1) time.

    E.g. assume four buckets and interval of 100::

        bucket[0] -> timestamp 50000-50100
        bucket[1] -> timestamp 50101-50200
        bucket[2] -> timestamp 50201-50300
        bucket[3] -> timestamp 50301-50400

    100 seconds later::

        bucket[0] -> timestamp 50401-50500
        bucket[1] -> timestamp 50101-50200
        bucket[2] -> timestamp 50201-50300
        bucket[3] -> timestamp 50301-50400

    100 seconds later::

        bucket[0] -> timestamp 50401-50500
        bucket[1] -> timestamp 50501-50600
        bucket[2] -> timestamp 50201-50300
        bucket[3] -> timestamp 50301-50400

    etc.

    The object assumes if a new timestamp is coming in that is newer
    than the current bucket, we go to the next bucket.   If the next bucket
    has data from the old range it had B buckets ago, we empty it out first.

    """

    __slots__ = "num_buckets", "buckets", "interval"

    def __init__(self, num_buckets, interval):
        self.num_buckets = num_buckets
        self.buckets = [
            {"slot": None, "data": {}, "timestamp": 0}
            for i in range(num_buckets)
        ]
        self.interval = interval

    def _get_bucket(self, timestamp):
        timestamp = int(timestamp)
        slot = timestamp // self.interval
        bucket_num = slot % self.num_buckets
        bucket = self.buckets[bucket_num]
        bucket_slot = bucket["slot"]
        if bucket_slot is None:
            bucket["slot"] = slot
            bucket["timestamp"] = timestamp
        elif bucket_slot < slot:
            bucket["data"].clear()
            bucket["slot"] = slot
            bucket["timestamp"] = timestamp
        elif bucket_slot > slot:
            raise KeyError()
        return bucket

    def put(self, timestamp, key, data):
        self._get_bucket(timestamp)["data"][key] = data

    def get(self, current_time, key):
        return self._get_bucket(current_time)["data"].get(key)

    def get_data(self, current_time):
        return self._get_bucket(current_time)["data"]
