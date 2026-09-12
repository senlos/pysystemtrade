"""Offline evidence for the documented boundary; no broker or database creation."""
import datetime
import unittest
from unittest.mock import Mock

from sysexecution.orders.contract_orders import contractOrder, limit_order_type
from sysexecution.stack_handler.create_broker_orders_from_contract_orders import (
    stackHandlerCreateBrokerOrders,
)
from sysobjects.production.trade_limits import tradeLimit
from sysobjects.production.tradeable_object import instrumentStrategy


class FirstPaperBoundaryAudit(unittest.TestCase):
    def test_limit_path_skips_capacity_check(self) -> None:
        handler = object.__new__(stackHandlerCreateBrokerOrders)
        handler.apply_trade_limits_to_contract_order = Mock(
            side_effect=AssertionError("Unexpected capacity check")
        )
        order = contractOrder("audit", "SP500", "20260900", 2,
                              order_type=limit_order_type)
        result = handler.size_contract_order(order)
        self.assertEqual(result.trade.as_single_trade_qty_or_error(), 2)
        handler.apply_trade_limits_to_contract_order.assert_not_called()

    def test_check_does_not_reserve_capacity(self) -> None:
        limit = tradeLimit(1, instrumentStrategy("", "SP500"))
        self.assertEqual(limit.what_abs_trade_is_possible(1), 1)
        self.assertEqual(limit.what_abs_trade_is_possible(1), 1)
        limit.add_trade(1)
        self.assertEqual(limit.what_abs_trade_is_possible(1), 0)

    def test_expired_timestamp_can_discard_new_charge(self) -> None:
        limit = tradeLimit(
            1, instrumentStrategy("", "SP500"),
            last_reset_time=datetime.datetime.now() - datetime.timedelta(days=2),
        )
        limit.add_trade(1)
        self.assertEqual(limit.as_dict()["trades_since_last_reset"], 0)


if __name__ == "__main__":
    unittest.main()
