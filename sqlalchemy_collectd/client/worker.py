import logging
import os
import threading
import time

log = logging.getLogger(__name__)

_WORKER_THREAD = None
_PID = os.getpid()

_collection_targets = []


def _check_threads_started():
    global _WORKER_THREAD, _PID
    ospid = os.getpid()

    if _WORKER_THREAD is None or _PID != ospid:

        _PID = ospid
        _WORKER_THREAD = threading.Thread(target=_process, args=(2,))
        _WORKER_THREAD.daemon = True
        _WORKER_THREAD.start()


def _process(interval):
    pid = os.getpid()
    log.info("Starting process thread in pid %s", pid)

    while True:
        now = time.time()
        for (
            collection_target,
            connection,
            sender,
            last_called,
        ) in _collection_targets:
            if now - last_called[0] > interval:
                last_called[0] = now
                sender.send(connection, collection_target, now, interval, pid)

        time.sleep(0.2)


def add_target(connection, collection_target, sender):
    _collection_targets.append((collection_target, connection, sender, [0]))
    _check_threads_started()
