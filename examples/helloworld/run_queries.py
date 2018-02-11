from sqlalchemy import create_engine
import random
import time
import threading
import multiprocessing

import logging
logging.basicConfig()
logging.getLogger("sqlalchemy_collectd").setLevel(logging.DEBUG)

e = create_engine("sqlite:///file.db?plugin=collectd")


def worker():
    e.dispose()

    def screw_w_pool():
        while True:
            conn = e.connect()
            try:
                time.sleep(random.random())
                conn.execute("select 1")
                time.sleep(random.random())
            finally:
                conn.close()
            time.sleep(random.randint(1, 5))

    threads = [threading.Thread(target=screw_w_pool) for i in range(20)]
    for t in threads:
        t.daemon = True
        t.start()

    while True:
        time.sleep(1)


procs = [multiprocessing.Process(target=worker) for i in range(5)]
for proc in procs:
    time.sleep(.5)
    proc.daemon = True
    proc.start()

while True:
    time.sleep(1)