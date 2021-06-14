===================
sqlalchemy-collectd
===================

Send statistics on `SQLAlchemy <http://www.sqlalchemy.org>`_ connection and
transaction metrics used by Python applications to the
`collectd <https://collectd.org/>`_ service.

sqlalchemy-collectd works as a SQLAlchemy plugin invoked via the database URL,
so can be used in any SQLAlchemy application (1.1 or greater) that accepts
arbitrary connection URLs.   The plugin is loaded using setuptools
entrypoints and no code changes to the application are required.   There
are no dependencies on database backends or drivers.

sqlalchemy-collectd is oriented towards providing a unified view of
application-side database metrics in sprawling, many-host / many-process
environments that may make use of any number of topologically complicating
technologies such as database clusters, proxy servers, large numbers of
client applications, multi-process applications, and containers.

What's collectd?
================

collectd is a statistics collection daemon that is easy to run.   It serves as
a collector and re-broadcaster of runtime statistics for a wide variety of
performance and other metrics.   Once a set of stats are in collectd, they can
be broadcast out virtually anywhere, including to `RRD <https://oss.oetiker.ch/rrdtool/>`_
databases and front-ends, to metrics
reporting applications like `Graphite <https://graphiteapp.org/>`_ and `Grafana
<https://grafana.com/>`_, and to `other collectd servers
<https://collectd.org/wiki/index.php/Networking_introduction>`_.

Architecture Nutshell
=====================

sqlalchemy-collectd gathers its statistics from **within** the Python
application itself, and delivers live metrics to a collectd service over UDP.
To achieve this, it's client portion is loaded within the process as a
SQLAlchemy **engine plugin** that attaches listeners to a
``sqlalchemy.engine.Engine`` object as well as the connection pool within it.
A background thread running within each process periodically sends a snapshot
of statistics out over UDP.

On the collectd side, a Python plugin listens on the same UDP port and
aggregates statistics received from any number of Python processes and hosts,
and then delivers them to the collectd engine itself as a series of
per-host and per-program statistics.

A key goal of this architecture is to allow a Python program that uses
multiple processes (e.g. via Python ``multiprocessing`` or just plain
``fork``) to report **unified** information on each engine/connection pool
within each subprocess, as well as to track multiple instances of the
same application running from many hosts (and of course it can track
any number of applications and hosts simultaneously).   Having a full
client/server model allows the collectd service itself to be located not only
on the same host as the application itself, but on any other host on the
network.

The network model itself makes use of collectd's own binary protocol; while
not strictly necessary, this is because originally the plan was to use the
collectd "network" plugin as the receiver, however after observing limitations
in collectd's "aggregation" plugin this was replaced with a full Python plugin
that does everything needed in a much more straightforward way.

How is this different from using database monitoring?
=====================================================

When you run a database like MySQL or Postgresql, there's lots of ways to see
activity in the database; you can list out statistics regarding connections,
transactions, threads / processes in use, and in most cases you can integrate
these server-side statistics with collectd itself to watch trends in real time.

However, while gathering stats from the server can provide insights into
activity, including being able to look at the originating host as well as the
specific database(s) being accessed by each client, in a large scale
environment it's difficult to get a unified, real-time picture for how each
process on each host is making use of its database connections, especially if
there are additional layers of indirection between application and
databases present, such as proxy servers like HAProxy, ProxySQL or PGBouncer,
as well as when databases and/or applications are containerized and potentially
hopping over additional network translation layers.   This kind of analysis
requires being able to relate database connections reported by the database
to the originating hosts and individual processes on each host.

SQLAlchemy-oriented applications usually make use of process-local connection pools as
well, and it is valuable to be able to see how well these pools are being
utilized, which includes being able to see how many connections are sitting
idle vs. how often does the application need to  create new connections in
order to respond to requests.   These are still things that can probably be
gleaned from the database itself from things like connection idle time, but
especially when layers of indirection are in place, it's simpler to get the
performance metrics you care about (e.g., how well are the **applications**
performing) from the applications themselves, as they can give you the exact
information about what they are doing without having to reverse-engineer it
from database servers and network status.

Of course, this assumes the applications are Python applications using
SQLAlchemy.   Which of course they should be! :)

Installation
============

To use SQLAlchemy-collectd, you need to have:

* SQLAlchemy-collectd installed as a Python library alongside SQLAlchemy
  itself, in all Python environments that run a SQLAlchemy-oriented
  application.

