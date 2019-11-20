====================
Hello World Example
====================

A minimal example to see sqlalchemy-collectd do something.

Step One - Run collectd as a console app
========================================

In one terminal window, run collectd as an interactive application with
the -f flag::

    # cd examples/helloworld
    # collectd -f -C client_plus_connmon.conf

The ``client_plus_connmon.conf`` file includes a relative path to the
sqlalchemy-collectd checkout as the module path.

Step Two - Run the demo program
================================

This program uses a SQLite database for starters.    It spins up
five processes with 20 threads each::

    # python run_queries.py

Step Three - watch collectd console
===================================

Output looks something like::

    $ collectd -f -C client_plus_connmon.conf
    [2018-02-11 18:29:35] plugin_load: plugin "logfile" successfully loaded.
    [2018-02-11 18:29:35] [info] plugin_load: plugin "write_log" successfully loaded.
    [2018-02-11 18:29:35] [info] plugin_load: plugin "python" successfully loaded.
    [2018-02-11 18:29:35] [info] sqlalchemy_collectd plugin version 0.0.1
    [2018-02-11 18:29:35] [info] Python version: 3.6.4 (default, Jan 23 2018, 22:28:37)
    [GCC 7.2.1 20170915 (Red Hat 7.2.1-2)]
    [2018-02-11 18:29:35] [info] Initialization complete, entering read-loop.
    [2018-02-11 18:29:45] [info] write_log values:
    [{"values":[0],"dstypes":["gauge"],"dsnames":["value"],"time":1518391784.793,"interval":10.000,"host":"photon2","plugin":"sqlalchemy","plugin_instance":"run_queries.py","type":"count","type_instance":"checkedin"}]
    [2018-02-11 18:29:45] [info] write_log values:
    [{"values":[0],"dstypes":["gauge"],"dsnames":["value"],"time":1518391784.793,"interval":10.000,"host":"photon2","plugin":"sqlalchemy","plugin_instance":"run_queries.py","type":"count","type_instance":"detached"}]
    [2018-02-11 18:29:45] [info] write_log values:
    [{"values":[6],"dstypes":["gauge"],"dsnames":["value"],"time":1518391784.793,"interval":10.000,"host":"photon2","plugin":"sqlalchemy","plugin_instance":"run_queries.py","type":"count","type_instance":"numprocs"}]
    [2018-02-11 18:29:45] [info] write_log values:
    [{"values":[6],"dstypes":["gauge"],"dsnames":["value"],"time":1518391784.793,"interval":10.000,"host":"photon2","plugin":"sqlalchemy","plugin_instance":"run_queries.py","type":"count","type_instance":"numpools"}]
    [2018-02-11 18:29:45] [info] write_log values:
    [{"values":[28],"dstypes":["gauge"],"dsnames":["value"],"time":1518391784.793,"interval":10.000,"host":"photon2","plugin":"sqlalchemy","plugin_instance":"host","type":"count","type_instance":"checkedout"}]

Step Four - Try out Connmon
===========================

The **connmon** console client is an optional feature that connects to the
SQLAlchemy-collectd plugin running inside the collectd server to print live
stats.  Once the above steps are all running, try out the client::

    # connmon


