from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from project.notebooks.research.small_account_diagnostics import (
    diagnostics_long,
    enrich_position_frames,
    phase_transition_table,
)


class DiagnosticHelpersTest(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2024-01-01", periods=3, freq="B")
        self.columns = ["A", "B"]
        self.continuous = pd.DataFrame(
            [[0.2, -0.4], [0.7, -1.2], [1.4, -0.8]],
            index=self.index,
            columns=self.columns,
        )

    def test_enrich_position_frames(self):
        optimised = pd.DataFrame(
            [[0, 0], [1, -1], [1, -1]], index=self.index, columns=self.columns
        )
        frames = {
            "continuous_position": self.continuous,
            "per_contract_value_fraction": pd.DataFrame(
                0.1, index=self.index, columns=self.columns
            ),
            "annual_pct_vol_fraction": pd.DataFrame(
                0.2, index=self.index, columns=self.columns
            ),
        }
        result = enrich_position_frames(frames, optimised)
        self.assertEqual(result["previous_integer_position"].iloc[0, 0], 0)
        self.assertEqual(result["position_change"].iloc[1, 0], 1)
        self.assertEqual(result["nearest_integer_position"].iloc[1, 0], 1)
        self.assertEqual(result["toward_zero_position"].iloc[1, 1], -1)
        self.assertAlmostEqual(
            result["instrument_tracking_error_risk_fraction"].iloc[2, 0],
            (1.4 - 1.0) * 0.1 * 0.2,
        )

    def test_diagnostics_long(self):
        long = diagnostics_long({"target": self.continuous, "actual": self.continuous.round()})
        self.assertEqual(long.index.names, ["date", "instrument"])
        self.assertEqual(long.shape, (6, 2))
        self.assertAlmostEqual(long.loc[(self.index[0], "A"), "target"], 0.2)

    def test_phase_transition_table(self):
        low = pd.DataFrame([[0, 1]], columns=self.columns)
        high = pd.DataFrame([[1, 1]], columns=self.columns)
        table = phase_transition_table({25_000.0: low, 100_000.0: high})
        self.assertEqual(table.loc[25_000.0, "active_markets"], 1)
        self.assertEqual(table.loc[100_000.0, "newly_active"], "A")


if __name__ == "__main__":
    unittest.main()
