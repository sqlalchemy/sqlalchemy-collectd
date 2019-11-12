import logging

import collectd


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
        record.msg = "[sqlalchemy-collectd] " + record.msg
        fn(self.format(record))
