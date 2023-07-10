from __future__ import annotations

import logging
import threading
from typing import Dict
import weakref

from sqlalchemy import event

from . import worker


class CollectionTarget:
    targets: Dict[str, CollectionTarget] = {}
    create_mutex = threading.Lock()

    def __init__(self, name):
        self.name = name

        self.collectors = weakref.WeakSet()

        # all identifiers for known DBAPI connections
        self.connections = set()

        # identifers for connections that have not been checked out
        # or were checked in
        self.checkedin = set()

        # not clear if this is useful yet.  only "soft" invalidated
        # will actually be present.  still counting them so that
        # we can return an accurate checkout count.
        self.invalidated = set()

        # detached connections.
        self.detached = set()

        # identifiers for connections where we've seen begin().
        # doesn't include DBAPI implicit transactions
        self.transactions = set()

        self.total_checkouts = 0
        self.total_invalidated = 0
        self.total_connects = 0
        self.total_disconnects = 0

    @classmethod
    def collection_for_name(cls, name):
        cls.create_mutex.acquire()
        try:
            if name not in cls.targets:
                cls.targets[name] = collection = CollectionTarget(name)
                return collection
            else:
                return cls.targets[name]
        finally:
            cls.create_mutex.release()

    @property
    def num_pools(self):
        return len(self.collectors)

    @property
    def num_checkedout(self):
        checkedout = (
            self.connections.difference(self.detached)
            .difference(self.invalidated)
            .difference(self.checkedin)
        )
        return len(checkedout)

    @property
    def num_checkedin(self):
        return len(self.checkedin)

    @property
    def num_detached(self):
        return len(self.detached)

    @property
    def num_invalidated(self):
        return len(self.invalidated)

    @property
    def num_connections(self):
        return len(self.connections)

    @property
    def num_transactions(self):
        return len(self.transactions)


class EngineCollector:
    def __init__(self, collection_target, engine):
        self.collection_target = collection_target
        self.engine = engine
        collection_target.collectors.add(self)

        eng = engine
        event.listen(eng, "connect", self._connect_evt)
        event.listen(eng, "checkout", self._checkout_evt)
        event.listen(eng, "checkin", self._checkin_evt)
        event.listen(eng, "invalidate", self._invalidate_evt)
        event.listen(eng, "soft_invalidate", self._invalidate_evt)
        event.listen(eng, "reset", self._reset_evt)
        event.listen(eng, "close", self._close_evt)
        event.listen(eng, "detach", self._detach_evt)
        event.listen(eng, "close_detached", self._close_detached_evt)

        self.connections = collection_target.connections
        self.checkedin = collection_target.checkedin
        self.transactions = collection_target.transactions
        self.invalidated = collection_target.invalidated
        self.detached = collection_target.detached
        self.logger = logging.getLogger("%s.%s" % (__name__, eng.logging_name))

    def conn_ident(self, dbapi_connection):
        return id(dbapi_connection)

    def _connect_evt(self, dbapi_conn, connection_rec):
        worker._check_threads_started()
        id_ = self.conn_ident(dbapi_conn)
        self.collection_target.total_connects += 1
        self.connections.add(id_)
        self.checkedin.add(id_)

    def _checkout_evt(self, dbapi_conn, connection_rec, connection_proxy):
        id_ = self.conn_ident(dbapi_conn)
        self.collection_target.total_checkouts += 1
        self.checkedin.remove(id_)

    def _checkin_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.checkedin.add(id_)

    def _invalidate_evt(self, dbapi_conn, connection_rec, exc):
        id_ = self.conn_ident(dbapi_conn)
        self.collection_target.total_invalidated += 1
        self.invalidated.add(id_)

    def _reset_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        # may or may not have been part of "transactions"
        self.transactions.discard(id_)

    def _close_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.transactions.discard(id_)
        self.invalidated.discard(id_)
        self.checkedin.discard(id_)

        try:
            self.connections.remove(id_)
            self.collection_target.total_disconnects += 1
        except KeyError:
            self._warn_missing_connection(dbapi_conn)

        # this shouldn't be there
        if id_ in self.detached:
            self._warn("shouldn't have detached")
        self.detached.discard(id_)

    def _warn_missing_connection(self, dbapi_conn):
        self._warn(
            "connection %s was closed but not part of "
            "total connections" % dbapi_conn
        )

    def _warn(self, msg):
        self.logger.warn(msg)

    def _detach_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.detached.add(id_)

    def _close_detached_evt(self, dbapi_conn):
        id_ = self.conn_ident(dbapi_conn)

        self.transactions.discard(id_)
        self.invalidated.discard(id_)
        self.checkedin.discard(id_)
        self.detached.discard(id_)

        try:
            self.connections.remove(id_)
            self.collection_target.total_disconnects += 1
        except KeyError:
            self._warn_missing_connection(dbapi_conn)
