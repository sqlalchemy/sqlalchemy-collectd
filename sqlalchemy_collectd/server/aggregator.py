import collections


class Aggregator(object):
    def __init__(self):
        # TOOD: configurable size
        self.queue = collections.deque(maxlen=100000)

    def put(self, message):
        self.queue.appendleft(message)

    def outgoing(self):
        while self.queue:
            yield self.queue.pop()
