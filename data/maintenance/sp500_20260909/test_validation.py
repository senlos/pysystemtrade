"""Offline tests of audit assertions. No broker or production writes."""
import unittest
import pandas as pd
from data.maintenance.sp500_20260909.run_validation import compare, quality


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = pd.DataFrame({'PRICE': [100., 101.]}, index=pd.date_range('2026-09-03', periods=2))

    def test_parquet_resolution_and_column_order_are_not_revisions(self) -> None:
        before = self.before.assign(FORWARD=102.)
        after = before[['FORWARD', 'PRICE']].copy()
        after.index = after.index.as_unit('us')
        self.assertEqual(compare(before, after)['changed_existing_timestamps'], [])

    def test_revision_rejected(self) -> None:
        after = self.before.copy()
        after.iloc[0, 0] = 99.
        with self.assertRaises(AssertionError):
            compare(self.before, after)

    def test_deletion_rejected(self) -> None:
        with self.assertRaises(AssertionError):
            compare(self.before, self.before.iloc[1:])

    def test_duplicate_rejected(self) -> None:
        with self.assertRaises(AssertionError):
            quality(pd.concat([self.before, self.before]))

    def test_empty_initial_history(self) -> None:
        self.assertEqual(compare(pd.DataFrame(), self.before)['rows_added'], 2)

    def test_bad_ohlc_rejected(self) -> None:
        with self.assertRaises(AssertionError):
            quality(pd.DataFrame({'OPEN': [100], 'HIGH': [99], 'LOW': [98], 'FINAL': [100], 'VOLUME': [1]}))


if __name__ == '__main__':
    unittest.main()
