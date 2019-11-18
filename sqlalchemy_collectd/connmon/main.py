from __future__ import absolute_import

import argparse
import logging

from . import display
from . import stat
from ..server import listener
from ..server import receiver

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

    receiver_ = receiver.Receiver(
        options.host, options.port, log, include_pids=False
    )

    listener.listen(receiver_)

    stat_ = stat.Stat(receiver_)
    stat_.start()

    service_str = "[Direct host: %s:%s]" % (options.host, options.port)

    #_dummy_wait()
    display_ = display.Display(stat_, service_str)
    display_.start()


def _dummy_wait():
    import time
    import logging

    logging.basicConfig()
    log.setLevel(logging.DEBUG)

    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
