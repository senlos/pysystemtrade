# Decisions

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
