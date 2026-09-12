"""Bounded, read-only IB bootstrap. Run with python -m; never places orders.

Raw snapshots survive validation failures. Existing production files are never
overwritten. The calendar has explicit sample boundaries, not invented rolls.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractFinalPrices
from sysobjects.roll_calendars import rollCalendar
from sysobjects.rolls import rollParameters
from sysobjects.multiple_prices import futuresMultiplePrices
from sysobjects.adjusted_prices import futuresAdjustedPrices

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "project/data/bootstrap/sp500_first_roll"
STORE = ROOT / "data/parquet"
IDENTITIES = {
    "20260600": (649180678, "ESM6", "20260618"),
    "20260900": (649180671, "ESU6", "20260918"),
    "20261200": (515416632, "ESZ6", "20261218"),
}


def validate_prices(frame: pd.DataFrame) -> dict:
    if frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("BLOCKER: missing daily prices")
    if frame.index.hasnans or not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("BLOCKER: invalid timestamp ordering/uniqueness")
    values = frame[["OPEN", "HIGH", "LOW", "FINAL", "VOLUME"]]
    bad = (~np.isfinite(values).all(axis=1) | (values.VOLUME < 0)
           | (values[["OPEN", "HIGH", "LOW", "FINAL"]] <= 0).any(axis=1)
           | (values.HIGH < values[["OPEN", "LOW", "FINAL"]].max(axis=1))
           | (values.LOW > values[["OPEN", "HIGH", "FINAL"]].min(axis=1)))
    return {"rows": len(frame), "start": str(frame.index[0]), "end": str(frame.index[-1]),
            "ohlcv_warning_dates": [str(x) for x in frame.index[bad]],
            "zero_volume_rows": int((values.VOLUME == 0).sum())}


def build_chain(frames: dict) -> tuple:
    # Exclude suspect bars from derivation only; preserve every raw observation.
    finals = {}
    for key, frame in frames.items():
        warnings = validate_prices(frame)["ohlcv_warning_dates"]
        finals[key] = frame.FINAL.drop(index=pd.to_datetime(warnings)).copy()
    prices = dictFuturesContractFinalPrices(finals)
    config = pd.read_csv(ROOT / "data/futures/csvconfig/rollconfig.csv", index_col=0).loc["SP500"]
    params = rollParameters(config.HoldRollCycle, config.PricedRollCycle,
                            config.RollOffsetDays, config.CarryOffset, config.ExpiryOffset)
    actual = rollCalendar.create_from_prices(prices, params)
    if len(actual) != 1 or not actual.check_dates_are_valid_for_prices(prices):
        raise ValueError("BLOCKER: expected one valid completed roll")
    roll = actual.index[0]
    start = max(s.index.min() for s in finals.values())
    end = min(finals[k].index.max() for k in ("20260900", "20261200"))
    if not start < roll < end:
        raise ValueError("BLOCKER: insufficient pre/post-roll coverage")
    calendar = rollCalendar(pd.DataFrame([
        ["20260600", "20260900", "20260900"],
        ["20260600", "20260900", "20260900"],
        ["20260900", "20261200", "20261200"],
    ], index=[start - pd.Timedelta(seconds=1), roll, end],
        columns=["current_contract", "next_contract", "carry_contract"]))
    multiple = futuresMultiplePrices.create_from_raw_data(calendar, prices)
    if not multiple.index.is_unique or not multiple.index.is_monotonic_increasing:
        raise ValueError("BLOCKER: invalid derived index")
    if not np.isfinite(multiple[["PRICE", "FORWARD", "CARRY"]]).all().all():
        raise ValueError("BLOCKER: missing derived prices")
    switches = multiple.PRICE_CONTRACT.ne(multiple.PRICE_CONTRACT.shift()).iloc[1:]
    if switches.sum() != 1:
        raise ValueError("BLOCKER: expected exactly one price contract transition")
    adjusted = futuresAdjustedPrices.stitch_multiple_prices(multiple)
    spread = float(finals["20260900"].loc[roll] - finals["20260600"].loc[roll])
    expected = multiple.PRICE.copy()
    expected.loc[:roll] += spread
    np.testing.assert_allclose(adjusted.values, expected.values, rtol=0, atol=1e-9)
    for name in ("PRICE", "FORWARD", "CARRY"):
        for date, row in multiple.iterrows():
            if row[name] != finals[row[name + "_CONTRACT"]].loc[date]:
                raise ValueError("BLOCKER: source mapping mismatch")
    overlap = pd.concat([finals["20260600"], finals["20260900"]], axis=1).dropna()
    if len(overlap.loc[:roll]) < 5 or (multiple.index > roll).sum() < 5:
        raise ValueError("BLOCKER: insufficient observations around roll")
    return calendar, multiple, adjusted, {"roll_date": str(roll), "roll_spread": spread,
        "overlap_rows": len(overlap), "rows": len(multiple), "start": str(multiple.index[0]),
        "end": str(multiple.index[-1]), "calendar_roles": ["start_boundary", "real_roll", "end_boundary"]}


def acquire() -> dict:
    from ib_async import IB, Future, util
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    ib = IB()
    identities = {}
    try:
        ib.connect("127.0.0.1", 4002, clientId=19361, timeout=12, readonly=True)
        for key, expected in IDENTITIES.items():
            details = ib.reqContractDetails(Future(symbol="ES", lastTradeDateOrContractMonth=key[:6],
                exchange="CME", currency="USD", multiplier="50", includeExpired=True))
            if len(details) != 1:
                raise ValueError("BLOCKER: ambiguous IB identity")
            contract = details[0].contract
            if (contract.conId, contract.localSymbol, contract.lastTradeDateOrContractMonth) != expected:
                raise ValueError("BLOCKER: IB identity changed")
            if (contract.secType, contract.symbol, contract.exchange, contract.currency,
                contract.multiplier, contract.tradingClass) != ("FUT", "ES", "CME", "USD", "50", "ES"):
                raise ValueError("BLOCKER: incorrect ES specification")
            identities[key] = contract.dict()
            if key == "20261200":
                continue
            path = ARCHIVE / (key + "_raw.parquet")
            if path.exists():
                continue
            end, duration = (("20260619 00:00:00 UTC", "45 D") if key == "20260600"
                             else ("20260905 00:00:00 UTC", "130 D"))
            contract.includeExpired = True
            bars = ib.reqHistoricalData(contract, endDateTime=end, durationStr=duration,
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=False, formatDate=1, timeout=60)
            raw = util.df(bars)
            if raw is None or raw.empty:
                raise ValueError("BLOCKER: no IB history for " + key)
            raw.to_parquet(path, index=False)
            identities[key]["request"] = {"end": end, "duration": duration, "bar": "1 day", "useRTH": False, "whatToShow": "TRADES"}
    finally:
        ib.disconnect()
    (ARCHIVE / "identities.json").write_text(json.dumps(identities, indent=2), encoding="utf-8")
    return identities


def run(acquire_data: bool = False) -> None:
    from syscore.dateutils import replace_midnight_with_notional_closing_time
    if acquire_data:
        acquire()
    frames = {}
    for key in IDENTITIES:
        if key == "20261200":
            frames[key] = pd.read_parquet(STORE / f"futures_contract_prices/Day@SP500#{key}.parquet")
        else:
            raw = pd.read_parquet(ARCHIVE / (key + "_raw.parquet"))
            frame = raw[["open", "high", "low", "close", "volume"]].copy()
            frame.columns = ["OPEN", "HIGH", "LOW", "FINAL", "VOLUME"]
            frame.index = pd.DatetimeIndex([replace_midnight_with_notional_closing_time(pd.Timestamp(d).to_pydatetime()) for d in raw.date])
            frames[key] = frame
    report = {"contracts": {k: validate_prices(v) for k, v in frames.items()}}
    for key, frame in frames.items():
        after_expiry = frame.index.normalize() > pd.Timestamp(IDENTITIES[key][2])
        report["contracts"][key]["excluded_after_expiry"] = [str(x) for x in frame.index[after_expiry]]
        frames[key] = frame.loc[~after_expiry].copy()
        report["contracts"][key]["usable_coverage"] = validate_prices(frames[key])
        if frames[key].index.min() > pd.Timestamp("2026-06-03") or frames[key].index.max() < pd.Timestamp("2026-06-17"):
            raise ValueError("BLOCKER: request did not cover the roll window")
    report["source_sha256"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ARCHIVE / "20260600_raw.parquet", ARCHIVE / "20260900_raw.parquet",
                  STORE / "futures_contract_prices/Day@SP500#20261200.parquet"]}
    calendar, multiple, adjusted, derived = build_chain(frames)
    report["derived"] = derived
    outputs = {ARCHIVE / "bounded_calendar.csv": calendar}
    for key, frame in frames.items():
        if key != "20261200":
            outputs[STORE / f"futures_contract_prices/Day@SP500#{key}.parquet"] = frame
        outputs[STORE / f"futures_contract_prices/SP500#{key}.parquet"] = frame
    outputs[STORE / "futures_multiple_prices/SP500.parquet"] = pd.DataFrame(multiple)
    outputs[STORE / "futures_adjusted_prices/SP500.parquet"] = pd.DataFrame({"price": adjusted})
    # Preflight every target before any derived writes. Reruns verify equality.
    for path, frame in outputs.items():
        if path.exists() and path.suffix == ".parquet":
            pd.testing.assert_frame_equal(pd.read_parquet(path), pd.DataFrame(frame), check_dtype=False, check_freq=False)
    for path, frame in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if path.suffix == ".csv":
                frame.to_csv(path)
            else:
                frame.to_parquet(path)
        if path.suffix == ".parquet":
            pd.testing.assert_frame_equal(pd.read_parquet(path), pd.DataFrame(frame), check_dtype=False, check_freq=False)
    report["sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}
    (ARCHIVE / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true")
    run(parser.parse_args().acquire)
