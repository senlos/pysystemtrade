# Decisions

- 2026-09-12 00:21: User authorized and normal dataPositionLimits interface
  persisted only sp500_execution_test/SP500 absolute position limit 1.
  Independent stored/effective readback passed; other Mongo state unchanged.
  Retain the dedicated cap. No trade allowance, override, lock, strategy input,
  roll or broker position change authorized. Subsequent live-quote gate failed
  with IB error 354; no order created or submitted.

- 2026-09-12: User-authorized execution policy date refresh for this single
  supervised attempt until 04:00 Asia/Shanghai, with native tradability and
  at least 30 minutes before the earlier session/policy close required.
  Preserve PAPER DUT077119, +1 ESU6 only, No_Roll/current PRICE verification,
  one checked parent/child/submission, passive DAY limit, immediate cancellation,
  no retry or automatic flatten; any fill requires separate authorization.
  Fresh missing dedicated strategy cap stopped this attempt before orders.

- 2026-09-10 22:09: Current execution-test authorization supersedes the older
  requirement to pre-authorize contingent flattening: on any fill stop, record
  actual state, and request separate authorization for the documented manual
  close. No automatic flatten or extra turnover is authorized. Preserve all
  other single-attempt PAPER gates and the September 11 local policy expiry.

- 2026-09-10: Deploy paired Asia/Shanghai timezone configuration: private config
  GMT_offset_hours=8 and private/private_config_trading_hours.yaml derived from
  the repository's documented GMT defaults, translating every entry +8 hours
  with weekday rollover. Keep default source, production code, IB safety trimming
  and all historical data unchanged. No historical rewrite accompanies this fix.
- Accept minute-resolution conservative midnight gaps: split at 23:59/00:00,
  never widen adjacent intervals to compensate. US/Central preserves intended
  23:00-04:00 as closely as supported; US/Eastern and example schedules use the
  same convention. GB-Eire ends at 23:59 instead of midnight. Prefer a brief
  false-negative to any permission outside the intended GMT interval. Record as
  MATERIAL BUT NON-BLOCKING (EXEC-SESSION-002); revisit only for an actual need
  to trade that minute, another market making it material, or a later hours-
  implementation revision. No parser fix is authorized in this task.
- Configuration validation is not execution authorization. Stop without orders;
  the next PAPER attempt requires a freshly reviewed/renewed execution policy
  and fresh preflight, even if the repaired gate becomes tradable tonight.

- 2026-09-10: Adopt ../policies/EXECUTION_TEST_POLICY.md for the first supervised SP500 PAPER
  test. Prefer exclusive staged operational control over production code changes:
  one reviewed parent, one outright child, one submission attempt, no retries.
  A generic cycle and stopping observation at acknowledgement are insufficient.
- Recommend a dedicated unscheduled sp500_execution_test explicit order using
  native override/position/lock methods and an explicit native turnover check
  compensating the limit path. Configure its own position limit only in a future
  authorised task; leave real target/capital/forecasts unchanged. Use plain passive
  DAY LMT +1 ESU6, exact identity/session gates, immediate cancellation on ack and
  a 10-second attempt deadline. No order is created by this policy decision.
- Future entry authorisation must include one conditional TWS PAPER SELL 1 market
  close only after terminal entry, broker +1 and no working ES orders. This is a
  narrowly reviewed administrative exit exception to turnover, without increasing
  or resetting controls. If not accepted, do not enter. Reconcile actual fills
  through native accounting and evidence-backed balance import, never synthetic
  position resets. Cancellation uncertainty means recovery only, no replacement.
- Defer general reservation/transaction, limit-path and restart hardening beyond
  this isolated test; they remain material limitations in EXEC-CONTROLS-002.

- 2026-09-10: For the isolated SP500 paper test, use native absolute position
  limits of 1 at instrument and sp500_target_test/SP500 scopes, plus instrument
  gross turnover allowance 1 contract per one-day elapsed reset period. Preserve
  capital, buffers, forecasts, override 1.0, unlocked status and No_Roll. These
  conservative application controls are not an unconditional broker exposure cap;
  require execution-boundary/exit design before any order-capable test. Do not
  raise limits or reset turnover to force an order or exit without separate review.
- Accept native rounding of the persisted lower buffer to 0 as successful
  NO TRADE. Use existing calculation APIs and in-memory instrument-order objects
  only, with submission/stack insertion guarded; do not register/run the mutating
  generator or alter the strategy to obtain a nonzero target.

- 2026-09-09: Use the provided simple two-EWMAC configuration through the native
  runSystemClassic production runner for sp500_target_test, SP500 only. Preserve
  rule speeds/scalars/equal forecast weights/FDM/25% volatility target. Set
  single-instrument weight/diversification to 1; do not optimise parameters.
- Initialise only USD 10000 explicit notional strategy capital through dataCapital;
  global total capital and broker synchronisation are unnecessary for this path.
  Register only backtest loader and run_systems method, invoke once directly,
  and stop at native buffered optimal-position persistence and backtest snapshot.
  This capital is a calculation input, not verified account equity or margin.

- Use bounded production-data bootstrap.
- Do not run full seed_price_data_from_IB across all contracts blindly.
- Preserve raw downloaded data.
- Treat non-blocking IB historical revisions as documented data-quality risk.
- Do not investigate individual data anomalies unless they block the next step.
- 2026-09-09: Use ESM6/ESU6/ESZ6 for the first completed roll test: June and
  September supply the actual price transition; December supplies post-roll
  forward/carry. Reuse the original December seed without refreshing revisions.
- Use existing SP500 roll parameters and native calendar/multiple/Panama builders.
  Preserve an explicitly bounded calendar separately from production schedules;
  sample boundary rows must never be interpreted as actual rolls.
- Preserve raw IB responses; exclude post-expiry bars from usable contract data.
  Daily-only merged contract files are sufficient for this bootstrap. Persist
  derived data only after in-memory validation; refuse conflicting overwrites.

- 2026-09-09: Accept user's manual verification of the current TWS PAPER /
  Simulated Trading session displaying DUT077119 as sufficient paper identity
  evidence. Set only private/private_config.yaml broker_account to DUT077119,
  the managed API account identifier (not login username or alias). Normal
  account-filtered production broker reads validated. This does not authorise
  order generation/submission, capital sync or position reconciliation.
