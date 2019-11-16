from . import protocol

# internal types.  These are used by the SQLAlchemy client plugin
# to talk to the SQLAlchemy collectd plugin.


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
