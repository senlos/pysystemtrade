"""Offline boundary tests: no database, broker or order-stack access."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from sysexecution.strategies.classic_buffered_positions import optimalPositions, trade_given_optimal_and_actual_positions
from sysobjects.production.position_limits import apply_position_limit_to_single_leg_trade
from sysobjects.production.trade_limits import tradeLimit
from sysobjects.production.tradeable_object import instrumentStrategy
from data.execution_controls.validate import forbidden


class BoundaryTests(unittest.TestCase):
    def test_real_buffer_decision(self) -> None:
        bounds = optimalPositions({'SP500': 0.028343866396665925},
            {'SP500': 0.016682764452995776}, {'SP500': 7680.5},
            {'SP500': '20260900'}, {'SP500': None})
        order = trade_given_optimal_and_actual_positions(SimpleNamespace(log=Mock()),
            'sp500_target_test', 'SP500', bounds, {})
        self.assertTrue(order.is_zero_trade())

    def test_position_bound_both_directions(self) -> None:
        for qty in (-2, 2):
            self.assertEqual(apply_position_limit_to_single_leg_trade(0, 1, qty), qty // 2)
        self.assertEqual(apply_position_limit_to_single_leg_trade(1, 1, 1), 0)

    def test_turnover_consumes_capacity(self) -> None:
        limit = tradeLimit(1, instrumentStrategy('', 'SP500'))
        self.assertEqual(limit.what_abs_trade_is_possible(2), 1)
        limit.add_trade(-1)
        self.assertEqual(limit.what_abs_trade_is_possible(1), 0)

    def test_execution_guard_raises(self) -> None:
        with self.assertRaises(AssertionError):
            forbidden()


if __name__ == '__main__':
    unittest.main()
