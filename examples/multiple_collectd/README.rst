=========================
Multiple Collectd Example
=========================

In this example, multiple collectd servers can relay their messages
to a central "aggregation" collectd server via the network plugin.  That
aggregation server then has stats for all the endpoints together which
can be viewed with collectd clients, and can also be inspected "live" using
connmon.

* local_client.conf - defines the setup for the initial collectd servers that
  are close to the SQLAlchemy applications generating stats.   Includes the
  network plugin instructing them to call out to the central aggregation server.

* receiver.conf - defines the central aggregation server.  Note this includes
  only the network plugin and the connmon plugin.  SQLAlchemy clients don't
  connect directly to this server.
