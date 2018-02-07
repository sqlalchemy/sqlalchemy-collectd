import threading


def _receive(connection, aggregator, receiver):
    while True:
        receiver.receive(connection, aggregator)


def listen(connection, aggregator, receiver):
    listen_thread = threading.Thread(
        target=_receive, args=(connection, aggregator, receiver))
    listen_thread.daemon = True
    listen_thread.start()


