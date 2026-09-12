# Controlled PAPER execution test — stopped before order creation

2026-09-10 22:09:57 Asia/Shanghai. Outcome: STOP, not a successful submission test.
Native ESU6 tradability returned False. Effective current session starts 23:00;
no gate bypass, wait-and-retry, parent, child, broker submission or cancellation.
Read-only client 19392 disconnected cleanly. Order APIs were patched to fail.

Fresh evidence: configured and managed account DUT077119; GMT offset 8;
ESU6 conId 649180671, CME/USD/50, expiry September 18, tick 0.25; stored No_Roll;
instrument and real-strategy caps 1; turnover 1/day, stored used 0, reset timestamp
September 10 20:19:00.186. Dedicated test-strategy cap remains absent.

Full preflight was not completed after the failed gate. Current TWS PAPER UI,
active PRICE, actual broker/local positions, open orders, override/lock and
exclusive process ownership are NOT certified by this attempt. Prior zero
positions/open orders are historical evidence only. No order IDs, quote, limit,
acknowledgement or lifecycle exist for this attempt. No runtime mutations were
requested; no strategy, control, roll, capital or execution-source changes made.

Policy review preserves scope and expiry before September 11 local; it replaces
older pre-authorized flatten requirements with the user's stop-and-seek-separate-
authorization instruction. Gate False and absent dedicated cap are BLOCKERS;
accepted timezone/gap and authorization clarification are NON-BLOCKING.

Validation: guarded diagnostic completed and saved preflight.json; no production
code changed. Initial sandbox Python launch failed before script execution;
the permitted runtime invocation then completed successfully. Git diff reviewed.

Next subtask: a fresh controlled PAPER attempt during the allowed session,
with fresh TWS identity, dedicated cap setup via native API, and all preflight
gates immediately before creation. Renew policy again if its date boundary passes.
Cancellation-only testing will not certify nonzero-fill accounting.
