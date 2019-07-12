import logging
import threading

log = logging.getLogger(__name__)


def _receive(connection, receiver):
    while True:
        try:
            receiver.receive(connection)
        except Exception:
            log.error("message receiver caught an exception", exc_info=True)
        except BaseException as be:
            log.info(
                "message receiver thread caught %s exception, exiting"
                % type(be).__name__
            )
            break


def listen(connection, receiver):
    global listen_thread
    listen_thread = threading.Thread(
        target=_receive, args=(connection, receiver)
    )
    listen_thread.daemon = True
    listen_thread.start()
