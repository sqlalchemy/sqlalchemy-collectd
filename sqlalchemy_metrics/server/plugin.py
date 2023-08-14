from __future__ import annotations

import logging
import time

from . import listener
from . import receiver
from .logging import CollectdHandler

if True:
    import collectd  # type: ignore[import]

log = logging.getLogger(__name__)

receiver_: receiver.Receiver


def get_config(config):
    global aggregator_

    start_plugin(config)


def start_plugin(config):
    global receiver_

    config_dict = {elem.key: tuple(elem.values) for elem in config.children}
    host, port = config_dict.get("listen", ("localhost", 25827))

    CollectdHandler.setup(__name__, config_dict.get("loglevel", ("info",))[0])

    receiver_ = receiver.Receiver(host, int(port), log)

    log.info(
        "sqlalchemy.collectd server listening for "
        "SQLAlchemy clients on UDP %s %d" % (host, port)
    )

    listener.listen(receiver_)

    monitor_host, monitor_port = config_dict.get("monitor", (None, None))
    if monitor_host is not None and monitor_port is not None:
        from sqlalchemy_collectd.connmon import plugin as connmon

        log.warn(
            "the connmon plugin should now be configured separately in its "
            "own <Module> section"
        )
        connmon.start_plugin(config)


def read(data=None):
    """Extract data from received messages periodically and broadcast to
    the collectd server in which we are embedded.

    The values are sent as "external" types, meaning we are using the
    "derive" and "count" types in collectd types.db.

    """
    global receiver_
    now = time.time()
    receiver_.summarize(collectd, now)


collectd.register_config(get_config)
collectd.register_read(read)
