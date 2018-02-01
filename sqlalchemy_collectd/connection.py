import collections
import struct
import socket
import logging
import threading
import time

log = logging.getLogger(__name__)

DEFAULT_INTERVAL = 10
MAX_PACKET_SIZE = 1024

VALUE_COUNTER  = 0
VALUE_GAUGE    = 1
VALUE_DERIVE   = 2
VALUE_ABSOLUTE = 3

# https://git.octo.it/?p=collectd.git;a=blob;hb=master;f=src/network.h
TYPE_HOST = 0x0000
TYPE_TIME = 0x0001
TYPE_PLUGIN = 0x0002
TYPE_PLUGIN_INSTANCE = 0x0003
TYPE_TYPE = 0x0004
TYPE_TYPE_INSTANCE = 0x0005
TYPE_VALUES = 0x0006
TYPE_INTERVAL = 0x0007


class MessageSender(object):
    def __init__(
        self, type, host, plugin="sqlalchemy", plugin_instance=None,
            type_instance=None, interval=DEFAULT_INTERVAL):

    # TODO: send template just like in types.db and fix to that

        self.type = type
        self.host = host
        self.plugin = plugin
        self.plugin_instance = plugin_instance
        self.type_instance = type_instance
        self.interval = interval
        self._queue = collections.deque()

    def _header(self, timestamp):
        buf = b''
        buf += struct.pack("!HH", TYPE_HOST, 5 + len(self.host)) + self.host + b"\0"
        buf += struct.pack("!HHq", TYPE_TIME, 12, timestamp)
        buf += struct.pack("!HH", TYPE_PLUGIN, 5 + len(self.plugin)) + self.plugin + b"\0"
        buf += struct.pack("!HH", TYPE_PLUGIN_INSTANCE, 5 + len(self.plugin_instance)) + self.plugin_instance + b"\0"
        buf += struct.pack("!HH", TYPE_TYPE, 5 + len(self.type)) + self.type + b"\0"
        buf += struct.pack("!HHq", TYPE_INTERVAL, 12, self.interval)
        buf += struct.pack("!HH", TYPE_TYPE_INSTANCE, 5 + len(self.type_instance)) + self.type_instance + b'\0'

        return buf

    def _gauge(self, dsname, dsvalue):
        buf = b''
        buf += struct.pack("!HHH", TYPE_VALUES, 15, 1)
        buf += struct.pack("<Bd", VALUE_GAUGE, dsvalue)

        return buf

    def _derive(self, dsname, dsvalue):
        buf = b''
        buf += struct.pack("!HHH", TYPE_VALUES, 15, 1)
        buf += struct.pack("!Bq", VALUE_DERIVE, dsvalue)

        return buf

    def queue_stat(self, *values):
        # TODO TODO
        pass

    def queue_gauge(self, name, value):
        self._queue.append((VALUE_GAUGE, time.time(), name, value))

    def queue_derive(self, name, value):
        self._queue.append((VALUE_DERIVE, time.time(), name, value))

    def flush(self, connection):
        now = time.time()
        too_old = now - self.interval
        header = self._header(now)

        while self._queue:
            type_, timestamp, name, value = self._queue.popleft()
            if timestamp < too_old:
                continue

            if type_ == VALUE_GAUGE:
                element = self._gauge(name, value)
            else:
                element = self._derive(name, value)

            connection.send(header + element)


class Connection(object):
    def __init__(self, host="localhost", port=25826):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._mutex = threading.Lock()

    def send(self, message):
        self._mutex.acquire()
        try:
            log.debug("sending: %s", message)
            self.socket.sendto(message, (self.host, self.port))
        except IOError:
            log.error("Error in socket.sendto", exc_info=True)
        finally:
            self._mutex.release()
