# Untangle decision log — 2026-11-06

## Baseline and inventory (before implementation)

Clean checkout at `21c87b4`; no existing edits to overwrite. Read root AGENTS.md
(the only repository guidance file) and the requested upstream skill. Both comment
and test cleanup are selected. No local tests, builds, benchmarks or browser checks
will run. No owned test process was found. Latest main CI run 41701890837 passed;
there is no demonstrated baseline test failure.

Reviewed Python validation, pricing, screening, replay, offline adapter, fixture
builders and HTTP/CLI boundaries; dashboard components, schemas, state handling,
styles, tests, CI, configuration and documentation.

## Decisions

- Derive dashboard payload types from their Zod schemas, keeping display formatting
  separate. `web/src/types.ts` manually duplicates source, dataset, candidate, ledger
  and report shapes in `parse-data.ts`; each payload change requires two edits.
  Preserve original JSON objects (including unusual own keys); the backend remains
  authoritative for dataset validation. Zod is already installed.
- Keep spread valuation and fill eligibility shared inside the engine.
  `evaluate_pair` and portfolio replay repeat time conversion and leg model calls;
  comparison and replay separately encode the same source execution restrictions.
  Extract domain helpers, retaining unrounded portfolio delta and rounded displayed
  Greeks. QuantLib remains the pricing implementation; no new dependency needed.
- Keep timestamp formatting with schema timestamps rather than fixture generation.
  `marketdata.py` duplicates `fixtures.iso`; CLI/server import a fixture-only default
  time (CLI intentionally uses the synthetic entry instant; server imports are unused).
  Share UTC serialization in schema and preserve existing fixture import compatibility.
- Remove repeated implementation comments only. Retain units, provenance, fail-closed
  settlement rules, accessibility rationales and external provider requirements.
- Evaluate tests last. Existing accounting, no-lookahead, import/property preservation,
  API and fixture reproducibility checks catch credible regressions and should remain.
  Parameterized fixtures protect different input data, not merely repeated code.
- Preserve deliberate special cases: unsupported exercise/delivery, unknown feeds,
  observation-only data, quote freshness/size, pending settlements, explicit replay
  cutoffs, request cancellation, API bounds and exact loopback origins express real
  requirements. Keep bounded Python validation separate from the UI renderability
  schema; their responsibilities differ. Do not introduce speculative frameworks or
  move small cohesive modules solely for size.
- CI already runs Python behavior/API tests, Vitest boundary tests, lint, formatting,
  typechecking, fixture conversion and build. Its parallel block is unusual but the
  latest successful run is evidence against changing it speculatively. Preserve it.

## Validation and review

Pending implementation and sequential independent static reviews. CI only for tests.

### First independent review

Reviewer confirmed type/model changes preserve contracts and identified:
- Dashboard repeats SCENARIOS despite an existing catalog endpoint. Consume and
  validate the catalog; test new IDs and malformed labels via existing Vitest.
- Production timestamp consumers should import schema.iso directly. Retain old
  fixture imports for callers without pass-through function wrappers.
- File reading and scenario loading did not share generation guards. A delayed
  older file or scenario could replace newer input, including after invalidation.
  Use the same generation ownership already used by analysis requests at every
  asynchronous completion and failure boundary.
- Browser error fallback assertion expected unwrapped text, although the UI wraps
  errors. Correct the assertion to the actual user-visible message. This is a
  baseline static finding, not an observed local or CI test failure.

No existing meaningful tests removed. Browser QA is currently manual; add CI
execution so the repaired interaction assertion and request ordering regression
are validated rather than claiming Vitest covers rendered behavior.

### Review follow-ups and validation preparation

Second reviewer caught a masking race in the regression check and an obsolete
lint override. The test now waits for stale-scenario analysis before releasing
controlled file text, awaits rendering, and checks selection before any new input
invalidation. Removed the override after making browser QA an imported function.
Third review caught the test runner's web/ working directory; fixture and capture
paths now resolve relative to the module instead of the calling directory.

Local formatting and lint completed successfully; `git diff --check` is clean.
No local tests or builds were run. Existing CI behavior tests remain intact;
Chromium installation and the rendered interaction check now follow the dashboard
build in CI. No dependency or custom script was added: reuse Playwright Core's
native installer and the existing Vitest runner. Final review pending.

Final independent reviewer confirmed the path corrections and found no remaining
worthwhile issues. Implementation and static review are complete; CI is the
remaining behavioral validation and merge gate.

### CI follow-up — run 42273998239

Python behavior/API tests, boundary tests, lint, format, typecheck and build passed.
The newly enabled browser suite exposed a pre-existing invalid fixture selection:
its slider reset check requested Call 100/110 while rejected spreads were hidden.
Use the eligible Call 95/100 instead, keeping the exact reset expectation. No
product behavior or risk filter changed, no test removed, no local reproduction.
