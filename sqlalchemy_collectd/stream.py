from . import protocol


class StreamTranslator(object):
    """Translates Value objects between internal types and "external"
    types.

    The "external" types are the simple types that are in collectd
    types.db, where we are looking at the "derive" type, which is a mapping
    to a single protocol.VALUE_DERIVE value, and the "count" type, which is
    a mapping to a zero-bounded protocol.VALUE_GAUGE type.  There is also
    a "gauge" type however we are working with zero-bounded ranges.

    We use these pre-defined types because SQLAlchemy-collectd does not
    have an entry in the collectd types.db file and collectd doesn't give us
    a straightforward way to extend on these types.


    """

    def __init__(self, *internal_types):
        self.internal_types = internal_types

        self._type_by_name = {t.name: t for t in internal_types}
        self.external_types = {}
        self.external_type_to_internal = {}
        self._protocol_type_string_names = {
            protocol.VALUE_GAUGE: "count",
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

    def break_into_individual_values(self, values_obj):
        internal_type = self._type_by_name[values_obj.type]
        for name, protocol_type, value_element in zip(
            internal_type.names, internal_type.types, values_obj.values
        ):
            external_type = self.external_types[name]
            yield values_obj.build(
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
        self.buckets = {
            type_.name: TimeBucket(4)
            for type_ in stream_translator.internal_types
        }

    def put_values(self, values_obj):
        external_type = self.stream_translator.external_types[
            values_obj.type_instance
        ]
        internal_type = self.stream_translator.external_type_to_internal[
            external_type
        ]
        bucket = self.buckets[internal_type.name]
        bucket_data = bucket.get_data(values_obj.time, values_obj.interval * 4)

        key = (values_obj.plugin_instance,)
        if key not in bucket_data:
            bucket_data[key] = per_instance_bucket = {}
        else:
            per_instance_bucket = bucket_data[key]

        external_name = external_type.name
        per_instance_bucket[external_name] = values_obj
        if len(per_instance_bucket) == len(internal_type.names):
            aggregated_value = sum(per_instance_bucket.values())
            aggregated_value = aggregated_value.build(
                type=internal_type.name,
                type_instance=None,
                values=[
                    per_instance_bucket[external_name].values[0]
                    for external_name in internal_type.names
                ],
            )
            del bucket_data[key]
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
        slot = int(timestamp // self.interval)
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
        if interval is None and self.interval is None:
            return None
        return self._get_bucket(current_time, interval)["data"].get(key)

    def get_data(self, current_time, interval=None):
        if interval is None and self.interval is None:
            return {}
        return self._get_bucket(current_time, interval)["data"]
