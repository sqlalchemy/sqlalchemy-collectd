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


class TimeBucket(object):
    """Store objects based on the latest one received, discarding
    those that are stale based on the timestamp / interval given for that
    value.

    """

    __slots__ = "bucket", "last_timestamp", "interval_factor", "last_interval"

    def __init__(self):
        self.bucket = {}
        self.last_timestamp = 0
        self.last_interval = 0
        self.interval_factor = 1.2

    def _get_bucket(self, timestamp, interval):
        if interval is not None:
            self.last_interval = interval

        oldest_to_accept = int(self.last_interval * self.interval_factor)

        if (
            self.last_interval
            and int(timestamp) < int(self.last_timestamp) - oldest_to_accept
        ):

            raise ValueError(
                "bucket timestamp is now %s, "
                "greater than given timestamp of %s plus interval %s"
                % (self.last_timestamp, timestamp, oldest_to_accept)
            )
        for k in list(self.bucket):
            ts, b_interval, value = self.bucket[k]
            if ts < timestamp - int(b_interval * self.interval_factor):
                del self.bucket[k]

        self.last_timestamp = timestamp
        return DictFacade(timestamp, interval, self.bucket)

    def put(self, timestamp, interval, key, data):
        bucket_data = self._get_bucket(timestamp, interval)
        bucket_data[key] = data
        return bucket_data

    def get(self, current_time, key, interval=None):
        return self._get_bucket(current_time, interval).get(key)

    def get_data(self, current_time, interval=None):
        return self._get_bucket(current_time, interval)


class DictFacade(object):
    __slots__ = "timestamp", "interval", "dictionary"

    def __init__(self, timestamp, interval, dictionary):
        self.timestamp = timestamp
        self.interval = interval
        self.dictionary = dictionary

    def __contains__(self, key):
        return key in self.dictionary

    def get(self, key, default=None):
        timestamp, interval, value = self.dictionary.get(
            key, (None, None, default)
        )
        return value

    def __getitem__(self, key):
        timestamp, interval, value = self.dictionary[key]
        return value

    def __setitem__(self, key, value):
        self.dictionary[key] = (self.timestamp, self.interval, value)

    def __delitem__(self, key):
        del self.dictionary[key]

    def __iter__(self):
        return iter(self.dictionary)

    def keys(self):
        return self.dictionary.keys()
