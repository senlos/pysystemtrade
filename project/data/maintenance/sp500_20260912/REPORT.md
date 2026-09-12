# SP500 refresh and September roll — completed

Executed September 12, 2026 at 00:39 Asia/Shanghai; independent verification
passed at 00:40. Stop condition A achieved. No broker orders, order generation,
execution, strategy calculation, or production implementation changes.

## Maintenance

Reused the previous bounded audit with a new evidence directory. Normal
update_active_contracts_for_instrument, get_and_add_prices_for_frequency (daily),
daily-only write_merged_prices_for_contract, then native multiple/adjusted update.
IB readonly=True, placeOrder blocked, Parquet writes allowlisted to SP500.
Normal TRADES/useRTH=True requests and cleaning retained; raw responses saved.

All three contracts advanced from September 8 23:00 to September 11 23:00:

| Contract | Rows before | Rows after | Added | Existing rows changed |
|---|---:|---:|---:|---:|
| September 2026 | 131 | 134 | 3 | 0 |
| December 2026 | 252 | 255 | 3 | 0 |
| March 2027 | 250 | 253 | 3 | 0 |

Daily and merged persisted data match. Multiple and adjusted histories advanced
99 -> 102 rows before roll, with three additions and zero existing changes.
No deleted/duplicate/null/nonfinite rows, invalid OHLC or negative volume.
All historical leg mappings and existing June +60.25 adjustment verified.
Eight intended price files changed; unrelated Parquet/bootstrap hashes unchanged.
Normal client 100 released after both broker phases; locks 106/107/108 unchanged.

## Native readiness and workflow

Before roll: No_Roll; PRICE 20260900, FORWARD/CARRY 20261200; priced position 0.
Proposed and verified: PRICE 20261200, FORWARD/CARRY 20270300.
Desired roll September 13 00:00, actual local calendar date September 12 (before
desired date). Native timedelta.days reports 0 because less than 24 hours remain.

diagVolumes uses the last 14 calendar days and ewm(span=3). Smoothed forward/current
ratio 0.03930773319; forward volume 35688.9002 (selector truncates to 35688).
Rule: ratio > 1 OR (ratio > 0.01 AND forward volume > 100). PASS.
near_expiry_days=10; auto_roll_expired=True; current expiry still five native days
away. Actual suggest_roll_state_for_instrument returned Roll_Adjusted because
liquidity passes and priced position is zero. READY, not forced by the calendar.

September/December: 133 matched observations, 122 both positive volume.
December/March: 253 matched observations, 42 both positive volume (latest positive
pair September 10). Exact September 11 FINAL prices available for every roll leg.
Native builder passes without inference or forward filling. Native workflow does
not require positive carry volume or completed-session certification.

Executed modify_roll_state -> state_change_to_roll_adjusted_prices ->
roll_adjusted_and_multiple_prices with the already-authorized automatic confirmation
option. Normal persistence and restoration to No_Roll succeeded. Broker connection
and interactive fallback blocked throughout. No manual price construction/writes.

## Post-roll checks

Native roll marker: September 11 23:00:01, one second after its source daily row;
this is a synthetic native roll boundary, not execution time or desired date.
PRICE 20261200 = 7740.00; FORWARD/CARRY 20270300 = 7788.00.
Differential 7740.00 - 7672.50 = +67.50, added to every pre-roll adjusted value.
Total adjustment before June's transition is now +127.75.
Existing multiple rows unchanged; one native transition row added (103 total).
Adjusted values immediately before/after marker both 7740.00; no roll-induced jump.
Both persisted outputs equal native recalculation from saved pre-roll snapshots;
no duplicates/nulls/nonfinite rows. Production simulation price/carry readers pass.
Only the two SP500 derived price files changed during the roll. Final No_Roll and
zero priced position verified. No broker connection for rolling; client IDs unchanged.

Audit-only timestamp precision and Series-name comparison errors are retained in
logs. Corrected comparisons passed independently without repeating the roll.
Eight offline audit tests pass. Git diff checked; existing user changes preserved.

## Remaining risk and next task

September 11 is an open-session daily bar at collection time, not a certified
completed-session close. The native latest-bar roll accepts it. IB may revise it;
normal append ingestion does not replace existing timestamps. March's latest price
7788 has zero volume (209 zero-volume historical rows), so mechanical continuity
does not certify fresh carry liquidity. Record this material limitation without
investigating isolated historical revisions in this task.

Next non-blocked subtask: after the September 11 session completes, compare final
matched roll-window bars with saved source observations, assess any material effect
on the +67.50 roll adjustment through the normal data workflow, and perform the
next SP500-only daily refresh. No strategy orders or execution entitlement work.

Evidence: validation.json, roll_preview.json, roll_result.json (initial audit
failure after successful roll), post_roll_validation.json (authoritative PASS),
pre_roll_*.parquet, raw snapshots, logs, and tests.log.
