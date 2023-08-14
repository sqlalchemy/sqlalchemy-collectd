import random

from .. import stream
from .. import testing


class TimeBucketTest(testing.TestBase):
    def _generate(self, interval):
        current = random.randint(729404, 930285)

        for i in range(200):
            yield current
            current += random.randint(0, interval // 2)

    def test_put(self) -> None:
        agg: stream.TimeBucket[str, str] = stream.TimeBucket()
        interval = 10
        agg.put(50530, interval, "key", "value_50530")

        self.assertEqual(agg.get(50532, "key"), "value_50530")

        agg.put(50534, interval, "key", "value_50534")
        self.assertEqual(agg.get(50535, "key"), "value_50534")

        self.assertEqual(agg.get(50538, "key"), "value_50534")

        # bucket has expired with this timestamp
        self.assertEqual(agg.get(50568, "key"), None)

        # can't look at previous time now
        self.assertRaises(ValueError, agg.get, 50535, "key")

        agg.put(50570, interval, "key", "value_50545")

        self.assertEqual(agg.get(50570, "key"), "value_50545")
        self.assertEqual(agg.get(50570.375, "key"), "value_50545")
        self.assertEqual(agg.get(50570, "key"), "value_50545")

        # can't see old value
        self.assertRaises(ValueError, agg.get, 50539, "key")

        # bump
        agg.put(50580, interval, "key", "value_50562")

        # can't see old value
        self.assertRaises(ValueError, agg.get, 50539, "key")
