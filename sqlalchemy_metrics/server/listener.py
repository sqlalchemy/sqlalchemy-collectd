from __future__ import annotations

import logging
import threading
import typing

if typing.TYPE_CHECKING:
    from .receiver import Receiver


log = logging.getLogger("sqlalchemy_collectd")


def _receive(receiver: "Receiver"):
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


listen_thread: threading.Thread


def listen(receiver: Receiver) -> None:
    global listen_thread
    listen_thread = threading.Thread(target=_receive, args=(receiver,))
    listen_thread.daemon = True
    listen_thread.start()
