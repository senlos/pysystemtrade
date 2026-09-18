"""Read-only research helpers for dynamic small-account optimisation.

The functions in this module deliberately use ``csvFuturesSimData`` and the
normal backtest stages.  They do not import production data, broker, order, or
position persistence interfaces.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import platform
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from copy import copy
from dataclasses import asdict, dataclass, replace
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysquant.estimators.covariance import covariance_from_stdev_and_correlation
from sysquant.estimators.mean_estimator import meanEstimates
from sysquant.optimisation.weights import portfolioWeights, seriesOfPortfolioWeights
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.forecasting import Rules
from systems.portfolio import Portfolios
from systems.positionsizing import PositionSizing
from systems.provided.dynamic_small_system_optimise.accounts_stage import (
    accountForOptimisedStage,
)
from systems.provided.dynamic_small_system_optimise.buffering import (
    speedControlForDynamicOpt,
)
from systems.provided.dynamic_small_system_optimise.optimisation import (
    objectiveFunctionForGreedy,
)
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import (
    optimisedPositions,
)
from systems.rawdata import RawData
from systems.risk import Risk


ROOT_BDAYS_INYEAR = math.sqrt(252.0)
BDAYS_INYEAR = 252.0
CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExperimentSpec:
    """Notebook configuration that is safe to serialise and cache."""

    quick_mode: bool = True
    start_date: str = "2021-01-01"
    end_date: str | None = None
    capital_base: float = 100_000.0
    percentage_vol_target: float = 25.0
    selected_instruments: tuple[str, ...] = (
        "SP500",
        "SP500_micro",
        "NASDAQ_micro",
        "US10",
        "EUR_micro",
        "GOLD_micro",
        "CRUDE_W",
        "CORN",
    )
    focus_instruments: tuple[str, ...] = ("SP500_micro", "SP500", "GOLD_micro")
    capital_sweep: tuple[float, ...] = (25_000.0, 100_000.0, 400_000.0)
    shadow_cost_values: tuple[float, ...] = (0.0, 50.0, 100.0)
    tracking_error_buffer_values: tuple[float, ...] = (0.0, 0.0125, 0.025)
    cost_multiplier_values: tuple[float, ...] = (0.5, 1.0, 2.0)
    correlation_shrinkage_values: tuple[float, ...] = (0.0, 0.5, 1.0)
    random_seed: int = 20260916

    def with_mode_defaults(self) -> "ExperimentSpec":
        if self.quick_mode:
            return self
        return replace(
            self,
            start_date="2016-01-01",
            selected_instruments=(
                "SP500",
                "SP500_micro",
                "NASDAQ",
                "NASDAQ_micro",
                "US10",
                "EUR",
                "EUR_micro",
                "GOLD",
                "GOLD_micro",
                "CRUDE_W",
                "CORN",
            ),
            capital_sweep=(25_000.0, 50_000.0, 100_000.0, 200_000.0, 500_000.0, 1_000_000.0),
            shadow_cost_values=(0.0, 25.0, 50.0, 100.0, 200.0),
            tracking_error_buffer_values=(0.0, 0.00625, 0.0125, 0.025, 0.05),
            cost_multiplier_values=(0.5, 1.0, 2.0, 4.0),
            correlation_shrinkage_values=(0.0, 0.25, 0.5, 0.75, 1.0),
        )


def default_spec(quick_mode: bool = True) -> ExperimentSpec:
    return ExperimentSpec(quick_mode=quick_mode).with_mode_defaults()


def _ewmac_rules() -> dict[str, dict[str, Any]]:
    return {
        "ewmac8_32": {
            "function": "systems.provided.rules.ewmac.ewmac",
            "data": ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
            "other_args": {"Lfast": 8, "Lslow": 32},
            "forecast_scalar": 5.3,
        },
        "ewmac32_128": {
            "function": "systems.provided.rules.ewmac.ewmac",
            "data": ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
            "other_args": {"Lfast": 32, "Lslow": 128},
            "forecast_scalar": 2.65,
        },
    }


def build_config(spec: ExperimentSpec, instruments: Sequence[str] | None = None) -> Config:
    """Build an isolated in-memory config; no repository YAML is modified."""

    instruments = tuple(instruments or spec.selected_instruments)
    equal_weight = 1.0 / len(instruments)
    return Config(
        {
            "start_date": spec.start_date,
            "percentage_vol_target": spec.percentage_vol_target,
            "notional_trading_capital": spec.capital_base,
            "base_currency": "USD",
            "trading_rules": _ewmac_rules(),
            "forecast_weights": {"ewmac8_32": 0.5, "ewmac32_128": 0.5},
            "forecast_div_multiplier": 1.1,
            "instrument_weights": {instrument: equal_weight for instrument in instruments},
            "instrument_div_multiplier": 2.0,
            "use_forecast_weight_estimates": False,
            "use_forecast_div_mult_estimates": False,
            "use_instrument_weight_estimates": False,
            "use_instrument_div_mult_estimates": False,
            "small_system": {
                "shadow_cost": 50.0,
                "cost_multiplier": 1.0,
                "tracking_error_buffer": 0.0125,
                "shrink_instrument_returns_correlation": 0.5,
            },
        }
    )


def build_system(spec: ExperimentSpec, instruments: Sequence[str] | None = None) -> System:
    """Build the dynamic system against packaged CSV simulation data only."""

    config = build_config(spec, instruments=instruments)
    return System(
        [
            Risk(),
            accountForOptimisedStage(),
            optimisedPositions(),
            Portfolios(),
            PositionSizing(),
            RawData(),
            ForecastCombine(),
            ForecastScaleCap(),
            Rules(),
        ],
        csvFuturesSimData(),
        config,
    )


def cache_key(spec: ExperimentSpec, label: str, **overrides: Any) -> str:
    payload = {"spec": asdict(spec), "label": label, "overrides": overrides}
    raw = json.dumps(payload, sort_keys=True, default=list).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def environment_manifest(repo_root: Path) -> pd.Series:
    """Return reproducibility facts without mutating git configuration."""

    def git_value(*args: str) -> str:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={repo_root.as_posix()}", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() or f"unavailable: {result.stderr.strip()}"

    return pd.Series(
        {
            "git_commit": git_value("rev-parse", "HEAD"),
            "git_branch": git_value("branch", "--show-current"),
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "pysystemtrade_path": str(repo_root.resolve()),
            "data_source": "csvFuturesSimData (repository CSV files; read-only)",
            "run_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        },
        name="value",
    )


def available_instruments(data: csvFuturesSimData, requested: Iterable[str]) -> list[str]:
    available = set(data.get_instrument_list())
    return [instrument for instrument in requested if instrument in available]


def _slice_dates(obj: pd.Series | pd.DataFrame, spec: ExperimentSpec):
    result = obj.loc[pd.Timestamp(spec.start_date) :]
    if spec.end_date is not None:
        result = result.loc[: pd.Timestamp(spec.end_date)]
    return result


def collect_core_frames(system: System, spec: ExperimentSpec) -> dict[str, pd.DataFrame]:
    """Collect a single aligned diagnostic layer from public stage APIs."""

    instruments = system.get_instrument_list()
    continuous = _slice_dates(system.portfolio.get_position_contracts_as_df(), spec)
    index = continuous.index

    def frame_from(method) -> pd.DataFrame:
        frame = pd.DataFrame({instrument: method(instrument) for instrument in instruments})
        return frame.reindex(index).ffill()

    frames: dict[str, pd.DataFrame] = {
        "price": frame_from(system.rawdata.get_daily_prices),
        "price_return": frame_from(system.rawdata.get_daily_prices).diff(),
        "daily_price_vol_pct": frame_from(system.positionSize.get_price_volatility),
        "annual_pct_vol_fraction": frame_from(system.portfolio.annualised_percentage_vol),
        "instrument_currency_daily_vol": frame_from(system.positionSize.get_instrument_currency_vol),
        "base_currency_daily_vol": frame_from(system.positionSize.get_instrument_value_vol),
        "combined_forecast": frame_from(system.combForecast.get_combined_forecast),
        "average_position": frame_from(system.positionSize.get_average_position_at_subsystem_level),
        "subsystem_position": frame_from(system.positionSize.get_subsystem_position),
        "instrument_weight": system.portfolio.get_instrument_weights().reindex(index).ffill(),
        "continuous_position": continuous,
        "per_contract_value_fraction": system.portfolio.get_per_contract_value_as_proportion_of_capital_df()
        .reindex(index)
        .ffill(),
        "fx": frame_from(system.positionSize.get_fx_rate),
    }
    idm = system.portfolio.get_instrument_diversification_multiplier().reindex(index).ffill()
    frames["instrument_diversification_multiplier"] = pd.DataFrame(
        np.repeat(idm.to_numpy()[:, None], len(instruments), axis=1),
        index=index,
        columns=instruments,
    )

    multipliers = pd.Series(
        {instrument: system.data.get_value_of_block_price_move(instrument) for instrument in instruments}
    )
    frames["contract_multiplier"] = pd.DataFrame(
        np.repeat(multipliers.reindex(instruments).to_numpy()[None, :], len(index), axis=0),
        index=index,
        columns=instruments,
    )
    capital = float(system.config.notional_trading_capital)
    frames["contract_value_base"] = frames["per_contract_value_fraction"] * capital
    frames["one_contract_annual_risk_fraction"] = (
        frames["per_contract_value_fraction"] * frames["annual_pct_vol_fraction"]
    )
    target_risk = float(system.config.percentage_vol_target) / 100.0
    frames["contract_granularity_ratio"] = (
        frames["one_contract_annual_risk_fraction"].abs() / target_risk
    )

    stage = system.optimisedPositions
    cost_coefficients = pd.DataFrame(
        {
            instrument: stage.get_cost_deflator(instrument).reindex(index).ffill()
            * stage.get_cost_per_notional_weight_as_proportion_of_capital(instrument)
            for instrument in instruments
        },
        index=index,
    )
    frames["cost_per_weight_fraction"] = cost_coefficients
    frames["cost_per_contract_fraction"] = (
        cost_coefficients * frames["per_contract_value_fraction"]
    )
    frames["cost_per_contract_base"] = frames["cost_per_contract_fraction"] * capital

    for rule_name in sorted(system.rules.trading_rules().keys()):
        frames[f"raw_forecast__{rule_name}"] = frame_from(
            lambda instrument, rule=rule_name: system.rules.get_raw_forecast(instrument, rule)
        )
        frames[f"scaled_forecast__{rule_name}"] = frame_from(
            lambda instrument, rule=rule_name: system.forecastScaleCap.get_scaled_forecast(instrument, rule)
        )
        frames[f"capped_forecast__{rule_name}"] = frame_from(
            lambda instrument, rule=rule_name: system.forecastScaleCap.get_capped_forecast(instrument, rule)
        )

    return frames


def diagnostics_long(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Convert aligned date x instrument frames to a tidy diagnostic table."""

    stacked = {name: frame.stack(dropna=False) for name, frame in frames.items()}
    result = pd.concat(stacked, axis=1)
    result.index.names = ["date", "instrument"]
    return result.sort_index()


