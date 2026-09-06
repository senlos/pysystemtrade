from ib_async import IB, Stock, MarketOrder
import time

ib = IB()
try:
    ib.connect('127.0.0.1', 4001, clientId=999)
    print('connected=', ib.isConnected())
    print('managed=', ib.managedAccounts())

    contract = Stock('AAPL', 'SMART', 'USD')
    ib.qualifyContracts(contract)
    print('qualified=', contract.conId)

    order = MarketOrder('BUY', 1)
    trade = ib.placeOrder(contract, order)
    print('trade=', trade)
    time.sleep(2)
finally:
    ib.disconnect()
