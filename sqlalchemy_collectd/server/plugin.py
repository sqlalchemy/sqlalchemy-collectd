import logging
import sys
import time

import collectd

from . import listener
from . import monitor
from . import receiver
from . import summarizer
from .. import __version__
from .. import protocol

log = logging.getLogger(__name__)

receiver_ = None


class CollectdHandler(logging.Handler):
    levels = {
        logging.INFO: collectd.info,
        logging.WARN: collectd.warning,
        logging.ERROR: collectd.error,
        logging.DEBUG: collectd.info,
        logging.CRITICAL: collectd.error,
    }

    def emit(self, record):
        fn = self.levels[record.levelno]
        fn(record.msg % record.args)


def get_config(config):
    global aggregator_

    start_plugin(config)


def start_plugin(config):
    global receiver_
    global monitor_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    monitor_host, monitor_port = config_dict.get("monitor", (None, None))

    logging.getLogger().addHandler(CollectdHandler())

    loglevel = {
        "warn": logging.WARN,
        "error": logging.ERROR,
        "debug": logging.DEBUG,
        "info": logging.INFO,
    }[config_dict.get("loglevel", ("info",))[0]]

    logging.getLogger().setLevel(loglevel)

    log.info("sqlalchemy_collectd plugin version %s", __version__)
    log.info("Python version: %s", sys.version)

    receiver_ = receiver.Receiver()

    if monitor_host is not None and monitor_port is not None:
        receiver_.monitors.append(
            monitor.Monitor(monitor_host, int(monitor_port))
        )

    connection = protocol.ServerConnection(host, int(port))

    listener.listen(connection, receiver_)


def read(data=None):
    now = time.time()
    summarizer.summarize(receiver_, now)


collectd.register_config(get_config)
collectd.register_read(read)
