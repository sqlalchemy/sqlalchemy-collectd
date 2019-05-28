"""Using the collectd protocol because we originally were going to
connect straight to the network plugin.

"""
import collections
import logging
import os
import socket
import struct
import threading

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

header = struct.Struct("!HH")
short = struct.Struct("!H")
char = struct.Struct("B")
long_ = struct.Struct("!q")

_value_formats = {
    VALUE_COUNTER: struct.Struct("!Q"),
    VALUE_GAUGE: struct.Struct("<d"),
    VALUE_DERIVE: long_,
    VALUE_ABSOLUTE: struct.Struct("!Q"),
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

    __slots__ = (
        "name",
        "_value_types",
        "_value_formats",
        "_message_template",
        "_field_names",
    )

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
        self._field_names = [dsname for dsname, value_type in db_template]
        self._value_types = [value_type for dsname, value_type in db_template]
        self._value_formats = [
            _value_formats[value_type] for value_type in self._value_types
        ]

        self._message_template = header.pack(
            TYPE_VALUES, 6 + (9 * len(db_template))
        ) + short.pack(len(db_template))
        for value_type in self._value_types:
            self._message_template += char.pack(value_type)

    def get_stat_index(self, name):
        return self._field_names.index(name)

    @property
    def names(self):
        return self._field_names

    @property
    def types(self):
        return self._value_types

    def _encode_values(self, *values):
        """Encode a series of values according to the type template."""

        msg = self._message_template
        for format_, dsvalue in zip(self._value_formats, values):
            msg += format_.pack(dsvalue)

        return msg


class MessageSender(object):
    """Represents all the fields necessary to send a message."""

    __slots__ = (
        "type",
        "host",
        "plugin",
        "plugin_instance",
        "type_instance",
        "interval",
        "_host_message_part",
        "_remainder_message_parts",
    )

    def __init__(
        self,
        type_,
        host,
        plugin,
        plugin_instance=None,
        type_instance=None,
        interval=DEFAULT_INTERVAL,
    ):

        self.type = type_
        self.host = host
        self.plugin = plugin
        self.plugin_instance = plugin_instance
        self.type_instance = type_instance
        self.interval = interval

        self._host_message_part = self._pack_string(TYPE_HOST, self.host)
        self._remainder_message_parts = (
            self._pack_string(TYPE_PLUGIN, self.plugin)
            + self._pack_string(TYPE_PLUGIN_INSTANCE, self.plugin_instance)
            + self._pack_string(TYPE_TYPE, self.type.name)
            + struct.pack("!HHq", TYPE_INTERVAL, 12, self.interval)
            + self._pack_string(TYPE_TYPE_INSTANCE, self.type_instance)
        )

    def _pack_string(self, typecode, value):
        return (
            header.pack(typecode, 5 + len(value))
            + value.encode("ascii")
            + b"\0"
        )

    def send(self, connection, timestamp, *values):
        """Send a message on a connection."""

        header_ = (
            self._host_message_part
            + header.pack(TYPE_TIME, 12)
            + long_.pack(int(timestamp))
            + self._remainder_message_parts
        )

        payload = self.type._encode_values(*values)

        log.debug("send: %s", _SendMsg(self, values))
        connection.send(header_ + payload)

    def __str__(self):
        return (
            "(host=%r, plugin=%r, plugin_instance=%r, "
            "type=%r, type_instance=%r, interval=%r)"
            % (
                self.host,
                self.plugin,
                self.plugin_instance,
                self.type.name,
                self.type_instance,
                self.interval,
            )
        )


class _SendMsg(collections.namedtuple("sendmsg", ["sender", "values"])):
    def __str__(self):
        sender = self.sender
        type_ = sender.type
        return (
            "(host=%r, plugin=%r, plugin_instance=%r, "
            "type=%r, type_instance=%r, interval=%r, values=%s)"
            % (
                sender.host,
                sender.plugin,
                sender.plugin_instance,
                type_.name,
                sender.type_instance,
                sender.interval,
                ", ".join(
                    "%s=%s" % (field_name, value)
                    for field_name, value in zip(type_.names, self.values)
                ),
            )
        )


class _RecvMsg(collections.namedtuple("receivemsg", ["result", "type"])):
    def __str__(self):
        if self.type:
            type_names = self.type.names
        else:
            type_names = ["(unknown)" for value in self.result[TYPE_VALUES]]

        return (
            "(host=%r, plugin=%r, plugin_instance=%r, "
            "type=%r, type_instance=%r, interval=%r, values=%s)"
            % (
                self.result[TYPE_HOST],
                self.result[TYPE_PLUGIN],
                self.result[TYPE_PLUGIN_INSTANCE],
                self.result[TYPE_TYPE],
                self.result[TYPE_TYPE_INSTANCE],
                self.result[TYPE_INTERVAL],
                ", ".join(
                    "%s=%s" % (field_name, value)
                    for field_name, value in zip(
                        type_names, self.result[TYPE_VALUES]
                    )
                ),
            )
        )


class MessageReceiver(object):
    def __init__(self, *types):
        self._receivers = {
            TYPE_HOST: self._unpack_string,
            TYPE_TIME: self._unpack_long,
            TYPE_PLUGIN: self._unpack_string,
            TYPE_PLUGIN_INSTANCE: self._unpack_string,
            TYPE_TYPE: self._unpack_string,
            TYPE_TYPE_INSTANCE: self._unpack_string,
            TYPE_VALUES: self._unpack_values,
            TYPE_INTERVAL: self._unpack_long,
        }
        self._types = {type_.name: type_ for type_ in types}

    def receive(self, buf):
        result = self._unpack_packet(buf)
        type_name = result[TYPE_TYPE]
        type_ = None
        try:
            type_ = self._types[type_name]
        except KeyError:
            log.warn("Type %s not known, skipping", type_name)
            return None
        else:
            result["type"] = type_
            result["values"] = {
                name: value
                for name, value in zip(type_._field_names, result[TYPE_VALUES])
            }
            return result
        finally:
            log.debug("receive: %s", _RecvMsg(result, type_))

    def _unpack_packet(self, buf):
        pos = 0
        length = len(buf)
        result = {}
        while pos < length:
            type_, len_ = header.unpack_from(buf, pos)

            try:
                fn = self._receivers[type_]
            except KeyError:
                log.warn("Message %s not known, skipping", type_)
            else:
                value = fn(type_, len_, buf[pos:])

                result[type_] = value

            pos += len_
        return result

    def _unpack_long(self, type_, length, buf):
        return long_.unpack_from(buf, header.size)[0]

    def _unpack_string(self, type_, length, buf):
        return buf[header.size : length - 1].decode("ascii")

    def _unpack_values(self, type_, length, buf):
        num = short.unpack_from(buf, header.size)[0]
        types_start = header.size + short.size
        values_pos = types_start + num * char.size
        result = []
        for pos in range(0, num * char.size, char.size):
            value_type = char.unpack_from(buf, types_start + pos)[0]
            struct_ = _value_formats[value_type]
            result.append(struct_.unpack_from(buf, values_pos)[0])
            values_pos += struct_.size
        return result


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
                cls.connections[key] = connection = ClientConnection(
                    host, port
                )
                return connection
            else:
                return cls.connections[key]

        finally:
            cls.create_mutex.release()

    def send(self, message):
        self._mutex.acquire()
        try:
            self._check_connect()
            self.socket.sendto(message, (self.host, self.port))
        except IOError:
            log.error("Error in socket.sendto", exc_info=True)
        finally:
            self._mutex.release()


class ServerConnection(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))

    def receive(self):
        data, addr = self.sock.recvfrom(1024)
        return data, addr
