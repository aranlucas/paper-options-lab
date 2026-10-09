# Paper Options Lab

A local options risk workbench: compare defined-risk call/put debit spreads, inspect payoff and QuantLib Greeks, and replay local paper events with auditable rejection reasons.

**Paper only. No broker connectivity, account data, credentials, external inference, order submission, or live execution code.** The seven included scenarios are synthetic, not historical investment performance. No data subscription or deployment is required.

## Run locally

Python 3.11+ (tested 3.14), Node 24+ (tested 26), and an official QuantLib wheel for your platform. Dependencies are pinned; no C++ compilation is needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
npm --prefix web ci
npm --prefix web run build
npm install -g portless@0.15.7
make dev
```

Open the URL printed by Portless (normally `https://paper-options-lab.localhost`). The server binds loopback only, runs one worker, and computes on demand. Stop it with Ctrl+C. The build is ~75 KB gzipped JS. There are no background trading jobs. Draft pull requests run one bounded GitHub Actions verification job; it does not deploy anything.

## Local URLs with Portless

After the existing Python dependency setup and `npm --prefix web run build`,
install the pinned [Portless](https://github.com/vercel-labs/portless) CLI with
Node.js 24 or newer and start the complete local dashboard:

```sh
npm install -g portless@0.15.7
make dev
```

The default URL is `https://paper-options-lab.localhost`; use the printed URL if
proxy settings differ. Linked Git worktrees get a branch-prefixed hostname. The
server reads the assigned `PORT` while still binding only to `127.0.0.1`. An explicit
`--port` retains precedence for direct runs; do not pass one to the Portless command.

The server accepts only the exact `PORTLESS_URL` Host and Origin in addition to
its existing loopback authorities. Other `.localhost` names, hostile origins,
and spoofed forwarded headers remain rejected. This local-only app deliberately
requires an HTTP(S) `.localhost` origin; custom public TLDs and LAN mode are not
accepted. Configure the proxy for `.localhost` before starting it.

The first HTTPS run can request administrator permission to bind port 443, trust
the local certificate, and synchronize local hostnames. Ctrl+C stops the server
and removes its route.

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

## Free-data compatibility

[Market Data Free Forever](https://www.marketdata.app/docs/account/plans/free-forever/) offers a no-card $0 plan with 100 daily credits, at least 24-hour-old quotes and one year of history. It is useful for offline inspection; historical requests omit IV and Greeks. The [research brief](docs/research.md#free-api-follow-up) explains the constraints and alternatives.

The offline importer accepts saved, bounded provider-shaped JSON plus explicit contract metadata. It makes no API calls and requires no account or token. Missing IV stays null. Every converted dataset is observation-only: comparison and replay block fills even when quote-age limits are relaxed.

```sh
.venv/bin/python -m options_lab import-marketdata --input fixtures/providers/marketdata-historical.json --metadata fixtures/providers/marketdata-historical.meta.json > /tmp/marketdata-offline.json
.venv/bin/python -m options_lab validate --input /tmp/marketdata-offline.json
.venv/bin/python -m options_lab audit-marketdata --input fixtures/providers/marketdata-historical.json --metadata fixtures/providers/marketdata-historical.meta.json
```

These examples contain fictional DEMO contracts generated offline, not vendor observations. Read the [adapter guide](docs/marketdata-import.md) before converting permitted local exports. A free EOD feed cannot establish intraday fills or historical strategy performance.

## Structure

`options_lab/`: pure pricing, strict schema, screening/replay, fixtures, CLI, loopback server. `web/`: React + TypeScript dashboard. `tests/`: deterministic financial invariants and fail-closed risk cases. `fixtures/`: generated, clearly synthetic JSON examples. `docs/`: research, schema, design and QA. No broker adapters or production deployment files exist.

## Lint policy

Run `npm --prefix web run lint` to check all owned JavaScript and TypeScript, including the browser QA script. Anti-slop is vendored under `web/tools/oxlint/anti-slop` at the revision in its `UPSTREAM.md`; all 18 generic rules and native `oxc/no-accumulating-spread` are errors. Oxlint and its plugin bridge are pinned together. The Playwright CLI consumes `tests/browser_qa.js` as a function expression, so only ESLint’s unused-expression check is disabled for that one file. No anti-slop rules are disabled.
