"""Offline tests: no broker connection or production writes."""
import unittest

import numpy as np
import pandas as pd

from sysinit.futures.bootstrap_sp500_first_roll import build_chain, validate_prices


def sample_frames() -> dict:
    result = {}
    for key, offset, end in [("20260600", 0, "2026-06-18"),
                             ("20260900", 60, "2026-09-04"),
                             ("20261200", 120, "2026-09-04")]:
        index = pd.bdate_range("2026-04-17", end) + pd.Timedelta(hours=23)
        price = np.arange(len(index), dtype=float) + 7000 + offset
        result[key] = pd.DataFrame({"OPEN": price, "HIGH": price + 1,
            "LOW": price - 1, "FINAL": price, "VOLUME": 100.0}, index=index)
    return result


class BootstrapTests(unittest.TestCase):
    def test_real_transition_and_panama_adjustment(self) -> None:
        _, multiple, adjusted, report = build_chain(sample_frames())
        self.assertEqual(report["roll_spread"], 60)
        self.assertEqual(multiple.PRICE_CONTRACT.nunique(), 2)
        self.assertEqual(adjusted.iloc[0], 7060)
        self.assertEqual(adjusted.iloc[-1], multiple.PRICE.iloc[-1])

    def test_duplicate_and_unordered_timestamps_block(self) -> None:
        frame = sample_frames()["20260600"]
        for invalid in (pd.concat([frame, frame.iloc[-1:]]), frame.iloc[::-1]):
            with self.assertRaises(ValueError):
                validate_prices(invalid)

    def test_ohlcv_anomaly_is_reported_without_mutation(self) -> None:
        frame = sample_frames()["20260600"]
        frame.iloc[0, frame.columns.get_loc("HIGH")] = 1
        report = validate_prices(frame)
        self.assertEqual(len(report["ohlcv_warning_dates"]), 1)
        self.assertEqual(frame.HIGH.iloc[0], 1)

    def test_zero_volume_warns_but_is_usable(self) -> None:
        frames = sample_frames()
        frames["20261200"]["VOLUME"] = 0
        self.assertGreater(validate_prices(frames["20261200"])["zero_volume_rows"], 0)
        build_chain(frames)

    def test_missing_forward_coverage_blocks(self) -> None:
        frames = sample_frames()
        frames["20261200"] = frames["20261200"].iloc[:3]
        with self.assertRaises(ValueError):
            build_chain(frames)


if __name__ == "__main__":
    unittest.main()