* The collectd service itself somewhere on the network.

* The collectd-python plugin, which may be delivered as a separate package
  depending on distribution

* SQLAlchemy-collectd installed as a Python library alongside the collectd
  server itself, either as part of the system Python which collectd-python
  accesses by default, **or** the SQLAlchemy-collectd application can be
  extracted into any arbitrary location that can be set up as an additional
  system path with collectd.

Without using a package manager, SQLAlchemy-collectd can be installed via
pip using::

	pip install sqlalchemy-collectd

Configuration
=============

Configuration involves both a client-side configuration as well as a server
side configuration.  Both are very simple.

Client
------

SQLAlchemy applications use a database connection URL, usually loaded
from a configuration system of some kind.  Wherever this URL is for your
target application, basically add ``?plugin=collectd`` to it (or ``&plugin=collectd``
if other query parameters already there).  Such as::

	mysql+pymysql://user:password@databasehost/dbname?charset=utf8&plugin=collectd

Using a URL as above, the sqlalchemy-collectd plugin will be pulled in where it
will attempt to send messages to a collectd server listening on localhost port
25827 (note this is one higher than the default collectd network plugin port of
25826).


Destination Host
^^^^^^^^^^^^^^^^

To send stats to collectd on a different host, add ``collectd_host``
(currently ipv4 only) and optionally ``collectd_port``::

	mysql+pymysql://user:password@databasehost/dbname?charset=utf8&plugin=collectd&collectd_host=172.18.5.2&collectd_port=25827

Program Name
^^^^^^^^^^^^

Another important configuration is the "program name" - this is the application
name that sqlalchemy-collectd will report within statistics.   Within a particular
"program name" on a particular host, statistics are **aggregated across all
processes**, regardless of parent process.

By default, the "program name" comes from ``sys.argv[0]``, but this is not
always what's desired; for example, if you're running from within mod_wsgi,
this will likely return ``httpd`` which is more vague that most would prefer.
Additionally, a single application might create connections to multiple
databases for different purposes, and one might want to separate the reporting
for these into different sections.  To set up this program name, add
``collectd_program_name``::

	mysql+pymysql://user:password@databasehost/dbname?charset=utf8&plugin=collectd&collectd_program_name=nova_api&collectd_host=172.18.5.2

With the above URL, all Python processes that use this URL on a single host
will aggregate their connection use statistics under the name ``nova_api``.

Startup
^^^^^^^

After the URL is configured, the vast majority of applications probably
need to be restarted for the change to take effect.

The plugin will transparently spawn a background thread for each individual process
that starts up which also connects to the database (don't worry, these work
if you are using gevent, eventlet, asyncio, gunicorn, etc.  threads are your
friend).



Server
------

sqlalchemy-collectd uses a Python plugin, so in your collectd.conf or in a
collectd.d/sqlalchemy.conf file, assuming a system-installed sqlalchemy-collectd::

	LoadPlugin python
	<Plugin python>
	    LogTraces true

	    Import "sqlalchemy_collectd.server.plugin"

	    <Module "sqlalchemy_collectd.server.plugin">
	    	# ipv4 only for the moment
	        listen "0.0.0.0" 25827

	        # set to "debug" to show messages received
	        loglevel "info"

	    </Module>
	</Plugin>

Above, the plugin will listen for UDP on port 25827 of the default network
interface.  It can also be configured to listen on "localhost" or any
other IP number (currently ipv4 only) on the host.

Custom Module Path
^^^^^^^^^^^^^^^^^^

To reference sqlalchemy-collectd extracted into an arbitrary file location,
add ``ModulePath``::

	LoadPlugin python
	<Plugin python>
		ModulePath "/path/to/sqlalchemy-collectd/"
	    LogTraces true

	    Import "sqlalchemy_collectd.server.plugin"

	    <Module "sqlalchemy_collectd.server.plugin">
	    	# ipv4 only for the moment
	        listen "0.0.0.0" 25827

	        # set to "debug" to show messages received
	        loglevel "info"
	    </Module>
	</Plugin>

For further information about the Python plugin system see
`collectd-python <https://collectd.org/documentation/manpages/collectd-python.5.shtml>`_.

The collectd server is typically restarted for the configurational change
to take effect.

TODO
^^^^

* ipv6 support

* security layer (e.g. network packet signing / encryption)

