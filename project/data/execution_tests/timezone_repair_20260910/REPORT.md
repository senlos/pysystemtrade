# Asia/Shanghai trading-hours configuration repair — 2026-09-10

Result: PASS. Applied only the authorized paired configuration correction.
No production code, market-data, strategy, positions, limits, capital, roll or
orders were changed. No PAPER execution is authorized by this repair.

## Configuration and translation

- Modified private/private_config.yaml: added GMT_offset_hours: 8.
- Created private/private_config_trading_hours.yaml from the repository default.
- Preserved all 11 keys, including example schedules. Source file unchanged.
- Private file selection and effective offset confirmed in a fresh Python process.

| Entry | Original documented GMT | Local representation (daily unless specified) |
|---|---|---|
| US/Central | 15:00-20:00 | 00:00-04:00; 23:00-23:59 |
| US/Eastern | 14:00-19:00 | 00:00-03:00; 22:00-23:59 |
| GB-Eire | 09:00-16:00 | 17:00-23:59 |
| MET | 08:00-15:00 | 16:00-23:00 |
| Japan | 01:00-06:00 | 09:00-14:00 |
| HongKong | 01:00-06:00 | 09:00-14:00 |
| Hongkong | 01:00-06:00 | 09:00-14:00 |
| Australia/NSW | 22:00-next day 03:00 | 06:00-11:00 |
| US2_example | 19:00-21:00; 18:05-18:10 | 03:00-05:00; 02:05-02:10 |
| US10_example | 19:00-21:00 | 03:00-05:00 |
| EDOLLAR_example | Weekday-specific | Mon 22:00-22:05, 23:00-23:59; Tue 00:00-05:00; Wed 00:00-05:00; Thu 01:00-05:00; Fri 02:00-05:00; Sat 03:00-05:00; Sun closed |

US/Central and US/Eastern omit the open interval (23:59:00, 00:00:00)
each day. EDOLLAR_example omits that interval Monday night only. GB-Eire
omits its last minute through the midnight endpoint; its intended interval
ends there, so no next-day positive-duration segment is needed. No other gaps
were introduced. These are explicitly authorized conservative false-negatives;
there is no compensation by widening another interval. Minute-resolution parser
and inclusive endpoint comparisons are unchanged.

Independent checks compared a full week of membership at every minute boundary
and half-minute against the original intended intervals shifted eight hours.
All 11 entries passed: no expansion, omissions only at the documented midnight
boundaries. Exact translated structures were also checked against the source.

## Fresh read-only native validation

Fresh process started September 10 21:51:12 +08:00. Connected directly with
client 19392, readonly=True, no startup portfolio/order fetch; placeOrder,
cancelOrder and reqGlobalCancel blocked by audit guards. Native instrument and
contract adapters used without a production dataBlob or DB client allocation.
Direct client disconnected in finally. Mongo was used only for raw read snapshots.

Exact ESU6 identity: conId 649180671, CME, USD, multiplier 50, expiry 20260918,
minimum tick 0.25. Fresh IB timeZoneId US/Central and tradingHours began
20260909:1700-20260910:1600. Native fixed timezone adjustment plus existing safety
trimming produced September 10 08:00 to September 11 05:00 Shanghai. The saved
hours intersection returned September 10 23:00-23:59, September 11 00:00-04:00.
Full raw envelope and all future effective intervals are in validation.json.

Native APIs accept only now(); an isolated test-process clock substitution
exercised the unchanged adapter.is_contract_okay_to_trade, without editing code
or changing the machine clock. Results:

| Shanghai timestamp | Native gate |
|---|---|
| Sep 10 22:59:59 | False |
| Sep 10 23:00:00 / 23:30:00 / 23:59:00 | True |
| Sep 10 23:59:30 | False |
| Sep 11 00:00:00 / 03:59:59 / 04:00:00 | True |
| Sep 11 04:00:01 | False |

Actual runtime gate at 21:51 was False, as expected; no waiting or execution.

## Regression evidence and remaining limitation

before.json and after.json contain SHA256 manifests of private files, all Parquet
files and relevant production source trees, plus canonical hashes/counts for every
production Mongo collection. Only the two authorized config paths differed.
All stored historical futures timestamps/data, continuous prices, strategy target
and backtests, capital, local positions, limits and roll state were unchanged.
Private YAML comparison confirmed only GMT_offset_hours added; account DUT077119
unchanged. No broker order was created, submitted or cancelled. This is a check
of this task's mutations, not a new external-account reconciliation.

The GMT setting affects future runtime timestamp interpretation; existing stored
files were neither recalculated nor rewritten. Existing fixed-offset/DST safety
trimming remains unchanged. Midnight-gap limitation is MATERIAL BUT NON-BLOCKING;
revisit only for a need to trade that exact minute, another market making the gap
material, or a later trading-hours implementation revision.

Run read-only verification in a new process with:
`.venv-py312/Scripts/python.exe -B -m data.execution_test.timezone_repair_20260910.audit validate`
The repair mode refuses to overwrite the now-existing private hours file.

Stop here. The next execution attempt requires a freshly reviewed/renewed policy
and fresh preflight; the old execution policy expires September 11 local midnight.
