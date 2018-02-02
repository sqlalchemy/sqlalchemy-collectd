import mock
import unittest

from sqlalchemy_collectd import collectd


class CollectDProtocolTest(unittest.TestCase):

    def test_encode_type_values(self):
        type_ = collectd.Type(
            "my_type",
            ("some_val", collectd.VALUE_GAUGE),
            ("some_other_val", collectd.VALUE_DERIVE)
        )

        self.assertEqual(
            b'\x00\x06\x00\x18\x00\x02\x01\x02\xc9v\xbe\x9f\x1a\xcf9'
            b'@\x00\x00\x00\x00\x00\x00\x01\xc2',
            type_.encode_values(25.809, 450)
        )

    def test_message_construct(self):
        type_ = collectd.Type(
            "my_type",
            ("some_val", collectd.VALUE_GAUGE),
            ("some_other_val", collectd.VALUE_DERIVE)
        )

        sender = collectd.MessageSender(
            type_, "somehost", "someplugin", "someplugininstance",
            "sometypeinstance"
        )

        connection = mock.Mock()

        sender.send(connection, 1517607042.95968, 25.809, 450)

        self.assertEqual(
            [
                mock.call(b'\x00\x00\x00\rsomehost\x00\x00\x01\x00\x0c\x00\x00\x00\x00Zt\xd8\x82\x00\x02\x00\x0fsomeplugin\x00\x00\x03\x00\x17someplugininstance\x00\x00\x04\x00\x0cmy_type\x00\x00\x07\x00\x0c\x00\x00\x00\x00\x00\x00\x00\n\x00\x05\x00\x15sometypeinstance\x00\x00\x06\x00\x18\x00\x02\x01\x02\xc9v\xbe\x9f\x1a\xcf9@\x00\x00\x00\x00\x00\x00\x01\xc2')
            ],
            connection.send.mock_calls
        )

