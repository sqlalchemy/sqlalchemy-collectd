import logging
import multiprocessing
import random
import threading
import time

from sqlalchemy import create_engine
from sqlalchemy import select

logging.basicConfig()
logging.getLogger("sqlalchemy_collectd").setLevel(logging.DEBUG)


def worker(appname):
    e = create_engine(
        f"sqlite:///file.db?plugin=collectd&collectd_program_name={appname}"
    )

    e.dispose()

    def screw_w_pool():
        while True:
            conn = e.connect()
            try:
                time.sleep(random.random())
                conn.execute(select(1))
                time.sleep(random.random())
            finally:
                conn.close()
            time.sleep(random.randint(1, 5))

    threads = [threading.Thread(target=screw_w_pool) for i in range(5)]
    for t in threads:
        t.daemon = True
        t.start()

    while True:
        time.sleep(1)


procs = [
    multiprocessing.Process(target=worker, args=((f"worker {i % 20}"),))
    for i in range(50)
]
for proc in procs:
    time.sleep(0.5)
    proc.daemon = True
    proc.start()

while True:
    time.sleep(1)
