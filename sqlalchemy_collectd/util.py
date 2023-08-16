from __future__ import annotations

import asyncio
import logging
import threading


class AsyncWorker:
    def __init__(self, log: logging.Logger):
        self.log = log

    async def _init_service_awaitable(self):
        raise NotImplementedError()

    async def _run_service_awaitable(self):
        raise NotImplementedError()

    async def _run_service(self):
        await self._init_service_awaitable()

        self.loop = asyncio.get_event_loop()
        while True:
            try:
                await self._run_service_awaitable()
            except Exception:
                self.log.error(
                    f"{self.__class__.__name__} caught an exception",
                    exc_info=True,
                )
            except BaseException as be:
                self.log.info(
                    f"{self.__class__.__name__} caught a fatal exception "
                    f"{type(be).__name__} exiting"
                )
                break

    def start(self):
        listener_thread = threading.Thread(
            target=asyncio.run, args=(self._run_service(),)
        )
        listener_thread.setDaemon(True)
        listener_thread.start()
