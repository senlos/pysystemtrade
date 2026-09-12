# Current State

## Bounded finalized-bar post-roll verification — PENDING, 2026-09-12 00:44 Shanghai
- Read the four authoritative handoff files. Current clock September 11 16:44 UTC
  / September 12 00:44 Shanghai: the September 11 US session is still open.
  The user's prerequisite (completed session and expected finalized daily data)
  is not met. Neither confirmation A nor material-discrepancy B is established.
- No broker connection, refresh, production writes or roll recalculation in this
  pending check. Existing December PRICE / March FORWARD-CARRY and +67.50 remain
  as previously validated; no new claim about finalized prices or March volume.
- IB documents that Friday futures settlement values may not arrive until
  Saturday: https://interactivebrokers.github.io/tws-api/historical_bars.html.
  A conservative review opportunity is September 13 10:00 Asia/Shanghai; actual
  availability must still be assessed. Do not treat a clock delay as proof of finality.
- Attempted scheduled follow-up was rejected by automatic approval review as
  unrequested persistent daily automation for production work. No automation was
  created. Resume manually after the publication window, or obtain explicit
  authorization for a bounded scheduled run. No execution entitlement work.
- Next non-blocked subtask while waiting: offline review of the existing strategy
  warm-up/cost evidence (STRATEGY-TARGET-001), without forecasts or capital changes.
- OPEN_ISSUES.md and ../decisions/DECISIONS.md unchanged: no new material data finding or
  project decision. This pending status does not invalidate the completed roll.

## SP500 production refresh and September roll — COMPLETE, 2026-09-12
- Stop condition A achieved at 00:39 Asia/Shanghai; independent post-roll readback
  PASS at 00:40. No orders, execution, strategy generation or production code edits.
- Normal SP500 daily maintenance refreshed September/December 2026 and March 2027:
  September 8 -> September 11 23:00, +3 rows each; totals 134/255/253.
  Zero existing changes/deletions, duplicate/null/nonfinite rows or invalid OHLC.
  Multiple/adjusted 99 -> 102 before roll; normal client 100 released cleanly.
- Actual native selector returned Roll_Adjusted: zero priced position; smoothed
  December/September volume ratio 0.0393077 > 0.01 and forward volume 35688 > 100.
  Desired date September 13 is tomorrow; native days_until_roll=0 (floor).
  Native liquidity/zero-position branch permits roll before desired calendar date.
- Normal roll completed: PRICE=20261200; FORWARD=CARRY=20270300; final No_Roll.
  Native boundary September 11 23:00:01; differential +67.50; 103 derived rows.
  Latest PRICE/adjusted 7740.00; FORWARD/CARRY 7788.00. Existing multiple rows
  preserved; adjusted boundary continuous. Persisted native recalculation equality,
  all quality checks and production simulation price/carry readability pass.
- September 11 source bar was collected during the open session; not certified
  final. Native workflow accepts latest bars. March latest volume zero; overlap
  sufficient mechanically. See DATA-ROLL-001 and existing IB-HIST-003.
- Eight offline audit tests PASS; diff inspected. Audit-only precision/name
  mismatches corrected via read-only verification, without repeating the roll.
  Evidence: project/data/maintenance/sp500_20260912/REPORT.md and post_roll_validation.json.
- Next non-blocked task: after session close, compare final matched roll-window
  bars against saved sources for material adjustment impact, then continue normal
  SP500 daily maintenance. Submission issue remains paused and outside this task.
- This section supersedes older SP500 contract/readiness/next-step statements below.

## FIRST PAPER broker-submission test — PAUSED, 2026-09-12
Execution subtask closed for now as PAUSED, not failed. Current blocker
EXEC-QUOTE-001: live ES bid/ask unavailable because the current IB account lacks
the required real-time CME/ES Level 1 market-data entitlement (IB error 354).
This blocks reliable construction of the deliberately passive one-contract
limit order required by ../policies/EXECUTION_TEST_POLICY.md. No order was created/submitted.

