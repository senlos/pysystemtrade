# Current State

## Environment
- Python: .venv-py312
- MongoDB: localhost production
- TWS API connectivity: working
- IB paper account verification: confirmed by user in current TWS PAPER / Simulated Trading UI
- broker_account: DUT077119; corrected and production broker reads validated

## Backtest
- Chapter 15 example runs successfully
- csvFuturesSimData
- six instruments
- net Sharpe ~0.478
- architecture understood sufficiently

## Production Data
- SP500 maps to CME ES
- ESZ6 contract resolved successfully
- one daily Parquet file seeded successfully
- IB historical data may revise retrospectively

## Completed bootstrap (2026-09-09)
- Stop condition A achieved: continuous chain validated in memory, persisted,
  and read back with equality checks. No orders or strategy/capital changes.
- Exact IB CME/USD/50 ES identities: ESM6 649180678 expires 2026-06-18;
  ESU6 649180671 expires 2026-09-18; ESZ6 515416632 expires 2026-12-18.
- Acquired ESM6: 45 raw bars, 44 usable (2026-04-17 through 2026-06-18).
  Excluded one post-expiry zero-volume bar; preserved raw snapshot.
- Acquired ESU6: 130 daily bars, 2026-03-04 through 2026-09-04.
- Reused unchanged ESZ6 seed: 251 bars, 2025-09-08 through 2026-09-04.
- Ordered/unique timestamps, OHLCV checks and coverage checks passed for usable
  inputs; 125 ESZ6 zero-volume observations remain a documented warning.
- Native configured calendar builder selected 2026-06-10 23:00 for ESM6 -> ESU6.
  44 overlapping daily observations; Panama spread +60.25 points.
- Multiple/adjusted prices: 98 rows, 2026-04-17 through 2026-09-04.
  All PRICE/FORWARD/CARRY mappings verified against sources; exactly one switch;
  independent adjustment arithmetic matched, with no nonfinite derived prices.
- Production Parquet: daily June/September files; daily-only merged June,
  September, December files in data/parquet/futures_contract_prices;
  data/parquet/futures_multiple_prices/SP500.parquet and
  data/parquet/futures_adjusted_prices/SP500.parquet.
- Evidence: data/bootstrap/sp500_first_roll/{identities.json,validation.json,
  20260600_raw.parquet,20260900_raw.parquet,bounded_calendar.csv}.
  validation.json includes source/output SHA256 and usable/raw coverage.
- The bounded calendar has a start boundary, one real roll, and an end boundary.
  Boundary rows are NOT actual rolls or an ongoing production roll schedule.
- Reproduce offline: .venv-py312/Scripts/python.exe -m
  sysinit.futures.bootstrap_sp500_first_roll (refuses differing existing outputs).
- Tests: 5 offline unittest cases passed; offline rerun passed persisted equality.
  Git diff checked; pre-existing notebook/basesystem changes left untouched.

## Current Objective
Read-only account validation completed (stop condition A): user confirmed PAPER
identity in TWS, broker_account corrected to DUT077119, normal account-filtered
production broker reads passed. Target-only vertical slice remains complete.

## Completed maintenance validation (2026-09-09)
- Resolved BLOCKER: SP500 had no Mongo contract metadata. Used normal
  update_active_contracts_for_instrument('SP500', data), registering/sampling
  20260900, 20261200, 20270300 with actual IB expiries September 18,
  December 18, and March 19. ESH7 conId 649180684, CME/USD/50.
- Used normal get_and_add_prices_for_frequency with DAILY_PRICE_FREQ and
  write_merged_prices_for_contract with [DAILY_PRICE_FREQ]. Existing merged
  histories were daily-only; no intraday history was discarded. No seed rerun.
- Native requests: 1 Y, 1 day, TRADES, useRTH=True, endDateTime='', formatDate=2.
  Native cleaning and spike threshold 8 retained. Read-only IB connection.
- September and December latest: September 4 -> September 8 23:00, +1 row each
  (131 and 252 total). March: newly sampled, 250 rows September 9, 2025 through
  September 8, 2026. No September 7 bar returned by these RTH requests.
- Native multiple/adjusted calculation and persistence: 98 -> 99 rows, through
  September 8 23:00. PRICE=20260900 at 7680.50; FORWARD=CARRY=20261200 at
  7747.25; latest adjusted=7680.50.
- Before/after comparison: zero changed or removed existing timestamps/values;
  no duplicates, nulls, nonfinite values or bad OHLC. All persisted leg mappings
  and independent +60.25 Panama arithmetic passed. No new contract transition.
  June 10 roll still first appears as September PRICE on June 11 daily row.
- Eight intended Parquet files changed/created; June, FX, unrelated prices and
  raw bootstrap files remained hash-identical. Client 100 released after every
  connection; pre-existing locks 106/107/108 left untouched.
- Audit-driver comparison/argument errors were corrected; retained in logs.
  Retries confirmed September DAILY append idempotence. Production modules were
  not changed. Evidence and before snapshots: data/maintenance/sp500_20260909/.
