from unittest import mock

import pytest
from sqlalchemy import create_engine

from .. import worker
from ..collector import CollectionTarget
from ..collector import EngineCollector
from ... import testing


# note this test suite switches to pure pytest testing so that we can
# use fixtures.
# a subsequent release of sqlalchemy-collectd will switch to pytest fully.


class CollectorTest(testing.TestBase):
    @pytest.fixture
    def collector_fixture(self):
        engine = create_engine("sqlite://")
        collection_target = CollectionTarget("some_target")
        engine_collector = EngineCollector(collection_target, engine)
        self.assertEqual(collection_target.connections, set())
        self.assertEqual(collection_target.checkedin, set())
        self.assertEqual(collection_target.total_connects, 0)

        with mock.patch.object(worker, "_check_threads_started"):
            yield collection_target, engine_collector, engine

        engine.dispose()

    def test_connect_event(self, collector_fixture):
        collection_target, engine_collector, engine = collector_fixture

        with engine.connect() as conn:
            ident = id(conn.connection.connection)

            self.assertEqual(collection_target.connections, {ident})
            self.assertEqual(collection_target.checkedin, set())
            self.assertEqual(collection_target.total_connects, 1)

        self.assertEqual(collection_target.checkedin, {ident})

    @pytest.mark.parametrize("soft", [(True,), (False,)])
    def test_invalidate_event(self, collector_fixture, soft):
        """test #11"""
        collection_target, engine_collector, engine = collector_fixture

        with engine.connect() as conn:
            ident = id(conn.connection.connection)

            self.assertEqual(collection_target.connections, {ident})
            self.assertEqual(collection_target.checkedin, set())
            self.assertEqual(collection_target.total_connects, 1)
            self.assertEqual(collection_target.total_invalidated, 0)
            self.assertEqual(collection_target.invalidated, set())

            conn.connection.invalidate(soft=soft)
            self.assertEqual(collection_target.total_invalidated, 1)

            if soft:
                self.assertEqual(collection_target.invalidated, {ident})
                self.assertEqual(collection_target.total_disconnects, 0)
            else:
                self.assertEqual(collection_target.invalidated, {})
                self.assertEqual(collection_target.total_disconnects, 1)

        if soft:
            self.assertEqual(collection_target.invalidated, {ident})
        else:
            self.assertEqual(collection_target.invalidated, set())
