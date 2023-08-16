"""Using the collectd protocol because we originally were going to
connect straight to the network plugin.

"""
from __future__ import annotations

import asyncio
import os
import socket
import threading
import time
from typing import Any
from typing import ClassVar
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING

from .protocol import MessagePacker
from .protocol import MessageUnpacker
from .protocol import Type
from .protocol import Values

if TYPE_CHECKING:
    from logging import Logger


class Connection:
    __slots__ = ("log", "host", "port")

    log: Logger
    host: str
    port: int
    protocol_name: ClassVar[str] = "UDP"

    def debug_receive_message(self, message: Any):
        self.log.debug(
            "receive[%s:%s:%s] -> %s",
            self.protocol_name,
            self.host,
            self.port,
            message,
        )

    def debug_send_message(self, message: Any):
        self.log.debug(
            "send[%s:%s:%s] -> %s",
            self.protocol_name,
            self.host,
            self.port,
            message,
        )


class AsyncSender(Connection):
    __slots__ = ()

    async def send_async(self, message: bytes) -> None:
        raise NotImplementedError()


class AsyncReceiver(Connection):
    __slots__ = ()

    async def receive_async(self) -> Tuple[bytes, str]:
        raise NotImplementedError()


class SyncReceiver(Connection):
    __slots__ = ()

    def receive(self) -> Tuple[bytes, str]:
        raise NotImplementedError()


class SyncSender(Connection):
    __slots__ = ()

    def send(self, message: bytes) -> None:
        raise NotImplementedError()


class _UDPProtocol(asyncio.DatagramProtocol):
    __slots__ = ("log", "transport")

    transport: asyncio.DatagramTransport | None

    def __init__(self, log):
        self.log = log

    def connection_made(self, transport):
        self.transport = transport

    def error_received(self, exc):
        self.log.error(f"Error received: {exc}")

    def connection_lost(self, exc):
        self.transport = None


class SyncOnlyUDPClientSender(SyncSender):
    """the network client used by the SQLAlchemy plugin.

    as this object is embedded in arbitrary programs, it intentionally does
    not do anything with event loops or threads,
    just puts packets on a udp socket and that's it.

    """

    __slots__ = ("_mutex", "socket", "pid")

    connections: ClassVar[dict[tuple[str, int], SyncOnlyUDPClientSender]] = {}

    create_mutex: ClassVar[threading.Lock] = threading.Lock()

    socket: socket.socket | None
    log: Logger

    def __init__(self, host: str, port: int, log: Logger):
        self.host = host
        self.port = port
        self.log = log
        self._mutex = threading.Lock()
        self.socket = None
        self.pid = None

    def _check_connect(self):
        if self.socket is None or self.pid != os.getpid():
            self.pid = os.getpid()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return self.socket

    @classmethod
    def for_host_port(
        cls, host: str, port: int, log: Logger
    ) -> SyncOnlyUDPClientSender:
        cls.create_mutex.acquire()
        try:
            key = (host, port)
            if key not in cls.connections:
                cls.connections[key] = connection = SyncOnlyUDPClientSender(
                    host, port, log
                )
                return connection
            else:
                return cls.connections[key]

        finally:
            cls.create_mutex.release()

    def send(self, message: bytes) -> None:
        self._mutex.acquire()
        try:
            socket = self._check_connect()
            socket.sendto(message, (self.host, self.port))
        except IOError:
            self.log.error("Error in socket.sendto", exc_info=True)
        finally:
            self._mutex.release()


class UDPClientReceiver(AsyncReceiver):
    _protocol: _ClientReceiverProtocol
    _transport: asyncio.DatagramTransport

    log: Logger

    class _ClientReceiverProtocol(_UDPProtocol):
        _queue: asyncio.Queue[Optional[Tuple[bytes, str]]]

        def __init__(self, log):
            super().__init__(log)
            self._queue = asyncio.Queue()

        def connection_made(self, transport):
            self.transport = transport
            self._send_helo_task = asyncio.create_task(self._send_helo())

        async def _send_helo(self):
            while self.transport is not None:
                self.transport.sendto(b"HELO")
                await asyncio.sleep(5)

        async def recvfrom(self) -> Tuple[bytes, str]:
            rec = await self._queue.get()
            if rec is None:
                # TODO: figure out what this should be
                raise IOError("closed")

            return rec

        def datagram_received(self, data, addr):
            self._queue.put_nowait((data, str(addr)))

        def connection_lost(self, exc):
            self._queue.put_nowait(None)
            super().connection_lost(exc)

    def __init__(self, host: str, port: int, log: Logger):
        self.host = host
        self.port = port
        self.log = log
        self.pid = None

    @classmethod
    async def connect(
        cls, host: str, port: int, log: Logger
    ) -> UDPClientReceiver:
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls._ClientReceiverProtocol(log),
            remote_addr=(host, port),
        )
        connection = UDPClientReceiver(host, port, log)
        connection._transport = transport
        connection._protocol = protocol
        return connection

    async def receive_async(self) -> Tuple[bytes, str]:
        return await self._protocol.recvfrom()


