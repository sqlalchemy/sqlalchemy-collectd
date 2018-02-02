from sqlalchemy.engine import CreateEnginePlugin


class Plugin(CreateEnginePlugin):
    def __init__(self, url, kwargs):
        self.url = url

    def handle_dialect_kwargs(self, dialect_cls, dialect_args):
        """parse and modify dialect kwargs"""

    def handle_pool_kwargs(self, pool_cls, pool_args):
        """parse and modify pool kwargs"""

    def engine_created(self, engine):
        """Receive the :class:`.Engine` object when it is fully constructed.

        The plugin may make additional changes to the engine, such as
        registering engine or connection pool events.

        """


