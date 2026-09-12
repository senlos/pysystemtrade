# Dedicated cap configured; execution stopped at live-quote gate

September 12, 2026, 00:21-00:23 Asia/Shanghai. No order creation or submission.

Persistent authorized change:
- Normal dataPositionLimits.set_position_limit_for_instrument_strategy called
  with instrumentStrategy('sp500_execution_test', 'SP500'), new_position_limit=1.
- Separate Python process and Mongo connection read exactly one matching
  strategy_instrument document with position_limit 1.0.
- Fresh normal get_maximum_position_contracts_for_instrument_strategy returned
  1.0. Global SP500 cap and sp500_target_test/SP500 cap remain 1.
- All production Mongo collections were compared before/after, excluding only
  this new document; exact equality passed. Broker connectivity was blocked
  during the write and effective-value check. No other control mutation requested.
- Evidence: controls_before.json and controls_after.json in this directory.
  No capital, forecasts, optimal positions, roll or broker position writes.

Remaining preflight observations:
- Elevated OS process query: TWS process 27168, no Python workers. Scheduled-task
  filter for Python/pysystemtrade/execution actions returned no matching tasks.
- 00:23:17-18 native reads: configured DUT077119, broker futures positions empty,
  broker open orders empty; local strategy/contract position tables empty,
  aggregate SP500 0; No_Roll; PRICE 20260900; desired roll September 13 00:00;
  override 1.0, unlocked, native trade capacity 1; native tradability TRUE.
- Turnover native read lazily refreshed the expired object in memory, showing
  allowance 1/day and usage 0. No persisted reset, increase or charge requested.
- Direct read-only client 19393: managed account only DUT077119; exact FUT ESU6
  conId 649180671, CME/USD/50, expiry 20260918, tick 0.25. All-client open orders,
  executions and ES positions empty. Evidence: broker_preflight.json.
- Earlier user manual PAPER / Simulated Trading confirmation remains recorded.
  No claim that all final immediately-before-entry gates completed is made.
- Policy time scope remains until September 12 04:00 Shanghai; unchanged here.

BLOCKER: fresh live quote requirement failed at 00:23:52 Shanghai. IB error 354:
requested market data is not subscribed; delayed data is available. Live ESU6
bid/ask and sizes NaN, quote timestamp None, quote_valid false. No delayed-data
fallback, limit calculation, quote bypass or submission retry attempted.

Zero parent, contract child or broker orders; zero submissions/cancellations.
No internal order lifecycle exists. Normal read-only client 100 released and
direct client 19393 disconnected. This remains the FIRST-submission test.

Next: restore live ES quote availability before another fully gated attempt.
Do not substitute stale/delayed quotes. Retain verified dedicated cap 1 and all
other controls. Renew policy if its deadline has passed. No automatic flatten.

Validation: independent control readback, effective-value assertion and full
other-Mongo-state equality passed. No production implementation changed.
