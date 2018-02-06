import struct
import socket
import logging
import threading
import os

log = logging.getLogger(__name__)

DEFAULT_INTERVAL = 10
MAX_PACKET_SIZE = 1024

VALUE_COUNTER = 0
VALUE_GAUGE = 1
VALUE_DERIVE = 2
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

header = struct.Struct("!2H")
number = struct.Struct("!Q")
short = struct.Struct("!H")
double = struct.Struct("<d")
char = struct.Struct("B")
long_ = struct.Struct("!q")

_value_formats = {
    VALUE_COUNTER: number,
    VALUE_GAUGE: double,
    VALUE_DERIVE: long_,
    VALUE_ABSOLUTE: number
}


class Type(object):
    """Represents a collectd type and its data template.

    Here, we are encoding what we need to know about a collectd type that we'd
    be targeting to send to a collectd server.A type  includes a name and a set
    of values and types that go along with it. These names and value
    definitions are a fixed thing on the collectd server  side, which are
    listed in a file called types.db.   Additional custom types can be  added
    by specifying additional type files in the collectd configuration.

    .. seealso::

        collectd's default types.db:
        https://github.com/collectd/collectd/blob/master/src/types.db

    """

    __slots__ = 'name', '_value_types', '_value_formats', '_message_template'

    def __init__(self, name, *db_template):
        """Contruct a new Type.

        E.g. to represent the "load" type in collectd's types.db::

            load = Type(
                "load",
                ("shortterm", VALUE_GAUGE),
                ("midterm", VALUE_GAUGE),
                ("longterm", VALUE_GAUGE)
            )

        note: for all the great effort here in working up types,
        collectd aggregation plugin doesn't support more than one dsvalue
        at a time in a record so all this flexibility is all a waste of
        time :(

        """
        self.name = name
        self._value_types = [value_type for dsname, value_type in db_template]
        self._value_formats = [
            _value_formats[value_type] for value_type in self._value_types]

        self._message_template = header.pack(
            TYPE_VALUES, 6 + (9 * len(db_template))
        ) + short.pack(len(db_template))
        for value_type in self._value_types:
            self._message_template += char.pack(value_type)

    def encode_values(self, *values):
        """Encode a series of values according to the type template."""

        msg = self._message_template
        for format_, dsvalue in zip(self._value_formats, values):
            msg += format_.pack(dsvalue)

        return msg


class MessageSender(object):
    """Represents all the fields necessary to send a message."""

    __slots__ = (
        'type', 'host', 'plugin', 'plugin_instance', 'type_instance',
        'interval', '_host_message_part', '_remainder_message_parts'
    )

    def __init__(
        self, type, host, plugin, plugin_instance=None,
            type_instance=None, interval=DEFAULT_INTERVAL):

        self.type = type
        self.host = host
        self.plugin = plugin
        self.plugin_instance = plugin_instance
        self.type_instance = type_instance
        self.interval = interval

        self._host_message_part = self._pack_string(TYPE_HOST, self.host)
        self._remainder_message_parts = (
            self._pack_string(TYPE_PLUGIN, self.plugin) +
            self._pack_string(TYPE_PLUGIN_INSTANCE, self.plugin_instance) +
            self._pack_string(TYPE_TYPE, self.type.name) +
            struct.pack("!HHq", TYPE_INTERVAL, 12, self.interval) +
            self._pack_string(TYPE_TYPE_INSTANCE, self.type_instance)
        )

    def _pack_string(self, typecode, value):
        return header.pack(
            typecode, 5 + len(value)) + value.encode('ascii') + b"\0"

    def send(self, connection, timestamp, *values):
        """Send a message on a connection."""

        header_ = self._host_message_part + \
            header.pack(TYPE_TIME, 12) + \
            long_.pack(int(timestamp)) + \
            self._remainder_message_parts

        payload = self.type.encode_values(*values)

        connection.send(header_ + payload)


class ClientConnection(object):
    connections = {}
    create_mutex = threading.Lock()

    def __init__(self, host="localhost", port=25826):
        self.host = host
        self.port = port
        self._mutex = threading.Lock()
        self.socket = None
        self.pid = None

    def _check_connect(self):
        if self.socket is None or self.pid != os.getpid():
            self.pid = os.getpid()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @classmethod
    def for_host_port(cls, host, port):
        cls.create_mutex.acquire()
        try:
            key = (host, port)
            if key not in cls.connections:
                cls.connections[key] = connection = \
                    ClientConnection(host, port)
                return connection
            else:
                return cls.connections[key]

        finally:
            cls.create_mutex.release()

    def send(self, message):
        self._mutex.acquire()
        try:
            self._check_connect()
            log.debug("sending: %r", message)
            self.socket.sendto(message, (self.host, self.port))
        except IOError:
            log.error("Error in socket.sendto", exc_info=True)
        finally:
            self._mutex.release()
