===================
sqlalchemy-collectd
===================

Send statistics on SQLAlchemy connection and transaction use (and maybe other
things in the future) to the `collectd <https://collectd.org/>`_ service.   collectd is a widely
used system statistics collection tool which is supported by virtually all
graphing and monitoring tools.


hostname/pid-12345/checkouts

host  /  plugin   / plugininstance  type / typeinstance

hostname/sqlalchemy-nova/checkouts-12345    derive value=value
hostname/sqlalchemy-nova/transactions-12345  derive value=value
hostname/sqlalchemy-nova/checkedout-12345   gauge
hostname/sqlalchemy-nova/pooled-12345   gauge
hostname/sqlalchemy-nova/connected-12345  gauge


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



