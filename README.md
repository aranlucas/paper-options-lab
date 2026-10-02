# Paper Options Lab

A local options risk workbench: compare defined-risk call/put debit spreads, inspect payoff and QuantLib Greeks, and replay local paper events with auditable rejection reasons.

**Paper only. No broker connectivity, account data, credentials, external inference, order submission, or live execution code.** The seven included scenarios are synthetic, not historical investment performance. No data subscription or deployment is required.

## Run locally

Python 3.11+ (tested 3.14), Node 22+ (tested 26), and an official QuantLib wheel for your platform. Dependencies are pinned; no C++ compilation is needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
npm --prefix web ci
npm --prefix web run build
.venv/bin/python -m options_lab serve --port 8792
```

Open <http://127.0.0.1:8792>. The server binds loopback only, runs one worker, and computes on demand. Stop it with Ctrl+C. The build is ~75 KB gzipped JS. There are no background trading jobs. Draft pull requests run one bounded GitHub Actions verification job; it does not deploy anything.

## CLI

```sh
.venv/bin/python -m options_lab compare --scenario rally
.venv/bin/python -m options_lab replay --scenario selloff
.venv/bin/python -m options_lab replay --scenario pending
.venv/bin/python -m options_lab replay --scenario rally --through 2026-10-02T14:00:03Z
.venv/bin/python -m options_lab validate --input fixtures/rally.json
.venv/bin/python -m options_lab compare --input fixtures/rally.json --at 2026-10-02T14:00:00Z
.venv/bin/python -m unittest discover -s tests -v
npm --prefix web run check
```

`--quantity` affects comparison; replay uses the quantities in dataset events. `--policy path.json` supplies a subset of the policy fields (see `options_lab/engine.py`). `--at` controls comparison and defaults to the synthetic fixture entry instant; always specify it for imported data. Replay processes the full planned dataset by default, including future scenario events. CLI `--through` instead produces an as-of replay, excludes later events, and recognizes settlement only when available by that instant. Reports go to stdout; redirects are explicit local writes.

## What you can explore

- Seven reproducible fixtures: rally, flat expiration, selloff, volatility crush with early close, stale data, missing bids, missing settlement.
- Bounded European cash-settled debit verticals; unsupported American/physical/adjusted contracts expose rejection reasons.
- Adverse bid/ask fills, per-leg slippage, fees, size/volume/OI filters, quote freshness, availability/lookahead checks, multipliers and final trading cutoffs.
- Position, aggregate risk, quantity, cash and refreshed gross delta caps. Risk and future fees remain reserved for unresolved positions.
- Payoff slider, explicit Greek units, readable ledger, JSON import/export, responsive dashboard, and CLI.

The dataset’s explicit paper events are plans, not recommendations. Eligible means only that a pair passed these deterministic filters. It does not predict profitability or assure real fills. Imports labeled OPRA/licensed still require independent provenance and rights checks; indicative and unknown feeds are rejected. The model assumes atomic packages and European settlement and cannot represent real equity-option assignment or stock delivery.

Read [research and modeling limits](docs/research.md), [import schema](docs/import-schema.md), and [verification evidence](docs/verification.md). Pricing uses the maintained [QuantLib](https://github.com/lballabio/QuantLib) library and official bindings, pinned to 1.43. See the brief for Cboe, OCC/OIC and broker documentation and alternative library review.

## Structure

`options_lab/`: pure pricing, strict schema, screening/replay, fixtures, CLI, loopback server. `web/`: React + TypeScript dashboard. `tests/`: deterministic financial invariants and fail-closed risk cases. `fixtures/`: generated, clearly synthetic JSON examples. `docs/`: research, schema, design and QA. No broker adapters or production deployment files exist.
