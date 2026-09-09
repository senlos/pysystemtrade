"""One-shot production target audit. No broker or order process is invoked."""
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch

from bson import json_util
from syscore.exceptions import missingData
from sysdata.data_blob import dataBlob
from syscontrol.strategy_tools import strategyRunner
from sysproduction.data.backtest import dataBacktest
from sysproduction.data.capital import dataCapital
from sysproduction.data.optimal_positions import dataOptimalPositions
from sysobjects.production.tradeable_object import instrumentStrategy

STRATEGY = "sp500_target_test"
CAPITAL = 10000.0
ROOT = Path(__file__).resolve().parents[2]


def validate_target(target: float, lower: float, upper: float) -> None:
    if not all(math.isfinite(x) for x in (target, lower, upper)):
        raise ValueError("Nonfinite target/buffers")
    if not lower <= target <= upper:
        raise ValueError("Target outside buffers")


def parquet_hashes() -> dict:
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "data/parquet").rglob("*.parquet")}


def mongo_snapshot(data: dataBlob) -> dict:
    db = data.mongo_db.db
    return {name: sorted(json_util.dumps(doc, sort_keys=True) for doc in db[name].find())
            for name in sorted(db.list_collection_names())}


def last(series) -> float:
    return float(series.iloc[-1])


def main(verify_existing: bool = False) -> None:
    out = ROOT / "data/strategy_target/sp500_target_test"
    out.mkdir(parents=True, exist_ok=True)
    with patch.object(dataBlob, "_get_new_ib_connection",
                      side_effect=RuntimeError("Broker access forbidden in target audit")) as broker_guard:
        data = dataBlob(log_name="sp500_target_audit")
        before_db, before_files = mongo_snapshot(data), parquet_hashes()
        if verify_existing:
            original = json.loads((out / "before.json").read_text())
            before_db = original["mongo"]
            before_files = {k.replace("\\", "/"): v for k, v in original["parquet"].items()}
        else:
            (out / "before.json").write_text(json.dumps(dict(mongo=before_db, parquet=before_files), indent=2))
        runner = strategyRunner(data, STRATEGY, "run_systems", "run_backtest")
        classic = runner.strategy_method.__self__
        system = classic.system_method(notional_trading_capital=CAPITAL, base_currency="USD")
        if system.get_instrument_list() != ["SP500"]:
            raise ValueError("Universe must be SP500 only")
        target = last(system.portfolio.get_notional_position("SP500"))
        buffers = system.portfolio.get_buffers_for_position("SP500").iloc[-1]
        validate_target(target, float(buffers.bot_pos), float(buffers.top_pos))
        capital = dataCapital(data)
        try:
            existing = capital.get_current_capital_for_strategy(STRATEGY)
        except missingData:
            if verify_existing:
                raise
            capital.update_capital_value_for_strategy(STRATEGY, CAPITAL)
        else:
            if existing != CAPITAL:
                raise ValueError("Refusing to replace different existing strategy capital")
        if classic._get_currency_and_capital() != ("USD", CAPITAL):
            raise ValueError("Unexpected production capital/currency")
        if not verify_existing:
            runner.run_strategy_method()
        positions = dataOptimalPositions(dataBlob())
        entry = positions.get_current_optimal_position_for_instrument_strategy(
            instrumentStrategy(strategy_name=STRATEGY, instrument_code="SP500"))
        for actual, expected in [(entry.lower_position, buffers.bot_pos),
                                 (entry.upper_position, buffers.top_pos)]:
            if not math.isclose(actual, expected, rel_tol=1e-12):
                raise ValueError("Persisted buffers differ")
        saved = dataBacktest(data).get_most_recent_backtest(STRATEGY)
        saved_target = last(saved.system.portfolio.get_notional_position("SP500"))
        if not math.isclose(saved_target, target, rel_tol=1e-12):
            raise ValueError("Snapshot target differs")
        multiple = system.data.get_instrument_raw_carry_data("SP500")
        adjusted = system.data.get_raw_price("SP500")
        if entry.reference_price != adjusted.iloc[-1] or str(entry.reference_contract) != str(int(multiple.PRICE_CONTRACT.iloc[-1])):
            raise ValueError("Reference mismatch")
        after_db, after_files = mongo_snapshot(data), parquet_hashes()
        changed = sorted(k for k in set(before_files) | set(after_files)
                         if before_files.get(k) != after_files.get(k))
        allowed = {"data/parquet/capital/sp500_target_test.parquet",
                   "data/parquet/optimal_positions/sp500_target_test SP500.parquet"}
        if set(changed) - allowed:
            raise ValueError(f"Unexpected Parquet changes: {changed}")
        if before_db != after_db:
            raise ValueError("Mongo state changed")
        broker_guard.assert_not_called()
        report = dict(strategy=STRATEGY, instrument="SP500", capital=CAPITAL,
                      currency="USD", percentage_vol_target=system.config.percentage_vol_target,
                      data_timestamp=str(adjusted.index[-1]), adjusted_rows=len(adjusted),
                      adjusted_price=float(adjusted.iloc[-1]), multiple_latest=multiple.iloc[-1].to_dict(),
                      raw_forecasts={r:last(system.rules.get_raw_forecast("SP500", r)) for r in ("ewmac8", "ewmac32")},
                      capped_forecasts={r:last(system.forecastScaleCap.get_capped_forecast("SP500", r)) for r in ("ewmac8", "ewmac32")},
                      combined_forecast=last(system.combForecast.get_combined_forecast("SP500")),
                      daily_price_volatility=last(system.rawdata.daily_returns_volatility("SP500")),
                      daily_cash_vol_target=system.positionSize.get_daily_cash_vol_target(),
                      average_position=last(system.positionSize.get_average_position_at_subsystem_level("SP500")),
                      subsystem_position=last(system.positionSize.get_subsystem_position("SP500")),
                      instrument_weight=float(system.portfolio.get_instrument_weights().SP500.iloc[-1]),
                      instrument_div_multiplier=system.config.instrument_div_multiplier,
                      target=target, persisted=vars(entry), snapshot_timestamp=saved.timestamp,
                      changed_parquet=changed, mongo_unchanged=True, broker_connection_attempts=broker_guard.call_count,
                      broker_verification="No broker access; no broker mutation possible through this run. External account state not queried.",
                      completed_at=str(datetime.datetime.now()))
        (out / "result.json").write_text(json.dumps(report, indent=2, default=str))
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main(verify_existing="--verify-existing" in sys.argv)
