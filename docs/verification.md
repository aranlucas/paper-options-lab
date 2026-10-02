# Verification evidence

Local final QA: October 1, 2026 Pacific. Python 3.14.7, QuantLib 1.43, Node 26.10.0, React 19.3.0, TypeScript 7.0.2, Vite 8.3.2 on the user's Mac. The source is isolated from the existing trading-mcp repository.

## Automated checks

```sh
.venv/bin/python -m unittest discover -s tests -v
npm --prefix web run check
npm --prefix web run build
git diff --check
```

The financial/API suite covers known option prices and finite-difference Greek checks; scaled multipliers/quantities; bounded payoffs and fee accounting; missing/stale/future/crossed/wide quotes; liquidity/size/IV omissions; asynchronous legs; exercise/delivery/adjustment exclusions; DTE and trading cutoffs; position/cash/quantity/delta/portfolio limits; delayed and missing official cash settlement; early close fees; deterministic replay; indicative feed rejection; malformed/unknown input fields; strict identities/timestamps; exact fixture regeneration; loopback origin/Host guards; JSON limits and duplicate keys; static path restrictions; and absence of an order endpoint. Twenty-seven tests pass, including three added cutoff tests for the follow-up replay-window experiment.

TypeScript check and the production build pass. Build output is approximately 240.5 KB JS (75 KB gzip) and 10.7 KB CSS (3.1 KB gzip). All seven saved fixtures match their deterministic generator exactly.

## Browser interactions

The in-app browser was attempted first. It became unavailable during the initial session, so the installed Playwright CLI was used for isolated browser regression and screenshot capture. After reconnection, the in-app browser loaded the final dashboard and verified the corrected European cash-settlement metadata. The saved browser regression completed successfully with 17 assertions, desktop 1440×1050, mobile 390×844, and zero page exceptions.

The script is `tests/browser_qa.js`. Run it with the installed Playwright CLI after starting the loopback server:

```sh
playwright-cli --session paper-options open http://127.0.0.1:8792
playwright-cli --session paper-options run-code --filename tests/browser_qa.js
playwright-cli --session paper-options close
```

It verifies call filtering, row selection, exercise metadata, payoff slider, rejected-row visibility and explanation, clearing old results after risk edits, a $50 risk budget blocking entries, restoring limits, pending settlement withholding equity, stale quotes blocking entries, local JSON import, dataset download, mobile overflow/slider visibility, and zero page exceptions.

## Visual review

The code-native design specification is [design.md](design.md). External concept generation was intentionally omitted to honor the request to avoid external inference. Actual browser captures were inspected visually with `view_image`; no generated image stands in for the interface.

| Inspection point | Spec and rendered evidence |
| --- | --- |
| Palette and framing | Navy masthead, true white workspace, cobalt selection/plot, muted separators, teal eligible and amber rejection states. Open table plus side inspector, rather than repetitive cards. |
| Copy and data labeling | Permanent paper-only status, fictional DEMO-INDEX and synthetic-result text are visible. No real-performance or profit claim. Above-the-fold task/control copy matches the code-native spec. |
| Typography and spacing | Deliberate heading/control/table hierarchy; monospace numerical data; consistent gutters and fine separators. Desktop table and chart remain legible. |
| Risk/math presentation | Entry debit, reserved risk, break-even and Greek units are explicit. Payoff includes costs. Settlement metadata agrees with the European-only gate. |
| Responsiveness | At 390px, inputs become two columns; decision control stacks; inspector follows the table. Horizontal table scrolling is contained; the page has no horizontal overflow. |
| Interaction/focus | Native labeled controls and a keyboard-operated payoff slider work. Risk edits invalidate previous results. Import/export and rejected-row selection are functional. |

Fixed issues: the dataset selector needed an explicit accessible label; stale results needed clearing after policy/time edits; the earlier capture used a backend without the exercise/settlement metadata fields. The backend was restarted and final screenshots regenerated with the correct European cash-settlement label. No material visual mismatch remains against the code-native specification.

Screenshots are intentionally retained as requested test evidence:

- [Desktop](../output/playwright/desktop.png), [full dashboard](../output/playwright/desktop-full.png)
- [Mobile inputs](../output/playwright/mobile.png), [mobile payoff](../output/playwright/mobile-payoff.png)

## Honest replay outcomes

Rally, flat, selloff and volatility-crush scenarios all settle or close their local paper positions. Stale and missing-bid scenarios produce zero eligible spreads and no positions. The missing-settlement scenario deliberately retains three positions and $731.61 reserved risk; its equity is unavailable. These are synthetic accounting examples, not measured historical strategy returns.

## Publication and hosted checks

The repository is private. Its initial main branch contains only an honest bootstrap README so the complete implementation can be reviewed in a meaningful PR. A single Ubuntu verification job has read-only contents permissions, immutable official action pins, a five-minute timeout, and no deployment, broker credentials, account operations or external inference. It checks the exact PR head and any resulting main commit, financial/API tests, fixture validation, TypeScript and production build. Hosted status is reported on the PR; local evidence alone is not a claim that hosted CI passed. The first hosted attempt identified a YAML scalar requiring quotation around pip's `:all:` argument; this was corrected before review or merge.

No live execution, broker login, financial account data, account creation, paid data subscription, credential setup, public release or deployment provisioning was performed. Historical option-chain licensing and provenance remain user-import responsibilities, as documented in the research brief.
