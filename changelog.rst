
==========
Changelog
==========

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



