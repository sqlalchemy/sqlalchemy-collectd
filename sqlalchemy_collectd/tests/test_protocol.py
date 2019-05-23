import unittest

import mock

from .. import protocol


class CollectDProtocolTest(unittest.TestCase):
    def test_encode_type_values(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        self.assertEqual(self.value_block, type_._encode_values(25.809, 450))

    value_block = (
        b"\x00\x06"  # TYPE_VALUES
        b"\x00\x18"  # part length
        b"\x00\x02"  # number of values
        b"\x01\x02"  # dstype codes GAUGE, DERIVE
        b"\xc9v\xbe\x9f\x1a\xcf9@"  # 8 bytes for 25.809
        b"\x00\x00\x00\x00\x00\x00\x01\xc2"  # 8 bytes for 450
    )

    message = (
        b"\x00\x00\x00\rsomehost\x00"  # TYPE_HOST
        b"\x00\x01\x00\x0c\x00\x00\x00\x00Zt\xd8\x82"  # TYPE_TIME
        b"\x00\x02\x00\x0fsomeplugin\x00"  # TYPE_PLUGIN
        # TYPE_PLUGIN_INSTANCE
        b"\x00\x03\x00\x17someplugininstance\x00"
        b"\x00\x04\x00\x0cmy_type\x00"  # TYPE_TYPE
        # TYPE_TIMESTAMP
        b"\x00\x07\x00\x0c\x00\x00\x00\x00\x00\x00\x00\n"
        b"\x00\x05\x00\x15sometypeinstance\x00"  # TYPE_TYPE_INSTANCE
    ) + value_block

    def test_message_construct(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        sender = protocol.MessageSender(
            type_,
            "somehost",
            "someplugin",
            "someplugininstance",
            "sometypeinstance",
        )

        connection = mock.Mock()

        sender.send(connection, 1517607042.95968, 25.809, 450)

        self.assertEqual([mock.call(self.message)], connection.send.mock_calls)

    def test_decode_packet(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        message_receiver = protocol.MessageReceiver(type_)
        result = message_receiver.receive(self.message)
        self.assertEqual(
            {
                protocol.TYPE_HOST: "somehost",
                protocol.TYPE_TIME: 1517607042,
                protocol.TYPE_PLUGIN: "someplugin",
                protocol.TYPE_PLUGIN_INSTANCE: "someplugininstance",
                protocol.TYPE_TYPE: "my_type",
                protocol.TYPE_TYPE_INSTANCE: "sometypeinstance",
                protocol.TYPE_VALUES: [25.809, 450],
                protocol.TYPE_INTERVAL: 10,
                "type": type_,
                "values": {"some_other_val": 450, "some_val": 25.809},
            },
            result,
        )
