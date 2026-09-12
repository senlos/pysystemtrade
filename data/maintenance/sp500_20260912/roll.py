"""Guarded SP500 normal roll and independent persisted validation; no broker access."""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from ib_async import IB
from sysdata.data_blob import dataBlob
from sysdata.parquet.parquet_access import ParquetAccess
from sysobjects.production.roll_state import RollState
from sysproduction.data.prices import diagPrices
from sysproduction.data.sim_data import get_sim_data_object_for_production
from sysproduction.reporting.data.rolls import rollingAdjustedAndMultiplePrices
from sysproduction.interactive_update_roll_status import (
    setup_roll_data_with_state_reporting, get_auto_roll_parameters_potentially_using_default,
    suggest_roll_state_for_instrument, modify_roll_state,
)
from data.maintenance.sp500_20260912.run_validation import ROOT, STORE, quality, files


def forbid(*args, **kwargs):
    raise RuntimeError('Broker access and interactive fallback forbidden for this roll')


def normalized(value):
    result = pd.DataFrame(value).copy()
    if isinstance(value, pd.Series):
        result.columns = ['price']
    result.index = result.index.as_unit('ns')
    return result


def main(execute: bool = False) -> None:
    report = {}
    output = ROOT / ('roll_result.json' if execute else 'roll_preview.json')
    original_write = ParquetAccess.write_data_given_data_type_and_identifier
    expected = {}

    def guarded_write(self, data_to_write, data_type, identifier):
        assert execute and identifier == 'SP500' and data_type in expected
        pd.testing.assert_frame_equal(normalized(data_to_write), normalized(expected[data_type]), check_dtype=False)
        return original_write(self, data_to_write, data_type, identifier)

    try:
        with patch.object(IB, 'connect', forbid), patch.object(IB, 'placeOrder', forbid), \
             patch('builtins.input', forbid), \
             patch.object(ParquetAccess, 'write_data_given_data_type_and_identifier', guarded_write), \
             dataBlob(log_name='SP500-normal-roll') as data:
            db = data.mongo_db.db
            def mongo_snapshot() -> dict:
                return {name: list(db[name].find({})) for name in db.list_collection_names()}
            mongo_before = mongo_snapshot()
            hashes_before = files()
            native = setup_roll_data_with_state_reporting(data, 'SP500')
            params = get_auto_roll_parameters_potentially_using_default(data, use_default=True)
            assert native.original_roll_status == RollState.No_Roll
            assert native.position_priced_contract == 0
            assert suggest_roll_state_for_instrument(native, params) == RollState.Roll_Adjusted
            calc = rollingAdjustedAndMultiplePrices(data, 'SP500', allow_forward_fill=False)
            old_m, old_a = calc.current_multiple_prices, calc.current_adjusted_prices
            new_m, new_a = calc.updated_multiple_prices, calc.new_adjusted_prices
            assert dict(old_m.current_contract_dict()) == dict(PRICE='20260900', FORWARD='20261200', CARRY='20261200')
            assert dict(new_m.current_contract_dict()) == dict(PRICE='20261200', FORWARD='20270300', CARRY='20270300')
            assert len(new_m) == len(old_m) + 1
            pd.testing.assert_frame_equal(normalized(new_m.iloc[:-1]), normalized(old_m))
            differential = float(old_m.FORWARD.iloc[-1] - old_m.PRICE.iloc[-1])
            np.testing.assert_allclose(new_a.iloc[:-1], old_a + differential, rtol=0, atol=1e-9)
            assert new_a.iloc[-1] == new_a.iloc[-2] == new_m.PRICE.iloc[-1]
            assert new_m.index[-1] == old_m.index[-1] + pd.Timedelta(seconds=1)
            for leg, contract in [('PRICE', '20261200'), ('FORWARD', '20270300'), ('CARRY', '20270300')]:
                source = pd.read_parquet(STORE / f'futures_contract_prices/SP500#{contract}.parquet')
                assert new_m[leg].iloc[-1] == source.loc[old_m.index[-1], 'FINAL']
            expected.update(futures_multiple_prices=pd.DataFrame(new_m),
                            futures_adjusted_prices=new_a.to_frame(name='price'))
            report.update(measured_at=str(pd.Timestamp.now()), differential=differential,
                          source_timestamp=str(old_m.index[-1]), roll_timestamp=str(new_m.index[-1]),
                          latest=new_m.iloc[-1].to_dict(), latest_adjusted=float(new_a.iloc[-1]),
                          multiple_quality=quality(pd.DataFrame(new_m)),
                          adjusted_quality=quality(new_a.to_frame()), native_inputs=vars(native))
            if execute:
                assert not (ROOT / 'pre_roll_multiple.parquet').exists(), 'Single-use roll audit'
                old_m.to_parquet(ROOT / 'pre_roll_multiple.parquet')
                old_a.to_frame(name='price').to_parquet(ROOT / 'pre_roll_adjusted.parquet')
                modify_roll_state(data, 'SP500', native.original_roll_status,
                                  RollState.Roll_Adjusted, confirm_adjusted_price_change=False)
                with dataBlob(log_name='SP500-roll-readback') as fresh:
                    prices = diagPrices(fresh)
                    pd.testing.assert_frame_equal(normalized(prices.get_multiple_prices('SP500')), normalized(new_m))
                    pd.testing.assert_frame_equal(normalized(prices.get_adjusted_prices('SP500')), normalized(new_a))
                    assert setup_roll_data_with_state_reporting(fresh, 'SP500').original_roll_status == RollState.No_Roll
                    sim = get_sim_data_object_for_production(fresh)
                    assert sim.get_raw_price('SP500').iloc[-1] == new_a.iloc[-1]
                    assert len(sim.get_instrument_raw_carry_data('SP500')) == len(new_m)
                assert mongo_snapshot() == mongo_before, 'Unexpected Mongo state change'
                changed = [p for p, h in files().items() if hashes_before.get(p) != h]
                assert set(changed) == {str(STORE / kind / 'SP500.parquet') for kind in expected}
                report.update(persisted_readback=True, strategy_data_readable=True,
                              mongo_unchanged=True, changed_files=changed, final_roll_state='No_Roll')
            report['status'] = 'PASS'
    except Exception as error:
        logging.exception('SP500 roll audit failed')
        report.update(status='FAIL', error=repr(error))
        raise
    finally:
        output.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


if __name__ == '__main__':
    main(execute='--execute' in sys.argv)