def universe_diagnostic(system: System, frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    capital = float(system.config.notional_trading_capital)
    for instrument in system.get_instrument_list():
        price = frames["price"][instrument].dropna()
        latest = price.index[-1]
        rows.append(
            {
                "instrument": instrument,
                "asset_class": system.data.asset_class_for_instrument(instrument),
                "data_start": price.index.min(),
                "data_end": price.index.max(),
                "price": price.iloc[-1],
                "multiplier": frames["contract_multiplier"].at[latest, instrument],
                "fx": frames["fx"].at[latest, instrument],
                "annual_vol": frames["annual_pct_vol_fraction"].at[latest, instrument],
                "one_contract_value": frames["contract_value_base"].at[latest, instrument],
                "one_contract_risk": capital
                * frames["one_contract_annual_risk_fraction"].at[latest, instrument],
                "granularity_ratio": frames["contract_granularity_ratio"].at[latest, instrument],
                "cost": frames["cost_per_contract_base"].at[latest, instrument],
            }
        )
    return pd.DataFrame(rows).set_index("instrument").sort_values("granularity_ratio")


def _covariance_for_date(system: System, relevant_date: pd.Timestamp, shrinkage: float):
    raw_correlation = system.portfolio.get_correlation_matrix(relevant_date=relevant_date)
    correlation = copy(
        raw_correlation.shrink_to_offdiag(shrinkage_corr=shrinkage, offdiag=0.0)
    )
    stdev = system.portfolio.get_stdev_estimate(relevant_date=relevant_date)
    return covariance_from_stdev_and_correlation(correlation, stdev)


def objective_for_date(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    relevant_date: pd.Timestamp,
    previous_positions: portfolioWeights,
    *,
    capital: float | None = None,
    shadow_cost: float | None = None,
    tracking_error_buffer: float | None = None,
    cost_multiplier: float | None = None,
    correlation_shrinkage: float | None = None,
) -> objectiveFunctionForGreedy:
    """Create the native objective with explicit research-only overrides."""

    base_capital = float(system.config.notional_trading_capital)
    capital = float(capital if capital is not None else base_capital)
    scale = capital / base_capital
    instruments = system.get_instrument_list()
    small = system.config.small_system
    shadow_cost = float(shadow_cost if shadow_cost is not None else small["shadow_cost"])
    tracking_error_buffer = float(
        tracking_error_buffer
        if tracking_error_buffer is not None
        else small["tracking_error_buffer"]
    )
    correlation_shrinkage = float(
        correlation_shrinkage
        if correlation_shrinkage is not None
        else small["shrink_instrument_returns_correlation"]
    )
    cost_multiplier = float(
        cost_multiplier if cost_multiplier is not None else small["cost_multiplier"]
    )
    base_cost_multiplier = float(small["cost_multiplier"])

    contracts_optimal = portfolioWeights(
        (frames["continuous_position"].loc[relevant_date, instruments] * scale).to_dict()
    )
    per_contract_value = portfolioWeights(
        (frames["per_contract_value_fraction"].loc[relevant_date, instruments] / scale).to_dict()
    )
    costs = meanEstimates(
        (
            frames["cost_per_weight_fraction"].loc[relevant_date, instruments]
            * cost_multiplier
            / base_cost_multiplier
        ).to_dict()
    )
    covariance = _covariance_for_date(system, relevant_date, correlation_shrinkage)
    return objectiveFunctionForGreedy(
        contracts_optimal=contracts_optimal,
        covariance_matrix=covariance,
        per_contract_value=per_contract_value,
        previous_positions=previous_positions,
        costs=costs,
        constraints=system.optimisedPositions.get_constraints(),
        speed_control=speedControlForDynamicOpt(
            trade_shadow_cost=shadow_cost,
            tracking_error_buffer=tracking_error_buffer,
        ),
    )


def run_optimisation(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    *,
    capital: float | None = None,
    shadow_cost: float | None = None,
    tracking_error_buffer: float | None = None,
    cost_multiplier: float | None = None,
    correlation_shrinkage: float | None = None,
    cache_dir: Path | None = None,
    cache_id: str | None = None,
) -> pd.DataFrame:
    """Replay the native objective through time, propagating integer positions."""

    instruments = system.get_instrument_list()
    index = frames["continuous_position"].index
    cache_path = None
    if cache_dir is not None and cache_id is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_payload = {
            "schema": CACHE_SCHEMA_VERSION,
            "requested_id": cache_id,
            "instruments": instruments,
            "index_start": str(index.min()),
            "index_end": str(index.max()),
            "index_length": len(index),
            "base_capital": float(system.config.notional_trading_capital),
            "percentage_vol_target": float(system.config.percentage_vol_target),
            "small_system": system.config.small_system,
            "capital": capital,
            "shadow_cost": shadow_cost,
            "tracking_error_buffer": tracking_error_buffer,
            "cost_multiplier": cost_multiplier,
            "correlation_shrinkage": correlation_shrinkage,
        }
        signature = hashlib.sha256(
            json.dumps(cache_payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:20]
        cache_path = cache_dir / f"optimised_positions_{signature}.pkl"
        if cache_path.exists():
            cached = pd.read_pickle(cache_path)
            if cached.index.equals(index) and list(cached.columns) == instruments:
                return cached

    previous = portfolioWeights.allzeros(instruments)
    rows: list[portfolioWeights] = []
    muted_output = StringIO()
    root_logger = logging.getLogger()
    prior_level = root_logger.level
    try:
        root_logger.setLevel(logging.CRITICAL)
        with redirect_stdout(muted_output), redirect_stderr(muted_output):
            for relevant_date in index:
                objective = objective_for_date(
                    system,
                    frames,
                    relevant_date,
                    previous,
                    capital=capital,
                    shadow_cost=shadow_cost,
                    tracking_error_buffer=tracking_error_buffer,
                    cost_multiplier=cost_multiplier,
                    correlation_shrinkage=correlation_shrinkage,
                )
                current = objective.optimise_positions()
                rows.append(current)
                previous = copy(current)
    finally:
        root_logger.setLevel(prior_level)
    result = pd.DataFrame(rows, index=index).reindex(columns=instruments).astype(float)
    if cache_path is not None:
        result.to_pickle(cache_path)
    return result


def tracking_error_series(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    positions: pd.DataFrame,
    *,
    capital: float | None = None,
    correlation_shrinkage: float | None = None,
) -> pd.Series:
    base_capital = float(system.config.notional_trading_capital)
    capital = float(capital if capital is not None else base_capital)
    scale = capital / base_capital
    shrinkage = float(
        correlation_shrinkage
        if correlation_shrinkage is not None
        else system.config.small_system["shrink_instrument_returns_correlation"]
    )
    values = []
    for date in positions.index:
        per_contract = frames["per_contract_value_fraction"].loc[date] / scale
        actual_weights = positions.loc[date].to_numpy(dtype=float) * per_contract.to_numpy(dtype=float)
        optimal_weights = frames["continuous_position"].loc[date].to_numpy(dtype=float) * frames[
            "per_contract_value_fraction"
        ].loc[date].to_numpy(dtype=float)
        gap = actual_weights - optimal_weights
        covariance = _covariance_for_date(system, date, shrinkage).subset(list(positions.columns)).values
        variance = float(gap.dot(covariance).dot(gap))
        values.append(math.sqrt(max(variance, 0.0)))
    return pd.Series(values, index=positions.index, name="portfolio_tracking_error")


def candidate_objective_table(
    objective: objectiveFunctionForGreedy,
    instrument: str,
    candidates: Sequence[int],
) -> pd.DataFrame:
    """Decompose native objective values while holding other prior positions fixed."""

    keys = objective.keys_with_valid_data
    idx = keys.index(instrument)
    base_weights = objective.weights_prior_as_np_replace_nans_with_zeros.copy()
    rows = []
    for candidate in candidates:
        weights = base_weights.copy()
        weights[idx] = candidate * objective.per_contract_value_as_np[idx]
        tracking = objective.tracking_error_against_optimal(weights)
        cost = objective.calculate_costs(weights)
        constraint = objective.constraint_function_value(weights)
        rows.append(
            {
                "candidate_contracts": candidate,
                "tracking_penalty": tracking,
                "cost_penalty": cost,
                "constraint_penalty": constraint,
                "total_objective": tracking + cost + constraint,
            }
        )
    return pd.DataFrame(rows).set_index("candidate_contracts")


def enrich_position_frames(
    frames: dict[str, pd.DataFrame], optimised: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    result = dict(frames)
    result["optimised_position"] = optimised
    result["previous_integer_position"] = optimised.shift(1).fillna(0.0)
    result["position_change"] = optimised.diff().fillna(optimised)
    result["nearest_integer_position"] = result["continuous_position"].round()
    result["toward_zero_position"] = pd.DataFrame(
        np.trunc(result["continuous_position"].to_numpy()),
        index=result["continuous_position"].index,
        columns=result["continuous_position"].columns,
    )
    result["instrument_tracking_error_contracts"] = (
        result["continuous_position"] - optimised
    )
    result["instrument_tracking_error_risk_fraction"] = (
        result["instrument_tracking_error_contracts"]
        * result["per_contract_value_fraction"]
        * result["annual_pct_vol_fraction"]
    )
    return result


def find_decision_events(frames: Mapping[str, pd.DataFrame], instrument: str) -> pd.Series:
    target = frames["continuous_position"][instrument]
    actual = frames["optimised_position"][instrument]
    prior = actual.shift(1).fillna(0.0)
    change = actual - prior
    target_change = target.diff().abs()
    gap = (target - actual).abs()
    events: dict[str, pd.Timestamp | pd.NaT] = {}

    mask = (target.abs() < 1.0) & (target.abs() > 0.25) & actual.eq(0)
    events["A_sub_one_target_held_zero"] = mask[mask].index[-1] if mask.any() else pd.NaT
    mask = prior.eq(0) & actual.ne(0)
    events["B_zero_to_nonzero"] = mask[mask].index[0] if mask.any() else pd.NaT
    mask = target_change.gt(target_change.quantile(0.75)) & change.eq(0)
    events["C_target_moves_no_trade"] = mask[mask].index[-1] if mask.any() else pd.NaT
    mask = actual.abs().lt(prior.abs()) & change.ne(0)
    events["D_reduction"] = mask[mask].index[-1] if mask.any() else pd.NaT
    events["E_largest_continuous_integer_gap"] = gap.idxmax()
    return pd.Series(events, name="date")


def decision_snapshot(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    instrument: str,
    date: pd.Timestamp,
    portfolio_tracking_error: pd.Series,
) -> pd.Series:
    capital = float(system.config.notional_trading_capital)
    return pd.Series(
        {
            "price": frames["price"].at[date, instrument],
            "combined_forecast": frames["combined_forecast"].at[date, instrument],
            "annual_vol_fraction": frames["annual_pct_vol_fraction"].at[date, instrument],
            "continuous_target_contracts": frames["continuous_position"].at[date, instrument],
            "previous_integer_position": frames["previous_integer_position"].at[date, instrument],
            "optimised_integer_position": frames["optimised_position"].at[date, instrument],
            "one_contract_value_fraction": frames["per_contract_value_fraction"].at[date, instrument],
            "one_contract_value_base": frames["contract_value_base"].at[date, instrument],
            "cost_per_contract_base": frames["cost_per_contract_base"].at[date, instrument],
            "shadow_cost": system.config.small_system["shadow_cost"],
            "portfolio_tracking_error": portfolio_tracking_error.at[date],
            "tracking_error_buffer": system.config.small_system["tracking_error_buffer"],
            "target_portfolio_vol_fraction": system.config.percentage_vol_target / 100.0,
            "capital": capital,
        },
        name=date,
    )


def strategy_returns(
    frames: Mapping[str, pd.DataFrame],
    positions: pd.DataFrame,
    capital: float,
    *,
    charge_costs: bool = True,
) -> pd.Series:
    aligned = positions.reindex(frames["price"].index).ffill().fillna(0.0)
    gross = (
        aligned.shift(1).fillna(0.0)
        * frames["price"].diff()
        * frames["contract_multiplier"]
        * frames["fx"]
    ).sum(axis=1) / capital
    if not charge_costs:
        return gross.rename("return")
    trade_cost = (
        aligned.diff().abs().fillna(aligned.abs())
        * frames["cost_per_contract_fraction"]
    ).sum(axis=1)
    return (gross - trade_cost).rename("return")


def method_metrics(
    frames: Mapping[str, pd.DataFrame],
    positions: pd.DataFrame,
    capital: float,
    tracking_error: pd.Series,
) -> pd.Series:
    returns = strategy_returns(frames, positions, capital)
    clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
    annual_return = clean.mean() * BDAYS_INYEAR
    annual_vol = clean.std(ddof=1) * ROOT_BDAYS_INYEAR
    wealth = (1.0 + clean).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    changes = positions.diff().abs().fillna(positions.abs())
    per_contract_fraction = frames["per_contract_value_fraction"]
    return pd.Series(
        {
            "annual_return": annual_return,
            "annual_vol": annual_vol,
            "sharpe": annual_return / annual_vol if annual_vol > 0 else np.nan,
            "max_drawdown": drawdown.min(),
            "contract_turnover_per_year": changes.sum(axis=1).mean() * BDAYS_INYEAR,
            "notional_turnover_per_year": (changes * per_contract_fraction).sum(axis=1).mean()
            * BDAYS_INYEAR,
            "estimated_cost_fraction_per_year": (
                changes * frames["cost_per_contract_fraction"]
            ).sum(axis=1).mean()
            * BDAYS_INYEAR,
            "average_tracking_error": tracking_error.mean(),
            "tracking_error_p95": tracking_error.quantile(0.95),
            "average_active_markets": positions.ne(0).sum(axis=1).mean(),
            "average_gross_exposure": (positions.abs() * per_contract_fraction).sum(axis=1).mean(),
            "position_changes": int(changes.ne(0).sum().sum()),
        }
    )


def capital_sweep(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    capitals: Sequence[float],
    cache_dir: Path | None = None,
    cache_prefix: str = "capital",
) -> tuple[pd.DataFrame, dict[float, pd.DataFrame], dict[float, pd.Series]]:
    rows = []
    positions_by_capital: dict[float, pd.DataFrame] = {}
    tracking_by_capital: dict[float, pd.Series] = {}
    base_capital = float(system.config.notional_trading_capital)
    for capital in capitals:
        cache_id = f"{cache_prefix}_{int(capital)}"
        positions = run_optimisation(
            system,
            frames,
            capital=capital,
            cache_dir=cache_dir,
            cache_id=cache_id,
        )
        tracking = tracking_error_series(system, frames, positions, capital=capital)
        scaled_frames = dict(frames)
        scaled_frames["per_contract_value_fraction"] = (
            frames["per_contract_value_fraction"] * base_capital / capital
        )
        scaled_frames["cost_per_contract_fraction"] = (
            frames["cost_per_contract_fraction"] * base_capital / capital
        )
        metrics = method_metrics(scaled_frames, positions, capital, tracking)
        metrics["capital"] = capital
        metrics["median_active_markets"] = positions.ne(0).sum(axis=1).median()
        metrics["pct_zero_positions"] = positions.eq(0).mean().mean()
        metrics["diversification_active_fraction"] = (
            positions.ne(0).sum(axis=1).mean() / positions.shape[1]
        )
        rows.append(metrics)
        positions_by_capital[float(capital)] = positions
        tracking_by_capital[float(capital)] = tracking
    summary = pd.DataFrame(rows).set_index("capital").sort_index()
    return summary, positions_by_capital, tracking_by_capital


def parameter_sweep(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    parameter: str,
    values: Sequence[float],
    *,
    capital: float | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    valid = {
        "shadow_cost",
        "tracking_error_buffer",
        "cost_multiplier",
        "correlation_shrinkage",
    }
    if parameter not in valid:
        raise ValueError(f"parameter must be one of {sorted(valid)}")
    capital = float(capital or system.config.notional_trading_capital)
    rows = []
    for value in values:
        kwargs = {parameter: float(value)}
        positions = run_optimisation(
            system,
            frames,
            capital=capital,
            cache_dir=cache_dir,
            cache_id=f"{parameter}_{value:g}_capital_{int(capital)}",
            **kwargs,
        )
        tracking = tracking_error_series(
            system,
            frames,
            positions,
            capital=capital,
            correlation_shrinkage=kwargs.get("correlation_shrinkage"),
        )
        metrics = method_metrics(frames, positions, capital, tracking)
        metrics[parameter] = value
        rows.append(metrics)
    return pd.DataFrame(rows).set_index(parameter).sort_index()


def risk_contributions(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    positions: pd.DataFrame,
    date: pd.Timestamp,
) -> pd.DataFrame:
    instruments = list(positions.columns)
    covariance = _covariance_for_date(
        system,
        date,
        float(system.config.small_system["shrink_instrument_returns_correlation"]),
    ).subset(instruments).values
    per_contract = frames["per_contract_value_fraction"].loc[date, instruments]
    ideal_weights = frames["continuous_position"].loc[date, instruments] * per_contract
    actual_weights = positions.loc[date, instruments] * per_contract

    def component(weights: pd.Series) -> pd.Series:
        values = weights.to_numpy(dtype=float)
        variance = float(values.dot(covariance).dot(values))
        if variance <= 0:
            return pd.Series(np.nan, index=instruments)
        return pd.Series(values * covariance.dot(values) / math.sqrt(variance), index=instruments)

    return pd.DataFrame(
        {"ideal_risk_contribution": component(ideal_weights), "integer_risk_contribution": component(actual_weights)}
    ).sort_values("ideal_risk_contribution")


def capital_heatmap_frames(
    frames: Mapping[str, pd.DataFrame],
    positions_by_capital: Mapping[float, pd.DataFrame],
    base_capital: float,
) -> dict[str, pd.DataFrame]:
    latest_granularity = frames["contract_granularity_ratio"].iloc[-1]
    granularity = pd.DataFrame(
        {
            capital: latest_granularity * base_capital / capital
            for capital in positions_by_capital
        }
    )
    pct_active = pd.DataFrame(
        {capital: positions.ne(0).mean() for capital, positions in positions_by_capital.items()}
    )
    mean_abs = pd.DataFrame(
        {capital: positions.abs().mean() for capital, positions in positions_by_capital.items()}
    )
    return {"granularity": granularity, "pct_active": pct_active, "mean_abs_position": mean_abs}


def phase_transition_table(positions_by_capital: Mapping[float, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    previous: set[str] = set()
    for capital, positions in sorted(positions_by_capital.items()):
        active = set(positions.columns[positions.abs().mean().gt(0)])
        rows.append(
            {
                "capital": capital,
                "active_markets": len(active),
                "newly_active": ", ".join(sorted(active - previous)) or "—",
            }
        )
        previous = active
    return pd.DataFrame(rows).set_index("capital")


def sanity_checks(
    frames: Mapping[str, pd.DataFrame],
    optimised: pd.DataFrame,
    positions_by_capital: Mapping[float, pd.DataFrame],
) -> pd.Series:
    checks: dict[str, bool] = {}
    checks["integer_invariant"] = bool(
        np.allclose(optimised.to_numpy(), np.round(optimised.to_numpy()), equal_nan=False)
    )
    checks["position_alignment"] = bool(
        optimised.index.equals(frames["continuous_position"].index)
        and optimised.columns.equals(frames["continuous_position"].columns)
    )
    critical = [
        "price",
        "combined_forecast",
        "annual_pct_vol_fraction",
        "continuous_position",
        "per_contract_value_fraction",
    ]
    checks["finite_critical_tail"] = all(
        np.isfinite(frames[name].tail(100).to_numpy()).all() for name in critical
    )
    checks["positive_contract_values"] = bool(
        frames["per_contract_value_fraction"].tail(100).gt(0).all().all()
    )
    capitals = sorted(positions_by_capital)
    latest = frames["per_contract_value_fraction"].iloc[-1]
    ratios = [latest * float(capitals[0]) / capital for capital in capitals]
    checks["contract_fraction_decreases_with_capital"] = all(
        (ratios[i + 1] <= ratios[i] + 1e-15).all() for i in range(len(ratios) - 1)
    )
    checks["no_infinite_positions"] = bool(np.isfinite(optimised.to_numpy()).all())
    result = pd.Series(checks, name="passed")
    if not result.all():
        failed = result.index[~result].tolist()
        raise AssertionError(f"Sanity checks failed: {failed}")
    return result


class Timer:
    """Small context manager used for honest notebook runtime reporting."""

    def __init__(self, timings: dict[str, float], label: str):
        self.timings = timings
        self.label = label
        self.started = 0.0

    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.timings[self.label] = time.perf_counter() - self.started
        return False


def style_axes(axes: Any) -> None:
    for ax in np.atleast_1d(axes).ravel():
        ax.grid(True, alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)


def heatmap(
    data: pd.DataFrame,
    title: str,
    cbar_label: str,
    *,
    cmap: str = "viridis",
    fmt: str = ".2f",
    figsize: tuple[float, float] = (10, 5),
):
    fig, ax = plt.subplots(figsize=figsize)
    image = ax.imshow(data.to_numpy(dtype=float), aspect="auto", cmap=cmap)
    ax.set_xticks(range(data.shape[1]), [f"${float(x):,.0f}" for x in data.columns])
    ax.set_yticks(range(data.shape[0]), data.index)
    ax.set_xlabel("Capital (USD)")
    ax.set_ylabel("Instrument")
    ax.set_title(title)
    if data.size <= 80:
        for row in range(data.shape[0]):
            for column in range(data.shape[1]):
                ax.text(column, row, format(data.iat[row, column], fmt), ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label=cbar_label)
    fig.tight_layout()
    return fig, ax


def covariance_and_correlation_frames(
    system: System, date: pd.Timestamp
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = system.portfolio.get_correlation_matrix(relevant_date=date)
    shrinkage = float(system.config.small_system["shrink_instrument_returns_correlation"])
    shrunk = raw.shrink_to_offdiag(shrinkage_corr=shrinkage, offdiag=0.0)
    stdev = system.portfolio.get_stdev_estimate(relevant_date=date)
    covariance = covariance_from_stdev_and_correlation(shrunk, stdev)
    return (
        pd.DataFrame(raw.values, index=raw.columns, columns=raw.columns),
        pd.DataFrame(shrunk.values, index=shrunk.columns, columns=shrunk.columns),
        pd.DataFrame(covariance.values, index=covariance.columns, columns=covariance.columns),
    )


def compare_native_replay(
    system: System,
    frames: Mapping[str, pd.DataFrame],
    replayed: pd.DataFrame,
    dates: int = 20,
) -> bool:
    """Re-run a short tail through the stage factory and compare objective results.

    This deliberately starts from the replayed position immediately before the
    selected tail so it tests the same state transition, not a new backtest.
    """

    if len(replayed) <= dates:
        start = 0
        previous = portfolioWeights.allzeros(list(replayed.columns))
    else:
        start = len(replayed) - dates
        previous = portfolioWeights(replayed.iloc[start - 1].to_dict())
    rows = []
    muted = StringIO()
    root_logger = logging.getLogger()
    prior_level = root_logger.level
    try:
        root_logger.setLevel(logging.CRITICAL)
        with redirect_stdout(muted), redirect_stderr(muted):
            for date in replayed.index[start:]:
                objective = system.optimisedPositions._get_optimal_positions_objective_instance(
                    relevant_date=date,
                    previous_positions=previous,
                )
                current = objective.optimise_positions()
                rows.append(current)
                previous = copy(current)
    finally:
        root_logger.setLevel(prior_level)
    native = pd.DataFrame(rows, index=replayed.index[start:]).reindex(columns=replayed.columns)
    return bool(np.array_equal(native.to_numpy(dtype=float), replayed.iloc[start:].to_numpy(dtype=float)))