BLOCKER for actual broker submission; NON-BLOCKING for production data
maintenance, strategy calculation, target generation, controls, dry-run order
logic, roll operations and other non-submission work, subject to their own gates.
Revisit only when appropriate live CME/ES Level 1 bid/ask becomes available.
No delayed/historical data, stale quotes, last/reference prices or guessed passive
prices may be used as a workaround. No further entitlement investigation now.
Resume submission only with valid policy and fresh preflight after that trigger.

Recommended next non-blocked subtask: refresh production SP500 daily data for
September/December 2026 and March 2027, then perform the scheduled September
11-14 roll-readiness review using matched completed-session prices. Keep that
subtask non-submission; this recommendation does not change roll state.
This handoff update changes no controls, limits, strategy state, optimal
positions, capital, broker positions, roll state or production code.

## Latest execution preflight — 2026-09-12 00:23 Asia/Shanghai
STOPPED BEFORE ORDER CREATION: IB error 354, ES live market data not subscribed;
bid/ask NaN and quote timestamp absent. Policy's fresh live quote gate failed.
Authorized persistent control change completed through dataPositionLimits:
sp500_execution_test/SP500 absolute position cap 1. Independent Mongo readback
and fresh normal effective-limit API both 1; all other Mongo state matched before.
Successful elevated OS process/scheduler inspection found TWS, no Python workers
and no matching scheduled execution tasks. Fresh native tradability TRUE;
configured/managed DUT077119; broker/local SP500 zero, all-client open orders and
executions empty; No_Roll, PRICE 20260900, desired roll September 13; override 1,
unlocked, native trade capacity 1. Exact ESU6 identity/tick verified. Normal client
100 released; direct read-only client 19393 disconnected. No order created or
submitted. Policy deadline remains September 12 04:00 Shanghai. Next attempt
requires usable fresh live ES bid/ask and refreshed runtime gates, not delayed
quotes or a gate bypass. Evidence:
project/data/execution_tests/20260912_002124_control_preflight/REPORT.md.

## Latest execution preflight — 2026-09-12 00:17 Asia/Shanghai
STOPPED BEFORE ORDER CREATION: gate 8 failed, dedicated
sp500_execution_test/SP500 position cap absent in fresh production readback.
SP500 instrument and sp500_target_test/SP500 caps each 1. Policy renewed for
this supervised September 12 attempt only, ending 04:00 Shanghai, retaining
ESU6/No_Roll and every one-submission/cancellation/no-flatten restriction.
Native September ES tradability TRUE at 00:16:56.192529; configured account
DUT077119. Guarded read-only broker client 100 disconnected and released.
Stored No_Roll and turnover 1/day, used 0, reset September 10 20:19:00.186 read;
effective turnover/reset safety and active PRICE not certified. OS process and
scheduler inspection denied access, so execution isolation remains unverified.
Full fresh preflight incomplete. No orders, submissions, position/control/roll
changes; this remains FIRST-submission preparation, not recovery.
Evidence: project/data/execution_tests/20260912_001656_preflight/REPORT.md.

## Latest execution preflight — 2026-09-11 20:22 Asia/Shanghai
STOPPED BEFORE ORDER CREATION: gate 15 failed. Current clock verified at
2026-09-11 12:22:43 UTC (20:22:43 Shanghai); ../policies/EXECUTION_TEST_POLICY.md explicitly
expires before September 11 Asia/Shanghai. User freshly confirmed current TWS
PAPER / Simulated Trading, account DUT077119; identity gate accepted, superseding
the previous missing-confirmation blocker. No broker connection, order creation,
submission, cancellation or control mutation in this resumed attempt. Remaining
runtime gates not checked after policy failure; September 10 readings are not
current certification. Policy unchanged. Separate policy refresh is required
before another attempt, with current contract/roll and all runtime gates verified.
Evidence: project/data/execution_tests/20260911_202243_preflight/REPORT.md.

