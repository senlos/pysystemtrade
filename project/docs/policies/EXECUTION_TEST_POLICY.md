# First SP500 PAPER execution boundary — 2026-09-10

## Current renewal — 2026-09-12 Asia/Shanghai

User-authorized date refresh for the FIRST submission test, not order recovery.
This renewal supersedes the expired September 11 cutoff below solely for this
supervised attempt on September 12, from renewal until 04:00 Asia/Shanghai.
The native tradability gate must be TRUE and at least 30 minutes must remain
until the earlier of native session close and this policy deadline before entry.
A failed gate ends this attempt; no waiting loop or automatic retry is authorized.

Scope unchanged: PAPER / Simulated Trading DUT077119 only; SP500, BUY exactly
one ESU6 (20260900), conId 649180671, CME/USD/50, tick 0.25, expiry 2026-09-18;
exactly one checked parent, one outright contract child and one broker submission
attempt; passive DAY LIMIT at fresh bid minus four ticks, below ask. Immediate
normal-path cancellation on acknowledgement; existing 10-second cancellation
trigger and 30-second terminal-state deadline remain. No automatic retry,
replacement, flatten, contract substitution or roll-state modification.

The September 11-14 roll-review period is now current. Fresh preflight must
verify stored No_Roll, active PRICE still 20260900, exact broker contract identity
and that current native roll selection remains valid without a roll-state change.
Any mismatch stops this test; do not substitute December. Handoff's September 13
desired roll date is historical context, not fresh roll certification.

All original controls, isolation, quote freshness, turnover accounting and linked
retired lifecycle requirements remain. Require all three SP500 position caps = 1:
instrument, sp500_target_test and sp500_execution_test. Verify current turnover
capacity and reset timing; do not reset/increase limits to manufacture capacity.
The original expired-reset accounting safeguards remain mandatory.

On ANY fill stop normal progression, cancel any working remainder, reconcile
actual fill and broker/local state, and require separate flatten authorization.
Older pre-authorized/manual-close language below is not authorization. Ambiguous
broker state permits read-only reconciliation and cancellation of the identified
entry only; no new order. Success requires cancellation before fill, no open
order, broker/local SP500 zero and the complete auditable internal lifecycle,
including the original two final snapshots at least five seconds apart.

Renewal is conditional policy validity, not a statement that preflight passed.

## Review for this attempt — 2026-09-10 22:09 Asia/Shanghai

Disposition: STOP BEFORE ORDER CREATION. This review does not certify readiness.
Fresh guarded read-only native gate returned False at 22:09:57; next configured
interval begins 23:00. No waiting/retry or order creation under this attempt.
Exact ESU6 identity revalidated: 649180671, CME/USD/50, expiry 2026-09-18,
tick 0.25. Stored roll state remains No_Roll. Active PRICE and full preflight
were not freshly verified after the failed gate; they remain mandatory.
Stored instrument cap 1 and sp500_target_test cap 1 remain; dedicated
sp500_execution_test cap is absent (BLOCKER before order creation). Stored
turnover is 1/day, used 0, reset timestamp September 10 20:19:00.186.
No control was changed or reset. Account configured/managed is DUT077119;
current TWS PAPER UI identity was not freshly verified in this attempt.

Only necessary policy change: the user's current fill instruction supersedes
all older requirements below for pre-authorized or promptly initiated flattening.
On ANY fill, stop normal progression, record quantity, price, remaining quantity,
broker/local position and internal fill state, and request separate authorization
for the documented manual-flatten procedure. No automatic flatten, additional
submission, or turnover consumption is authorized. The older manual-close details
remain a proposal for separate authorization, not permission to execute them.
This authorization change is NON-BLOCKING for the requested cancellation test.

Scope remains PAPER DUT077119, SP500 ESU6 only, BUY exactly 1, one checked
parent, one child, exactly one normal-path submission attempt, passive DAY LIMIT,
immediate cancellation on acknowledgement, no retry, explicit stop/recovery-only
on ambiguity. All original identity, control, isolation, quote, time-to-close,
accounting and retirement gates remain. Expiry is NOT extended: before September
11 Asia/Shanghai; no December substitution or roll change. The repaired timezone
and accepted midnight gap are NON-BLOCKING; native gate False NOW is BLOCKER.
Evidence: project/data/execution_tests/20260910_renewed_preflight/preflight.json.

## Conclusion and scope

The proposed isolation list alone is insufficient: a generic cycle is not a
one-submission boundary, and stopping the process at acknowledgement abandons
cancellation/accounting. An augmented, manually staged procedure below is
sufficient to bound intended ES exposure to one contract without changing the
production execution system. This is conditional operational assurance, not an
unconditional broker cap. No broker connection, order, stack mutation, control
change, scheduler or strategy change was made in this review.

