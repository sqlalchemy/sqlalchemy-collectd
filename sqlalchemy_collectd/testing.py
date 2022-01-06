class TestBase:
    def assertEqual(self, a, b):
        assert a == b, "%r != %r" % (a, b)
