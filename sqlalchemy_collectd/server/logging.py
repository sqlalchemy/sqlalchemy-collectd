from __future__ import absolute_import

import logging
import sys

import collectd

from .. import __version__

_the_handler = None


class CollectdHandler(logging.Handler):
    levels = {
        logging.INFO: collectd.info,
        logging.WARN: collectd.warning,
        logging.ERROR: collectd.error,
        logging.DEBUG: collectd.info,
        logging.CRITICAL: collectd.error,
    }

    def emit(self, record):
        fn = self.levels[record.levelno]
        record.msg = ("[%s] " % record.name) + record.msg
        fn(self.format(record))

    @classmethod
    def setup(cls, name, config_loglevel):
        global _the_handler
        if _the_handler is None:
            _the_handler = CollectdHandler()
            collectd.info(
                "[sqlalchemy-collectd] sqlalchemy_collectd version: %s"
                % __version__
            )
            collectd.info(
                "[sqlalchemy-collectd] Python version: %s" % sys.version
            )

        log = logging.getLogger(name)
        log.addHandler(_the_handler)

        loglevel = {
            "warn": logging.WARN,
            "error": logging.ERROR,
            "debug": logging.DEBUG,
            "info": logging.INFO,
        }[config_loglevel]

        log.setLevel(loglevel)
