from . import protocol

# internal types.  These are used by the SQLAlchemy client plugin
# to talk to the SQLAlchemy collectd plugin.
pool_internal = protocol.Type(
    "sqlalchemy_pool",
    ("numpools", protocol.VALUE_GAUGE),
    ("checkedout", protocol.VALUE_GAUGE),
    ("checkedin", protocol.VALUE_GAUGE),
    ("detached", protocol.VALUE_GAUGE),
    # ("invalidated", protocol.VALUE_GAUGE),
    ("connections", protocol.VALUE_GAUGE),
    ("numprocs", protocol.VALUE_GAUGE),
)

transactions_internal = protocol.Type(
    "sqlalchemy_transactions",
    ("commits", protocol.VALUE_DERIVE),
    ("rollbacks", protocol.VALUE_DERIVE),
    ("transactions", protocol.VALUE_DERIVE),
)

totals_internal = protocol.Type(
    "sqlalchemy_totals",
    ("checkouts", protocol.VALUE_DERIVE),
    ("invalidated", protocol.VALUE_DERIVE),
    ("connects", protocol.VALUE_DERIVE),
    ("disconnects", protocol.VALUE_DERIVE),
)


# TODO: build two stream translators - receive a stream of protocol.Values
# and convert from internal to external messages, another that converts
# from external back to internal.  the latter will need to use TimeBucket
# so that distinct Values can be grouped back together.

# external types.  These are the ones we send out to collectd to be
# consumed, so they are generated from a stream of internal types.
# Also the connmon plugin receives these from a collectd server and aggregates
# them back into internal types to be consumed by the connmon client.
# The rationale for this is to reduce both in-Python overhead as well as the
# size of messages.    It's a bit of premature optimization, but the way
# collectd has a very large message just for one metric is pretty wasteful
# being that our plugin has a lot of separate metrics, not just a few.

# equivalent to:
# numpools_external = protocol.Type(
#     "numpools",
#     ("value", protocol.VALUE_GAUGE)
# )

external_types = {}
for _type in [pool_internal, transactions_internal, totals_internal]:
    for name, value_type in zip(_type.names, _type.types):
        external_types[name] = protocol.Type(name, ("value", value_type))