- Roll state remains No_Roll. Actual-expiry-based production desired roll date:
  September 13 (Sunday), not approximate bootstrap date September 10. Review
  around September 11-14 using fresh matched completed-session prices.
- Next PRICE=20261200; next FORWARD=CARRY=20270300. September/December have
  130 matched rows (119 both positive volume); December/March 250 (40 both
  positive volume), including September 8. No further contract month required
  for this roll; continue refreshing these three contracts.
- Forward liquidity test is currently false: smoothed December/September volume
  ratio 0.005172 < 0.01, although December smoothed volume 6091 > 100.
  Calendar roll date is not due; no roll or roll-state change executed.
- Eleven offline tests passed; persisted checks passed; git diff inspected.
  Only pre-existing tracked notebook/basesystem changes remain.

## Next Step
Prepare explicit SP500 paper-test risk bounds and an isolated dry-run design
that prevents submission and production order-stack writes. Keep the
September 11-14 roll review as a separate scheduled operational concern; see
data/maintenance/sp500_20260909/REPORT.md. No roll investigation in this subtask.

## Completed production target calculation (2026-09-09)
- Strategy sp500_target_test uses runSystemClassic and the unchanged provided
  simplesystemconfig EWMAC8 (8/32) and EWMAC32 (32/128) rules. Universe SP500 only.
- Config: private/private_config.yaml strategy_list/load_backtests;
  private/private_control_config.yaml run_systems method only;
  private/sp500_target_test.yaml inherits the example, overrides USD 10000,
  instrument weight 1 and instrument diversification 1. No scheduler started,
  no order-generator configuration added, broker_account unchanged.
- Explicit strategy capital USD 10000 persisted via dataCapital. No total
  capital initialised, no broker capital sync or strategy allocation run.
  Existing example volatility target 25%; annual cash risk 2500, daily 156.25.
- Input: 99 adjusted/multiple observations through 2026-09-08 23:00.
  Adjusted/PRICE 7680.50, PRICE 20260900; FORWARD/CARRY 20261200 at 7747.25.
- Raw EWMAC8/EWMAC32: 0.5050429461 / 1.6391540626. Scaled/capped forecasts:
  2.6767276144 / 4.3437582659. Equal weights, FDM 1.1; combined 3.8612672342.
- Daily sizing volatility 53.5969930646 index points. USD 50/point multiplier;
  average position 0.0583055097, subsystem/final target +0.02251331542483085.
  Target = (156.25 / (53.5969930646 * 50)) * (3.8612672342 / 10).
- Persisted bufferedOptimalPositions: lower 0.016682764452995776,
  upper 0.028343866396665925; reference September 20260900 at 7680.50;
  calculation timestamp 2026-09-09 21:17:18.732799 local Asia/Shanghai.
- Exact optimal store: data/parquet/optimal_positions/sp500_target_test SP500.parquet.
  Capital store: data/parquet/capital/sp500_target_test.parquet.
  Classic schema stores bounds/reference; continuous target is in the backtest
  cache and equals buffer midpoint. No integer order target generated.
- Snapshot: private/backtests/sp500_target_test/20260909_211718_backtest.pck
  and 20260909_211718_config.yaml. Loaded through dataBacktest; target matched.
  Buffers/reference read through dataOptimalPositions in a fresh dataBlob.
- Evidence: data/strategy_target/sp500_target_test/{before.json,result.json}.
  All Mongo collections unchanged (only IBClientTracker, futures_contracts,
  futures_roll_status exist). No order-stack/history entries created. All
  Parquet except the two intended capital/optimal files hash-identical.
- Broker connection factory patched to fail; no broker requests or mutations.
  External account state was not independently queried; PAPER-001 remains open.
- Driver: python -m sysinit.futures.calculate_sp500_target. Read-only recheck:
  append --verify-existing. First audit hit Windows separator mismatch after
  successful persistence; fixed and verified without a second production run.
- Three offline target validation tests passed. Diff inspected; pre-existing
  notebook/basesystem edits preserved. Warm-up and missing spread cost are
  material but non-blocking; this is a mechanical test, not deployment readiness.

## Read-only account verification (2026-09-09)
- Stop condition B / BLOCKER: fresh API identity responses did not explicitly
  identify PAPER status. Native TWS UI inspection is unavailable in this session.
  Manually verify the running TWS displays PAPER / Simulated Trading and its
  account window identifies DUT077119 as the intended paper account. Port 4002,
  DU prefix and approximately USD 1 million equity are not sufficient proof.
- Fresh ib_async connection to 127.0.0.1:4002, client 19391, readonly=True;
  disconnected in finally. Managed accounts: only DUT077119. AccountCode agrees;
  AccountType INDIVIDUAL, AccountReady true. No alias or explicit paper/simulation
  marker returned among the account identity fields inspected.
- Account summary snapshot (USD): NetLiquidation 1000817.06, TotalCashValue
  928486.05, AvailableFunds and FullExcessLiquidity 982365.52, initial and
  maintenance margin 17959.82. Diagnostic API reads only; no capital sync.
