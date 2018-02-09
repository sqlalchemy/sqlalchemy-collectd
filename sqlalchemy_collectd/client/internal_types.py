from .. import protocol

pool = protocol.Type(
    "sqlalchemy_pool",
    ("numpools", protocol.VALUE_GAUGE),
    ("checkedout", protocol.VALUE_GAUGE),
    ("checkedin", protocol.VALUE_GAUGE),
    ("detached", protocol.VALUE_GAUGE),
    # ("invalidated", protocol.VALUE_GAUGE),
    ("connections", protocol.VALUE_GAUGE),
)

transactions = protocol.Type(
    "sqlalchemy_transactions",
    ("commits", protocol.VALUE_DERIVE),
    ("rollbacks", protocol.VALUE_DERIVE),
    ("transactions", protocol.VALUE_DERIVE),
)

totals = protocol.Type(
    "sqlalchemy_totals",
    ("checkouts", protocol.VALUE_DERIVE),
    ("invalidated", protocol.VALUE_DERIVE),
    ("connects", protocol.VALUE_DERIVE),
    ("disconnects", protocol.VALUE_DERIVE),
)
