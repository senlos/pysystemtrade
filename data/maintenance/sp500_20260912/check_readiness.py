"""Read-only persisted-history and roll-readiness verification."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from data.maintenance.sp500_20260912.run_validation import ROOT, STORE, REPORT, compare, quality, save
from sysdata.data_blob import dataBlob
from sysproduction.data.contracts import dataContracts
from sysproduction.reporting.data.rolls import (
    relative_volume_in_forward_contract_versus_price, volume_contracts_in_forward_contract,
)
from sysdata.mongodb.mongo_roll_state_storage import mongoRollStateData
from sysproduction.interactive_update_roll_status import (
    setup_roll_data_with_state_reporting, get_auto_roll_parameters_potentially_using_default,
    suggest_roll_state_for_instrument, check_if_forward_liquid,
)


def main() -> None:
    report = json.loads(REPORT.read_text())
    multiple = pd.read_parquet(STORE / 'futures_multiple_prices/SP500.parquet')
    adjusted = pd.read_parquet(STORE / 'futures_adjusted_prices/SP500.parquet')
    for kind, frame in [('futures_multiple_prices', multiple), ('futures_adjusted_prices', adjusted)]:
        before = pd.read_parquet(ROOT / 'before' / kind / 'SP500.parquet')
        report[kind + '_persisted_comparison'] = compare(before, frame)
    source = {date: pd.read_parquet(STORE / f'futures_contract_prices/SP500#{date}.parquet')
              for date in ('20260600', '20260900', '20261200', '20270300')}
    for frame in [multiple, adjusted, *source.values()]:
        frame.index = frame.index.as_unit('ns')
        quality(frame)
    for leg in ('PRICE', 'FORWARD', 'CARRY'):
        for date, group in multiple.groupby(leg + '_CONTRACT'):
            np.testing.assert_array_equal(group[leg].values, source[str(date)].loc[group.index, 'FINAL'].values)
    switches = multiple.index[multiple.PRICE_CONTRACT.ne(multiple.PRICE_CONTRACT.shift())][1:]
    assert len(switches) == 1
    expected = multiple.PRICE.copy()
    expected.loc[expected.index < switches[0]] += 60.25
    np.testing.assert_array_equal(expected.values, adjusted.iloc[:, 0].values)
    report['persisted_all_leg_mappings_and_panama_passed'] = True
    report['registered_transition_timestamps'] = list(map(str, switches))
    report['overlaps'] = {}
    for a, b in [('20260900', '20261200'), ('20261200', '20270300')]:
        joined = source[a].add_suffix('_a').join(source[b].add_suffix('_b'), how='inner')
        positive = joined[(joined.VOLUME_a > 0) & (joined.VOLUME_b > 0)]
        report['overlaps'][a + '_' + b] = dict(rows=len(joined), first=str(joined.index.min()),
            last=str(joined.index.max()), positive_volume_rows=len(positive),
            last_positive_volume=str(positive.index.max()), latest=joined.iloc[-1].to_dict())
    with dataBlob(log_name='SP500-readiness-readonly') as data:
        contracts = dataContracts(data)
        date = contracts.get_contract_date_object_with_roll_parameters('SP500', '20260900')
        next_date = date.next_held_contract()
        relative = relative_volume_in_forward_contract_versus_price(data, 'SP500')
        absolute = volume_contracts_in_forward_contract(data, 'SP500')
        params = data.config.roll_status_auto_update
        native_data = setup_roll_data_with_state_reporting(data, 'SP500')
        native_params = get_auto_roll_parameters_potentially_using_default(data, use_default=True)
        native_suggestion = suggest_roll_state_for_instrument(native_data, native_params)
        report['native_roll_review'] = dict(
            inputs=vars(native_data), parameters=vars(native_params),
            suggestion=str(native_suggestion),
            forward_liquid=bool(check_if_forward_liquid(native_data, native_params)),
        )
        report['readiness'] = dict(current_contracts=dict(contracts.get_current_contract_dict('SP500')),
            roll_state=mongoRollStateData(mongo_db=data.mongo_db).get_roll_state('SP500').name,
            next_price=next_date.date_str, next_forward=next_date.next_held_contract().date_str,
            next_carry=next_date.carry_contract().date_str, desired_roll_date=str(date.desired_roll_date),
            measured_at=str(pd.Timestamp.now()), smoothed_relative_forward_volume=relative,
            smoothed_absolute_forward_volume=absolute, configured_auto_roll_parameters=params,
            forward_liquid=bool(relative > params['auto_roll_if_relative_volume_higher_than'] or
                               (relative > params['min_relative_volume'] and absolute > params['min_absolute_volume'])))
    report['audit_driver_errors_resolved'] = True
    save(report)
    print(json.dumps({k: report[k] for k in ('contracts', 'multiple', 'adjusted', 'latest_multiple',
          'latest_adjusted', 'overlaps', 'readiness', 'native_roll_review', 'registered_transition_timestamps')}, indent=2, default=str))


if __name__ == '__main__':
    main()

