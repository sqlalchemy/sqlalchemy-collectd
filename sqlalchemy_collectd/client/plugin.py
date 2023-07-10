from __future__ import annotations

import logging
import os
import socket
import sys
from typing import Any
from typing import Dict
from typing import TYPE_CHECKING

from sqlalchemy.engine import CreateEnginePlugin

from . import collector
from . import sender
from . import worker

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy import URL


log = logging.getLogger("sqlalchemy_collectd")


class Plugin(CreateEnginePlugin):
    url: URL
    config: Dict[str, Any]

    def __init__(self, url: URL, kwargs: dict[str, Any]):
        self.url = url
        self.config = {}
        self._get_argument(
            "collectd_host", "collectd_host", self.config, url, kwargs
        )
        self._get_argument(
            "collectd_port", "collectd_port", self.config, url, kwargs, int
        )
        self._get_argument(
            "collectd_report_host", "hostname", self.config, url, kwargs
        )
        self._get_argument(
            "collectd_program_name", "progname", self.config, url, kwargs
        )

    def _get_argument(self, name, dest_name, dest, url, kwargs, coerce_=None):
        # favor the URL but pop the name from both
        if name in kwargs:
            dest[dest_name] = kwargs.pop(name)
            if coerce_:
                dest[dest_name] = coerce_(dest[dest_name])

        sqla14_style = hasattr(CreateEnginePlugin, "update_url")

        if name in url.query:
            if sqla14_style:
                dest[dest_name] = url.query[name]
            else:
                dest[dest_name] = url.query.pop(name)
            if coerce_:
                dest[dest_name] = coerce_(dest[dest_name])

    def update_url(self, url: URL) -> URL:
        return url.difference_update_query(
            [
                "collectd_host",
                "collectd_port",
                "collectd_report_host",
                "collectd_program_name",
            ]
        )

    def handle_url_params(self, url_query):
        """modify url query parameters"""

    def handle_dialect_kwargs(self, dialect_cls, dialect_args):
        """parse and modify dialect kwargs"""

    def handle_pool_kwargs(self, pool_cls, pool_args):
        """parse and modify pool kwargs"""

    def engine_created(self, engine: Engine) -> None:
        """Receive the :class:`.Engine` object when it is fully constructed.

        The plugin may make additional changes to the engine, such as
        registering engine or connection pool events.

        """
        start_plugin(engine, **self.config)


def start_plugin(
    engine: Engine,
    hostname: str | None = None,
    progname: str | None = None,
    collectd_host: str = "localhost",
    collectd_port: int = 25827,
) -> None:
    if hostname is None:
        hostname = socket.gethostname()

    if progname is None:
        progname = os.path.basename(sys.argv[0])

    # registry on progname
    collection_target = collector.CollectionTarget.collection_for_name(
        progname
    )

    # unique per Engine
    collector.EngineCollector(collection_target, engine)

    # registry on host/prog/host/port
    sender_ = sender.Sender.get_sender(
        hostname, progname, collectd_host, collectd_port, log
    )

    # registry on collection_target / sender
    worker.add_target(collection_target, sender_)
