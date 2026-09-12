"""Bounded configuration repair and read-only verification; no order APIs used."""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
from bson import json_util
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'project/data/execution_tests/timezone_repair_20260910'
PRIVATE = ROOT / 'private/private_config.yaml'
HOURS = ROOT / 'private/private_config_trading_hours.yaml'
SOURCE = ROOT / 'sysbrokers/IB/ib_config_trading_hours.yaml'
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def snapshot() -> dict:
    files = {}
    for directory in ('private', 'data/parquet', 'sysbrokers', 'sysobjects', 'sysdata', 'syscore', 'sysexecution', 'sysproduction'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    with MongoClient('127.0.0.1', 27017, serverSelectionTimeoutMS=5000) as client:
        database = client['production']
        mongo = {}
        for name in sorted(database.list_collection_names()):
            docs = sorted(json_util.dumps(doc, sort_keys=True) for doc in database[name].find({}))
            mongo[name] = {'count': len(docs), 'sha256': digest('\n'.join(docs).encode())}
    return {'files': files, 'mongo': mongo, 'private_config': yaml.safe_load(PRIVATE.read_text())}


def intervals(value: list) -> list:
    return value if not value or isinstance(value[0], list) else [value]


def minute(value: str) -> int:
    hour, minutes = map(int, value.split(':'))
    return hour * 60 + minutes


def clock(value: int) -> str:
    return f'{value // 60:02d}:{value % 60:02d}'


def translate(source: dict) -> dict:
    result = {}
    for name, value in source.items():
        week = {day: [] for day in DAYS}
        for day_index, day in enumerate(DAYS):
            for start, end in intervals(value.get(day, []) if isinstance(value, dict) else value):
                left = minute(start) + 480
                right = minute(end) + 480
                if right <= left:
                    right += 1440
                while left < right:
                    relative_day = left // 1440
                    boundary = (relative_day + 1) * 1440
                    segment_end = min(right, boundary)
                    # Existing parser cannot express 24:00. Never widen to compensate.
                    close = 1439 if segment_end == boundary else segment_end % 1440
                    week[DAYS[(day_index + relative_day) % 7]].append([clock(left % 1440), clock(close)])
                    left = segment_end
        for sessions in week.values():
            sessions.sort()
        result[name] = week if isinstance(value, dict) else week['Monday']
    return result


def write_json(name: str, value: dict) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def repair() -> None:
    assert not HOURS.exists(), 'Refuse to overwrite an existing hours configuration'
    before = snapshot()
    write_json('before.json', before)
    assert 'GMT_offset_hours' not in before['private_config']
    source = yaml.safe_load(SOURCE.read_text())
    result = translate(source)
    header = ('# Source: sysbrokers/IB/ib_config_trading_hours.yaml (documented GMT windows).\n'
              '# All entries translated +8 hours for Asia/Shanghai, including weekday rollover.\n'
              '# Authorized conservative limitation: midnight endings use 23:59, not 24:00.\n'
              '# On each split: (23:59, 00:00) is not tradable; no compensating widening.\n'
              '# Applies to US/Central, US/Eastern, GB-Eire and EDOLLAR_example Monday.\n'
              '# GB-Eire ends at midnight, so its last minute is omitted without a next segment.\n'
              '# Other example intervals roll wholly onto the following local weekday.\n')
    HOURS.write_text(header + yaml.safe_dump(result, sort_keys=False), encoding='utf-8')
    content = PRIVATE.read_bytes()
    newline = b'\r\n' if b'\r\n' in content else b'\n'
    PRIVATE.write_bytes(content + newline + b'# Machine local time: Asia/Shanghai (UTC+8).' + newline + b'GMT_offset_hours: 8' + newline)
    write_json('translations.json', result)
    print('Paired repair applied; baseline saved')


def validate() -> None:
    from ib_async import IB
    from ib_async.ib import StartupFetchNONE
    from sysbrokers.IB import ib_trading_hours as hours_module
    from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
    from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
    from sysobjects.contracts import futuresContract
    from sysobjects.production.trading_hours import trading_hours as native_hours

    result = {'started': dt.datetime.now().astimezone().isoformat()}
    assert hours_module.get_GMT_offset_hours() == 8
    result['GMT_offset_hours'] = 8
    original_reader = hours_module.read_trading_hours
    with patch.object(hours_module, 'read_trading_hours', wraps=original_reader) as reader:
        saved = hours_module.get_saved_trading_hours()
        selected = Path(reader.call_args.args[0]).resolve()
        assert selected == HOURS.resolve(), selected
        result['selected_file'] = str(selected)
    source = yaml.safe_load(SOURCE.read_text())
    actual = yaml.safe_load(HOURS.read_text())
    assert actual == translate(source)
    assert set(actual) == set(source)
    # Independent membership check over a full week at half-minute resolution.
    # Includes each minute boundary and the middle of every potential midnight gap.
    week_seconds = 7 * 86400
    checks = {}
    for name, value in source.items():
        intended = []
        for i, day in enumerate(DAYS):
            for start, end in intervals(value.get(day, []) if isinstance(value, dict) else value):
                start_seconds = i * 86400 + minute(start) * 60 + 28800
                end_seconds = i * 86400 + minute(end) * 60 + 28800
                if end_seconds <= start_seconds:
                    end_seconds += 86400
                for shift in (-week_seconds, 0, week_seconds):
                    intended.append((start_seconds + shift, end_seconds + shift))
        observed = [(i * 86400 + s.opening_time.hour * 3600 + s.opening_time.minute * 60,
                     i * 86400 + s.closing_time.hour * 3600 + s.closing_time.minute * 60)
                    for i, day in enumerate(DAYS) for s in saved[name][day]]
        omitted = []
        for second in range(0, week_seconds, 30):
            want = any(a <= second <= b for a, b in intended)
            have = any(a <= second <= b for a, b in observed)
            assert not have or want, (name, second, 'expanded window')
            if want and not have:
                # Includes midnight endpoint when a source interval ends exactly there.
                assert second % 86400 in (86370, 0), (name, second)
                omitted.append(second)
        checks[name] = {'no_expansion': True, 'only_authorized_midnight_omissions': True, 'omitted_half_minute_samples': omitted}
    result['all_entries'] = checks

    def forbidden(*args: object, **kwargs: object) -> None:
        raise RuntimeError('Order mutation forbidden in timezone audit')

    ib = IB()
    with patch.object(IB, 'placeOrder', forbidden), patch.object(IB, 'cancelOrder', forbidden), patch.object(IB, 'reqGlobalCancel', forbidden):
        try:
            ib.connect('127.0.0.1', 4002, clientId=19392, readonly=True, timeout=10, fetchFields=StartupFetchNONE)
            connection = SimpleNamespace(ib=ib)
            data = SimpleNamespace()
            data.broker_futures_instrument = ibFuturesInstrumentData(connection, data)
            adapter = ibFuturesContractData(connection, data)
            contract = futuresContract('SP500', '20260900')
            enriched = adapter.get_contract_object_with_IB_data(contract)
            details = adapter.ib_client.ib_get_contract_details(enriched)
            c = details.contract
            identity = (c.conId, c.localSymbol, c.exchange, c.currency, c.multiplier, c.lastTradeDateOrContractMonth, details.minTick)
            assert identity == (649180671, 'ESU6', 'CME', 'USD', '50', '20260918', 0.25), identity
            result['identity'] = identity
            result['timeZoneId'] = details.timeZoneId
            result['raw_tradingHours'] = details.tradingHours
            result['parsed_ib_hours'] = str(hours_module.get_trading_hours_from_contract_details(details))
            effective = adapter.get_trading_hours_for_contract(contract)
            result['effective'] = [[s.opening_time.isoformat(), s.closing_time.isoformat()] for s in effective]
            expected = [('2026-09-10T23:00:00', '2026-09-10T23:59:00'), ('2026-09-11T00:00:00', '2026-09-11T04:00:00')]
            for pair in expected:
                assert list(pair) in result['effective'], pair
            # Only the isolated test process clock is substituted; source files unchanged.
            evaluations = {}
            for timestamp, expected_value in [('2026-09-10T22:59:59', False), ('2026-09-10T23:00:00', True), ('2026-09-10T23:30:00', True), ('2026-09-10T23:59:00', True), ('2026-09-10T23:59:30', False), ('2026-09-11T00:00:00', True), ('2026-09-11T03:59:59', True), ('2026-09-11T04:00:00', True), ('2026-09-11T04:00:01', False)]:
                fixed = dt.datetime.fromisoformat(timestamp)

                class FixedDatetime(dt.datetime):
                    @classmethod
                    def now(cls, tz: object = None) -> dt.datetime:
                        return fixed

                with patch.object(native_hours, 'datetime', SimpleNamespace(datetime=FixedDatetime)):
                    observed_value = adapter.is_contract_okay_to_trade(contract)
                assert observed_value is expected_value, (timestamp, observed_value)
                evaluations[timestamp] = observed_value
            result['synthetic_native_gate'] = evaluations
            result['actual_gate_at_validation'] = adapter.is_contract_okay_to_trade(contract)
        finally:
            ib.disconnect()
            result['disconnected'] = not ib.isConnected()
    after = snapshot()
    before = json.loads((OUT / 'before.json').read_text())
    changed = sorted(k for k in before['files'].keys() | after['files'].keys() if before['files'].get(k) != after['files'].get(k))
    assert set(changed) == {str(PRIVATE.relative_to(ROOT)), str(HOURS.relative_to(ROOT))}, changed
    assert before['mongo'] == after['mongo'], 'Mongo state changed'
    expected_config = dict(before['private_config'], GMT_offset_hours=8)
    assert after['private_config'] == expected_config
    assert after['private_config']['broker_account'] == 'DUT077119'
    write_json('after.json', after)
    result.update(status='PASS', changed_files=changed, mongo_unchanged=True, historical_and_strategy_files_unchanged=True, orders_created=0, orders_submitted=0)
    write_json('validation.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['repair']:
        repair()
    elif sys.argv[1:] == ['validate']:
        validate()
    else:
        raise ValueError('Specify repair or validate')
