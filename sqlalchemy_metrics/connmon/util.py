import contextlib


def periodic_timer(interval, start=0):
    """return True only every 'interval' seconds."""

    last_check = [start]

    def reset(now):
        last_check[0] = now

    def check(now):
        if now - last_check[0] > interval:
            last_check[0] = now
            return True
        else:
            return False

    check.last_check = last_check
    check.interval = interval
    check.reset = reset
    return check


@contextlib.contextmanager
def stop_on_keyinterrupt():
    try:
        yield
    except KeyboardInterrupt:
        pass
