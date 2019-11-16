import logging
import time

import collectd

from . import listener
from . import receiver
from .logging import CollectdHandler
from .. import protocol

log = logging.getLogger(__name__)

receiver_ = None


def get_config(config):
    global aggregator_

    start_plugin(config)


def start_plugin(config):
    global receiver_
    global monitor_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    monitor_host, monitor_port = config_dict.get("monitor", (None, None))

    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])
    CollectdHandler.setup(
        protocol.__name__, config_dict.get("loglevel", ("info",))[0]
    )

    receiver_ = receiver.Receiver()

    connection = protocol.ServerConnection(host, int(port))
    log.info(
        "sqlalchemy.collectd server listening for "
        "SQLAlchemy clients on UDP %s %d" % (host, port)
    )

    listener.listen(connection, receiver_)


def read(data=None):
    now = time.time()
    receiver_.summarize(collectd, now)


collectd.register_config(get_config)
collectd.register_read(read)
