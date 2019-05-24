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
