from .. import __version__
import sys
import collectd
from . import listener
from . import receiver
from .. import protocol
import time
import logging

log = logging.getLogger(__name__)

receiver_ = None


# TODO: merge collectd.notice w/ python logging?
def _notice(msg):
    collectd.notice("[sqlalchemy-collectd] %s" % msg)


def get_config(config):
    global aggregator_

    _notice("sqlalchemy_collectd plugin version %s" % __version__)
    _notice("Python version: %s" % sys.version)
    start_plugin(config)


def start_plugin(config):
    global receiver_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    receiver_ = receiver.Receiver()
    connection = protocol.ServerConnection(host, int(port))

    listener.listen(connection, receiver_)


def read(data=None):
    now = time.time()
    receiver_.summarize(now)


collectd.register_config(get_config)
collectd.register_read(read)
