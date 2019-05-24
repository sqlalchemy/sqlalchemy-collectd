import socket


class Monitor(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def forward(self, data):
        self.sock.sendto(data, (self.host, self.port))
