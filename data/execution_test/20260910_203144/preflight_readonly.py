"""Supplementary read-only gates; never creates or transmits an order."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ib_async import IB
from sysdata.data_blob import dataBlob
from sysobjects.contracts import futuresContract
from sysproduction.data.broker import dataBroker

OUT = Path(__file__).resolve().parents[3] / 'project/data/execution_tests/20260910_203144'

def forbidden(*args: object, **kwargs: object) -> None:
    raise RuntimeError('Order mutation forbidden during preflight')


def main() -> None:
    result = {'started': datetime.now(timezone.utc).isoformat(),
              'paper_identity': 'Fresh user TWS confirmation accepted'}
    original = IB.connect

    def readonly(self: IB, *args: object, **kwargs: object) -> object:
        kwargs['readonly'] = True
        return original(self, *args, **kwargs)

    try:
        with patch.object(IB, 'connect', readonly), patch.object(IB, 'placeOrder', forbidden), patch.object(IB, 'cancelOrder', forbidden), patch.object(IB, 'reqGlobalCancel', forbidden):
            with dataBlob(log_name='ExecutionTestReadOnlyPreflight') as data:
                broker = dataBroker(data)
                ib = data.ib_conn.ib
                result['configured_account'] = data.config.broker_account
                assert result['configured_account'] == 'DUT077119'
                orders = ib.reqAllOpenOrders()
                result['all_client_open_orders'] = [str(t) for t in orders]
                assert not orders, 'Open broker orders exist'
                result['executions'] = [str(f) for f in ib.reqExecutions()]
                assert not result['executions'], 'Fresh executions require review'
                fc = futuresContract('SP500', '20260900')
                enriched = broker.broker_futures_contract_data.get_contract_object_with_IB_data(fc)
                details = broker.broker_futures_contract_data.ib_client.ib_get_contract_details(enriched)
                c = details.contract
                result['contract'] = dict(conId=c.conId, localSymbol=c.localSymbol, exchange=c.exchange, currency=c.currency, multiplier=c.multiplier, expiry=c.lastTradeDateOrContractMonth, minTick=details.minTick)
                assert (c.conId, c.localSymbol, c.exchange, c.currency, c.multiplier, c.lastTradeDateOrContractMonth, details.minTick) == (649180671, 'ESU6', 'CME', 'USD', '50', '20260918', 0.25)
                result['tradable'] = broker.is_contract_okay_to_trade(fc)
                result['trading_hours'] = str(broker.get_trading_hours_for_contract(fc))
                assert result['tradable'], 'Native contract tradability gate failed'
                result['less_than_30_minutes'] = broker.broker_futures_contract_data.less_than_N_hours_of_trading_left_for_contract(fc, N_hours=0.5)
                assert not result['less_than_30_minutes'], 'Less than 30 minutes remaining'
                ticker = ib.reqMktData(c, '', False, False)
                try:
                    deadline = datetime.now(timezone.utc).timestamp() + 15
                    while datetime.now(timezone.utc).timestamp() < deadline:
                        ib.sleep(0.2)
                        if ticker.time and math.isfinite(ticker.bid) and math.isfinite(ticker.ask) and ticker.bid > 0 and ticker.ask >= ticker.bid:
                            break
                    age = (datetime.now(timezone.utc) - ticker.time).total_seconds() if ticker.time else None
                    result['quote'] = dict(bid=ticker.bid, ask=ticker.ask, bidSize=ticker.bidSize, askSize=ticker.askSize, time=ticker.time, age_seconds=age, marketDataType=ticker.marketDataType)
                    assert age is not None and age <= 2 and ticker.marketDataType == 1 and 0 < ticker.bid <= ticker.ask, 'Fresh live bid/ask gate failed'
                finally:
                    ib.cancelMktData(c)
                result['status'] = 'PASS'
            result['disconnected'] = not ib.isConnected()
    except Exception as exc:
        result['status'] = 'STOP'
        result['error'] = repr(exc)
        raise
    finally:
        result['finished'] = datetime.now(timezone.utc).isoformat()
        (OUT / 'supplementary_preflight.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