class UDPClientSender(AsyncSender):
    log: Logger

    protocol: _ClientSenderProtocol | None
    transport: asyncio.DatagramTransport | None

    pid: int | None

    class _ClientSenderProtocol(_UDPProtocol):
        def send(self, message, addr):
            if self.transport is not None:
                self.transport.sendto(message)

        def error_received(self, exc):
            if isinstance(exc, ConnectionRefusedError):
                return
            super().error_received(exc)

        def datagram_received(self, data, addr):
            pass

    def __init__(self, host: str, port: int, log: Logger):
        self.host = host
        self.port = port
        self.log = log
        self.transport = self.protocol = None
        self.pid = None

    async def _check_connect(self) -> _ClientSenderProtocol:
        if self.protocol is None or self.pid != os.getpid():
            self.pid = os.getpid()
            loop = asyncio.get_running_loop()

            transport, protocol = await loop.create_datagram_endpoint(
                lambda: self._ClientSenderProtocol(self.log),
                remote_addr=(self.host, self.port),
            )

            self.transport, self.protocol = transport, protocol

        return self.protocol

    async def send_async(self, message: bytes) -> None:
        protocol = await self._check_connect()
        protocol.send(message, (self.host, self.port))


class UDPServerSender(AsyncSender):
    _protocol: _ServerSenderProtocol
    _transport: asyncio.DatagramTransport

    class _ServerSenderProtocol(_UDPProtocol):
        def __init__(self, log):
            super().__init__(log)
            self.addrs = {}

        def send_to_all(self, message):
            # TODO: timeout?
            now = time.time()
            for addr, ts in list(self.addrs.items()):
                if now - ts > 30:
                    self.addrs.pop(addr)
                elif self.transport is not None:
                    self.transport.sendto(message, addr)

        def datagram_received(self, data, addr):
            if data == b"HELO":
                self.addrs[addr] = time.time()

    def __init__(self, host, port, log):
        self.host = host
        self.port = port
        self.log = log

    @classmethod
    async def listen_for_receive_clients(
        cls, host, port, log
    ) -> UDPServerSender:
        connection = UDPServerSender(host, port, log)
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls._ServerSenderProtocol(log), local_addr=(host, port)
        )
        connection._transport = transport
        connection._protocol = protocol
        return connection

    async def send_async(self, message: bytes) -> None:
        self._protocol.send_to_all(message)


class UDPServerReceiver(AsyncReceiver):
    _protocol: _ServerReceiverProtocol
    _transport: asyncio.DatagramTransport

    class _ServerReceiverProtocol(_UDPProtocol):
        _queue: asyncio.Queue[Optional[Tuple[bytes, str]]]

        def __init__(self, log):
            super().__init__(log)
            self._queue = asyncio.Queue()

        async def recvfrom(self) -> Tuple[bytes, str]:
            rec = await self._queue.get()
            if rec is None:
                # TODO: figure out what this should be
                raise IOError("closed")

            return rec

        def datagram_received(self, data, addr):
            self._queue.put_nowait((data, str(addr)))

        def connection_lost(self, exc):
            self._queue.put_nowait(None)
            super().connection_lost(exc)

    def __init__(self, host, port, log):
        self.host = host
        self.port = port
        self.log = log

    @classmethod
    async def receive_from_send_clients(
        cls, host, port, log
    ) -> UDPServerReceiver:
        connection = UDPServerReceiver(host, port, log)
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls._ServerReceiverProtocol(log), local_addr=(host, port)
        )
        connection._transport = transport
        connection._protocol = protocol
        return connection

    async def receive_async(self) -> Tuple[bytes, str]:
        return await self._protocol.recvfrom()


class AsyncNetworkReceiver(MessageUnpacker):
    def __init__(self, connection: AsyncReceiver, types: Sequence[Type]):
        self.connection = connection
        super().__init__(types, connection.log)

    async def receive_async(self) -> Optional[Values]:
        connection = self.connection
        buf, _ = await connection.receive_async()

        value = self.unpack_bytes(buf)
        if value is not None:
            self.connection.debug_receive_message(value)

        return value


class NetworkSender(MessagePacker):
    def __init__(self, connection: SyncSender, types: Sequence[Type]):
        self.connection = connection
        super().__init__(types, connection.log)

    def send(self, values_obj: Values) -> None:
        connection = self.connection

        message = self.pack_values(values_obj)

        self.connection.debug_send_message(values_obj)
        connection.send(message)


class AsyncNetworkSender(MessagePacker):
    def __init__(self, connection: AsyncSender, types: Sequence[Type]):
        self.connection = connection
        super().__init__(types, connection.log)

    async def send_async(self, values_obj: Values) -> None:
        connection = self.connection

        message = self.pack_values(values_obj)

        self.connection.debug_send_message(values_obj)
        await connection.send_async(message)
