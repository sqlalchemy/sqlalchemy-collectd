from sqlalchemy import event
import threading


class Collector(object):
    collectors = {}
    create_mutex = threading.Mutex()

    def __init__(self, name):
        self.name = name

        # all identifiers for known DBAPI connections
        self.connections = set()

        # identifers for connections that have not been checked out
        # or were checked in
        self.checkedin = set()

        # identifiers for connections where we've seen begin().
        # doesn't include DBAPI implicit transactions
        self.transactions = set()

        # note these are prior to being closed and/or discarded
        self.invalidated = set()

        # detached connections.
        self.detached = set()

    @classmethod
    def collector_for_name(cls, name):
        cls.create_mutex.acquire()
        try:
            if name not in cls.collectors:
                cls.collectors[name] = collector = Collector(name)
                return collector
            else:
                return cls.collectors[name]
        finally:
            cls.create_mutex.release()

    def conn_ident(self, dbapi_connection):
        return id(dbapi_connection)

    def _connect_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.connections.add(id_)
        self.checkedin.add(id_)

    def _checkout_evt(self, dbapi_conn, connection_rec, connection_proxy):
        id_ = self.conn_ident(dbapi_conn)
        self.checkedin.remove(id_)

    def _checkin_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.checkedin.add(id_)

    def _invalidate_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
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

        if not self.connections.discard(id_):
            self._warn_missing_connection(dbapi_conn)

        # this shouldn't be there
        if self.detached.discard(id_):
            self._warn("shouldn't have detached")

    def _detach_evt(self, dbapi_conn, connection_rec):
        id_ = self.conn_ident(dbapi_conn)
        self.detached.add(id_)

    def _close_detached_evt(self, dbapi_conn):
        id_ = self.conn_ident(dbapi_conn)

        if not self.connections.discard(id_):
            self._warn_missing_connection(dbapi_conn)

        self.transactions.discard(id_)
        self.invalidated.discard(id_)
        self.checkedin.discard(id_)
        self.detached.discard(id_)

    def add_engine(self, sqlalchemy_engine):
        eng = sqlalchemy_engine
        event.listen(eng, "connect", self._connect_evt)
        event.listen(eng, "checkout", self._checkout_evt)
        event.listen(eng, "checkin", self._checkin_evt)
        event.listen(eng, "invalidate", self._invalidate_evt)
        event.listen(eng, "soft_invalidate", self._invalidate_evt)
        event.listen(eng, "reset", self._reset_evt)
        event.listen(eng, "close", self._close_evt)
        event.listen(eng, "detach", self._detach_evt)
        event.listen(eng, "close_detached", self._close_detached_evt)

