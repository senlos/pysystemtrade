# Project rules

## Objective

This repository is a systematic futures trading system.

Primary broker:
Interactive Brokers.

Primary development language:
Python.

## Architecture

Keep these components separated:

- market data
- forecasting
- position sizing
- portfolio construction
- execution
- accounting
- risk management

## Coding rules

- Prefer simple implementations.
- Do not duplicate logic.
- Preserve existing APIs unless necessary.
- Do not modify strategy logic when working on execution.
- Use type hints.
- Add tests for new behavior.
- Never hide exceptions without logging.

## Trading safety

- Default to paper trading.
- Never submit live orders in tests.
- Broker connectivity must be mockable.
- Position limits must be enforced before order submission.
- Orders must be idempotent where possible.

## Workflow

Before starting work, read the local project documentation relevant to the task:

1. `project/README.md`
2. `project/docs/state/PROJECT_STATE.md`
3. `project/docs/state/OPEN_ISSUES.md`
4. `project/docs/decisions/DECISIONS.md`

Generated local evidence is under `project/data/`; consult historical evidence only
when it is relevant to the active task. Interactive learning work belongs under
`project/notebooks/`. Preserve the upstream source and runtime layout.

Before major changes:

1. inspect relevant code
2. explain architecture
3. propose change

After changes:

1. run tests
2. inspect git diff
3. report remaining risks
