# Paper Options Lab feature roadmap

Updated 2026-10-26. Proposed local learning/research work after Digits/MCP
priorities. Paper-only boundaries remain: no broker integration or order entry.

## Ordered releases

1. **Explain why a scenario passes or fails.** Turn the existing rejection
   reasons into a trace from input observation through each policy decision.
   Acceptance: the user can inspect the decisive quote/time/contract assumption;
   missing data remains missing; a hypothetical edit is labeled separately from
   the saved observation and never grants observation-only data fill eligibility.
2. **Compare assumptions side by side.** Save named local variants of fees,
   slippage or supported scenario inputs and compare their effects.
   Acceptance: variants retain provenance, share a clearly stated as-of time,
   and expose which assumptions changed. No variant silently imports future
   observations or expands the supported settlement model.
3. **Keep a reproducible research notebook.** Attach a hypothesis, selected
   scenario, explicit input/policy version and later observation to a local
   record. Acceptance: replay can recover the same permitted input condition;
   unresolved positions and reserved risk stay visible; revisions preserve the
   original hypothesis instead of rewriting it after the outcome.
4. **Make local import review easier.** Preview contract coverage, missing
   fields and provenance before accepting a saved provider export.
   Acceptance: unsupported contracts explain their rejection, source rights
   remain the user's separate responsibility, and no API key or network fetch
   is added merely to streamline the import screen.

## First slice and evidence

Use the existing synthetic scenarios to evaluate the decision trace. Ask whether
a reader can identify the blocking assumption and distinguish observed data from
a hypothetical edit. Measure comprehension, corrections and repeat notebook use,
not simulated returns. Set numerical targets only after observing a baseline.

Trading MCP may later exchange an explicitly versioned research record;
it must not turn this local lab into an execution service.
