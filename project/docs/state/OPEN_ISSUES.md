# Open Issues

## DATA-ROLL-001: latest-session roll inputs not final-session certified
Classification: MATERIAL BUT NON-BLOCKING for completed native mechanical roll.
September 12 00:39 Shanghai: normal SP500 roll used September 11 daily bars while
that session was still open. Native selector passed liquidity (ratio 0.0393077)
and zero position, and native builder/readback passed; it has no completed-session
gate. Roll differential +67.50; no manual adjustment or forced roll.
Revisit after session completion: compare matched final roll-window bars with
saved raw/source observations, and assess any material adjustment effect through
normal data procedures. Append maintenance preserves existing timestamps, so a
repeat refresh alone does not certify final values. No isolated historical anomaly
investigation now. Evidence: project/data/maintenance/sp500_20260912/REPORT.md.

September 12 update to IB-HIST-003: March is now FORWARD/CARRY after the native
roll; latest price 7788.00 has zero volume. December/March have 253 matched rows,
42 both positive volume, latest positive pair September 10. Exact September 11
price overlap passes the normal builder, but fresh carry liquidity is not certified.

## EXEC-QUOTE-001: live ES bid/ask unavailable
Issue: Live ES bid/ask unavailable because the current IB account lacks the
required real-time CME/ES Level 1 market-data entitlement. IB error 354 observed
September 12 00:23 Shanghai; ESU6 bid/ask NaN and quote timestamp absent.

Impact: Blocks reliable construction of the deliberately passive one-contract
limit order required by ../policies/EXECUTION_TEST_POLICY.md.

Status: BLOCKER for actual broker submission. FIRST PAPER broker-submission
execution subtask PAUSED, not failed, and closed for now before order creation.
NON-BLOCKING for production data maintenance, strategy calculation, target
generation, controls, dry-run order logic, roll operations and other
non-submission work, subject to their own gates.

Revisit trigger: Appropriate live CME/ES Level 1 bid/ask becomes available.
Do not investigate further now. No workaround using delayed data, historical
data, stale quotes, last/reference prices or guessed passive prices. Any resumed
submission requires a valid execution policy and fresh preflight.

Dedicated sp500_execution_test/SP500 cap remains independently verified at 1;
the earlier missing-cap blocker is resolved. No runtime state changed by this
issue update. Evidence:
project/data/execution_tests/20260912_002124_control_preflight/REPORT.md.

## EXEC-SESSION-001: first PAPER test stopped by native tradability gate
Status: RESOLVED configuration cause, 2026-09-10 21:51 Asia/Shanghai.
GMT defaults had been interpreted as Shanghai wall time. Authorized paired fix:
GMT_offset_hours=8 and a private hours file translating every default entry +8h.
Fresh read-only native ESU6 validation returned September 10 23:00-23:59 and
September 11 00:00-04:00 local. Synthetic gate boundaries and conservative gap
passed; all entries checked for no expansion. No orders or unrelated state changes.
Evidence: project/data/execution_tests/timezone_repair_20260910/validation.json.
Next execution requires a freshly reviewed/renewed policy and fresh preflight.

Historical failed attempt, 2026-09-10 20:36 Asia/Shanghai:
Fresh exact ESU6 identity passed, but native is_contract_okay_to_trade returned
False. Adapter returned September 10 trading hours 15:00-20:00 local; check ran
after this window. This records application tradability, not a conclusion that
the exchange itself was closed. No order was created or submitted and no hours
were changed. Review configured/native session interpretation separately; preserve
the gate. Execution policy expires September 11 Asia/Shanghai and requires a
separate refresh after that date. Evidence:
project/data/execution_tests/20260910_203144/supplementary_preflight.json.

