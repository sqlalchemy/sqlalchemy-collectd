
==========
Changelog
==========

.. changelog::
    :version: 0.1.0
    :include_notes_from: unreleased_changes

.. changelog::
    :version: 0.0.8
    :released: January 6, 2022

    .. change::
        :tags: bug
        :tickets: 11

        Fixed bug where the argument signature for the invalidate event handler
        incorrectly formed, preventing invalidation events from being intercepted
        correctly.  Pull request courtesy Dmitry Kulagin.

.. changelog::
    :version: 0.0.7
    :released: June 14, 2021

    .. change::
        :tags: change

        Updated the SQLAlchemy plugin to accommodate for changes
        to the URL object in SQLAlchemy 1.4.


.. changelog::
    :version: 0.0.6
    :released: November 21, 2019

    .. change::
        :tags: bug
        :tickets: 9

        The "pid" value that is collected by the client plugin and passed to the
        aggregator in order to disambiguate separate processes is now augmented
        by a six character random hex string, so that a single host that may have
        the same pid repeated, such as when process namespaces or containers are
        used, sends correct statistics for the same program name configuration.


    .. change::
        :tags: feature

        Made large improvements to the connmon display, including a help screen,
        switching between program / host stats, and new stats views.   Overall, as
        connmon is attempting to collect from collectd servers which may also be in
        a network of servers, the "interval" by which messages are received may be
        long, ten seconds by default and much more. To allow a console view to be
        meaningful, new stats are added that illustrate how many connects /
        checkouts have occurred over the last "interval".  That way, even though
        you might never see the current number of "checkouts" go above zero, you
        can at least see that the last ten second interval had 25 checkouts occur.
        The checkouts per second number can be derived from other values shown in
        the display.


    .. change::
        :tags: bug
        :tickets: 7

        Fixed bug where the command line options to connmon didn't work due to
        incorrect argument signature for the main() function.

    .. change::
        :tags: bug
        :tickets: 8

        The "connmon" tool can now display stats for SQLAlchemy stats that are sent
        to a collectd server via the "network" plugin or through any other means.
        Previously, the connmon tool could only display stats for messages that
        were sent to a the collectd server by the SQLAlchemy-collectd plugin
        itself.

        The server side configuration for "connmon" is now separate from that of
        the SQLAlchemy-collectd plugin, and the two plugins can run independently
        of each other.  This allows for a configuration where many hosts send
        SQLAlchemy-collectd messages to local collectd servers for aggregation, and
        those servers then pass their messages onto another collectd server, where
        the "connmon" tool can provide a view inside the current stats.

        In order to achieve this, major refactoring such that the internals now
        deal with data in terms of a structure which mirrors the collectd-python
        "Values" object is in place, along with a rearchitecture of the connmon
        tool such that it now consumes collectd "Values" objects from a particular
        collectd server regardless of how those "Values" arrived in that server.


.. changelog::
    :version: 0.0.5
    :released: August 5, 2019

    .. change::
        :tags: bug, setup
        :tickets: 6

        Reorganized the tox.ini script so that a plain run of ``tox`` will run
        against a single interpreter.  The "python setup.py test" command is
        no longer supported by setuptools and now emits a message that ``tox``
        should be used.

    .. change::
        :tags: bug, protocol
        :tickets: 4

        Added additional resiliency to the network protocol, such that if an
        entirely garbled message is sent to the server (such as making a test
        connection with nc and sending random characters), the protocol parser
        reports that the message is invalid rather than producing KeyError due to
        not being able to locate a message type.

    .. change::
        :tags: bug
        :tickets: 5

        Added error resiliency to the server and client threads, so that exceptions
        which occur are logged and the thread continues to run. Additionally, fixed
        the logging handler in the server plugin so that stack traces for errors
        are added to the output.

    .. change::
        :tags: bug, config
        :tickets: 3

        Fixed bug where the port number included in the SQLAlchemy URL with the
        collectd_port query string value would not be coerced into an integer,
        failing when it is passed to the socket send operation.

.. changelog::
    :version: 0.0.4
    :released: May 29, 2019

    .. change::
        :tags: feature

        The connmon real-time console UX, first developed as its own client/server
        project, has now been migrated to SQLAlchemy-collectd, consuming collectd
        events over UDP from the collectd server itself which runs the
        SQLAlchemy-collectd plugin.   This greatly reduces the footprint and
        complexity of the previous connmon implementation and allows applications
        to be monitored both by traditional collectd consumers as well as the
        connmon console for a quick "top" of connection activity.  See the
        "helloworld" example for further details.

.. changelog::
    :version: 0.0.3
    :released: November 27, 2018

    .. change::
       :tags: change

       Included tests within the Pypi release, establihsed a
       package manifest as well as added this changelog.



