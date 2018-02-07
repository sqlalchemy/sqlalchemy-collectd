import socket
import sys

from sqlalchemy.engine import CreateEnginePlugin

from .. import protocol
from . import sender
from . import worker
from . import collector


class Plugin(CreateEnginePlugin):
    def __init__(self, url, kwargs):
        self.url = url

    def handle_dialect_kwargs(self, dialect_cls, dialect_args):
        """parse and modify dialect kwargs"""

    def handle_pool_kwargs(self, pool_cls, pool_args):
        """parse and modify pool kwargs"""

    def engine_created(self, engine):
        """Receive the :class:`.Engine` object when it is fully constructed.

        The plugin may make additional changes to the engine, such as
        registering engine or connection pool events.

        """
        start_plugin(engine)


def start_plugin(engine):
    # TODO: all this configurable
    hostname = socket.gethostname()
    progname = sys.argv[0]

    collectd_hostname = "localhost"
    collectd_port = 25827

    sender_ = sender.Sender(hostname, progname)
    collection_target = collector.CollectionTarget.collection_for_name(
        progname)
    collector.EngineCollector(collection_target, engine)

    connection = protocol.ClientConnection.for_host_port(
        collectd_hostname, collectd_port)

    worker.add_target(
        connection,
        collection_target,
        sender_)

