import random
import unittest

from .. import stream


class TimeBucketTest(unittest.TestCase):
    def _generate(self, interval):
        current = random.randint(729404, 930285)

        for i in range(200):
            yield current
            current += random.randint(0, interval // 2)

    def test_no_conflicting_intervals(self):
        agg = stream.TimeBucket(4)
        agg.put(50530, 10, "key", "value_50530")
        self.assertRaises(ValueError, agg.put, 50530, 15, "key", "value_50530")

    def test_put(self):
        agg = stream.TimeBucket(4)
        interval = 5
        agg.put(50530, interval, "key", "value_50530")

        self.assertEqual(agg.get(50532, "key"), "value_50530")

        agg.put(50534, interval, "key", "value_50534")
        self.assertEqual(agg.get(50535, "key"), "value_50534")

        self.assertEqual(agg.get(50538, "key"), "value_50534")

        # bucket has expired with this timestamp
        self.assertEqual(agg.get(50542, "key"), None)

        # but we can still see it w/ recent timestamp
        self.assertEqual(agg.get(50539, "key"), "value_50534")

        # current bucket
        agg.put(50545, interval, "key", "value_50545")

        # bump
        agg.put(50556, interval, "key", "value_50556")

        # still see old value
        self.assertEqual(agg.get(50539, "key"), "value_50534")

        # bump
        agg.put(50562, interval, "key", "value_50562")

        # still see old value
        self.assertEqual(agg.get(50539, "key"), "value_50534")
        self.assertEqual(agg.get_data(50539)["key"], "value_50534")

        # bump
        agg.put(50574, interval, "key", "value_50574")

        # now it's gone
        self.assertRaises(KeyError, agg.get_data, 50539)

    def test_series(self):
        agg = stream.TimeBucket(4)
        previous_time = None
        for round_, time in enumerate(self._generate(10)):
            if round_ % 4 == 1:
                value = agg.get(time, "key", interval=5)
                if value is None:
                    assert previous_time // 10 != time // 10
                else:
                    assert previous_time // 10 == time // 10
                    self.assertEqual(
                        max(
                            [
                                bucket["data"].get("key", "")
                                for bucket in agg.buckets
                            ]
                        ),
                        value,
                    )
            else:
                agg.put(time, 5, "key", "value_%s" % time)
            previous_time = time
