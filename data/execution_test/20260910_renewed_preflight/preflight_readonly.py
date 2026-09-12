"""Read-only preflight; stops at first failed gate, with no order APIs."""
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from ib_async import IB
from ib_async.ib import StartupFetchNONE
from pymongo import MongoClient
import yaml
from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysobjects.contracts import futuresContract

OUT = Path(__file__).resolve().parents[3] / 'project/data/execution_tests/20260910_renewed_preflight'

def forbidden(*args: object, **kwargs: object) -> None:
    raise RuntimeError('Order mutation forbidden in read-only preflight')

def main() -> None:
    result = {'started': dt.datetime.now().astimezone().isoformat(), 'orders_created': 0, 'submission_attempts': 0,
              'paper_identity': 'Prior handoff confirmation only; current UI not independently verified'}
    ib = IB()
    try:
        config = yaml.safe_load(Path('private/private_config.yaml').read_text())
        result['configured_account'] = config['broker_account']
        result['GMT_offset_hours'] = config['GMT_offset_hours']
        with MongoClient('127.0.0.1', 27017, serverSelectionTimeoutMS=5000) as client:
            db = client['production']
            names = db.list_collection_names()
            selected = [n for n in names if any(s in n.lower() for s in ('position', 'limit', 'lock', 'override', 'roll', 'stack'))]
            result['local_readonly_records'] = {n: list(db[n].find({}, {'_id': 0})) for n in selected}
        with patch.object(IB, 'placeOrder', forbidden), patch.object(IB, 'cancelOrder', forbidden), patch.object(IB, 'reqGlobalCancel', forbidden):
            ib.connect('127.0.0.1', 4002, clientId=19392, readonly=True, timeout=10, fetchFields=StartupFetchNONE)
            result['managed_accounts'] = ib.managedAccounts()
            connection = SimpleNamespace(ib=ib)
            data = SimpleNamespace()
            data.broker_futures_instrument = ibFuturesInstrumentData(connection, data)
            adapter = ibFuturesContractData(connection, data)
            contract = futuresContract('SP500', '20260900')
            details = adapter.ib_client.ib_get_contract_details(adapter.get_contract_object_with_IB_data(contract))
            c = details.contract
            result['contract'] = dict(conId=c.conId, localSymbol=c.localSymbol, exchange=c.exchange, currency=c.currency, multiplier=c.multiplier, expiry=c.lastTradeDateOrContractMonth, minTick=details.minTick)
            result['native_tradable_now'] = adapter.is_contract_okay_to_trade(contract)
            result['effective_hours'] = str(adapter.get_trading_hours_for_contract(contract))
            result['gate_checked_at'] = dt.datetime.now().astimezone().isoformat()
            if not result['native_tradable_now']:
                result.update(status='STOP', blocker='Native tradability gate is False; remaining preflight not completed')
                return
            result.update(status='STOP', blocker='Full preflight and fresh UI identity still required; this diagnostic cannot submit')
    except Exception as exc:
        result.update(status='STOP', blocker=repr(exc))
        raise
    finally:
        ib.disconnect()
        result['disconnected'] = not ib.isConnected()
        result['finished'] = dt.datetime.now().astimezone().isoformat()
        (OUT / 'preflight.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
        print(json.dumps(result, indent=2, default=str))

if __name__ == '__main__':
    main()
