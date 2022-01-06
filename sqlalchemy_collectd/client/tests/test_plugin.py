from unittest import mock

from sqlalchemy.engine import url as sqla_url

from .. import plugin
from ... import testing


class PluginTest(testing.TestBase):
    def test_start_no_args(self):
        with mock.patch.object(plugin, "start_plugin") as start_plugin:
            url = sqla_url.make_url("mysql+pymysql://scott:tiger@localhost/")
            p = plugin.Plugin(url, {})
            engine = mock.Mock()
            p.engine_created(engine)

        self.assertEqual([mock.call(engine)], start_plugin.mock_calls)

    def test_start_engine_args(self):
        with mock.patch.object(plugin, "start_plugin") as start_plugin:
            url = sqla_url.make_url("mysql+pymysql://scott:tiger@localhost/")
            p = plugin.Plugin(
                url, {"collectd_host": "127.0.0.1", "collectd_port": 5678}
            )
            engine = mock.Mock()
            p.engine_created(engine)

        self.assertEqual(
            [mock.call(engine, collectd_host="127.0.0.1", collectd_port=5678)],
            start_plugin.mock_calls,
        )

    def test_start_url_args(self):
        with mock.patch.object(plugin, "start_plugin") as start_plugin:
            url = sqla_url.make_url(
                "mysql+pymysql://scott:tiger@localhost/"
                "?collectd_host=127.0.0.1&somekey=somevalue&collectd_port=1234"
            )
            kwargs = {"unrelated": "bar"}
            p = plugin.Plugin(url, kwargs)
            if hasattr(url, "difference_update_query"):
                url = p.update_url(url)
            engine = mock.Mock()
            p.engine_created(engine)

        self.assertEqual(
            [mock.call(engine, collectd_host="127.0.0.1", collectd_port=1234)],
            start_plugin.mock_calls,
        )
        self.assertEqual({"somekey": "somevalue"}, url.query)
        self.assertEqual({"unrelated": "bar"}, kwargs)

    def test_start_url_args_no_port(self):
        with mock.patch.object(plugin, "start_plugin") as start_plugin:
            url = sqla_url.make_url(
                "mysql+pymysql://scott:tiger@localhost/"
                "?collectd_host=127.0.0.1&somekey=somevalue"
            )
            kwargs = {"unrelated": "bar"}
            p = plugin.Plugin(url, kwargs)
            if hasattr(url, "difference_update_query"):
                url = p.update_url(url)
            engine = mock.Mock()
            p.engine_created(engine)

        self.assertEqual(
            [mock.call(engine, collectd_host="127.0.0.1")],
            start_plugin.mock_calls,
        )
        self.assertEqual({"somekey": "somevalue"}, url.query)
        self.assertEqual({"unrelated": "bar"}, kwargs)

    def test_start_both_args(self):
        with mock.patch.object(plugin, "start_plugin") as start_plugin:
            url = sqla_url.make_url(
                "mysql+pymysql://scott:tiger@localhost/"
                "?collectd_host=127.0.0.1&collectd_port=1234"
            )
            kwargs = {"collectd_host": "172.18.0.2", "collectd_port": 5678}
            p = plugin.Plugin(url, kwargs)
            if hasattr(url, "difference_update_query"):
                url = p.update_url(url)
            engine = mock.Mock()
            p.engine_created(engine)

        # argument is popped from both but favors url argument
        self.assertEqual(
            [mock.call(engine, collectd_host="127.0.0.1", collectd_port=1234)],
            start_plugin.mock_calls,
        )
        self.assertEqual({}, url.query)
        self.assertEqual({}, kwargs)
