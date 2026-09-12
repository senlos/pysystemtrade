"""One-off SP500 control configuration and guarded, non-persisting calculation.

Run from repository root with python -m data.execution_controls.validate.
Default is verification only; --configure explicitly installs the three bounds.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ib_async import IB
from pymongo import MongoClient
from sysdata.data_blob import dataBlob
from sysdata.mongodb.mongo_order_stack import mongoOrderStackData
from sysproduction.data.broker import dataBroker
from sysproduction.data.contracts import dataContracts
from sysproduction.data.controls import dataPositionLimits, dataTradeLimits, dataLocks, diagOverrides
from sysproduction.data.positions import diagPositions
from sysobjects.production.tradeable_object import instrumentStrategy
from sysexecution.strategies.classic_buffered_positions import (
    orderGeneratorForBufferedPositions, trade_given_optimal_and_actual_positions,
)
from sysexecution.strategies.strategy_order_handling import orderGeneratorForStrategy


def forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError("Execution and order-stack mutation prohibited")


def hashes() -> dict:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for root in (Path('data/parquet'), Path('private'))
            for p in root.rglob('*') if p.is_file()}


def main(configure: bool = False) -> None:
    db = MongoClient('127.0.0.1', 27017, serverSelectionTimeoutMS=5000).production
    def snapshot() -> dict:
        return {n: list(db[n].find({}, {'_id': 0})) for n in sorted(db.list_collection_names())}
    result = {'mongo_before': snapshot(), 'files_before': hashes()}
    output = Path('project/data/execution_controls/configure_result.json' if configure else 'project/data/execution_controls/verify_result.json')
    original_connect = IB.connect
    def readonly_connect(self: IB, *args: object, **kwargs: object) -> object:
        kwargs['readonly'] = True
        return original_connect(self, *args, **kwargs)
    try:
        with ExitStack() as guards:
            guards.enter_context(patch.object(IB, 'connect', readonly_connect))
            for name in ('placeOrder', 'cancelOrder', 'reqGlobalCancel'):
                guards.enter_context(patch.object(IB, name, forbidden))
            guards.enter_context(patch.object(mongoOrderStackData, '_put_order_on_stack_no_checking', forbidden))
            for name in ('get_and_place_orders', 'submit_order_list', 'submit_order'):
                guards.enter_context(patch.object(orderGeneratorForStrategy, name, forbidden))
            with dataBlob(log_name='SP500ControlsDryRun') as data:
                assert data.config.broker_account == 'DUT077119'
                broker = dataBroker(data)
                conn = data.ib_conn
                assert conn.ib.managedAccounts() == ['DUT077119']
                assert len(broker.get_all_current_contract_positions()) == 0
                assert len(broker.get_list_of_orders()) == 0
                result['broker_actual'] = 0
                result['open_broker_orders'] = 0
                local = diagPositions(data)
                strategy = instrumentStrategy('sp500_target_test', 'SP500')
                actual = local.get_dict_of_actual_positions_for_strategy(strategy.strategy_name)
                position = local.get_current_position_for_instrument_strategy(strategy)
                total = local.get_current_instrument_position_across_strategies('SP500')
                assert position == total == 0
                assert len(local.get_all_current_contract_positions()) == 0
                assert not any('stack' in n.lower() and rows for n, rows in result['mongo_before'].items())
                limits, trades = dataPositionLimits(data), dataTradeLimits(data)
                locks = dataLocks(data)
                override = diagOverrides(data).get_cumulative_override_for_instrument_strategy(strategy)
                assert not locks.is_instrument_locked('SP500') and override.as_numeric_value() == 1.0
                assert str(local.get_roll_state('SP500')) == 'RollState.No_Roll'
                if configure:
                    limits.set_abs_position_limit_for_instrument('SP500', 1)
                    limits.set_position_limit_for_instrument_strategy(strategy, 1)
                    trades.update_instrument_limit_with_new_limit('SP500', 1, 1)
                assert limits.get_maximum_position_contracts_for_instrument_strategy(strategy) == 1
                relevant = trades.db_trade_limit_data.get_trade_limits_for_instrument('SP500')
                assert len(relevant) == 1 and relevant[0].trade_limit == 1 and relevant[0].period_days == 1
                result['trade_limits'] = [x.as_dict() for x in relevant]
                # Read/calculation API only: do not instantiate or run the mutating generator.
                view = SimpleNamespace(data=data, strategy_name=strategy.strategy_name)
                optimal = orderGeneratorForBufferedPositions.get_optimal_positions(view)
                assert set(optimal.lower_positions) == {'SP500'}
                lower, upper = optimal.lower_positions['SP500'], optimal.upper_positions['SP500']
                desired = round(lower) if position < lower else round(upper) if position > upper else position
                result['calculation_before_order_object'] = dict(actual=position, aggregate_actual=total,
                    lower=lower, upper=upper, midpoint=(lower+upper)/2,
                    inside_buffer=lower <= position <= upper, rounded_desired=desired, required_trade=desired-position)
                # Production function creates only an in-memory instrumentOrder, never a stack record.
                order = trade_given_optimal_and_actual_positions(data, strategy.strategy_name, 'SP500', optimal, actual)
                revised = limits.apply_position_limit_to_order(override.apply_override(position, order))
                assert order.is_zero_trade() and revised.is_zero_trade()
                assert trades.what_trade_is_possible_for_strategy_instrument(strategy, revised.trade) == 0
                assert trades.what_trade_qty_possible_for_instrument_strategy(strategy, 2) == 1
                result['decision'] = 'NO TRADE'
                result['in_memory_order'] = str(revised)
                result['priced_contract'] = dataContracts(data).get_priced_contract_id('SP500')
                result['locked'] = locks.is_instrument_locked('SP500')
                result['override'] = diagOverrides(data).get_cumulative_override_for_instrument_strategy(strategy).as_numeric_value()
                assert result['locked'] is False and result['override'] == 1.0
        assert not conn.ib.isConnected()
        result['mongo_after'] = snapshot()
        changed = [n for n in set(result['mongo_before']) | set(result['mongo_after'])
                   if result['mongo_before'].get(n) != result['mongo_after'].get(n)]
        result['changed_collections'] = changed
        assert set(changed) <= ({'position_limit_status', 'limit_status'} if configure else set())
        if configure:
            assert result['mongo_before'].get('position_limit_status', []) == []
            assert result['mongo_before'].get('limit_status', []) == []
        positions = result['mongo_after']['position_limit_status']
        assert len(positions) == 2 and all(p['instrument_code'] == 'SP500' and p['position_limit'] == 1 for p in positions)
        assert len(result['mongo_after']['limit_status']) == 1
        assert result['files_before'] == hashes()
        result['status'] = 'PASS'
    finally:
        output.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        print(json.dumps({k: v for k, v in result.items() if k not in ('files_before', 'mongo_before', 'mongo_after')}, indent=2, default=str))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--configure', action='store_true')
    main(parser.parse_args().configure)