Ready for a future supervised test ONLY after the fresh gates below pass and its
entry/contingent-exit scope is authorised. The current strategy remains NO TRADE.
This document is a procedure, not an installed executable test runner.

## Actual control locations and bypass reachability

Source paths below are relative to the repository; function names identify the
reviewed boundaries.

| Path | Checks and consequence | Classification for selected workflow |
| --- | --- | --- |
| `sysexecution/strategies/strategy_order_handling.py`: `get_and_place_orders` | Applies cumulative override using recorded strategy position, then instrument and strategy position limits; `submit_order_list` checks lock before insertion. Position limits do not reserve working orders. | Reuse these control methods explicitly for dedicated test order; do not run real strategy generator. |
| `sysexecution/stack_handler/spawn_children_from_instrument_orders.py`: `spawn_children_from_instrument_order_id` | Rechecks lock; maps instrument to contract using roll state. Does not repeat overrides/position limits. | Reachable; require No_Roll and exactly one inspected child of quantity +1. |
| Same file: `spawn_children_from_instrument_order` | Calls `auto_update_roll_status` before selecting contracts. | Reachable; verify No_Roll remains unchanged; any changed state aborts before submission. No roll operation is authorised. |
| `sysexecution/stack_handler/create_broker_orders_from_contract_orders.py`: `preprocess_contract_order` | Rejects filled/algo-controlled order, checks lock and tradability, then sizes unfilled quantity. No position/override check here. | Reachable; repeat upstream controls immediately before submission under exclusive ownership. |
| `size_contract_order`: limit type | Returns remaining quantity before trade-limit and liquidity checks. | Reachable by selected passive test; compensate explicitly with `apply_trade_limits_to_contract_order` before the sole submission; abort unless result is exactly +1. |
| `preprocess_contract_order`: panic flag | Returns original order before lock, market, remaining-quantity and trade sizing checks. Market algo also skips its size cap for panic. | Manual/admin only in selected workflow; reject panic at every inspected layer. |
| `sysproduction/interactive_order_stack.py`: `create_manual_trade` | Inserts manual instrument order directly, optionally contract child; bypasses generator override and position limits. | Manual/admin only; raw menu is not the selected entry method. |
| Direct `submit_order`, raw stack insertion, `send_to_algo`, Algo or `dataBroker.submit_broker_order` calls | Can skip upstream checks. IB adapter builds and submits; no universal application controls at broker boundary. | Manual/admin only; prohibit except prescribed, checked stage calls. |
| Roll-order creation and multi-contract/spread routes | Separate parents/children outside strategy generation; net position caps need not bound gross legs. | Not reachable: no roll handler, no active roll, no spreads, no second instrument/child. No deeper investigation required. |
| Algo allocation override or preallocated algo | `allocate_algo_to_order.py` honours existing algo and instrument override before type selection. | Reachable configuration risk; inspect resolved class and require exactly `algo_limit_orders.algoLimit`. Otherwise abort. |
| `algo_original_best.py` | Can choose market initially or reprice aggressively; `algo_market.py` submits market. | Not reachable under selected fixed limit algo. Neither provides the desired passive lifecycle. |
| Retry/restart, releasing controlling algo or reactivating incomplete parent | Can make unfilled quantity eligible again. | Prohibited during this test; ambiguous submission enters recovery only. |

The native plain limit algo is non-blocking and contains one submit call, no
management/repricing loop. `Algo.get_and_submit_broker_order_for_contract_order`
reaches `dataBroker.submit_broker_order`, then IB `broker_submit_order`, which
contains one `placeOrder` call. A single outright +1 order therefore has at most
one contract of fills, provided there are no other orders or actors. A return
from `placeOrder` is not proof of broker acknowledgement.

## Capacity accounting: concrete failure modes

`dataTradeLimits.what_trade_is_possible_for_strategy_instrument` converts quantity
to gross absolute size. `sysdata/production/trade_limits.py` reads instrument-wide
and strategy-specific limits and takes the minimum capacity. Checking does not
reserve anything. Adding usage reads them again, increments objects and writes
each separately; `sysdata/mongodb/mongo_trade_limits.py` overwrites documents.
There is no atomic compare/reserve or transaction spanning broker submission.

The handler calls `add_trade_to_database` AFTER algo submission. Its
`post_trade_processing` later charges `executed_order.trade.total_abs_qty()`
(submitted quantity, not fill quantity), propagates fills and releases algo
control. This runs automatically only for blocking algos. Plain `algoLimit`
does not take that branch: neither its sizing nor this automatic charge protects
the next order. Fill propagation is not a substitute for charging capacity.

