import os
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
        self.config = {}
        self._get_argument(
            "collectd_host", "collectd_host", self.config, url, kwargs)
        self._get_argument(
            "collectd_port", "collectd_port", self.config, url, kwargs)
        self._get_argument(
            "collectd_report_host", "hostname", self.config, url, kwargs)
        self._get_argument(
            "collectd_program_name", "progname", self.config, url, kwargs)

    def _get_argument(self, name, dest_name, dest, url, kwargs):
        # favor the URL but pop the name from both
        if name in kwargs:
            dest[dest_name] = kwargs.pop(name)

        if name in url.query:
            dest[dest_name] = url.query.pop(name)

    def handle_dialect_kwargs(self, dialect_cls, dialect_args):
        """parse and modify dialect kwargs"""

    def handle_pool_kwargs(self, pool_cls, pool_args):
        """parse and modify pool kwargs"""

    def engine_created(self, engine):
        """Receive the :class:`.Engine` object when it is fully constructed.

        The plugin may make additional changes to the engine, such as
        registering engine or connection pool events.

        """
        start_plugin(engine, **self.config)


def start_plugin(
        engine, hostname=None, progname=None,
        collectd_host="localhost", collectd_port=25827):

    if hostname is None:
        hostname = socket.gethostname()

    if progname is None:
        progname = os.path.basename(sys.argv[0])

    sender_ = sender.Sender(hostname, progname)
    collection_target = collector.CollectionTarget.collection_for_name(
        progname)
    collector.EngineCollector(collection_target, engine)

    connection = protocol.ClientConnection.for_host_port(
        collectd_host, collectd_port)

    worker.add_target(
        connection,
        collection_target,
        sender_)
