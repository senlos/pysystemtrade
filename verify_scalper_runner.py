from systems.provided.scalper.entry import MRRunner

runner = MRRunner('SP500')
print('instrument=', runner.instrument)
print('futures_contract=', runner.futures_contract)
print('broker=', runner.data_broker.get_broker_name())
print('strategy_parameters=', type(runner.strategy_parameters).__name__)
print('price_contract=', runner.futures_contract_with_actual_expiry)
