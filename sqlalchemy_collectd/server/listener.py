from __future__ import absolute_import

import logging
import threading

log = logging.getLogger("sqlalchemy_collectd")


def _receive(receiver):
    while True:
        try:
            receiver.receive()
        except Exception:
            log.error("message receiver caught an exception", exc_info=True)
        except BaseException as be:
            log.info(
                "message receiver thread caught %s exception, exiting"
                % type(be).__name__
            )
            break


def listen(receiver):
    global listen_thread
    listen_thread = threading.Thread(target=_receive, args=(receiver,))
    listen_thread.daemon = True
    listen_thread.start()
