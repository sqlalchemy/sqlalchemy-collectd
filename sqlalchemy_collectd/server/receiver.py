from .. import protocol
from .. import types


receivers = []


def receives(protocol_type):
    def decorate(fn):
        receivers.append((protocol_type, fn))
        return fn

    return decorate


class Receiver(object):
    def __init__(self):
        self.message_receiver = protocol.MessageReceiver(
            types.pool,
            types.checkouts,
            types.commits,
            types.rollbacks,
            types.invalidated,
            types.transactions
        )

    def receive(self, connection, aggregator):
        data, host = connection.receive()
        message = self.message_receiver.receive(data)
        if message is not None:
            message['host'] = host
        # TODO: look up type-specific handler
        # feed to aggregator per-type
        aggregator.put(message)