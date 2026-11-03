# Paper Options Lab

A local options risk workbench: compare defined-risk call/put debit spreads, inspect payoff and QuantLib Greeks, and replay local paper events with auditable rejection reasons.

**Paper only. No broker connectivity, account data, credentials, external inference, order submission, or live execution code.** The included scenarios are synthetic, not historical investment performance. No data subscription or deployment is required.

## Run locally

Python 3.11+, Node 24+ (the development version is in [.node-version](.node-version)), and an official QuantLib wheel for your platform. Python dependencies are pinned in [requirements.txt](requirements.txt); no C++ compilation is needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
npm --prefix web ci
npm --prefix web run build
make dev
```

`make dev` runs the server through [Portless](https://github.com/vercel-labs/portless), a `web/` dev dependency. Open the URL printed by the server: normally <https://paper-options-lab.localhost>, with a branch prefix in worktrees. The first run may ask for `sudo` to bind port 443 and trust a local certificate. The server binds loopback only, runs one worker, and computes on demand. Stop it with Ctrl+C. Rebuild the dashboard after frontend edits.

To use plain loopback without Portless, run `.venv/bin/python -m options_lab serve --port 8792` and open <http://127.0.0.1:8792>.

## CLI and imports

```sh
.venv/bin/python -m options_lab compare --scenario rally
.venv/bin/python -m options_lab replay --scenario pending
.venv/bin/python -m options_lab replay --scenario rally --through 2026-10-02T14:00:03Z
.venv/bin/python -m options_lab validate --input fixtures/rally.json
.venv/bin/python -m options_lab compare --input fixtures/rally.json --at 2026-10-02T14:00:00Z
```

`--quantity` affects comparison; replay uses the quantities in dataset events. `--policy path.json` supplies a subset of the fields in [`Policy`](options_lab/engine.py). `--at` controls comparison and defaults to the synthetic fixture entry instant; always specify it for imported data. Replay processes the full planned dataset by default, including future scenario events. CLI `--through` produces an as-of replay, excludes later events, and recognizes settlement only when available by that instant. Reports go to stdout; redirects are explicit local writes.

The dataset's paper events are plans, not recommendations. Eligible means only that a pair passed deterministic filters; it does not predict profitability or assure real fills. The model assumes atomic packages and European cash settlement and cannot represent equity-option assignment or stock delivery. Read the [research and modeling limits](docs/research.md) before interpreting results.

For dashboard JSON imports, use the [schema contract](docs/import-schema.md). For saved provider-shaped exports, follow the [offline MarketData adapter guide](docs/marketdata-import.md). The adapter makes no API calls and requires no token. Its output is always observation-only: comparison and replay block fills even with relaxed quote-age limits. Provider fixtures contain fictional DEMO contracts, not vendor observations. Imported feed labels, provenance and usage rights require independent verification.

The [roadmap](ROADMAP.md) records proposed learning and research priorities.

## Development checks

```sh
.venv/bin/python -m unittest discover -s test -v
npm --prefix web run lint
npm --prefix web test
npm --prefix web run format:check
npm --prefix web run check
npm --prefix web run build
git diff --check
```

For browser regression, start the plain loopback server above after building the dashboard. With `playwright-cli` installed separately, run from the repository root:

```sh
playwright-cli --session paper-options open http://127.0.0.1:8792
playwright-cli --session paper-options run-code --filename test/browser-qa.test.js
playwright-cli --session paper-options close
```

The browser check exercises imports, error recovery, risk controls, selection, export and mobile layout; it overwrites captures in `output/playwright/`. The lint exception for its single function expression is documented in [the check](test/browser-qa.test.js) and scoped in [.oxlintrc.json](.oxlintrc.json).
