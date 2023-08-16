from __future__ import annotations

import argparse
import asyncio
import logging

from . import display
from . import stat
from .. import collectd_types
from .. import networking

log = logging.getLogger(__name__)


async def main_async(argv=None) -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["listen", "connect"],
        help="Listen on a UDP socket or connect to a listening UDP socket",
    )
    parser.add_argument(
        "--host",
        type=str,
        # asyncio UDP seems to not understand "localhost" name...
        default="127.0.0.1",
        help="collectd hostname to listen or connect for UDP messages",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=25828,
        help="collectd port to listen or connect for UDP messages ",
    )
    options = parser.parse_args(argv)

    if options.command == "listen":
        network_receiver = networking.AsyncNetworkReceiver(
            (
                await networking.UDPServerReceiver.receive_from_send_clients(
                    options.host, options.port, log
                )
            ),
            [collectd_types.count_external, collectd_types.derive_external],
        )
    elif options.command == "connect":
        network_receiver = networking.AsyncNetworkReceiver(
            (
                await networking.UDPClientReceiver.connect(
                    options.host, options.port, log
                )
            ),
            [collectd_types.count_external, collectd_types.derive_external],
        )
    else:
        assert False

    stat_ = stat.Stat(network_receiver, log)
    stat_.start()

    # await asyncio.sleep(30)
    service_str = "[Direct host: %s:%s]" % (options.host, options.port)
    display_ = display.Display(stat_, service_str)
    await display_.run_async()


def main(argv=None):
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