`sysobjects/production/trade_limits.py` lazily resets when elapsed time is greater
than the configured days, not at midnight. A read resets only that object until
it is persisted. There is also a sequential edge case: `add_trade` increments
without first resetting; subsequent `as_dict` reads the reset-triggering usage
property and can discard the newly added usage if its loaded timestamp expired.

| Risk class | Concrete outcome |
| --- | --- |
| A: concurrency | Two workers see capacity 1 before either charges; both submit. Separate read/overwrite updates can lose increments. Algo ownership is not a portfolio capacity reservation. |
| B: single path | Multiple limit children can submit without sizing/charging even in one thread. Panic bypasses controls. Expired reset timestamp can erase a sequential charge. Blocking cancellation helper returns after 60 seconds even without confirmed cancellation; processing may then release ownership. |
| C: retries/restarts | Broker acceptance followed by DB failure leaves uncertain external state. Recreating order or clearing ownership may duplicate it. A parent cancelled unfilled can remain eligible for later execution. Reset rollover can restore capacity. |
| D: manual interfaces | Raw manual/direct/panic orders bypass controls; fabricated balance fills corrupt local safety inputs. |

Answer: YES, one single-threaded sequence can submit more than one ES order under
the current controls. NO, the specified single plain-limit submit call on exactly
one +1 outright child has no internal mechanism to submit a second entry. Its
safety rests on the one-attempt rule, not on the turnover counter. Isolation plus
that rule and the explicit checks is sufficient; concurrency alone is not the
whole diagnosis. Broad locking/transaction changes are deferred.

## Selected mechanism and preflight

Use one explicit instrument order under a dedicated, unscheduled strategy name
`sp500_execution_test`, with a unique audit run ID. Use existing
`orderGeneratorForStrategy.apply_overrides_and_position_limits` and
`submit_order_list` in a reviewed manual sequence; no forecast/target generator,
capital allocation or optimal-position persistence is needed. Abort if adjusted
quantity differs from +1. This differs from the raw manual-order menu by explicitly
retaining the generator controls. Native child spawning preserves parentage.

Alternatives: raw manual menu needs the same compensating checks and makes them
easier to omit; temporary real-strategy target contaminates its state; IB what-if
does not validate actual acknowledgement/cancellation/accounting. Select the
dedicated explicit order, not a temporary target or scheduler registration.

Before a future order is created:

1. Establish one operator and exclusive execution ownership. Verify OS processes,
   scheduler jobs, other API clients and TWS activity; stopped process flags alone
   are insufficient. No stack-handler service or batch cycle; only named stages.
2. Reconfirm current PAPER session/account DUT077119 using established identity
   evidence; abort if session/account changed. Check broker open orders across
   clients and TWS, fresh executions, and all local pending instrument/contract/
   broker stacks. Require no unresolved or working orders; do not delete them to
   make this gate pass. All ES maturities and local SP500 positions must be zero.
3. Require instrument position cap 1 and add/read back dedicated test-strategy
   SP500 cap 1 via normal control API in the future task. Existing
   `sp500_target_test` limit does not cover a new strategy. Require effective
   override 1.0, unlocked, instrument turnover allowance 1 and used 0. Inspect
   every relevant period/scope; never reset to manufacture capacity.
4. This policy permits only SP500 20260900 / ESU6, conId 649180671, CME, USD,
   multiplier 50, tick 0.25, expiry 2026-09-18 from the handoff. Revalidate exact
   identity and current tradability. Require No_Roll and current priced contract
   still 20260900. Limit this policy to a test before the September 11-14 roll
   review window (before September 11 Asia/Shanghai); otherwise refresh policy
   separately. Do not automatically substitute December or change roll state.
5. Use a liquid open session with valid current bid/ask (observed within 2 seconds)
   and at least 30 minutes until close. Plan cancellation access in TWS as fallback.
   Require the turnover reset deadline at least 10 minutes away for the test.
6. Save preflight evidence and a durable unique run record BEFORE submitting,
   marking the entry attempt spent before the order-capable call. An interrupted
   attempt is never replayed. Review exactly one +1 parent and one +1 outright
   child; panic/roll flags false, no siblings, exact plain limit algo.
7. Immediately reapply position/override checks to the original +1 proposal, check
   lock/broker zero/open orders, then explicitly call native
   `apply_trade_limits_to_contract_order` on the inspected unfilled limit child.
   Require exactly +1. Run native `preprocess_contract_order` and inspect result.
   Under exclusive ownership, call `send_to_algo` ONCE and `add_trade_to_database`
   once on its result. Do not invoke the generic all-orders loop. These named
   handler methods are staged use, not starting a stack-handler process.

## Order lifecycle and exit policy

