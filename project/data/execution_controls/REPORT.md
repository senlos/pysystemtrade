# SP500 bounded controls and non-mutating decision — 2026-09-10

Result: **NO TRADE**. Native calculation and persistent control verification PASS.
No instrument-stack records, contract orders, broker orders, execution algorithm,
stack handler, submission, cancellation or modification were performed.

## Controls and exact semantics

| Control | Store and scope | Quantity and enforcement | Missing configuration |
|---|---|---|---|
| Position limit | Mongo production.position_limit_status; instrument and strategy/instrument, no dated-contract scope | Absolute net contracts: evaluates local recorded position plus proposed instrument trade; both limits applied after override in orderGeneratorForStrategy, then conservative result selected | No limit; leaves trade unconstrained |
| Trade limit | Mongo production.limit_status; instrument or strategy/instrument plus period_days | Gross absolute contract quantity across legs, not order count or dollars; most restrictive relevant remaining allowance. Normal non-limit, non-panic contract-order sizing applies it before algo submission | Empty applicable list passes requested quantity; a directly requested missing limit object uses sentinel 999999 |
| Override | Mongo production.overide_status (actual spelling); strategy, instrument, strategy/instrument; combined with production config instrument classifications | Numeric 0..1 scales desired position, then derives trade; 1 leaves it unchanged. Special close/no-trading/reduce-only semantics. Applied before position limits | 1.0, subject to config overrides |
| Lock | Mongo production.locks; instrument | Boolean gate at instrument-stack submission and normal contract-to-broker handling; does not itself cancel existing broker orders | Unlocked |

Trade allowance uses elapsed time since last reset, resetting when more than
period_days has elapsed; it is not a midnight calendar-day or sliding-window cap.
The counter adds broker order requested absolute quantity through add_trade after
submission/database handling, not just fills. It has removal/reset interfaces.
Position limits constrain net exposure, not gross offsetting contract positions;
a reversal from +1 to -1 can require two contracts even with a position limit of 1.
Hence a separate turnover allowance is necessary.

Policy proposed before writes and installed through dataPositionLimits and
dataTradeLimits normal interfaces:

- SP500 instrument absolute position limit = 1.
- sp500_target_test/SP500 absolute position limit = 1.
- SP500 instrument trade limit = 1 contract per 1-day period. No redundant
  strategy trade limit needed: instrument allowance includes all strategies.
- Preserve override 1.0, unlocked state, USD 10000 strategy capital and No_Roll.

Persistent changes: exactly two documents in position_limit_status (instrument
marker and strategy_instrument marker) and one in limit_status with key
`instrument_strategy_key=" SP500"`, period_days=1, trade_limit=1,
trades_since_last_reset=0, last_reset_time=2026-09-10 20:19:00.186 local.
Both collections were absent/empty before this test. No unrelated instrument
records changed. IB client 100 was temporarily allocated and released; pre-existing
tracker records unchanged. Full before/after Mongo snapshots and private/Parquet
hashes are in configure_result.json. Independent verify_result.json reports no
changed collections and identical file hashes.

## Numeric decision and accounting

Fresh account-filtered broker reads: DUT077119, zero futures positions and zero
open orders. Existing user PAPER confirmation retained. Local strategy and local
contract positions are zero; aggregate local SP500 position across strategies is
zero. There are no populated order stacks. The generator uses recorded strategy
positions, not broker positions or an automatic reconciliation adjustment.
Its stack stage normally adjusts for existing unfilled orders; none exist here.

Persisted lower bound = 0.016682764452995776, upper = 0.028343866396665925.
Midpoint/continuous target = +0.02251331542483085. Actual 0 is **below**, not inside,
the continuous buffer. Classic production logic chooses the lower edge, then
Python round(lower)=0 (nearest integer, ties to even). Required change = 0-0=0.
Override 1.0 and both position limits leave zero unchanged; trade-capacity query
also returns zero for this requirement. No ceiling-to-one behavior exists.

First the bounds/actual/rounding were calculated without an order object. Then
orderGeneratorForBufferedPositions.get_optimal_positions was called as a read
method on a data/strategy view, followed by the exact production function
trade_given_optimal_and_actual_positions. It returns an **in-memory** zero-size
best instrumentOrder. Native Override.apply_override and
dataPositionLimits.apply_position_limit_to_order confirmed zero. No generator
instance, get_and_place_orders, submit_order_list or stack insertion was run.
With no existing stack orders, normal insertion would reject this zero order via
zeroOrderException. This dry run stopped before that mutating interface.

## Normal path and next boundary (inspection only)

update_strategy_orders / strategyRunner -> configured generator
get_and_place_orders -> get_required_orders -> persisted buffered optimum and
recorded strategy position -> native buffer decision -> override -> position
limits -> lock -> instrument-stack insertion/adjustment.

The private control config currently registers only run_systems, not this strategy's
order generator. The classic buffered class is the compatible production path for
its persisted schema; no scheduler/generator configuration was added.

After an instrument order: spawn_children_from_instrument_orders selects the priced
contract in No_Roll and creates contract children; current dataContracts read gives
20260900 (ESU6, prior verified conId 649180671, expiry September 18). Subsequent
create_broker_orders_from_contract_orders checks locks/market eligibility, sizes
remaining quantity using trade allowance and liquidity, allocates an algo, and
calls algo.submit_trade. Broker adapters eventually call
sysbrokers/IB/client/ib_orders_client.py broker_submit_order -> IB.placeOrder.
All of those stages remain unexecuted. September roll is separate.

## Findings and limits of certification

- INFORMATIONAL: NO TRADE is correct; fractional target does not imply one ES.
- MATERIAL BUT NON-BLOCKING for this read-only test: controls are application
  bounds for normal serialized best-order handling, not a universal guarantee.
  Panic orders bypass downstream checks; limit-type contract orders bypass
  trade sizing. Trade capacity is not atomically reserved before submission;
  concurrency/stale positions or direct broker activity can defeat these bounds.
  An unconditional environment-wide one-contract guarantee is **not established**.
  Treat this as a BLOCKER before any order-capable test, not permission to execute.
- MATERIAL BUT NON-BLOCKING: one unit of turnover can prevent same-period exit
  after a one-contract entry. Do not automatically raise/reset it; design explicit
  exit handling in the next execution-safety subtask.

Validation: configure run PASS, independent no-write readback PASS; four offline
tests PASS (native zero decision, directional position clipping, turnover usage,
execution guard). IB place/cancel/global-cancel and generator submit methods were
patched to fail; Mongo stack insertion also guarded. No production implementation
or strategy config changes. Git diff inspected; evidence directory is untracked
and retained in the workspace; no commit made.

Next: establish a bounded single-order paper execution design with pre-submission
exposure/quantity checks, exclusion of bypass paths, serialized capacity handling
and an explicit exit policy, still without submission. Keep roll review separate.
