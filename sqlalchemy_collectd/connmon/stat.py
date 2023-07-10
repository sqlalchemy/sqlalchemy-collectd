from __future__ import annotations

import threading
import time
from typing import Callable
from typing import Protocol
from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from logging import Logger

    from ..protocol import NetworkReceiver
    from ..protocol import Values


class HostProg:
    last_time: int
    hostname: str
    progname: str | None
    checkout_count: int | None
    max_checkedout: int
    process_count: int | None
    max_process_count: int
    connection_count: int | None
    max_connections: int
    total_connects: int | None
    interval_connects: int | None
    total_checkouts: int | None
    last_checkouts: int | None
    interval_checkouts: int | None
    last_total_checkout_time: int | None
    checkouts_per_second: float | None
    interval: int

    def __init__(self, hostname: str, progname: str | None):
        self.last_time = 0

        # hostname where stats came from
        self.hostname = hostname

        # progname marked on the stat
        self.progname = progname

        # pool_internal.checkedout
        self.checkout_count = None

        # max of pool_internal.checkedout
        self.max_checkedout = 0

        # process_internal.numprocs
        self.process_count = None

        # max of pool_internal.numprocs
        self.max_process_count = 0

        # pool_internal.connections
        self.connection_count = None

        # max of pool_internal.connections
        self.max_connections = 0

        # totals_internal.connects
        self.total_connects = None

        # totals_internal.connects growth over last interval
        self.interval_connects = None

        # totals_internal.checkouts
        self.total_checkouts = None

        # previous value of totals_internal.checkouts
        self.last_checkouts = None

        # totals_internal.checkouts growth over last interval
        self.interval_checkouts = None

        # timestamp where we last got totals_internal.checkouts
        self.last_total_checkout_time = None

        # calculated checkouts per second
        self.checkouts_per_second = None

        # last interval received
        self.interval = 0

    def last_metric(self, now: float) -> float:
        return now - self.last_time

    def kill_processes(self) -> None:
        self.process_count = self.connection_count = self.checkout_count = 0
        self.checkouts_per_second = 0.0


class _UpdaterProto(Protocol):
    def __call__(
        self, values_obj: Values, value: float | int, hostprog: HostProg
    ) -> None:
        ...


_UP = TypeVar("_UP", bound=_UpdaterProto)

_hostproc_updaters: dict[str, _UpdaterProto] = {}


def updates(name: str) -> Callable[[_UP], _UP]:
    def decorate(fn):
        _hostproc_updaters[name] = fn
        return fn

    return decorate


@updates("numprocs")
def update_process_count(
    values_obj: Values, value: float | int, hostprog: HostProg
):
    if TYPE_CHECKING:
        assert isinstance(value, int)

    hostprog.process_count = value
    hostprog.max_process_count = max(
        hostprog.process_count, hostprog.max_process_count
    )


@updates("checkedout")
def update_checkedout(
    values_obj: Values, value: float | int, hostprog: HostProg
):
    if TYPE_CHECKING:
        assert isinstance(value, int)

    hostprog.checkout_count = value
    hostprog.max_checkedout = max(
        hostprog.max_checkedout, hostprog.checkout_count
    )


@updates("connections")
def update_connection_count(
    values_obj: Values, value: float | int, hostprog: HostProg
):
    if TYPE_CHECKING:
        assert isinstance(value, int)

    hostprog.connection_count = value
    hostprog.max_connections = max(
        hostprog.max_connections, hostprog.connection_count
    )


@updates("connects")
def update_total_connects(
    values_obj: Values, value: float | int, hostprog: HostProg
):
    if TYPE_CHECKING:
        assert isinstance(value, int)

    if hostprog.total_connects is not None:
        hostprog.interval_connects = value - hostprog.total_connects

    hostprog.total_connects = value


@updates("checkouts")
def update_total_checkouts(
    values_obj: Values, value: float | int, hostprog: HostProg
):
    if TYPE_CHECKING:
        assert isinstance(value, int)

    total_checkouts = value

    if hostprog.last_total_checkout_time:
        assert hostprog.total_checkouts is not None
        hostprog.interval_checkouts = (
            total_checkouts - hostprog.total_checkouts
        )
        time_delta = values_obj.time - hostprog.last_total_checkout_time

        if time_delta >= values_obj.interval and hostprog.total_checkouts > 0:
            hostprog.checkouts_per_second = (
                hostprog.interval_checkouts
            ) / time_delta
    hostprog.total_checkouts = total_checkouts
    hostprog.last_total_checkout_time = values_obj.time


