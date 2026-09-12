"""Read-only final verification from preserved pre-roll inputs; never repeats a roll."""
import json
from unittest.mock import patch
import numpy as np
import pandas as pd
from ib_async import IB
from sysdata.data_blob import dataBlob
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.adjusted_prices import futuresAdjustedPrices
from sysobjects.production.roll_state import RollState
from sysproduction.data.prices import diagPrices
from sysproduction.data.sim_data import get_sim_data_object_for_production
from sysproduction.reporting.data.rolls import rollingAdjustedAndMultiplePrices
from sysproduction.interactive_update_roll_status import setup_roll_data_with_state_reporting
from data.maintenance.sp500_20260912.run_validation import ROOT, STORE, quality, files
from data.maintenance.sp500_20260912.roll import forbid, normalized


def main() -> None:
    report = json.loads((ROOT / 'roll_result.json').read_text())
    with patch.object(IB, 'connect', forbid), patch.object(IB, 'placeOrder', forbid), dataBlob() as data:
        calc = rollingAdjustedAndMultiplePrices(data, 'SP500')
        calc._current_multiple_prices = futuresMultiplePrices(pd.read_parquet(ROOT / 'pre_roll_multiple.parquet'))
        calc._current_adjusted_prices = futuresAdjustedPrices(pd.read_parquet(ROOT / 'pre_roll_adjusted.parquet').squeeze())
        expected_m, expected_a = calc.updated_multiple_prices, calc.new_adjusted_prices
        prices = diagPrices(data)
        actual_m, actual_a = prices.get_multiple_prices('SP500'), prices.get_adjusted_prices('SP500')
        pd.testing.assert_frame_equal(normalized(actual_m), normalized(expected_m))
        pd.testing.assert_frame_equal(normalized(actual_a), normalized(expected_a))
        np.testing.assert_allclose(actual_a.iloc[:-1], calc.current_adjusted_prices + 67.5, rtol=0, atol=1e-9)
        assert actual_a.iloc[-1] == actual_a.iloc[-2] == 7740.0
        state = setup_roll_data_with_state_reporting(data, 'SP500')
        assert state.original_roll_status == RollState.No_Roll and state.position_priced_contract == 0
        assert dict(actual_m.current_contract_dict()) == dict(PRICE='20261200', FORWARD='20270300', CARRY='20270300')
        sim = get_sim_data_object_for_production(data)
        assert sim.get_raw_price('SP500').iloc[-1] == 7740.0
        assert len(sim.get_instrument_raw_carry_data('SP500')) == 103
        maintenance = json.loads((ROOT / 'validation.json').read_text())
        changed = [p for p, h in files().items() if maintenance['hashes_after'].get(p) != h]
        assert set(changed) == {str(STORE / kind / 'SP500.parquet') for kind in ('futures_multiple_prices', 'futures_adjusted_prices')}
        clients = list(data.mongo_db.db.IBClientTracker.find({}, {'_id': 0}))
        assert clients == maintenance['prices_client_ids_after']
        report.update(status='PASS', audit_error_resolved='Normalized Series column name and timestamp precision; read-only recheck, no roll repeated',
                      persisted_readback=True, strategy_data_readable=True,
                      multiple_quality=quality(pd.DataFrame(actual_m)), adjusted_quality=quality(actual_a.to_frame()),
                      final_roll_state='No_Roll', client_ids_unchanged=True, changed_files=changed,
                      verified_at=str(pd.Timestamp.now()))
    (ROOT / 'post_roll_validation.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')


if __name__ == '__main__':
    main()
