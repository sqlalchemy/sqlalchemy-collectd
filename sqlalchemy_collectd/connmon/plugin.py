import logging

import collectd

from .. import protocol
from ..client import internal_types
from ..server import aggregator
from ..server.logging import CollectdHandler
from ..server.receiver import COLLECTD_PLUGIN_NAME

log = logging.getLogger(__name__)


def get_config(config):

    start_plugin(config)


def start_plugin(config):
    global client_
    global values_aggregator

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}

    monitor_host, monitor_port = config_dict.get(
        "monitor", ("localhost", 25828)
    )
    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])

    values_aggregator = ValuesAggregator(
        [type_.name for type_ in [internal_types.pool, internal_types.totals]]
    )

    client_ = protocol.ClientConnection(monitor_host, int(monitor_port))
    log.info(
        "sqlalchemy.collectd forwarding server-wide SQLAlchemy "
        "messages to connmon clients on %s %d",
        monitor_host,
        monitor_port,
    )


# TODO: don't do this work here.   Build a generic "external types to internal types"
# stream translator, test it separately, then connect that here.


class ValuesAggregator(object):
    def __init__(self, bucket_names, num_buckets=4):
        self.buckets = None
        self.interval = None
        self.bucket_names = bucket_names

    def _init_buckets(self, interval):
        # the interval at which we bucket the data has to be longer than
        # the interval coming in from the messages, since we want to give
        # enough time for all of them to come in
        self.interval = int(interval) * 2
        self.buckets = {
            name: aggregator.TimeBucket(4, self.interval)
            for name in self.bucket_names
        }

    def receive_value(self, value):
        if not self.interval:
            self._init_buckets(value.interval)

        # note that the Value object is for a single element of one
        # of the elements of the "type".  this corresponds to how we
        # send it from the summarizer.
        type_ = internal_types.type_by_value_name[value.type_instance]
        bucket_name = type_.name
        bucket = self.buckets[bucket_name]
        records = bucket.get_data(value.time)
        key = (value.host, value.plugin_instance)
        if key not in records:
            records[key] = {}
        records[key][value.type_instance] = value.values[0]
        if len(records[key]) == len(type_.names):
            print("ready to broadcast: %s" % records[key])


def write(values):
    if values.plugin == COLLECTD_PLUGIN_NAME:
        print(values)
        values_aggregator.receive_value(values)


collectd.register_config(get_config)
collectd.register_write(write)