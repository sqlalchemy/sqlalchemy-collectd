import threading
import unittest

import mock

from .. import worker


class WorkerTest(unittest.TestCase):
    def test_worker_resilency(self):
        canary = mock.Mock()

        collection_one = ["one", KeyError("random internal error"), "three"]
        collection_two = ["one", "two", SystemExit()]

        def send(collection, collection_target, now, interval, pid):
            obj = collection.pop(0)
            if isinstance(obj, BaseException):
                raise obj
            else:
                canary.send(collection_target, obj)

        the_time = [100]

        mutex = threading.Lock()

        # worker thread will call this at the top of its main loop.
        def start_loop():
            # still supporting Python 2, in Py3k only can instead use
            # nonlocal for "the_time"
            mutex.acquire()
            try:
                return the_time[0]
            finally:
                the_time[0] += 5
                mutex.release()

        with mock.patch.object(
            worker, "log"
        ) as mock_logger, mock.patch.object(
            worker.time, "time", mock.Mock(side_effect=start_loop)
        ), mock.patch.object(
            worker.time, "sleep"
        ):
            mutex.acquire()
            try:
                # this adds the target and also starts the worker thread.
                # however we have it blocked from doing anything via the
                # mutex above...
                worker.add_target(
                    collection_one, "target one", mock.Mock(send=send)
                )

                # ...so that we can also add this target and get deterministic
                # results
                worker.add_target(
                    collection_two, "target two", mock.Mock(send=send)
                )
            finally:
                # worker thread is unblocked
                mutex.release()

            # now wait, it will hit the SystemExit and exit.
            # if it times out, we failed.
            worker._WORKER_THREAD.join(1)

        # see that it did what we asked.
        self.assertEqual(
            [
                mock.call.send("target one", "one"),
                mock.call.send("target two", "one"),
                mock.call.send("target two", "two"),
                mock.call.send("target one", "three"),
            ],
            canary.mock_calls,
        )

        self.assertEqual(
            [
                mock.call.info("Starting process thread in pid %s", mock.ANY),
                mock.call.error("error sending stats", exc_info=True),
                mock.call.info(
                    "message sender thread caught SystemExit "
                    "exception, exiting"
                ),
            ],
            mock_logger.mock_calls,
        )