Stats
=====

Now that sqlalchemy-collectd is running, what stats can we see?

Supposing we have the plugin turned on for the applications ``neutron``
and ``nova``, the namespace we would see in a tool like graphana would
look like::

	hostname
		sqlalchemy-host
			count-checkedin
			count-checkedout
			count-connections
			count-detached
			count-numpools
			count-numprocs
			derive-checkouts
			derive-connects
			derive-disconnects
			derive-invalidated
			derive-commits
			derive-rollbacks
			derive-transactions

		sqlalchemy-neutron
			count-checkedin
			count-checkedout
			count-connections
			count-detached
			... everything else

		sqlalchemy-nova
			count-checkedin
			count-checkedout
			count-connections
			count-detached
			... everything else

Above, we first see that all stats are grouped per-hostname.   Within that,
we have a fixed *plugin instance* called "host", which renders as ``sqlalchemy-host``.
This represents aggregated statistics for the entire host, that is, statistics
that take into account all database connections used by all applications (that
use sqlalchemy-collectd) on this particular host.

Following that, we can see there are groups for the individual ``program_name``
we set up, for ``nova`` and ``neutron`` we get stats aggregated for that
name specifically.

The statistics themselves are labeled ``count-<name>`` or ``derive-<name>``,
which correspond to pre-supplied collectd types ``count`` and ``derive`` (see
"collectd types" below for why the naming is done this way).  The stats labeled
``count`` are integers representing the current count of a resource or
activity:

* ``count-checkedin`` - current number of connections that are checked in to the
  connection pool

* ``count-checkedout`` - current number of connections that are checked out from
  the connection pool, e.g. are in use by the application to talk to the
  database.

* ``count-connections`` - total number of connections to the database at this moment,
  checked out, checked in, detached, or soft-invalidated.

* ``count-detached`` - total number of connections that are **detached**; meaning
  they have been disconnected from the engine/pool using the ``.detach()``
  method but are still being used as a database connection.

* ``count-numpools`` - the number of connection pools in use.  A SQLAlchemy
  ``Engine`` features exactly one connection pool.  If an application connects
  to two different database URLs in a process and creates two different
  ``Engine`` objects, then you'd have two pools.  If that same application
  spawns off into ten subprocesses, then you have 20 or 22 pools in use,
  depending on how the parent uses the database also.   Use ``count-numpools``
  to make sure this number is what you expect.  A poorly written application
  that is spawning a brand new ``Engine`` for each request will have a
  dramatically larger number here (as well as one that is changing constantly)
  and that is an immediate red flag that the application should be fixed.

* ``count-numprocs`` - the total number of Python processes, e.g. parent and
  subprocesses, that are contributing to the connection statistics in this
  group.   This number will match ``count-numpools`` if you have one
  ``Engine`` per process.

  Both the ``count-numpools`` and ``count-numprocs`` values provide context to
  when one looks at the total connections and  checkouts. If connection pools
  are configured to allow at most 20 connections max, and you have 10
  connection pools on the host, now you can have 200  connections max to your
  database.

The stats labeled ``derive`` are floating point values representing a
**rate** of activity.   sqlalchemy-collectd sends these numbers to the
collectd server as a total number of events occurred as of a specific
timestamp; collectd then compares this to the previous value to determine
the rate.  How the rate is reported (e.g. number per second, etc.) depends
on the reporting tools being used.

* ``derive-checkouts`` - rate of connections being checked out.

* ``derive-connects`` - rate of new connections made to the database

* ``derive-disconnects`` - rate of database connections being closed

* ``derive-invalidated`` - rate of connections that are explicitly **invalidated**,
  e.g. have encountered a connectivity error which made the program invalidate
  the connection.  The application may or may not have tried to connect
  again immediately depending on how it is using this feature.  See the
  section on "invalidated connections" below for details on this.

* ``derive-commits`` - (TODO: not implemented yet) rate of calls to ``transaction.commit()``.  This value
  can be used to estimate TPS, e.g. transactions per second, however note that
  this is limited to SQLAlchemy-explicit transactions where the Engine-level
  begin() / commit() methods are being invoked.   When using the SQLAlchemy
  ORM with the ``Session``, this rate should be tracking the rate of
  calls to ``Session.commit()``.

* ``derive-rollbacks`` - (TODO: not implemented yet) rate of calls to ``transaction.rollback()``.

