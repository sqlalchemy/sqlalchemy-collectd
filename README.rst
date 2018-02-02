===================
sqlalchemy-collectd
===================

Send statistics on SQLAlchemy connection and transaction use (and maybe other
things in the future) to the `collectd <https://collectd.org/>`_ service.   collectd is a widely
used system statistics collection tool which is supported by virtually all
graphing and monitoring tools.


hostname/pid-12345/checkouts

host  /  plugin   / plugininstance  type / typeinstance

# use real types, requires custom types.db w/ awkward configuration
hostname/sqlalchemy-nova/checkouts-12345
hostname/sqlalchemy-nova/transactions-12345
hostname/sqlalchemy-nova/checkedout-12345
hostname/sqlalchemy-nova/pooled-12345
hostname/sqlalchemy-nova/connected-12345

# another one w/ a "wide" value

# key:
# host / plugin-plugininstance / type-typeinstance

# we will use this layout, "configured-name" is part of the
# sqlalchemy url conf, e.g  mysql://nova:pw@hostname/nova?plugin=sqlalchemy-collectd&collectd_name=nova

# host / sqlalchemy-<configured-name> / <sqlalchemy custom type>-<process id>


# for the values, when we see a "gauge" thats a number we report directly,
# when we see a "derived", collectd can turn that into a rate over time, e.g.
# checkouts / sec  transactions / sec

# so say nova has process ids 123 and 4567, neutron has procss ids 9856 and 786,

hostname/sqlalchemy-nova/sqlalchemy_pool-123   numpools=gauge checkedout=gauge overflow=gauge pooled=gauge total=gauge
hostname/sqlalchemy-nova/sqlalchemy_transactions-123   count=gauge
hostname/sqlalchemy-nova/sqlalchemy_checkouts-123   count=derived
hostname/sqlalchemy-nova/sqlalchemy_commits-123   count=derived
hostname/sqlalchemy-nova/sqlalchemy_rollbacks-123   count=derived
hostname/sqlalchemy-nova/sqlalchemy_invalidated-123   count=derived


hostname/sqlalchemy-neutron/sqlalchemy_pool-9865   numpools=gauge checkedout=gauge overflow=gauge pooled=gauge total=gauge
hostname/sqlalchemy-neutron/sqlalchemy_checkouts-9865   count=derived
hostname/sqlalchemy-neutron/sqlalchemy_transactions-9865   count=derived
hostname/sqlalchemy-neutron/sqlalchemy_pool-786   numpools=gauge checkedout=gauge overflow=gauge pooled=gauge total=gauge
hostname/sqlalchemy-neutron/sqlalchemy_checkouts-786   count=derived
hostname/sqlalchemy-neutron/sqlalchemy_transactions-786   count=derived


# then we're going to use the <Plugin "aggregation"> to flatten out the
# process id part of it so that we get the stats per program / database URL
# overall, then a second <Plugin "aggregation"> will further take that
# and get us the stats per hostname, that's what will be sent to graphite
# out of the box.



hostname/sqlalchemy-nova/sqlalchemy_checkouts-12345   count=derived
hostname/sqlalchemy-nova/sqlalchemy_transactions-12345   count=derived



# alternate - but no way to aggregate b.c. can't aggregate on regexp
hostname/sqlalchemy-nova-12345/derive-checkouts
hostname/sqlalchemy-nova-12345/derive-transactions
hostname/sqlalchemy-nova-12345/gauge-checkedout
hostname/sqlalchemy-nova-12345/gauge-pooled
hostname/sqlalchemy-nova-12345/gauge-connected

# alternate #2
hostname/sqlalchemy-12345/derive-nova-checkouts    value
hostname/sqlalchemy-12345/derive-nova-transactions value
hostname/sqlalchemy-12345/gauge-nova-checkedout  value
hostname/sqlalchemy-12345/gauge-nova-pooled      value
hostname/sqlalchemy-12345/gauge-nova-connected   value

# with #2, aggregate on host, type instance, gives us:
hostname/sqlalchemy/derive-nova-checkouts    value
hostname/sqlalchemy/derive-nova-transactions value
hostname/sqlalchemy/gauge-nova-checkedout  value
hostname/sqlalchemy/gauge-nova-pooled      value
hostname/sqlalchemy/gauge-nova-connected   value

# but! still can't aggregate across nova/neutron/etc





