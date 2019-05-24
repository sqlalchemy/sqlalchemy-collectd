import argparse

from . import display
from . import stat
from .. import protocol
from ..server import listener
from ..server import receiver


def main(argv=[]):
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

    receiver_ = receiver.Receiver()

    connection = protocol.ServerConnection(options.host, options.port)

    listener.listen(connection, receiver_)

    stat_ = stat.Stat(receiver_.aggregator)
    stat_.start()

    display_ = display.Display(stat_, connection)
    display_.start()


if __name__ == "__main__":
    main()