* ``derive-transactions`` - (TODO: not implemented yet) rate of transactions overall.  This should add up
  to the commit and rollback rates combined, however may be higher than that
  if the application also discards transactions and/or ``Session`` objects
  without calling ``.commit()`` or ``.rollback()``.

Invalidated Connections
-----------------------

The ``derive-invalidated`` stat records the rate of invalidations.

By invalidated, we mean the ``.invalidated()`` method on the connection
is called, which marks this connection as no longer usable and marks it
for refresh on next use (soft invalidation) or more commonly closes it
immediately (hard invalidation).   Typically, when a connection is invalidated,
the application is either pre-pinging the database and will try to connect
again, or it was in the middle of an operation when the database got
cut off, in which case depending on how the application was designed it
may or may not try the operation again.

Invalidation usually corresponds to a
connection that reported a problem in being able to communicate with the
database, and for which an error was raised.  For this reason, the
"invalidated" rate should be considered to be roughly an "error" rate -
each count here usually corresponds to a connectivity error encountered by the
application to which it responded by invalidating the connection, which results
either in immediate or eventual reconnection.

For most invalidation scenarios, the entire pool of connections is
invalidated at once using a "freshness" timestamp; any connection older than
this timestamp is refreshed on next use.  This is to suit the case of assuming
that the database was probably restarted, so all connections need to be
reconnected.  These connections which have been **implicitly** invalidated
are **not** included in this count.

Collectd Types
--------------

These funny names ``count-`` and ``derive-`` are an artifact of how
collectd provides *types*.  collectd has a fixed list of "types" which it
lists in a file called ``types.db``. The server does not accept type names
that are not either in this file or in a separately configured custom types file,
as each type is accompanied by a template for what kinds of values it
carries.  Annoyingly, collectd does not let us add these names within the
regular .conf file, which would make it very easy for us to include
our own custom names; it instead requires they be listed in completely separate file that must be
explicitly referred to by absolute path within a conf file, and then to
make matters worse when this option is used, we have to uncomment the location
of the default types.db file in the central collectd.conf else it will
no longer be able to find it.  Given the choice between "very nice names"
and "no need to set up three separate config files", we chose the latter :)

connmon mode
============

As an added feature, the **connmon** UX has now been integrated into SQLAlchemy-collectd.
This is a console application that displays a "top"-like display of the current
status of connections.

Using the configuration above, we can add a a plugin configuration for the
connmon server plugin::


    LoadPlugin python
    <Plugin python>
        LogTraces true

        Import "sqlalchemy_collectd.server.plugin"

        <Module "sqlalchemy_collectd.server.plugin">
            # ipv4 only for the moment
            listen "0.0.0.0" 25827

            # set to "debug" to show messages received
            loglevel "info"

        </Module>

        Import "sqlalchemy_collectd.connmon.plugin"
        <Module "sqlalchemy_collectd.connmon.plugin">
            monitor "localhost" 25828

            # set to "debug" to show messaging
            #loglevel "debug"
        </Module>

    </Plugin>

We can now run "connmon" on localhost port 25828::

    connmon --port 25828

The connmon plugin and command line tool as of version 0.6 works independently
of the "server" plugin, and may be configured by itself without the server
plugin being present.  It now consumes sqlalchemy-collectd events not only from
the local server plugin if present, but from also from any other
sqlalchemy-collectd messages that are forwarded to the server from elsewhere,
typically via the "network" plugin.

Screenshot of connmon:

|connmon_screenshot|

.. |connmon_screenshot| image:: connmon.png
   :width: 800

The SQLAlchemy Project
======================

SQLAlchemy-collectd is part of the `SQLAlchemy Project <https://www.sqlalchemy.org>`_ and
adheres to the same standards and conventions as the core project.

Development / Bug reporting / Pull requests
--------------------------------------------

Please refer to the
`SQLAlchemy Community Guide <https://www.sqlalchemy.org/develop.html>`_ for
guidelines on coding and participating in this project.

Code of Conduct
---------------

Above all, SQLAlchemy places great emphasis on polite, thoughtful, and
constructive communication between users and developers.
Please see our current Code of Conduct at
`Code of Conduct <https://www.sqlalchemy.org/codeofconduct.html>`_.

License
=======

SQLAlchemy-collectd is distributed under the `MIT license
<https://opensource.org/licenses/MIT>`_.