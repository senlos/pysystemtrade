# SP500 production maintenance validation — September 9, 2026

Completed A/B/C: normal DAILY ingestion validated, continuous prices updated,
and September roll readiness established. No roll executed.

## Scope and normal workflow

The contract-price updater samples MongoDB metadata, not the bounded bootstrap
calendar. Initial SP500 metadata was empty (BLOCKER, resolved with the normal
SP500-only sampled-contract updater). Its native chain includes September 2026,
December 2026 and March 2027; March is collected ahead of the next roll.

The standard instrument wrapper requests both intraday and daily data. This
bounded operation invoked its existing frequency-specific function with DAILY
only, then its existing merged-price writer with a daily-only list. Preflight
verified stored daily and merged histories were equal. These are the normal
maintenance functions; no bootstrap/seed/replacement acquisition was invoked.

IB requests used ES CME/USD/50 contracts ESU6 (649180671), ESZ6 (515416632),
ESH7 (649180684): 1 Y, 1 day, TRADES, useRTH=True, endDateTime='', formatDate=2,
20-second timeout. Five historical requests total, including two September
retries after audit-driver errors. Responses ended September 8; no September 7
bar was returned. Native cleaning and spike checks remained enabled. Requests
and latest raw responses are saved alongside validation.json.

Native merge accepts timestamps strictly newer than the existing latest date.
It ignores overlapping IB revisions and does not backfill older gaps. Parquet
files are physically rewritten, but their prior history is preserved. Native
multiple-price maintenance uses current leg IDs; native adjusted-price maintenance
rejects an unregistered roll before either derived output is written.

## Persistence scope

MongoDB localhost production: created futures_contracts records keyed by
SP500/20260900, SP500/20261200, SP500/20270300, including actual expiries and
sampling flags. IBClientTracker temporarily locked/released client_id=100.
No roll-state record was written. Existing locks 106/107/108 were untouched.

Under D:/dev/pysystemtrade/data/parquet, exactly these files changed or were created:

- futures_contract_prices/Day@SP500#20260900.parquet
- futures_contract_prices/SP500#20260900.parquet
- futures_contract_prices/Day@SP500#20261200.parquet
- futures_contract_prices/SP500#20261200.parquet
- futures_contract_prices/Day@SP500#20270300.parquet
- futures_contract_prices/SP500#20270300.parquet
- futures_multiple_prices/SP500.parquet
- futures_adjusted_prices/SP500.parquet

Before snapshots and SHA256 comparisons verify June, FX, unrelated Parquet data
and all bootstrap evidence stayed unchanged. No account/risk/strategy/capital
configuration or production Python module was changed. IB connections used
readonly=True, order submission was guarded, and email was disabled in the audit.

## Before/after results

| Dataset | Previous latest | New latest | Rows added | Total |
|---|---|---|---:|---:|
| September daily/merged | September 4 23:00 | September 8 23:00 | 1 | 131 |
| December daily/merged | September 4 23:00 | September 8 23:00 | 1 | 252 |
| March daily/merged | Absent | September 8 23:00 | 250 | 250 |
| Multiple | September 4 23:00 | September 8 23:00 | 1 | 99 |
| Adjusted | September 4 23:00 | September 8 23:00 | 1 | 99 |

All existing timestamps/values preserved; zero deletions, duplicates, nulls,
nonfinite values, invalid OHLC or negative volumes. Daily and merged readbacks
match. Latest PRICE=7680.50, FORWARD=CARRY=7747.25, adjusted=7680.50.
All historical leg values match their persisted contract sources. Independent
Panama arithmetic retains +60.25 before the June roll. The sole PRICE-contract
switch still first appears on June 11 (following June 10 roll observation).

## September roll readiness

- Current state No_Roll; PRICE September, FORWARD/CARRY December.
- Next PRICE December; next FORWARD/CARRY March 2027, already sampled and stored.
- HMUZ hold/priced cycle, carry offset +1, roll offset -5 calendar days,
  approximate expiry offset 14 unchanged. Production actual expiry September 18
  gives desired roll September 13 (Sunday). Review window September 11-14;
  this is an operational review window, not a configured business-day adjustment.
- September/December: 130 overlapping daily rows, 119 with positive volume in
  both legs. December/March: 250 overlaps, 40 with positive volume in both.
  Latest matched observation is September 8 for all legs.
- Latest volumes: September 1,088,909; December 8,768; March 4. March is thin.
- Native smoothed forward/price volume ratio 0.005172; forward volume 6091.26.
  Configured liquidity requires ratio >1, or ratio >0.01 AND volume >100.
  Current liquidity test fails. Desired calendar roll date is not yet due.
- Native near-roll threshold is 10 days. Its optional auto-selector would suggest
  No_Open while near the roll with an illiquid forward. We did not invoke it or
  alter risk/execution state. If forward becomes liquid and no priced position
  exists, that workflow can propose Roll_Adjusted even before the desired date;
  position-dependent execution states belong to later order-capable work.
- Continue DAILY refreshes of the three sampled contracts; recheck fresh matched
  prices, liquidity and the actual roll date. Use the explicit SP500 production
  roll workflow to register the transition when appropriate. No additional month
  is needed before this roll. Do not install the bounded bootstrap calendar.

## Issue classification and checks

- BLOCKER resolved: absent sampling metadata.
- MATERIAL BUT NON-BLOCKING: March thin/zero-volume history and current December
  liquidity below configured threshold; documented in IB-HIST-003. Mechanical
  coverage passes, but future carry freshness needs checking.
- MATERIAL BUT NON-BLOCKING: bootstrap all-session versus maintenance RTH settings;
  documented as DATA-MAINT-001. Latest roll inputs share production settings.
- INFORMATIONAL: IB 2104/2106/2158 farm-status OK messages and pacing pauses.
  No broker request failures or price-spike errors occurred.
- INFORMATIONAL: audit-driver errors involved ns/us timestamp labels, adjusted
  Series naming and swapped positional arguments. Corrected using normalized
  comparisons and named arguments; retained logs explain retries. No erroneous
  derived file was written. September retries added zero further rows.
- Six offline audit tests and five existing offline bootstrap tests passed.
  Independent persisted-history/leg/Panama/overlap checks passed. Git diff checked;
  pre-existing notebook/basesystem edits left untouched. No new project decision.

Next subtask: bounded SP500 roll review around September 11-14 with fresh data,
then explicit roll registration when appropriate. Paper-account verification and
broker_account correction remain separate prerequisites before order-capable work.
