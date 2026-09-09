# Open Issues

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
Evidence: data/account_validation/result.json. Execution controls remain a
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
Classification: MATERIAL BUT NON-BLOCKING for account identity/read-only checks;
prerequisite before an order-capable test.
Normal local reads report No limit for sp500_target_test/SP500 position limit,
no trade limits, SP500 unlocked, override 1.0. No controls were configured.
Choose explicit bounds and verify enforcement before permitting orders; an
isolated dry-run must prohibit submission and production order-stack writes.