- Broker positions: AAPL +1, QQQ +100; no futures, hence SP500/ES actual 0.
  INFORMATIONAL for SP500-only position comparison: unrelated equities exist.
  They affect account equity/margin; this is not full-account reconciliation.
- Current repository broker_account semantics: API account identifier, not login
  username. connectionIB passes it to IB.connect(account=...), static data returns
  it, accounting selects account-keyed summary values, positions/orders filter by
  exact account, and future broker orders use it as order.account.
- Proposed correction, NOT applied: private/private_config.yaml line 10,
  tradersenlos -> DUT077119. Consumers include connection subscription, capital,
  FX balances, broker position/order reads, commissions and order assignment.
  PAPER confirmation is required before applying this user-authorised correction.
- Normal local production reads: strategy and contract position tables empty;
  sp500_target_test/SP500 actual 0. Optimal buffer remains present (~0.017/0.028);
  exact bounds and continuous target +0.0225133154 are recorded above from the
  completed target slice. SP500 local/broker actual positions agree at zero;
  account-filtered production broker reconciliation remains unverified.
- Mongo collection counts before/after local reads unchanged: IBClientTracker 3,
  futures_contracts 3, futures_roll_status 1. No order stack/history collections.
- Read-only controls: effective SP500 strategy/instrument position limit No limit;
  trade limits []; SP500 locked False; cumulative override 1.0; roll No_Roll.
  Missing explicit position/trade bounds are MATERIAL prerequisites for a later
  order-capable test. No controls, roll state or strategy inputs changed.
- Deferred behind identity blocker: corrected-config production broker reads,
  open broker orders (not queried), fresh contract-details validation and final
  execution-readiness certification. Existing SP500 -> CME ES mapping and prior
  expiry evidence are in the completed handoff; no roll investigation repeated.
- Minimum next sequence: confirm TWS paper identity; apply one-line account fix;
  validate normal account-filtered capital/positions/open-orders and SP500
  contract reads; decide explicit risk bounds and isolated dry-run design before
  any order-generation test. No generator, stacks or execution code was invoked.
- Validation: diagnostic reads succeeded; no implementation changes or test orders.
  Initial sandbox runtime launch failed; approved runtime access succeeded.

## Completed account-filtered broker validation (2026-09-09 21:35 local)
- Stop condition A achieved. Supersedes the earlier API-only stop condition B.
  User explicitly confirmed current TWS PAPER / Simulated Trading and DUT077119;
  accepted as sufficient project evidence without further identity investigation.
- Only configuration edit: private/private_config.yaml broker_account
  tradersenlos -> DUT077119. Other configuration left unchanged.
- Normal dataBlob/connectionIB allocation and dataBroker reads used. The audit
  wraps IB.connect with readonly=True and blocks placeOrder/cancelOrder/global
  cancel. No order generator, stack handler or execution algorithm invoked.
- Configured account, dataBroker.get_broker_account and managedAccounts agree:
  DUT077119 (only managed account). Account-specific capital adapter and normal
  base-currency reads passed: USD NetLiquidation 1000833.06; excess liquidity
  982377.53. Account-filtered FX balance helper returned {}; informational only,
  not a claim of zero account cash, and not needed for this validation.
- dataBroker.get_all_current_contract_positions returned no futures positions.
  Its IB position client with explicit account_id returned AAPL +1 and QQQ +100.
  Equity holdings are outside the futures-only interface, as expected.
- dataBroker.get_list_of_orders completed its account-filtered broker request:
  zero open orders. No orders were submitted, modified or cancelled.
- Fresh native SP500 contract enrichment and IB adapter details: ESU6 conId
  649180671, expiry 20260918; ESZ6 conId 515416632, expiry 20261218. Both CME,
  USD, multiplier 50, minTick 0.25. No contract metadata or roll state writes.
- Fresh persisted optimal bounds 0.016682764452995776 / 0.028343866396665925;
  midpoint +0.02251331542483085, reference 20260900 at 7680.5. Local strategy
  actual 0, local contract/strategy position tables empty, broker SP500 actual 0.
  SP500 actual positions agree; unrelated equities are not locally reconciled.
- Controls reconfirmed unchanged: position limit No limit; trade limits [];
  override 1.0; SP500 unlocked; roll No_Roll. EXEC-CONTROLS-001 remains material
  but non-blocking for this completed read-only validation. No deep investigation.
- Client 100 released by dataBlob context exit; disconnected=True. Mongo before
  and after snapshots match, including existing client locks 106/107/108 and no
  order-stack/history collections. No position, optimal-position or capital writes.
- Evidence and guarded audit driver: data/account_validation/result.json and
  validate_readonly.py. Assertions passed (status PASS); configuration/document
  edits reviewed and tracked diff checked. No production implementation changed.
- Next subtask: agree explicit SP500 paper-test position/trade bounds and prepare
  an isolated dry-run order-generation test that cannot submit orders or write
  production order stacks. Roll review remains a separate operational concern.