<Plugin "aggregation">
  <Aggregation>
	# translate from:
	#
	# <host>/<plugin>-<program-name>/<type>-<process pid>
	#
	# hostname/sqlalchemy-nova/checkouts-12345
	# hostname/sqlalchemy-nova/checkouts-5839
	# hostname/sqlalchemy-nova/checkouts-9905
	# hostname/sqlalchemy-neutron/checkouts-19385
	# hostname/sqlalchemy-neutron/checkouts-6991
	#
	# to:
	#
	# <host>/<plugin>-<program-name>/<type>
	#
	# hostname/sqlalchemy-nova/checkouts
	# hostname/sqlalchemy-neutron/checkouts

    Plugin "sqlalchemy"

    GroupBy "Host"
    GroupBy "PluginInstance"

	CalculateNum true
    CalculateSum true
    CalculateAverage true
  </Aggregation>

  <Aggregation>
	# translate from:
	#
	# <host>/<plugin>-<program-name>/<type>-<process pid>
	#
	# hostname/sqlalchemy-nova/checkouts-12345
	# hostname/sqlalchemy-nova/checkouts-5839
	# hostname/sqlalchemy-nova/checkouts-9905
	# hostname/sqlalchemy-neutron/checkouts-19385
	# hostname/sqlalchemy-neutron/checkouts-6991
	#
	# to:
	#
	# <host>/<plugin>-all/<type>
	#
	# hostname/sqlalchemy-all/checkouts

    Plugin "sqlalchemy"

    GroupBy "Host"
    SetPluginInstance "all"

    CalculateSum true
    CalculateAverage true
  </Aggregation>


</Plugin>

# send all SQLAlchemy messages to the aggregation plugin,
# and don't send them anywhere else, thereby filtering out the
# per-PID messages.
LoadPlugin "match_regex"
<Chain "PostCache">
  <Rule>
    <Match regex>
      Plugin "^sqlalchemy$"
    </Match>
    <Target write>
      Plugin "aggregation"
    </Target>
    Target stop
  </Rule>
</Chain>


[{"values":[1069067],"dstypes":["derive"],"dsnames":["value"],"time":1517512597.320,"interval":10.000,"host":"photon2","plugin":"cpu","plugin_instance":"2","type":"cpu","type_instance":"idle"}]


[{"values":[0.31,0.34,0.28],"dstypes":["gauge","gauge","gauge"],"dsnames":["shortterm","midterm","longterm"],"time":1517512718.495,"interval":10.000,"host":"photon2","plugin":"load","plugin_instance":"","type":"load","type_instance":""}]


hostname/pid-12345/checkins
hostname/pid-12345/checkouts



{
	"host": "foobar.host",
	"plugin": "sqlalchemy",
	"plugin_instance": "<pid>",
	"type": "progname",
	"type_instance": "nova",
	"current_connections": 108,    (gauge)
	"current_checkouts": 25,       (gauge)
	"checkouts": 38975,     (counter)
	"checkins": 38972,      (counter)
	"transactions": 38932          (counter)
}



 [{"values":[0,0],"dstypes":["derive","derive"],"dsnames":["rx","tx"],"time":1517372403.790,"interval":10.000,"host":"photon2","plugin":"interface","plugin_instance":"virbr2","type":"if_errors","type_instance":""}]
Jan 30 23:20:03 photon2 collectd[26416]: write_log values:
                                         [{"values":[0,0],"dstypes":["derive","derive"],"dsnames":["rx","tx"],"time":1517372403.790,"interval":10.000,"host":"photon2","plugin":"interface","plugin_instance":"virbr3-nic","type":"if_packets","type_instance":""}]
Jan 30 23:20:03 photon2 collectd[26416]: write_log values:
                                         [{"values":[0,0],"dstypes":["derive","derive"],"dsnames":["rx","tx"],"time":1517372403.790,"interval":10.000,"host":"photon2","plugin":"interface","plugin_instance":"virbr2","type":"if_dropped","type_instance":""}]
Jan 30 23:20:03 photon2 collectd[26416]: write_log values:
                                         [{"values":[0,0],"dstypes":["derive","derive"],"dsnames":["rx","tx"],"time":1517372403.790,"interval":10.000,"host":"photon2","plugin":"interface","plugin_instance":"virbr3-nic","type":"if_octets","type_instance":""}]



