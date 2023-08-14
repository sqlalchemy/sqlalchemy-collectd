from unittest import mock

from .. import listener
from ... import testing


class ListenerTest(testing.TestBase):
    def test_receive_resilency(self):
        canary = mock.Mock()

        collection = [
            "one",
            "two",
            "three",
            KeyError("random internal error"),
            "four",
            SystemExit(),
            "five",
        ]

        def receive():
            obj = collection.pop(0)
            if isinstance(obj, BaseException):
                raise obj
            else:
                canary.receive(obj)

        with mock.patch.object(listener, "log") as mock_logger:
            listener.listen(mock.Mock(receive=receive))

            # join the thread while the mock_logger is still attached
            listener.listen_thread.join(5)

        # call "five" doesn't happen because we should have exited
        self.assertEqual(
            [
                mock.call.receive("one"),
                mock.call.receive("two"),
                mock.call.receive("three"),
                mock.call.receive("four"),
            ],
            canary.mock_calls,
        )
        self.assertEqual(
            [
                mock.call.error(
                    "message receiver caught an exception", exc_info=True
                ),
                mock.call.info(
                    "message receiver thread caught SystemExit "
                    "exception, exiting"
                ),
            ],
            mock_logger.mock_calls,
        )