## EXEC-SESSION-002: conservative minute-resolution midnight gap
Classification: MATERIAL BUT NON-BLOCKING; explicitly accepted 2026-09-10.
Current parser supports only same-day minute-resolution intervals. Translated
windows crossing midnight end at 23:59 and resume at 00:00, so times strictly
after 23:59:00 and before midnight are not tradable. No compensating widening.
Applies daily to US/Central (23:00-04:00 intended), US/Eastern (22:00-03:00),
and the EDOLLAR_example Monday-to-Tuesday split (23:00-05:00). GB-Eire's intended
17:00-midnight interval ends at 23:59, omitting its final minute and midnight
endpoint; no positive-duration next-day interval is needed. Other translated
entries have no midnight gap. Example entries remain examples, not SP500 rules.
Fresh native ESU6 test confirms 23:59:30 False and 00:00 True; independent weekly
membership checks find no expanded intervals for any of the 11 entries.
Revisit ONLY if actual production trading needs that exact minute, another
market's required window makes the gap operationally material, or the trading-
hours implementation is later revised. No parser change is part of this repair.

## STRATEGY-TARGET-001: short warm-up and incomplete cost evidence
Classification: MATERIAL BUT NON-BLOCKING for target calculation.
The provided simple EWMAC system produces finite SP500 forecasts and positions
with 99 production observations. EWMAs use min_periods=1 and rule volatility
requires 10 returns; the 128-day slow span is not fully seasoned, the robust
volatility floor has limited history, and the default mixed sizing volatility
has no long history. No history restriction was bypassed or parameter tuned.
Missing Mongo spread cost logs a warning and uses zero in forecast cost checks;
both existing rules pass. Results certify the mechanical calculation/persistence
path only. Revisit warm-up and measured costs before deployment evaluation.

## IB-HIST-001
IB historical daily bars can revise retrospectively.

Evidence:
ESZ6 2025-12-17 originally stored close 7000;
later repeated requests return 6925.75.

Impact:
Potential issue near roll-overlap observations.

Status:
MATERIAL BUT NON-BLOCKING.

Revisit if:
- revision occurs near selected roll date
- revisions appear systematic
- roll construction fails validation

## IB-HIST-002: post-expiry bar in bounded response
Classification: MATERIAL BUT NON-BLOCKING.
ESM6 request ended 2026-06-19 00:00 UTC (45 D, daily TRADES, all sessions).
IB returned 45 observations spanning April 17 through June 22, including a
June 22 zero-volume bar after confirmed June 18 expiry and the request end.
Raw response retained; that row is excluded from usable daily/merged prices.
June 10 roll uses valid positive-volume June/September bars, so construction passes.
Revisit if post-expiry rows recur in incremental ingestion or affect a roll.

## IB-HIST-003: deferred-contract zero volume
Classification: MATERIAL BUT NON-BLOCKING.
Existing ESZ6 seed has 125 zero-volume rows out of 251, with finite sane OHLC.
These were preserved, not forward-filled or replaced. Zero volume alone does
not invalidate the mechanical chain, but carry liquidity/price freshness is
not certified. December is not the price leg in this bounded chain.
Revisit before using carry forecasts or when December becomes the roll target.

Maintenance update September 9: December remains at 125 zero-volume historical
rows; latest September 8 volume is 8768. Newly sampled March 2027 has 208/250
zero-volume rows and latest volume 4. December/March have 40 positive-volume
matched observations, including September 8. Mechanical roll/carry coverage is
sufficient; fresh March carry pricing remains a MATERIAL BUT NON-BLOCKING risk.
December/September smoothed volume ratio 0.005172 fails the configured 0.01
liquidity threshold; recheck before rolling. No roll was performed.

## DATA-BOOT-001: bounded history and calendar
Classification: MATERIAL BUT NON-BLOCKING for bootstrap; prerequisite for ongoing updates.
Continuous data ends September 4 and contains 98 daily observations, insufficient
to assume readiness for arbitrary strategy lookbacks. No intraday data acquired.
Bounded calendar's first/last rows are sample boundaries, not actual rolls.
Do not install this calendar as an ongoing production roll schedule.
Existing configured approximate expiry offset 14 and roll offset -5 select
June 10, rather than actual IB expiry minus five days; configuration is preserved.
Revisit during incremental update/September roll scheduling, and before selecting
strategy history requirements. No need to extend unrelated history now.