## Latest execution attempt — 2026-09-10 23:10 Asia/Shanghai
STOPPED BEFORE ORDER CREATION: fresh native ES September tradability TRUE at
23:10:52.554365; configured broker account DUT077119. Current TWS PAPER /
Simulated Trading identity was not freshly confirmed; confirmation requested,
no response received before stopping. Remaining preflight gates unverified;
dedicated cap not changed. Zero parent/child/submission/cancellation attempts.
Guarded read-only normal client 100 disconnected and released. Policy date scope
still before September 11, but full readiness is NOT certified. On any future
fill, separate flatten authorization remains mandatory. Next attempt requires
current TWS identity and every fresh gate, including time-to-close and policy
expiry. Evidence: project/data/execution_tests/20260910_231052_preflight/REPORT.md.


## Latest execution attempt — 2026-09-10 22:09 Asia/Shanghai
STOPPED BEFORE ORDER CREATION: fresh native ESU6 tradability False at 22:09:57,
with next effective interval 23:00. Zero parent/child/submission attempts; guarded
read-only client 19392 disconnected. Contract identity, configured/managed account,
stored No_Roll and existing caps/turnover matched handoff. Dedicated test cap still
absent; remaining full preflight, including fresh positions/open orders and UI
identity, not completed. Policy reviewed without extending expiry or scope;
current instruction requires separate flatten authorization after any fill and
supersedes older pre-authorized-close text. Evidence and next step:
project/data/execution_tests/20260910_renewed_preflight/REPORT.md.

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
- Evidence: project/data/bootstrap/sp500_first_roll/{identities.json,validation.json,
  20260600_raw.parquet,20260900_raw.parquet,bounded_calendar.csv}.
  validation.json includes source/output SHA256 and usable/raw coverage.
- The bounded calendar has a start boundary, one real roll, and an end boundary.
  Boundary rows are NOT actual rolls or an ongoing production roll schedule.
- Reproduce offline: .venv-py312/Scripts/python.exe -m
  sysinit.futures.bootstrap_sp500_first_roll (refuses differing existing outputs).
- Tests: 5 offline unittest cases passed; offline rerun passed persisted equality.
  Git diff checked; pre-existing notebook/basesystem changes left untouched.

## Current Objective
Timezone configuration repair completed 2026-09-10 21:51 Asia/Shanghai.
Classification B resolved: private/private_config.yaml now sets GMT_offset_hours
to 8; private/private_config_trading_hours.yaml translates all 11 default entries
+8 hours, including example weekday rollover. Native parser and safety trimming
are unchanged. Authorized conservative midnight gaps use 23:59 then 00:00.
Fresh-process guarded read-only validation resolved exact ESU6 and derived
September 10 23:00-23:59 plus September 11 00:00-04:00 local. Synthetic native
gate checks passed before/inside/after and during the midnight gap. Actual gate
was False at 21:51, as expected. All timezone entries passed no-expansion checks.
Private/Parquet/production-source hashes and all production Mongo collections
were compared: only the two authorized config files changed. Broker account
DUT077119 unchanged; no historical rewrite, strategy/position/limit/capital/roll
mutation, order creation or submission. Direct read-only IB client disconnected.
Evidence: project/data/execution_tests/timezone_repair_20260910/{REPORT.md,validation.json,
before.json,after.json,translations.json,audit.py}.
STOP: no PAPER execution in this task. The next execution attempt requires a
freshly reviewed/renewed execution policy and fresh preflight; the old policy
expires September 11 local midnight. See EXEC-SESSION-002 for the accepted gap.

Latest execution attempt (2026-09-10 20:36 Asia/Shanghai): STOPPED BEFORE
ORDER CREATION. Fresh user TWS PAPER/account confirmation satisfied identity.
Read-only preflight passed broker/local zero positions, no open orders, existing
controls and exact ESU6 identity, but native contract tradability returned False.
Adapter trading window ended at 20:00 local. No parent/child/submission, control
change or trading-hours bypass occurred; client 100 released. See
project/data/execution_tests/20260910_203144/REPORT.md. Session configuration is now repaired
as recorded above; renew execution policy before another preflight. Current user instruction
requires stopping on any fill and obtaining separate flatten authorization;
the older pre-authorized-close requirement is superseded for this task.

