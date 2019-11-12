import logging
import sys

import collectd

from .. import __version__
from .. import protocol
from ..client import internal_types
from ..server.logging import CollectdHandler
from ..server.receiver import COLLECTD_PLUGIN_NAME

log = logging.getLogger(__name__)


def get_config(config):

    start_plugin(config)


def start_plugin(config):
    global client_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}

    monitor_host, monitor_port = config_dict.get(
        "monitor", ("localhost", 25828)
    )

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

    client_ = protocol.ClientConnection(monitor_host, int(monitor_port))
    log.info(
        "sqlalchemy.collectd forwarding server-wide SQLAlchemy "
        "messages to connmon clients on %s %d",
        monitor_host,
        monitor_port,
    )


class ValuesCollector(object):
    def __init__(self, type_obj, host, plugin_instance):
        self.sender = protocol.MessageSender(
            type_=type_obj,
            host=host,
            plugin=COLLECTD_PLUGIN_NAME,
            plugin_instance=plugin_instance,
        )


aggregated_values = {}


def write(values):
    if values.plugin == COLLECTD_PLUGIN_NAME:
        print(values)
        return

        type_obj = internal_types.type_by_value_name[values.type_instance]

        key = (type_obj, values.host, values.plugin_instance)
        if key not in aggregated_values:
            aggregated_values[key] = sender = protocol.MessageSender(
                type_=type_obj,
                host=values.host,
                plugin=values.plugin,
                plugin_instance=values.plugin_instance,
                type_instance=values.type_instance,
                interval=values.interval,
            )
        else:
            sender = aggregated_values[key]


collectd.register_config(get_config)
collectd.register_write(write)
