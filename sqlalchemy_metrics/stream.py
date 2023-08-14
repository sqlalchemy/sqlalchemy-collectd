from __future__ import annotations

from typing import Dict
from typing import Generic
from typing import Iterator
from typing import Optional
from typing import Tuple
from typing import TypeVar
from typing import Union

from . import protocol


class StreamTranslator:
    """Translates Value objects from the "internal" to the "external"
    types.

    The mapping from the "internal" types in collectd_types.py to
    the "external" types is to break each internal type into individual
    values of type GAUGE or DERIVE.  The collectd "count" and "derive" types
    defined in types.db serve as the destination for these values.

    While the "internal" types are more efficient and suitable for the large
    volume of messages sent by SQLAlchemy clients, as they are sent with a low
    "interval" setting as well as a full set of messages per  process, the
    "external" types are publicly available for other collectd services and as
    the per-process messages have been aggregated into per-"program" messages
    and are usually at a lower interval, there is less message volume.

    """

    def __init__(self, *collectd_types):
        self.collectd_types = collectd_types

        self._type_by_name = {t.name: t for t in collectd_types}
        self.external_types = {}
        self.external_type_to_internal = {}
        self._protocol_type_string_names = {
            protocol.VALUE_GAUGE: "count",
            protocol.VALUE_DERIVE: "derive",
        }

        for internal_type in collectd_types:
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


_TBKEY = TypeVar("_TBKEY")
_TBVALUE = TypeVar("_TBVALUE")


class TimeBucket(Generic[_TBKEY, _TBVALUE]):

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

    def _get_bucket(
        self, timestamp: Union[float, int], interval: Optional[int]
    ) -> "DictFacade[_TBKEY, _TBVALUE]":
        if interval is not None:
            self.last_interval = interval

        oldest_to_accept = int(self.last_interval * self.interval_factor)

        if (
            self.last_interval
            and int(timestamp) < int(self.last_timestamp) - oldest_to_accept
        ):
            raise ValueError(
                f"bucket timestamp is now {self.last_timestamp}, "
                f"greater than given timestamp of {timestamp} "
                f"plus interval {oldest_to_accept}"
            )
        for k in list(self.bucket):
            ts, b_interval, value = self.bucket[k]
            if ts < timestamp - int(b_interval * self.interval_factor):
                del self.bucket[k]

        self.last_timestamp = timestamp
        return DictFacade(timestamp, interval, self.bucket)

    def put(
        self,
        timestamp: int,
        interval: int,
        key: _TBKEY,
        data: _TBVALUE,
    ) -> "DictFacade[_TBKEY, _TBVALUE]":
        bucket_data = self._get_bucket(timestamp, interval)
        bucket_data[key] = data
        return bucket_data

    def get(
        self,
        current_time: Union[float, int],
        key: _TBKEY,
        interval: Optional[int] = None,
    ) -> Optional[_TBVALUE]:
        return self._get_bucket(current_time, interval).get(key)

    def get_data(
        self, current_time: Union[float, int], interval: Optional[int] = None
    ) -> "DictFacade[_TBKEY, _TBVALUE]":
        return self._get_bucket(current_time, interval)


class DictFacade(Generic[_TBKEY, _TBVALUE]):
    __slots__ = "timestamp", "interval", "dictionary"

    def __init__(
        self,
        timestamp: Union[float, int],
        interval: Optional[int],
        dictionary: Dict[
            _TBKEY, Tuple[Union[float, int], Optional[int], _TBVALUE]
        ],
    ):
        self.timestamp = timestamp
        self.interval = interval
        self.dictionary = dictionary

    def __contains__(self, key: _TBKEY) -> bool:
        return key in self.dictionary

    def get(
        self, key: _TBKEY, default: Optional[_TBVALUE] = None
    ) -> Optional[_TBVALUE]:
        timestamp, interval, value = self.dictionary.get(
            key, (None, None, default)
        )
        return value

    def __getitem__(self, key: _TBKEY) -> _TBVALUE:
        timestamp, interval, value = self.dictionary[key]
        return value

    def __setitem__(self, key: _TBKEY, value: _TBVALUE):
        self.dictionary[key] = (self.timestamp, self.interval, value)

    def __delitem__(self, key: _TBKEY):
        del self.dictionary[key]

    def __len__(self) -> int:
        return len(self.dictionary)

    def __iter__(self) -> Iterator[_TBKEY]:
        return iter(self.dictionary)

    def keys(self) -> Iterator[_TBKEY]:
        return iter(self.dictionary.keys())
