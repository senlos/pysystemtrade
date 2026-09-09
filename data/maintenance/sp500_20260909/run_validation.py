"""Bounded audit of existing production functions; run from repository root.

No strategy/order setup. Uses read-only IB connection and a SP500 write allowlist.
Evidence directory is deliberately single-use for the price update.
"""
from __future__ import annotations

import json
import hashlib
import logging
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from ib_async import IB, util

from syscore.constants import success
from syscore.dateutils import DAILY_PRICE_FREQ
from sysdata.data_blob import dataBlob
from sysdata.parquet.parquet_access import ParquetAccess
from sysdata.tools.cleaner import get_config_for_price_filtering
from sysproduction.data.contracts import dataContracts
from sysproduction.data.prices import diagPrices
from sysproduction.update_sampled_contracts import update_active_contracts_for_instrument
import sysproduction.update_historical_prices as historical
from sysproduction.update_multiple_adjusted_prices import (
    calc_updated_multiple_prices, calc_update_adjusted_prices, update_with_new_prices,
)
from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData

ROOT = Path('data/maintenance/sp500_20260909')
STORE = Path('data/parquet')
DATES = {'20260900', '20261200', '20270300'}
REPORT = ROOT / 'validation.json'


def save(report: dict) -> None:
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


def files() -> dict:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for base in (STORE, Path('data/bootstrap')) for p in base.rglob('*') if p.is_file()}


def quality(frame: pd.DataFrame) -> dict:
    result = dict(rows=len(frame), first=str(frame.index.min()), latest=str(frame.index.max()),
                  duplicates=int(frame.index.duplicated().sum()), nulls=int(frame.isna().sum().sum()),
                  ordered=frame.index.is_monotonic_increasing)
    numeric = frame.select_dtypes(include=np.number)
    result['nonfinite'] = int((~np.isfinite(numeric)).sum().sum())
    if {'OPEN', 'HIGH', 'LOW', 'FINAL', 'VOLUME'} <= set(frame.columns):
        result['bad_ohlc'] = int(((frame.HIGH < frame[['OPEN', 'LOW', 'FINAL']].max(axis=1)) |
                                  (frame.LOW > frame[['OPEN', 'HIGH', 'FINAL']].min(axis=1))).sum())
        result['negative_volume'] = int((frame.VOLUME < 0).sum())
        result['zero_volume'] = int((frame.VOLUME == 0).sum())
    assert not any(result.get(k, 0) for k in ('duplicates', 'nulls', 'nonfinite', 'bad_ohlc', 'negative_volume')), result
    assert result['ordered'], result
    return result


def compare(before: pd.DataFrame, after: pd.DataFrame) -> dict:
    before, after = before.copy(), after.copy()
    if isinstance(before.index, pd.DatetimeIndex):
        before.index = before.index.as_unit('ns')
    if isinstance(after.index, pd.DatetimeIndex):
        after.index = after.index.as_unit('ns')
    result = quality(after)
    result.update(previous_latest=str(before.index.max()), rows_added=len(after.index.difference(before.index)),
                  removed_timestamps=len(before.index.difference(after.index)))
    if before.empty:
        result['changed_existing_timestamps'] = []
        return result
    assert set(before.columns) == set(after.columns)
    after = after.reindex(columns=before.columns)
    common = before.index.intersection(after.index)
    changed = ~((before.loc[common] == after.loc[common]) |
                (before.loc[common].isna() & after.loc[common].isna())).all(axis=1)
    result['changed_existing_timestamps'] = [str(x) for x in common[changed]]
    assert result['removed_timestamps'] == 0 and not result['changed_existing_timestamps'], result
    return result


