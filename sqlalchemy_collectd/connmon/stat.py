from __future__ import division

import threading
import time


class HostProg(object):
    def __init__(self, hostname, progname):
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

    def last_metric(self, now):
        return now - self.last_time

    def kill_processes(self):
        self.process_count = self.connection_count = self.checkout_count = 0
        self.checkouts_per_second = 0.0


_hostproc_updaters = {}


def updates(name):
    def decorate(fn):
        _hostproc_updaters[name] = fn
        return fn

    return decorate


@updates("numprocs")
def update_process_count(values_obj, value, hostprog):
    hostprog.process_count = value
    hostprog.max_process_count = max(
        hostprog.process_count, hostprog.max_process_count
    )


@updates("checkedout")
def update_checkedout(values_obj, value, hostprog):
    hostprog.checkout_count = value
    hostprog.max_checkedout = max(
        hostprog.max_checkedout, hostprog.checkout_count
    )


@updates("connections")
def update_connection_count(values_obj, value, hostprog):

    hostprog.connection_count = value
    hostprog.max_connections = max(
        hostprog.max_connections, hostprog.connection_count
    )


@updates("connects")
def update_total_connects(values_obj, value, hostprog):
    if hostprog.total_connects is not None:
        hostprog.interval_connects = value - hostprog.total_connects
    hostprog.total_connects = value


@updates("checkouts")
def update_total_checkouts(values_obj, value, hostprog):
    total_checkouts = value

    if hostprog.last_total_checkout_time:

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


class Stat(object):
    def __init__(self, receiver, log):
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

    def start(self):
        self.worker = threading.Thread(target=self._wrap_update)
        self.worker.daemon = True

        self.process = threading.Thread(target=self._process_hostprogs)
        self.process.daemon = True
        self.worker.start()
        self.process.start()

    def _get_hostprog(self, hostname, progname):
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

    def _process_hostprogs(self):
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

    def _wrap_update(self):
        while True:
            try:
                self._update()
            except Exception:
                self.log.error(
                    "message receiver caught an exception", exc_info=True
                )
            except BaseException as be:
                self.log.info(
                    "message receiver thread caught %s exception, exiting"
                    % type(be).__name__
                )
                break

    def _update(self):
        values_obj = self.receiver.receive()

        hostname = values_obj.host
        progname = values_obj.plugin_instance

        hostprog = self._get_hostprog(hostname, progname)

        # print("got stat %sfor %s" % (values_obj, progname))

        updater = _hostproc_updaters.get(values_obj.type_instance)
        if updater:
            updater(values_obj, values_obj.values[0], hostprog)
            hostprog.interval = values_obj.interval
            hostprog.last_time = values_obj.time

    def update_host_stats(self):
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
