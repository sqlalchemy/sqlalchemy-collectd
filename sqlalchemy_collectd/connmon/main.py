from __future__ import annotations

import argparse
import logging

from . import display
from . import stat
from .. import collectd_types
from .. import protocol

log = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="collectd hostname to listen for UDP messages",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=25828,
        help="collectd port to listen for UDP messages ",
    )
    options = parser.parse_args(argv)

    network_receiver = protocol.NetworkReceiver(
        protocol.ServerConnection(options.host, options.port, log),
        [collectd_types.count_external, collectd_types.derive_external],
    )

    stat_ = stat.Stat(network_receiver, log)
    stat_.start()

    service_str = "[Direct host: %s:%s]" % (options.host, options.port)

    display_ = display.Display(stat_, service_str)
    display_.start()


if __name__ == "__main__":
    main()
