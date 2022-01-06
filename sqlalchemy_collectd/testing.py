class TestBase:
    def assertEqual(self, a, b):
        assert a == b, "%r != %r" % (a, b)

    def assertRaises(self, exc_cls, fn, *arg, **kw):
        try:
            fn(*arg, **kw)
        except exc_cls as err:
            return err
        except:
            raise
        else:
            assert False, "Callable did not raise an exception"
