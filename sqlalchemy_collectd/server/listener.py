import threading


def _receive(connection, receiver):
    while True:
        receiver.receive(connection)


def listen(connection, receiver):
    listen_thread = threading.Thread(
        target=_receive, args=(connection, receiver))
    listen_thread.daemon = True
    listen_thread.start()


