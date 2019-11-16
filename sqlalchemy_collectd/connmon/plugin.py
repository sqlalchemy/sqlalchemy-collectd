import logging

import collectd

from .. import internal_types
from .. import protocol
from .. import stream
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

    types = [
        internal_types.pool_internal,
        internal_types.totals_internal,
        internal_types.process_internal,
    ]

    client_connection = protocol.ClientConnection(
        monitor_host, int(monitor_port)
    )
    message_sender = protocol.MessageSender(*types)

    def sender(values_obj):
        #        print("translated values_obj: %s" % values_obj)
        message_sender.send(client_connection, values_obj)

    values_aggregator = stream.StreamTranslator(
        *types
    ).combine_into_grouped_values(sender)
    log.info(
        "sqlalchemy.collectd forwarding server-wide SQLAlchemy "
        "messages to connmon clients on %s %d",
        monitor_host,
        monitor_port,
    )


def write(cd_values_obj):
    if cd_values_obj.plugin == COLLECTD_PLUGIN_NAME:
        values_obj = protocol.Values.from_collectd_values(cd_values_obj)
        # print(values_obj)
        values_aggregator.put_values(values_obj)


collectd.register_config(get_config)
collectd.register_write(write)
