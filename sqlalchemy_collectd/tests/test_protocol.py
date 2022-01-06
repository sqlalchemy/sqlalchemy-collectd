from unittest import mock

from .. import protocol
from .. import testing


class CollectDProtocolTest(testing.TestBase):
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

    def test_values_sum(self):
        value = protocol.Values(
            type="my_type",
            host="somehost",
            plugin="someplugin",
            plugin_instance="someplugininstance",
            type_instance="sometypeinstance",
        )

        self.assertEqual(
            sum(
                [
                    value.build(values=[5, 10]),
                    value.build(values=[25, 8]),
                    value.build(values=[11, 7]),
                ]
            ),
            value.build(values=[41, 25]),
        )

        # other fields that are different are removed
        self.assertEqual(
            sum(
                [
                    value.build(type_instance="one", values=[5, 10]),
                    value.build(type_instance="two", values=[25, 8]),
                    value.build(values=[11, 7]),
                ]
            ),
            value.build(type_instance=None, values=[41, 25]),
        )

    def test_values_build(self):
        value = protocol.Values(
            type="my_type",
            host="somehost",
            plugin="someplugin",
            plugin_instance="someplugininstance",
            type_instance="sometypeinstance",
            time=50,
        )

        v2 = value.build(time=70)

        self.assertEqual(
            value,
            protocol.Values(
                type="my_type",
                host="somehost",
                plugin="someplugin",
                plugin_instance="someplugininstance",
                type_instance="sometypeinstance",
                time=50,
            ),
        )
        self.assertEqual(
            v2,
            protocol.Values(
                type="my_type",
                host="somehost",
                plugin="someplugin",
                plugin_instance="someplugininstance",
                type_instance="sometypeinstance",
                time=70,
            ),
        )

    def test_message_construct(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        value = protocol.Values(
            type="my_type",
            host="somehost",
            plugin="someplugin",
            plugin_instance="someplugininstance",
            type_instance="sometypeinstance",
        )

        connection = mock.Mock()

        sender = protocol.NetworkSender(connection, [type_])
        sender.send(value.build(time=1517607042.95968, values=[25.809, 450]))

        self.assertEqual([mock.call(self.message)], connection.send.mock_calls)

    def test_decode_packet(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        connection = mock.Mock(
            receive=mock.Mock(return_value=(self.message, "localhost"))
        )
        network_receiver = protocol.NetworkReceiver(connection, [type_])
        result = network_receiver.receive()
        self.assertEqual(
            protocol.Values(
                type="my_type",
                host="somehost",
                plugin="someplugin",
                plugin_instance="someplugininstance",
                type_instance="sometypeinstance",
                values=[25.809, 450],
                interval=10,
                time=1517607042,
            ),
            result,
        )

    def test_decode_unknown_type(self):
        type_ = protocol.Type(
            "my_type",
            ("some_val", protocol.VALUE_GAUGE),
            ("some_other_val", protocol.VALUE_DERIVE),
        )

        log = mock.Mock()
        connection = mock.Mock(
            receive=mock.Mock(
                return_value=(b"asdfjq34kt2n34kjnas", "localhost")
            ),
            log=log,
        )
        network_receiver = protocol.NetworkReceiver(connection, [type_])

        result = network_receiver.receive()
        self.assertEqual(result, None)
        self.assertEqual(
            log.mock_calls,
            [
                mock.call.warn("Message %s not known, skipping", mock.ANY),
                mock.call.warn(
                    "Message did not have TYPE_TYPE block, skipping"
                ),
            ],
        )