Entry: BUY exactly 1 ESU6, plain DAY LMT, no attached order, stop, algorithmic
repricing or automatic replacement. Set limit to fresh bid minus four ticks
(1.00 index point), tick aligned; verify below ask immediately before sending.
Non-marketable is an initial condition, not a no-fill guarantee. Verify actual
IB ticket quantity, account, contract, limit and DAY before treating ack as valid.

Stop all NEW submission capability immediately after the single attempt; keep
broker observation, cancellation and accounting active. Cancel the exact order
immediately on Submitted/PreSubmitted acknowledgement, or at 10 seconds from
attempt if acknowledgement has not arrived, whichever comes first. Cancel earlier
on unexpected status/fields, quote loss, disconnect, local write failure or operator
abort. No second entry even if rejected or cancelled with zero fills.

Allow at most 30 seconds after cancellation request to establish terminal broker
status and reconcile executions. PendingCancel is not cancellation. On timeout,
use TWS to inspect/cancel that same identified order; never send an offset against
an uncertain working entry. If connection/cancellation remains unavailable, stop
the test, retain supervision and seek broker support; do not declare success or
promise a timed flatten during an outage. An outstanding single entry still has
at most one contract of potential fills. Record this as failed/incomplete.

One outright ES contract cannot normally have a nonzero fractional partial fill.
If status reports a partial fill, cancel remainder, reconcile actual executions
and broker position; inconsistent/fractional data is an immediate stop, not a
reason to round or send another order. If a valid filled position is +1, apply the
full-fill procedure only after no entry quantity remains working.

Zero fill: confirm terminal cancel/reject, zero broker position and no open ES
orders; propagate native zero-fill state, then retire the unfilled parent/child
using completion/inactivation tooling so it cannot be resubmitted. Preserve audit
history. Do not rely on an algo-controlled flag as permanent retirement.

Full fill: reconcile entry executions and normal fill propagation first where
available; immediately prepare a SELL 1 of the exact same contract to flatten.
Target initiation within 30 seconds of confirmed entry terminal state and +1
broker position. This contingency must be approved as part of the future test
BEFORE entry: one supervised TWS PAPER market close, only after fresh broker +1
and zero working ES orders. It is an explicit administrative risk-reducing exit
exception to application turnover, NOT a claim that the configured allowance
permits a round trip. No limit increase/reset, panic order, opposite speculative
position, repeated close or automated retry is allowed. The close must satisfy
quantity = actual position = 1, SELL direction, and projected position zero.
If this contingent exception is not accepted, do not enter the test.

Observe close for 10 seconds, then cancel any confirmed unfilled remainder and
resolve through TWS. If outcome is uncertain, no replacement; recovery requires
fresh terminal order/execution/position evidence. There is no guaranteed time to
flat if IB is unavailable. Never flatten from local stale position alone.

Accounting: for the entry use broker fill -> contract fill -> instrument fill
methods in `sysexecution/stack_handler/fills.py` and normal completion/history.
Plain limit needs explicit one-time `add_trade_to_trade_limits` after persistence;
record that charge in the audit, confirm readback, and keep the run spent even
if charging fails. Submitted entry quantity is 1 even on zero-fill cancellation;
do not refund/reset it. Avoid reset boundaries and never blindly repeat a charge.
For the external close, import the actual execution once using the existing
`stackHandlerCreateBalanceTrades.create_balance_trade`/balance-trade interface,
with exact execution evidence, quantity, price, time, commission and dedicated
strategy attribution. This writes accounting, not another broker order. Verify
entry accounting before applying the close; if unavailable, recover entry first.
Do not fabricate fills or set position tables to zero. Keep a unique execution-ID
audit check before any balance import/retry. Record external close turnover
separately; the application counter is not a complete round-trip ledger.

Success requires two fresh agreeing broker snapshots at least 5 seconds apart:
zero ES positions across maturities, no working ES orders, executions matching
recorded entry/close quantities; local contract and dedicated strategy SP500 zero,
aggregate SP500 zero, parent/child/broker histories linked and retired, commissions
accounted for (pending commissions keep accounting incomplete), and unchanged
real strategy target/capital and roll state. Unrelated equity holdings are outside
this reconciliation. Cancellation-only validates lifecycle and zero-fill handling;
it does not certify nonzero-fill accounting.

Any identity, quantity, contract, position, control, order-count, ownership or
reconciliation mismatch stops entry immediately. After exposure exists, stopping
means recovery-only supervision, not abandoning the position. Retain test limits
and audit history until flat/complete; remove temporary strategy-specific control
only afterward using normal API, leaving instrument and real-strategy controls.

IB reference for cancellation semantics:
https://interactivebrokers.github.io/tws-api/order_submission.html
(PendingCancel does not establish cancellation; executions must be monitored).
