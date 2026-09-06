"""
This is a futures system

A system consists of a system, plus a config

"""
from syscore.constants import arg_not_supplied

from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config

from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.rawdata import RawData
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.accounts.accounts_stage import Account


def futures_system(
    data=arg_not_supplied,
    config=arg_not_supplied,
    trading_rules=arg_not_supplied,
):
    """

    :param data: data object (defaults to reading from csv files)
    :type data: sysdata.data.simData, or anything that inherits from it

    :param config: Configuration object (defaults to futuresconfig.yaml in this directory)
    :type config: sysdata.configdata.Config

    :param trading_rules: Set of trading rules to use (defaults to set specified in config object)
    :type trading_rules: list or dict of TradingRules, or something that can be parsed to that


    >>> system=futures_system()
    >>> system
    System base_system with .config, .data, and .stages: accounts, portfolio, positionSize, rawdata, combForecast, forecastScaleCap, rules
    >>> system.rules.get_raw_forecast("EDOLLAR", "ewmac2_8").dropna().head(2)
    index
    1984-04-06   -1.146346
    1984-04-09   -0.867647
    Freq: B, Name: price, dtype: float64
    >>> system.rules.get_raw_forecast("EDOLLAR", "carry").dropna().head(2)
    index
    1984-04-06    0.950172
    1984-04-09    1.010585
    Freq: B, dtype: float64
    """

    if data is arg_not_supplied:
        data = csvFuturesSimData()

    if config is arg_not_supplied:
        config = Config("systems.provided.futures_chapter15.futuresconfig.yaml")

    rules = Rules(trading_rules)

    system = System(
        [
            Account(),
            Portfolios(),
            PositionSizing(),
            RawData(),
            ForecastCombine(),
            ForecastScaleCap(),
            rules,
        ],
        data,
        config,
    )

    return system


if __name__ == "__main__":
    import doctest

    doctest.testmod()
