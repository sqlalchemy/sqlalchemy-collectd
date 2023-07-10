from __future__ import annotations

import logging

from .. import collectd_types
from .. import protocol
from ..server.logging import CollectdHandler

if True:
    import collectd  # type: ignore[import]

log = logging.getLogger(__name__)


def get_config(config):
    start_plugin(config)


def start_plugin(config):
    global client_
    global message_sender

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}

    monitor_host, monitor_port = config_dict.get(
        "monitor", ("localhost", 25828)
    )
    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])

    types = [collectd_types.derive_external, collectd_types.count_external]

    message_sender = protocol.NetworkSender(
        protocol.ClientConnection(monitor_host, int(monitor_port), log), types
    )

    log.info(
        "sqlalchemy.collectd forwarding server-wide SQLAlchemy "
        "messages to connmon clients on %s %d",
        monitor_host,
        monitor_port,
    )


def write(cd_values_obj):
    """Receive values from the collectd server and forward out on UDP
    for connmon listeners to receive.

    The values are received as "external" types, meaning they use the
    "derive" and "count" types in collectd types.db.  The connmon client
    now receives and interprets these objects directly.

    """

    if cd_values_obj.plugin == collectd_types.COLLECTD_PLUGIN_NAME:
        values_obj = protocol.Values.from_collectd_values(cd_values_obj, log)
        message_sender.send(values_obj)


collectd.register_config(get_config)
collectd.register_write(write)
