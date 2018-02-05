from . import collectd


senders = []


def sends(name, type_):
    collectd_type = collectd.Type(
        name, ("value", type_)
    )

    def decorate(fn):
        senders.append((collectd_type, fn))
        return fn

    return decorate


class Sender(object):
    def __init__(self, hostname, stats_name):
        self.hostname = hostname
        self.stats_name = stats_name

    def send(self, connection, collection_target, timestamp, interval, pid):
        for collectd_type, sender in senders:
            message_sender = collectd.MessageSender(
                collectd_type, self.hostname, "sqlalchemy",
                plugin_instance=str(pid), type_instance=self.stats_name,
                interval=interval
            )
            value = sender(collection_target)
            message_sender.send(connection, timestamp, value)


@sends("sqlalchemy_numpools", collectd.VALUE_GAUGE)
def _numpools(collection_target):
    return collection_target.num_pools


@sends("sqlalchemy_checkedout", collectd.VALUE_GAUGE)
def _checkedout(collection_target):
    return collection_target.num_checkedout


@sends("sqlalchemy_checkedin", collectd.VALUE_GAUGE)
def _checkedin(collection_target):
    return collection_target.num_checkedin


@sends("sqlalchemy_detached", collectd.VALUE_GAUGE)
def _detached(collection_target):
    return collection_target.num_detached


@sends("sqlalchemy_invalidated", collectd.VALUE_GAUGE)
def _invalidated(collection_target):
    return collection_target.num_invalidated


@sends("sqlalchemy_connections", collectd.VALUE_GAUGE)
def _connections(collection_target):
    return collection_target.num_connections

