from .. import __version__
import sys
import collectd
from . import listener
from . import receiver
from . import aggregator
from .. import protocol

aggregator_ = None


def _notice(msg):
    collectd.notice("[sqlalchemy-collectd] %s" % msg)


def get_config(config):
    global aggregator_

    _notice("sqlalchemy_collectd plugin version %s" % __version__)
    _notice("Python version: %s" % sys.version)
    start_plugin(config)


def start_plugin(config):
    global aggregator_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    aggregator_ = aggregator.Aggregator()
    receiver_ = receiver.Receiver()
    connection = protocol.ServerConnection(host, int(port))

    listener.listen(connection, aggregator_, receiver_)


def _read_raw_struct_to_values(message):
    # dispatch(
    #    [type][, values][, plugin_instance]
    # [, type_instance][, plugin][, host][, time][, interval]) -> None.

    return collectd.Values(
        type=message[protocol.TYPE_TYPE],
        values=message[protocol.TYPE_VALUES],
        plugin=message[protocol.TYPE_PLUGIN],
        host=message[protocol.TYPE_HOST],
        time=message[protocol.TYPE_TIME],
        type_instance=message[protocol.TYPE_TYPE_INSTANCE],
        plugin_instance=message[protocol.TYPE_PLUGIN_INSTANCE],
        interval=message[protocol.TYPE_INTERVAL]
    )

_read_struct_to_values = _read_raw_struct_to_values


def read(data=None):
    for message in aggregator_.outgoing():
        values = _read_struct_to_values(message)
        values.dispatch()


collectd.register_config(get_config)
collectd.register_read(read)
