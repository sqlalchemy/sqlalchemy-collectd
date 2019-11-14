"""Using the collectd protocol because we originally were going to
connect straight to the network plugin.

"""
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


class Values(object):
    """A mirror object of collectd.Values"""

    __slots__ = (
        "type",
        "type_instance",
        "plugin",
        "plugin_instance",
        "host",
        "time",
        "interval",
        "values",
    )

    def __init__(self, **kw):
        # TODO: see what new python 3 values objects or what can help
        # with this
        for k in self.__slots__:
            setattr(self, k, kw[k] if k in kw else None)
        if self.interval is None:
            self.interval = DEFAULT_INTERVAL

    def _asdict(self):
        return {k: getattr(self, k) for k in self.__slots__}

    def build(self, **kw):
        d = self._asdict()
        d.update(kw)
        return Values(**d)

    def __eq__(self, other):
        if not isinstance(other, Values):
            return False

        return [getattr(self, k) for k in self.__slots__] == [
            getattr(other, k) for k in self.__slots__
        ]

    def __repr__(self):
        return "sqlalchemy_collectd.Values(%s)" % (
            ", ".join("%s=%r" % (k, getattr(self, k)) for k in self.__slots__),
        )

    # TODO: conversion to and from collectd.values
    # dispatch method
    # etc


class MessageSender(object):
    def __init__(self, *types):
        self._types = {type_.name: type_ for type_ in types}
        self._senders = {}

    def send(self, connection, values_obj):
        timestamp = values_obj.time
        type_name = values_obj.type

        try:
            type_obj = self._types[type_name]
        except KeyError:
            raise TypeError("don't know type: %s" % type_name)

        _pack_string = self._pack_string
        _host_message_part = _pack_string(TYPE_HOST, values_obj.host)
        _remainder_message_parts = (
            _pack_string(TYPE_PLUGIN, values_obj.plugin)
            + _pack_string(TYPE_PLUGIN_INSTANCE, values_obj.plugin_instance)
            + _pack_string(TYPE_TYPE, type_obj.name)
            + struct.pack("!HHq", TYPE_INTERVAL, 12, values_obj.interval)
            + _pack_string(TYPE_TYPE_INSTANCE, values_obj.type_instance)
        )
        header_ = (
            _host_message_part
            + header.pack(TYPE_TIME, 12)
            + long_.pack(int(timestamp))
            + _remainder_message_parts
        )

        payload = type_obj._encode_values(*values_obj.values)

        log.debug("send: %s", values_obj)
        connection.send(header_ + payload)

    def _pack_string(self, typecode, value):
        return (
            header.pack(typecode, 5 + len(value))
            + value.encode("ascii")
            + b"\0"
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
        try:
            type_name = result[TYPE_TYPE]
        except KeyError:
            log.warn("Message did not have TYPE_TYPE block, skipping")
            return None

        try:
            self._types[type_name]
        except KeyError:
            log.warn("Type %s not known, skipping", type_name)
            return None
        else:
            value = self._to_value(result)
            return value
        finally:
            log.debug("receive: %s", value)

    def _to_value(self, result):
        return Values(
            host=result[TYPE_HOST],
            time=result[TYPE_TIME],
            plugin=result[TYPE_PLUGIN],
            plugin_instance=result[TYPE_PLUGIN_INSTANCE],
            type=result[TYPE_TYPE],
            type_instance=result[TYPE_TYPE_INSTANCE],
            values=result[TYPE_VALUES],
            interval=result[TYPE_INTERVAL],
        )

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
