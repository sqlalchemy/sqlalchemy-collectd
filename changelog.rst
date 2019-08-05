
==========
Changelog
==========

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



