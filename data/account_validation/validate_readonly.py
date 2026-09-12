"""Bounded read-only production broker validation; never generates orders."""
import json
from pathlib import Path
from unittest.mock import patch
from ib_async import IB
from pymongo import MongoClient
from sysdata.data_blob import dataBlob
from sysproduction.data.broker import dataBroker
from sysproduction.data.positions import diagPositions
from sysproduction.data.optimal_positions import dataOptimalPositions
from sysproduction.data.controls import dataPositionLimits, dataTradeLimits, dataLocks, diagOverrides
from sysobjects.production.tradeable_object import instrumentStrategy
from sysobjects.contracts import futuresContract

original_connect = IB.connect

def readonly_connect(self, *args, **kwargs):
    kwargs['readonly'] = True
    return original_connect(self, *args, **kwargs)

def forbidden(*args, **kwargs):
    raise AssertionError('Order-changing API prohibited in read-only validation')

def main() -> None:
    db = MongoClient('127.0.0.1',27017,serverSelectionTimeoutMS=5000).production
    def snapshot():
        return {n:list(db[n].find({}, {'_id':0})) for n in db.list_collection_names()}
    before = snapshot()
    result = {'paper_evidence':'User manually verified current TWS PAPER / Simulated Trading, DUT077119', 'mongo_before':before}
    connection = None
    try:
        with patch.object(IB,'connect',readonly_connect), patch.object(IB,'placeOrder',forbidden), patch.object(IB,'cancelOrder',forbidden), patch.object(IB,'reqGlobalCancel',forbidden):
            with dataBlob(log_name='ReadOnlyAccountValidation') as data:
                broker = dataBroker(data)
                result['configured_account'] = data.config.broker_account
                result['broker_account'] = broker.get_broker_account()
                connection = data.ib_conn
                result['client_id'] = connection.client_id()
                result['managed_accounts'] = connection.ib.managedAccounts()
                assert result['configured_account'] == result['broker_account'] == 'DUT077119'
                assert result['managed_accounts'] == ['DUT077119']
                account = result['broker_account']
                result['capital_by_currency'] = broker.broker_capital_data.get_account_value_across_currency(account)
                result['capital_base'] = broker.get_total_capital_value_in_base_currency()
                result['excess_liquidity_base'] = broker.get_total_excess_liquidity_in_base_currency()
                result['fx_balances'] = broker.broker_fx_balances()
                positions = broker.get_all_current_contract_positions()
                result['futures_positions'] = str(positions)
                assert len(positions) == 0
                all_positions = broker.broker_contract_position_data.ib_client.broker_get_positions(account_id=account)
                result['positions_by_asset'] = all_positions
                stocks = {p['symbol']:p['position'] for p in all_positions.get('STK',[])}
                assert stocks.get('AAPL') == 1 and stocks.get('QQQ') == 100
                result['broker_sp500_actual'] = 0
                orders = broker.get_list_of_orders()
                result['open_orders'] = [str(o) for o in orders]
                result['open_order_count'] = len(orders)
                result['contracts'] = {}
                for month in ['20260900','20261200']:
                    contract = futuresContract('SP500',month)
                    enriched = broker.broker_futures_contract_data.get_contract_object_with_IB_data(contract)
                    details = broker.broker_futures_contract_data.ib_client.ib_get_contract_details(enriched)
                    c = details.contract
                    result['contracts'][month] = {'conId':c.conId,'symbol':c.symbol,'localSymbol':c.localSymbol,'exchange':c.exchange,'currency':c.currency,'multiplier':c.multiplier,'expiry':c.lastTradeDateOrContractMonth,'minTick':details.minTick}
                    assert (c.symbol,c.exchange,c.currency,c.multiplier) == ('ES','CME','USD','50')
                strategy = instrumentStrategy('sp500_target_test','SP500')
                local = diagPositions(data)
                result['local_sp500_actual'] = local.get_current_position_for_instrument_strategy(strategy)
                result['local_contract_positions'] = str(local.get_all_current_contract_positions())
                result['local_strategy_positions'] = str(local.get_all_current_strategy_instrument_positions())
                optimal = dataOptimalPositions(data).get_current_optimal_position_for_instrument_strategy(strategy)
                result['optimal_fields'] = vars(optimal)
                result['optimal_buffer_midpoint'] = (optimal.lower_position+optimal.upper_position)/2
                assert abs(result['optimal_buffer_midpoint']-0.02251331542483085)<1e-12
                assert result['local_sp500_actual'] == 0
                result['controls'] = {'position_limit':str(dataPositionLimits(data).get_maximum_position_contracts_for_instrument_strategy(strategy)), 'trade_limits':str(dataTradeLimits(data).get_all_limits()), 'locked':dataLocks(data).is_instrument_locked('SP500'), 'override':str(diagOverrides(data).get_cumulative_override_for_instrument_strategy(strategy)), 'roll':str(local.get_roll_state('SP500'))}
        result['disconnected'] = not connection.ib.isConnected()
        result['mongo_after'] = snapshot()
        result['mongo_unchanged'] = result['mongo_after'] == before
        assert result['disconnected'] and result['mongo_unchanged']
        result['status'] = 'PASS'
    finally:
        Path('project/data/account_validation/result.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
        print(json.dumps(result,indent=2,default=str))

if __name__ == '__main__':
    main()