Execution-boundary review complete; see ../policies/EXECUTION_TEST_POLICY.md. Operational
isolation plus exactly one checked submission attempt is sufficient for a bounded
supervised PAPER test; a generic single cycle is not sufficient. No production
execution code change is required. Readiness is conditional on fresh preflight
and future authorisation covering entry and contingent manual flatten. Real
strategy remains NO TRADE; no test order exists and nothing was submitted to IB.

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
  not changed. Evidence and before snapshots: project/data/maintenance/sp500_20260909/.
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
Freshly review/renew ../policies/EXECUTION_TEST_POLICY.md before any new execution attempt,
including an attempt tonight. The existing policy expires September 11 local
midnight. Resolve entry/exit authorization in that separate task, then perform
fresh preflight in the corrected session. No order is authorized by this repair;
the dedicated execution-test strategy limit is still not configured. Keep the
September 11-14 roll review as a separate scheduled operational concern; see
project/data/maintenance/sp500_20260909/REPORT.md. No roll investigation in this subtask.

## Completed execution-boundary review (2026-09-10)
- Traced generator, child spawning, preprocessing, algo allocation/submission,
  turnover storage/reset and fill/balance accounting. Reachability, race classes,
  selected mechanism and deterministic lifecycle are in ../policies/EXECUTION_TEST_POLICY.md.
- Confirmed sequential risks beyond concurrency: limit orders skip capacity sizing
  and automatic blocking-algo usage charge; lazy expired reset can erase a charge;
  uncertain cancellation/restart can allow duplicate exposure if retried.
- No broad locking fix needed for one exclusive, single-attempt outright order.
  Explicit native controls compensate the selected limit path. One-contract
  gross turnover cannot fund a round trip: policy requires future acceptance of
  one broker-verified risk-reducing manual close, without raising/resetting limits.
- Seven offline tests passed (three new audit cases and four existing boundary
  cases); git diff reviewed. No DB/broker runtime, order creation, handler service,
  capital/forecast/control/position/roll changes in this task. Existing handoff
  changes and project/data/execution_controls artifacts preserved.

## Completed execution-control / dry-run slice (2026-09-10)
- Normal interfaces persisted SP500 absolute position limit 1, strategy/instrument
  sp500_target_test/SP500 position limit 1, SP500 trade allowance 1 contract per
  elapsed one-day reset period. Used 0; reset timestamp 20:19:00.186 local.
- Exact writes: two production.position_limit_status documents and one
  production.limit_status document. Independent readback PASS; override 1.0,
  unlocked, No_Roll. Other Mongo state unchanged; all private/Parquet hashes equal.
- Fresh broker actual futures 0 and open orders 0; local strategy/contract and
  aggregate SP500 position 0. Account DUT077119; existing PAPER confirmation used.
- Lower/upper 0.016682764452995776 / 0.028343866396665925; midpoint
  0.02251331542483085. Actual 0 below buffer; native round(lower)=0; change 0.
  Native buffer/override/position-limit APIs returned in-memory zero best order.
  No mutating generator, stack handler, contract/broker order or algo invoked.
- No_Roll priced contract readback 20260900 (ESU6). Generator is not registered
  for this strategy; no registration or scheduler changes made.
- Four offline tests PASS; guarded configure and independent verification PASS;
  diff checked. Evidence and full semantics: project/data/execution_controls/REPORT.md,
  configure_result.json, verify_result.json, validate.py, test_validation.py.
- Normal controls do not provide an unconditional one-contract environment cap:
  bypasses and non-atomic capacity accounting are documented in EXEC-CONTROLS-002.
  They do not block this completed non-mutating calculation, but block execution
  certification. One-contract turnover also needs an explicit eventual exit policy.

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
- Evidence: project/data/strategy_target/sp500_target_test/{before.json,result.json}.
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
- Evidence and guarded audit driver: project/data/account_validation/result.json and
  validate_readonly.py. Assertions passed (status PASS); configuration/document
  edits reviewed and tracked diff checked. No production implementation changed.
- Next subtask: agree explicit SP500 paper-test position/trade bounds and prepare
  an isolated dry-run order-generation test that cannot submit orders or write
  production order stacks. Roll review remains a separate operational concern.
