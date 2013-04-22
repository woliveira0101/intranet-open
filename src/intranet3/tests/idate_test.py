import unittest
import datetime

from intranet3.utils import idate


class IDateTest(unittest.TestCase):

    def test_quarter(self):
        months = [datetime.date(2013, x, 1) for x in range(1, 13)]
        quarters = [idate.quarter_number(date) for date in months]
        self.assertEqual(quarters, [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4])

    def test_next_quater(self):
        self.assertEqual(
            [idate.next_quater(q) for q in [1, 2, 3, 4]],
            [2, 3, 4, 1]

        )

    def test_prev_quater(self):
        self.assertEqual(
            [idate.prev_quater(q) for q in [1, 2, 3, 4]],
            [4, 1, 2, 3],
        )

    def test_months_between(self):
        start = datetime.date(2012, 11, 1)
        end = datetime.date(2013, 5, 1)

        result = idate.months_between(start, end)

        self.assertEqual(
            result,
            [11, 12, 1, 2, 3, 4, 5]
        )