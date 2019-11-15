from . import protocol


class StreamTranslator(object):
    def __init__(self, *internal_types):
        self.internal_types = internal_types

        self._type_by_name = {t.name: t for t in internal_types}
        self.external_types = {}
        self.external_type_to_internal = {}
        self._protocol_type_string_names = {
            protocol.VALUE_GAUGE: "gauge",
            protocol.VALUE_DERIVE: "derive",
        }

        for internal_type in internal_types:
            for name, value_type in zip(
                internal_type.names, internal_type.types
            ):
                self.external_types[name] = self._type_by_name[
                    name
                ] = external_type = protocol.Type(name, ("value", value_type))
                self.external_type_to_internal[external_type] = internal_type

    def break_into_individual_values(self, list_of_values):
        for value in list_of_values:
            internal_type = self._type_by_name[value.type]
            for name, protocol_type, value_element in zip(
                internal_type.names, internal_type.types, value.values
            ):
                external_type = self.external_types[name]
                yield value.build(
                    type_instance=external_type.name,
                    type=self._protocol_type_string_names[protocol_type],
                    values=[value_element],
                )

    def combine_into_grouped_values(self, consumer_fn):
        return ValueAggregator(self, consumer_fn)


class ValueAggregator(object):
    def __init__(self, stream_translator, consumer_fn):
        self.stream_translator = stream_translator
        self.consumer_fn = consumer_fn
        self.time_bucket = TimeBucket(4)

    def put_values(self, values):
        external_type = self.stream_translator.external_types[
            values.type_instance
        ]
        internal_type = self.stream_translator.external_type_to_internal[
            external_type
        ]
        key = (internal_type.name, external_type.name)
        bucket_data = self.time_bucket.put(
            values.time, values.interval, key, values
        )
        if len(bucket_data) == len(internal_type.names):
            aggregated_value = sum(bucket_data.values())
            aggregated_value = aggregated_value.build(
                type=internal_type.name,
                values=[
                    bucket_data[(internal_type.name, external_name)].values[0]
                    for external_name in internal_type.names
                ],
            )
            bucket_data.clear()
            self.consumer_fn(aggregated_value)


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

    def __init__(self, num_buckets):
        self.num_buckets = num_buckets
        self.buckets = [
            {"slot": None, "data": {}, "timestamp": 0}
            for i in range(num_buckets)
        ]
        self.interval = None

    def _get_bucket(self, timestamp, interval):
        if interval is not None:
            if self.interval != interval:
                if self.interval is None:
                    self.interval = interval
                else:
                    raise ValueError(
                        "current time bucket interval %d does not match "
                        "incoming interval %d" % (self.interval, interval)
                    )
        assert self.interval is not None
        timestamp = int(timestamp)
        slot = timestamp // (self.interval * 2)
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

    def put(self, timestamp, interval, key, data):
        bucket_data = self._get_bucket(timestamp, interval)["data"]
        bucket_data[key] = data
        return bucket_data

    def get(self, current_time, key, interval=None):
        return self._get_bucket(current_time, interval)["data"].get(key)

    def get_data(self, current_time, interval=None):
        return self._get_bucket(current_time, interval)["data"]
