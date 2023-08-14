"""Type objects representing the collectd types used.

There are two classes of types here; "internal" types are used between
the SQLAlchemy-collectd client plugin embedded in applications and the
SQLAlchemy-collectd server plugin.  These type objects are not part of
collectd's types.db, and in the interests of configuration simplicity
and portability, these types are not exposed outside of the communication
between the two SQLAlchemy-collectd plugins.

The other type defined here are "external" types, which are public collectd
types defined in /usr/share/collectd/types.db or similar.  We are using the
"count" and "derive" types which are generic types that define a single "GAUGE"
and a single "DERIVE" value, respectively.  When the SQLAlchemy-collectd server
plugin aggregates and reports on the results it receives from the client, it
converts the "internal" types into "external" types and streams them into
collectd as the result.   These are the stats that are then consumable by all
collectd "writer" systems such as logging, network and grafana.


"""
from . import protocol


COLLECTD_PLUGIN_NAME = "sqlalchemy"

# these values are the current number of something at a point in time,
# like current number of connections, number of processes.
# these numbers go up and down.
pool_internal = protocol.Type(
    "sqlalchemy_pool",
    ("numpools", protocol.VALUE_GAUGE),
    ("checkedout", protocol.VALUE_GAUGE),
    ("checkedin", protocol.VALUE_GAUGE),
    ("detached", protocol.VALUE_GAUGE),
    # ("invalidated", protocol.VALUE_GAUGE),
    ("connections", protocol.VALUE_GAUGE),
)

# numprocs is not passed by the client, it's calculated by the
# server-side aggregator
process_internal = protocol.Type(
    "sqlalchemy_process", ("numprocs", protocol.VALUE_GAUGE)
)

# these values are passed as aggregate totals, and continue to grow.
# by using  DERIVE, the ultimate stat will be the rate of change, e.g.
# checkouts / sec etc.
totals_internal = protocol.Type(
    "sqlalchemy_totals",
    ("checkouts", protocol.VALUE_DERIVE),
    ("invalidated", protocol.VALUE_DERIVE),
    ("connects", protocol.VALUE_DERIVE),
    ("disconnects", protocol.VALUE_DERIVE),
)

# transactions are not implemented yet :)
transactions_internal = protocol.Type(
    "sqlalchemy_transactions",
    ("commits", protocol.VALUE_DERIVE),
    ("rollbacks", protocol.VALUE_DERIVE),
    ("transactions", protocol.VALUE_DERIVE),
)


# external types "count" and "derive".
count_external = protocol.Type("count", ("value", protocol.VALUE_GAUGE))
derive_external = protocol.Type("derive", ("value", protocol.VALUE_DERIVE))
