from __future__ import absolute_import

import logging

import collectd

from .. import internal_types
from .. import protocol
from .. import stream
from ..server.logging import CollectdHandler

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

    message_sender = protocol.NetworkSender(
        protocol.ClientConnection(monitor_host, int(monitor_port), log), types
    )

    values_aggregator = stream.StreamTranslator(
        *types
    ).combine_into_grouped_values(message_sender.send)
    log.info(
        "sqlalchemy.collectd forwarding server-wide SQLAlchemy "
        "messages to connmon clients on %s %d",
        monitor_host,
        monitor_port,
    )


def write(cd_values_obj):
    """Receive values from the collectd server in which we are embedded, and
    send them to an aggregator that will broadcast them to clients.

    The values are received as "external" types, meaning they use the
    "derive" and "count" types in collectd types.db; an aggregator collects
    these and builds them into "internal" types which combine multiple
    types of values into single records.

    """

    if cd_values_obj.plugin == internal_types.COLLECTD_PLUGIN_NAME:
        values_obj = protocol.Values.from_collectd_values(cd_values_obj, log)
        values_aggregator.put_values(values_obj)


collectd.register_config(get_config)
collectd.register_write(write)