Maintenance update September 9: sampling metadata now registered and ongoing
updates validated; continuous history now 99 rows through September 8. Production
uses actual expiry September 18 minus five calendar days = September 13; the
approximate bootstrap schedule is not installed or used for ongoing rolls.

## PAPER-001: account identity/configuration resolved (2026-09-09)
Status: RESOLVED. User manually verified the currently connected TWS explicitly
shows PAPER / Simulated Trading and account DUT077119; accepted as sufficient
project evidence. broker_account corrected from tradersenlos to DUT077119.
Normal account-filtered production capital, position and open-order reads passed;
fresh SP500 contract details passed and client 100 was released cleanly.
Evidence: project/data/account_validation/result.json. Execution controls remain a
separate prerequisite; this resolution does not authorise order generation.

## DATA-BOOT-002: request coverage semantics
Classification: INFORMATIONAL.
Bounded requests returned 45 and 130 daily observations, spanning more calendar
days than the duration labels suggest. Actual first/last timestamps are recorded
in validation.json; overlap and post-roll coverage are sufficient.
Revisit only if a bounded request omits required roll-window observations.

## DATA-MAINT-001: session definition across bootstrap/maintenance
Classification: MATERIAL BUT NON-BLOCKING.
Normal production requests useRTH=True; the bounded June/September bootstrap
used all sessions. Normal append preserves the older bars and adds only newer
timestamps, so OHLC/volume session definitions may differ across the boundary.
September 8 PRICE/FORWARD/CARRY inputs all have the same production request
settings, pass OHLC checks, and have matched coverage. No historical rewrite
was attempted. Revisit before session-sensitive strategy/volume analysis or if
fresh matched roll observations disagree; use refreshed same-session observations
for the upcoming roll.

### PAPER-001 final verification (2026-09-09)
Configured and managed account both DUT077119. Broker holds AAPL +1 and QQQ +100,
no futures; local and broker SP500 actual both 0. No open broker orders returned.
Earlier API-only identity blocker is superseded by the user's TWS confirmation.

## EXEC-CONTROLS-001: explicit test risk bounds absent
Status: RESOLVED 2026-09-10 for missing configuration. SP500 instrument and
sp500_target_test/SP500 absolute position limits each 1; instrument turnover
allowance 1 per one-day elapsed reset period, used 0. Independent readback PASS;
unlocked, override 1.0. Native non-mutating decision NO TRADE. See
project/data/execution_controls/REPORT.md. This does not certify all execution paths.

## EXEC-CONTROLS-002: execution bounds have bypasses and no atomic reservation
Classification: MATERIAL BUT NON-BLOCKING for the exclusive one-attempt procedure
in ../policies/EXECUTION_TEST_POLICY.md; still BLOCKER for an unconditional cap, unattended
execution, generic cycles or automatic retries. Reviewed 2026-09-10.
Position limits use recorded net positions, without working-order reservation.
Panic bypasses downstream checks. Limit orders skip trade sizing AND, being
non-blocking, skip automatic handler post_trade_processing usage charging.
Concurrent read/check/submit/read/overwrite can overtrade and lose increments.
Sequential lazy reset can erase newly added usage at persistence when the loaded
reset timestamp has expired. These are demonstrated in offline audit tests.
Broker acceptance before local persistence and cancellation timeout followed by
ownership release leave retry/restart ambiguity. No automatic recovery is safe
without broker reconciliation. Deferred production fixes; do not generalise the
single-order operational assurance to normal execution.
Selected procedure explicitly checks native controls/capacity, has one +1 child
and one spent attempt, charges limit usage explicitly once and never re-enters.
One-contract turnover cannot support entry plus exit. Current September 10
execution instructions supersede prior pre-authorized-close requirements: on any
fill stop, record state and request separate manual-flatten authorization; no
automatic flatten or additional turnover is authorized. No control reset/increase is proposed. Cancellation-only success
does not validate nonzero-fill accounting; outages prevent guaranteed time to flat.
