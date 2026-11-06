# Reliability audit — 2026-11-06

Baseline: remote default `4fc831c` (merged untangle pass). Clean isolated worktree;
no local tests or builds run. This is a behavior audit, not structural cleanup.

## Inventory and boundaries

- Python CLI: fixture/validate/compare/replay, bounded local JSON and policy files,
  offline provider import/audit. argparse owns command validation; stdout reports
  and exit code 2 distinguish rejected input.
- Loopback HTTP: host/origin checks, 2 MiB JSON cap, strict schema and duplicate-key
  rejection, static assets confined to web/dist, no broker or outbound requests.
  Single worker avoids QuantLib global races; sockets have a ten-second timeout.
- Engine: quote availability and freshness, supported European cash verticals,
  cost/risk/delta budgets, atomic paper opens/closes and official settlement.
  Unavailable settlement retains exposure; replay cutoff avoids future events.
- React dashboard: scenario/import selection, request cancellation and generation
  isolation, validated responses, risk controls, payoff inspection and JSON export.
- Persistence: none beyond explicitly downloaded/redirected reports. No accounts,
  tenants, authentication, production credentials or external writes exist.
- CI: Python unittest, Vitest boundaries and browser journeys, formatting, lint,
  type checking and production build. Preserve all existing gates.

## Confirmed findings (before fixes)

1. **Timestamp normalization can escape input rejection (high confidence).**
   `options_lab/schema.py:timestamp` catches parse errors but normalizes outside
   the try block. Valid ISO syntax `0001-01-01T00:00:00+01:00` underflows when
   converted to UTC. CLI validate/replay then raises uncaught OverflowError
   instead of a clean input rejection (HTTP already catches OverflowError).
   Normalize inside the guarded block and raise InputError for out-of-range UTC.

2. **Control edits can strand a scenario download (high confidence).**
   `web/src/app.tsx:loadScenario`: shared generation invalidation discards the
   pending fixture after a risk/time control edit, leaving dataset undefined and
   Compare disabled. Accept the still-selected fixture but keep its analysis
   invalidated; preserve a changed decision time. Deterministic browser regression
   holds the flat response, edits risk to $50, releases it, then submits and checks
   the risk rejection. Scenario changes still abort old fixture downloads.

## Reconciled/rejected hypotheses

- Premature settlement/payoff rounding was rejected on closer inspection: both
  expressions already scale inside money(). No accounting change is justified.
- Provider imports cannot create paper fills: observation_only is immutable true
  in conversion and checked by both compare and replay, covered by API tests.
- Missing settlement is not fabricated from spot: explicit official value and
  availability are required, covered by pending and cutoff tests.
- Stale imports cannot overwrite a newer scenario: generation guard spans file
  reads and requests, covered by browser regression from the untangle pass.
- Static traversal and cross-origin computation are guarded and covered by API
  tests. No tenant or transaction store exists to audit.
- Source licensing labels are user assertions, explicitly described as unverified;
  this audit does not invent a remote entitlement service.

## Validation plan / framework applicability

Add targeted timestamp boundary regressions to existing unittest runner and a CI pre-fix
reproduction using the original engine with new assertions, followed by fixed
suite. Integrate real published tester-army `e2e` with `@e2e-dev/web` for a
credential-free scenario → risk rejection → recovery journey against the built
Python-served dashboard. Retain existing import/export/mobile/browser tests.
Published quickstart and CI docs inspected; versions and evidence recorded below
when resolved. Independent review must challenge both findings and changes.

Published npm versions verified: e2e 0.23.0 (tester-army repository),
@e2e-dev/web 0.15.5; Node requirement ^22.22.3 or >=24.8, CI uses 26.12.1.
Installed with scripts suppressed. Read published quickstart, CI, GitHub Actions
and installed guide. Dependencies chosen because user requested the maintained
runner and its official Playwright web engine. No agent/model/login steps.

CI setup evidence: run 42303961461 exposed shallow history in the baseline
reproduction (fixed with checkout fetch-depth 0). Run 42304292421 exposed Python
3.14 standard-library `test` package shadowing our namespace directory; the
reproduction now uses native unittest discovery with `-s test -p test_engine.py
-k test_timestamp_utc_range_rejected_as_input_error`, like the existing suite.
Neither run established test success; subsequent CI remains required.
