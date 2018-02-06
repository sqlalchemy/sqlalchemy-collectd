from . import protocol

pool = protocol.Type(
	"sqlalchemy_pool",
	("numpools", protocol.VALUE_GAUGE),
	("checkedout", protocol.VALUE_GAUGE),
	("checkedin", protocol.VALUE_GAUGE),
	("detached", protocol.VALUE_GAUGE),
	("invalidated", protocol.VALUE_GAUGE),
	("total", protocol.VALUE_GAUGE),
)

checkouts = protocol.Type(
	"sqlalchemy_checkouts", ("count", protocol.VALUE_DERIVE))

commits = protocol.Type(
	"sqlalchemy_commits", ("count", protocol.VALUE_DERIVE))

rollbacks = protocol.Type(
	"sqlalchemy_rollbacks", ("count", protocol.VALUE_DERIVE))

invalidated = protocol.Type(
	"sqlalchemy_invalidated", ("count", protocol.VALUE_DERIVE))

transactions = protocol.Type(
	"sqlalchemy_transactions", ("count", protocol.VALUE_DERIVE))

