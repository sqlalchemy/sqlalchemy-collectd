from . import collectd

pool = collectd.Type(
	"sqlalchemy_pool",
	("numpools", collectd.VALUE_GAUGE),
	("checkedout", collectd.VALUE_GAUGE),
	("checkedin", collectd.VALUE_GAUGE),
	("detached", collectd.VALUE_GAUGE),
	("invalidated", collectd.VALUE_GAUGE),
	("total", collectd.VALUE_GAUGE),
)

checkouts = collectd.Type(
	"sqlalchemy_checkouts", ("count", collectd.VALUE_DERIVE))

commits = collectd.Type(
	"sqlalchemy_commits", ("count", collectd.VALUE_DERIVE))

rollbacks = collectd.Type(
	"sqlalchemy_rollbacks", ("count", collectd.VALUE_DERIVE))

invalidated = collectd.Type(
	"sqlalchemy_invalidated", ("count", collectd.VALUE_DERIVE))

transactions = collectd.Type(
	"sqlalchemy_transactions", ("count", collectd.VALUE_DERIVE))

