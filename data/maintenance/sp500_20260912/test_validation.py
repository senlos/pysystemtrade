"""Offline audit regression tests; no production access."""
import unittest
import pandas as pd
from data.maintenance.sp500_20260909.test_validation import AuditTests
from data.maintenance.sp500_20260912.roll import normalized


class RollAuditTests(unittest.TestCase):
    def test_storage_metadata_normalized(self) -> None:
        original = pd.Series([100.0, 101.0], index=pd.date_range('2026-09-09', periods=2))
        stored = original.rename('price').copy()
        stored.index = stored.index.as_unit('us')
        pd.testing.assert_frame_equal(normalized(original), normalized(stored))

    def test_price_change_still_rejected(self) -> None:
        original = pd.Series([100.0], index=pd.date_range('2026-09-09', periods=1))
        with self.assertRaises(AssertionError):
            pd.testing.assert_frame_equal(normalized(original), normalized(original + 1))


if __name__ == '__main__':
    unittest.main()
