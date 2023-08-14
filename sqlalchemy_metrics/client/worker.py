from __future__ import annotations

import collections
import logging
import os
import threading
import time
from typing import TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .collector import CollectionTarget
    from .sender import Sender

log = logging.getLogger(__name__)

_WORKER_THREAD: threading.Thread | None = None
_PID = os.getpid()

_collection_targets: dict[
    tuple[CollectionTarget, Sender], list[int | float]
] = collections.OrderedDict()


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
    process_token = "%s:%s" % (pid, str(uuid.uuid4())[0:6])
    log.info(
        "Starting process thread in pid %s, process token %s",
        pid,
        process_token,
    )

    try:
        while True:
            now = time.time()
            for (
                (collection_target, sender),
                last_called,
            ) in _collection_targets.items():
                if now - last_called[0] > interval:
                    last_called[0] = now
                    try:
                        sender.send(
                            collection_target, now, interval, process_token
                        )
                    except Exception:
                        log.error("error sending stats", exc_info=True)

            time.sleep(0.2)
    except BaseException as be:
        log.info(
            "message sender thread caught %s exception, exiting"
            % type(be).__name__
        )


def add_target(collection_target, sender):
    if (collection_target, sender) not in _collection_targets:
        _collection_targets[(collection_target, sender)] = [0]
    _check_threads_started()