def main(phase: str) -> None:
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    original_connect = IB.connect
    original_write = ParquetAccess.write_data_given_data_type_and_identifier
    original_request = IB.reqHistoricalData
    original_update = historical.price_updating_or_errors

    def readonly(self, *args, **kwargs):
        kwargs['readonly'] = True
        return original_connect(self, *args, **kwargs)

    def guarded_write(self, data_to_write, data_type, identifier):
        allowed = (data_type == 'futures_contract_prices' and
                   identifier in {prefix + 'SP500#' + date for prefix in ('', 'Day@') for date in DATES})
        allowed |= data_type in ('futures_multiple_prices', 'futures_adjusted_prices') and identifier == 'SP500'
        assert allowed, (data_type, identifier)
        return original_write(self, data_to_write, data_type, identifier)

    def request(self, contract, *args, **kwargs):
        assert contract.symbol == 'ES' and kwargs['barSizeSetting'] == '1 day'
        bars = original_request(self, contract, *args, **kwargs)
        raw = util.df(bars)
        assert raw is not None and len(raw), 'Empty IB historical response'
        raw.to_parquet(ROOT / f'{contract.localSymbol}_raw.parquet')
        report.setdefault('requests', []).append(dict(contract=util.dataclassAsDict(contract), **kwargs, rows=len(raw)))
        save(report)
        return bars

    def checked_update(*args, **kwargs):
        quality(pd.DataFrame(kwargs['new_prices_checked']))
        return original_update(*args, **kwargs)

    def no_mail(*args, **kwargs):
        raise RuntimeError('Email disabled for this bounded validation; see local log')

    def no_orders(*args, **kwargs):
        raise RuntimeError('Orders forbidden in data maintenance validation')

    with patch.object(IB, 'connect', readonly), patch.object(IB, 'placeOrder', no_orders), \
         patch.object(IB, 'reqHistoricalData', request), \
         patch.object(ParquetAccess, 'write_data_given_data_type_and_identifier', guarded_write), \
         patch.object(historical, 'price_updating_or_errors', checked_update), \
         patch.object(historical, 'send_production_mail_msg', no_mail):
        data = dataBlob(log_name='SP500-maintenance-validation')
        handler = logging.FileHandler(ROOT / f'{phase}.log', encoding='utf-8')
        logging.getLogger().addHandler(handler)
        db = data.mongo_db.db
        report[f'{phase}_client_ids_before'] = list(db.IBClientTracker.find({}, {'_id': 0}))
        try:
            contracts = dataContracts(data)
            prices = diagPrices(data)
            report['storage'] = str(prices.db_futures_contract_price_data.parquet.accessor._base_path)
            assert Path(report['storage']).resolve() == STORE.resolve()
            if phase == 'metadata':
                report['metadata_before'] = list(db.futures_contracts.find({'contract_key': {'$regex': '^SP500/'}}, {'_id': 0}))
                update_active_contracts_for_instrument('SP500', data)
                sampled = contracts.get_all_sampled_contracts('SP500')
                assert {c.date_str for c in sampled} == DATES
                report['metadata_after'] = [c.as_dict() for c in sampled]
                report['roll_parameters'] = contracts.get_roll_parameters('SP500').as_dict()
                report['desired_roll_date'] = str(contracts.when_to_roll_priced_contract('SP500'))
                report['roll_state'] = mongoRollStateData(mongo_db=data.mongo_db).get_roll_state('SP500').name
                report['cleaning'] = get_config_for_price_filtering(data)._asdict()
            elif phase in ('prices', 'prices_resume', 'derived'):
                if phase == 'prices':
                    assert not (ROOT / 'before').exists(), 'Single-use audit already started'
                    before_hashes = files()
                    report['hashes_before'] = before_hashes
                    for path in before_hashes:
                        source = Path(path)
                        if source.is_relative_to(STORE):
                            target = ROOT / 'before' / source.relative_to(STORE)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(source, target)
                else:
                    assert not report.get('price_update_passed'), 'Audit already completed'
                    before_hashes = report['hashes_before']
                save(report)
                sampled = contracts.get_all_sampled_contracts('SP500')
                assert {c.date_str for c in sampled} == DATES
                if phase == 'derived':
                    assert set(report['contracts']) == DATES
                else:
                    report['contracts'] = {}
                for contract in ([] if phase == 'derived' else sorted(sampled, key=lambda c: c.date_str)):
                    daily_path = ROOT / 'before/futures_contract_prices' / f'Day@SP500#{contract.date_str}.parquet'
                    merged_path = ROOT / 'before/futures_contract_prices' / f'SP500#{contract.date_str}.parquet'
                    daily_before = pd.read_parquet(daily_path) if daily_path.exists() else pd.DataFrame()
                    merged_before = pd.read_parquet(merged_path) if merged_path.exists() else pd.DataFrame()
                    assert daily_before.equals(merged_before), 'Daily-only merge would lose existing intraday data'
                    result = historical.get_and_add_prices_for_frequency(data, contract, DAILY_PRICE_FREQ,
                                get_config_for_price_filtering(data), interactive_mode=False)
                    assert result is success
                    daily_after = pd.DataFrame(prices.get_prices_at_frequency_for_contract_object(contract, DAILY_PRICE_FREQ))
                    assert len(daily_after), 'No persisted daily data'
                    daily_result = compare(daily_before, daily_after)
                    historical.write_merged_prices_for_contract(data, contract, [DAILY_PRICE_FREQ])
                    merged_after = pd.DataFrame(prices.get_merged_prices_for_contract_object(contract))
                    pd.testing.assert_frame_equal(daily_after, merged_after)
                    report['contracts'][contract.date_str] = dict(daily=daily_result, merged=compare(merged_before, merged_after))
                    save(report)
                old_multiple = prices.get_multiple_prices('SP500')
                old_adjusted = prices.get_adjusted_prices('SP500')
                new_multiple = calc_updated_multiple_prices(data, 'SP500')
                new_adjusted = calc_update_adjusted_prices(data, 'SP500', new_multiple)
                report['multiple'] = compare(pd.DataFrame(old_multiple), pd.DataFrame(new_multiple))
                report['adjusted'] = compare(old_adjusted.to_frame(name='price'), new_adjusted.to_frame(name='price'))
                assert old_multiple.current_contract_dict() == new_multiple.current_contract_dict()
                assert new_multiple.index[-1] == new_adjusted.index[-1]
                update_with_new_prices(data, 'SP500', updated_adjusted_prices=new_adjusted,
                                       updated_multiple_prices=new_multiple)
                compare(pd.DataFrame(new_multiple), pd.DataFrame(prices.get_multiple_prices('SP500')))
                compare(new_adjusted.to_frame(name='price'), prices.get_adjusted_prices('SP500').to_frame(name='price'))
                report['latest_multiple'] = new_multiple.iloc[-1].to_dict()
                report['latest_adjusted'] = float(new_adjusted.iloc[-1])
                report['hashes_after'] = files()
                report['changed_files'] = [p for p, h in report['hashes_after'].items() if before_hashes.get(p) != h]
                allowed = {str(STORE / 'futures_contract_prices' / (prefix + 'SP500#' + date + '.parquet'))
                           for prefix in ('', 'Day@') for date in DATES}
                allowed |= {str(STORE / kind / 'SP500.parquet') for kind in ('futures_multiple_prices', 'futures_adjusted_prices')}
                assert set(report['changed_files']) <= allowed
                assert set(before_hashes) <= set(report['hashes_after'])
                report['price_update_passed'] = True
            else:
                raise ValueError(phase)
        except Exception as error:
            logging.exception('SP500 bounded validation failed')
            report[f'{phase}_error'] = repr(error)
            raise
        finally:
            connection = getattr(data, '_ib_conn', None)
            if hasattr(connection, 'client_id'):
                report[f'{phase}_client_id'] = connection.client_id()
            data.close()
            report[f'{phase}_client_ids_after'] = list(db.IBClientTracker.find({}, {'_id': 0}))
            report[f'{phase}_client_ids_released'] = report[f'{phase}_client_ids_before'] == report[f'{phase}_client_ids_after']
            save(report)
            logging.getLogger().removeHandler(handler)
            handler.close()
    print(json.dumps(report, indent=2, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