class Stat:
    worker: threading.Thread
    process: threading.Thread
    host_count: int
    max_host_count: int
    process_count: int
    max_process_count: int
    connection_count: int
    max_connections: int
    max_checkedout: int
    checkouts_per_second: float | None
    hostprogs: dict[tuple[str, str | None], HostProg]
    hosts: dict[str, HostProg]

    def __init__(self, receiver: NetworkReceiver, log: Logger):
        self.receiver = receiver
        self.log = log
        self.host_count = 0
        self.max_host_count = 0
        self.process_count = 0
        self.max_process_count = 0
        self.connection_count = 0
        self.max_connections = 0
        self.checkout_count = 0
        self.max_checkedout = 0
        self.checkouts_per_second = None
        self.hostprogs = {}
        self.hosts = {}

    def start(self) -> None:
        self.worker = threading.Thread(target=self._wrap_update)
        self.worker.daemon = True

        self.process = threading.Thread(target=self._process_hostprogs)
        self.process.daemon = True
        self.worker.start()
        self.process.start()

    def _get_hostprog(self, hostname: str, progname: str | None) -> HostProg:
        if progname is None or progname == "host":
            if hostname not in self.hosts:
                self.hosts[hostname] = hostprog = HostProg(hostname, None)
            else:
                hostprog = self.hosts[hostname]
        else:
            if (hostname, progname) not in self.hostprogs:
                self.hostprogs[(hostname, progname)] = hostprog = HostProg(
                    hostname, progname
                )
            else:
                hostprog = self.hostprogs[(hostname, progname)]
        return hostprog

    def _process_hostprogs(self) -> None:
        while True:
            time.sleep(0.5)

            self.update_host_stats()

            now = time.time()

            for hostprog in list(self.hostprogs.values()):
                if hostprog.interval is None:
                    continue

                age = now - hostprog.last_time

                if age > hostprog.interval * 5:
                    del self.hostprogs[(hostprog.hostname, hostprog.progname)]
                elif age > hostprog.interval * 2:
                    hostprog.kill_processes()

    def _wrap_update(self) -> None:
        while True:
            try:
                self._update()
            except Exception:
                self.log.error(
                    "message receiver caught an exception", exc_info=True
                )
            except BaseException as be:
                self.log.info(
                    "message receiver thread caught %s exception, exiting",
                    type(be).__name__,
                )
                break

    def _update(self) -> None:
        values_obj = self.receiver.receive()
        if values_obj is None:
            return

        hostname = values_obj.host
        progname = values_obj.plugin_instance

        hostprog = self._get_hostprog(hostname, progname)

        # print(f"got stat {values_obj}for {progname}")

        updater = _hostproc_updaters.get(values_obj.type_instance)
        if updater:
            updater(values_obj, values_obj.values[0], hostprog)
            hostprog.interval = values_obj.interval
            hostprog.last_time = values_obj.time

    def update_host_stats(self) -> None:
        self.host_count = len(set(host for (host, prog) in self.hostprogs))
        self.process_count = sum(
            hostprog.process_count
            for hostprog in self.hostprogs.values()
            if hostprog.process_count is not None
        )
        self.connection_count = sum(
            hostprog.connection_count
            for hostprog in self.hostprogs.values()
            if hostprog.connection_count is not None
        )
        self.checkout_count = sum(
            hostprog.checkout_count
            for hostprog in self.hostprogs.values()
            if hostprog.checkout_count is not None
        )
        self.checkouts_per_second = sum(
            hostprog.checkouts_per_second
            for hostprog in self.hostprogs.values()
            if hostprog.checkouts_per_second is not None
        )

        self.max_host_count = max(self.max_host_count, self.host_count)
        self.max_process_count = max(
            self.max_process_count, self.process_count
        )
        self.max_checkedout = max(self.max_checkedout, self.checkout_count)
        self.max_connections = max(self.max_connections, self.connection_count)
