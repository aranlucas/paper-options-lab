# Paper Options Lab research brief

Reviewed October 1, 2026 (Pacific; October 2 UTC). This is a local, paper-only research prototype. Synthetic scenario outputs are illustrations, not historical investment performance, investment advice, or evidence of profitable recommendations.

## Bounded workflow

Compare call debit verticals (long lower strike, short higher strike) and put debit verticals (long higher strike, short lower strike), with equal quantity, expiration, underlying, multiplier, exercise style and trading cutoff. The UI orders eligible candidates by reserved maximum loss, never expected return. Rejected candidates expose machine-readable reasons.

The OIC’s [bull call spread](https://www.optionseducation.org/strategies/all-strategies/bull-call-spread-debit-call-spread) and [bear put spread](https://www.optionseducation.org/strategies/all-strategies/bear-put-spread) describe limited-loss, limited-gain structures. This prototype’s cash-settled terminal value is the difference of two intrinsic values times multiplier and quantity, less the entry debit and fees. For physically settled positions, that convenient diagram alone does not model operational exercise/assignment exposure.

## Exercise, assignment, and expiration

Cboe identifies [SPX options](https://www.cboe.com/tradable-products/sp-500/spx-options/) as European and cash settled. Its [contract specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications/) state a 100 multiplier and distinguish the final trading times of SPX and SPXW. This motivates an explicitly European cash-settlement scope; DEMO-INDEX is fictional and is not an actual SPX chain.

The [OIC exercise FAQ](https://www.optionseducation.org/referencelibrary/faq/options-exercise) explains that American-style assignment may occur before expiration and that dividends can raise call exercise incentives. Offsetting option legs are not a guarantee of synchronized assignment. Therefore all American-style contracts, physical delivery, and adjusted deliverables are rejected, rather than passed through a European payoff engine. The [OCC disclosure document landing page](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document) is the authoritative starting point for standardized option characteristics and risks.

Expiration is an exact timezone-aware instant; last trading time is a separate field. Settlement consumes an explicit cash exercise-settlement value matching underlying and expiration. Ordinary underlying closing prices are not substituted for exchange settlement values. Availability timestamps delay settlement recognition. Missing values leave positions open, cash unchanged, equity unreported, and risk reserved. Exchange holidays, half days, AM/PM settlement conventions, publication schedules and contract metadata must be supplied correctly; there is no built-in exchange calendar.

## Data constraints

Alpaca’s official [historical option data documentation](https://docs.alpaca.markets/us/docs/historical-option-data) says coverage begins in February 2024. It distinguishes indicative derivatives of OPRA quotes, with delayed derivative trades, from subscribed consolidated BBO data. Its [option-chain reference](https://docs.alpaca.markets/us/reference/optionchain) also distinguishes subscribed OPRA from the free indicative feed with modified quotes. Neither feed is accessed by this application. No account, subscription, credential, or external data adapter is created.

No licensed historical chains were available for this task. The included fixtures construct explicit synthetic spot/volatility scenarios and price fictional option contracts using QuantLib. They are not historical chains reconstructed from stock bars. Imports must contain actual timestamped contract-level bid/ask observations, IV, size/liquidity fields, metadata and provenance. Indicative and unknown feeds are rejected for executable-fill simulation. Imported `opra` or `licensed` labels are user assertions, not verified rights or quality certifications. Do not redistribute imported data without appropriate rights.

## GitHub libraries reviewed

| Project | Fit and decision |
| --- | --- |
| [QuantLib](https://github.com/lballabio/QuantLib) and [QuantLib-SWIG](https://github.com/lballabio/QuantLib-SWIG) | Selected. Mature pricing library and official Python bindings. Analytical option valuation and coherent Greeks add real value without reinventing numerical finance. |
| [vollib](https://github.com/vollib/vollib) | Focused Black / Black–Scholes / Black–Scholes–Merton and implied-volatility tooling; a reasonable lighter alternative. Not included: the prototype imports IV and QuantLib already provides the required analytical calculations. |
| [backtesting.py](https://github.com/kernc/backtesting.py) | Useful strategy testing framework, whose README illustrates OHLCV-style stock strategies. Not used to imply options-chain history exists. A small contract/event replay engine makes quote availability, contract identity and cash settlement explicit. |

[QuantLib PyPI](https://pypi.org/project/QuantLib/) showed current release 1.43 (July 14, 2026); the wheel is pinned to 1.43. The project notes that shared C++ globals can make concurrent use unsafe. This app uses a single-worker loopback server and independent `BlackCalculator` objects without the global evaluation date. The [official BlackCalculator header](https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/blackcalculator.hpp) documents its spot delta/gamma, theta-per-day and volatility sensitivities. Vega is divided by 100 to report dollars per one percentage-point IV change; every net Greek is scaled by multiplier and quantity. Pricing uses ACT/365 continuous time, continuously compounded rates and a continuous dividend yield.

The general Trending investigation belongs to the parent’s overnight research task. These libraries were evaluated on domain relevance; no claim is made that any were trending today.

## Deterministic assumptions and limits

- Entry: long at ask plus configurable adverse slippage; short at bid minus slippage. Per-contract fees apply to both legs. No midpoint fills. Debit must be strictly positive and below strike width.
- Close: reverse bid/ask and adverse slippage, both-leg fees. Atomic package exit must have nonnegative credit within strike width, otherwise it is rejected with no fill. This permits a loss bound but can leave the paper position open. No legging or stock position is simulated.
- Risk: reserve entry debit, entry fees and the greater of close/settlement fees. Portfolio limits use the sum of individual worst losses without correlation offsets. Existing gross absolute delta is refreshed from current visible quotes before new entries; unavailable marks reject new entries. Limits gate entries; changing markets do not trigger automatic liquidation.
- Liquidity: positive, uncrossed bid/ask; each spread ≤0.6 points and ≤25% of midpoint; quote age ≤120 seconds; two-leg timestamp skew ≤5 seconds; volume ≥10, OI ≥100, both displayed sizes ≥quantity. Liquidity observations must have been available and be ≤24 hours old. These are screening heuristics, not proof of executable liquidity.
- The default fictional paper capital is $10,000; position risk cap $500; aggregate cap $1,500; at most three positions and two spreads per position; gross delta budget 200 units; 7–60 DTE. Fee assumptions are illustrative, not a broker fee schedule.
- Greeks are local European model sensitivities, not probabilities of real-world profits. Inputs are not calibrated to a volatility surface. Constant IV, continuous yield, no discrete dividends, no stochastic rates, no jumps within pricing, no queues/latency, no market impact or partial fills, no margin/tax/funding modeling. The synthetic gap scenario tests a changed terminal outcome, not an estimated jump process.
- The replay is an event-accounting harness for user-specified spread plans. It does not optimize a strategy, construct a survivorship-free historical universe, perform statistical validation, calculate Sharpe ratios, or report a mark-to-market equity curve. Open equity is deliberately unavailable; realized P&L excludes unresolved positions.

## Replay-window experiment

The follow-up replay-window experiment adds a CLI `--through` cutoff. Full replay deliberately evaluates the entire synthetic plan; the cutoff evaluates only events and published settlement available by one instant. It appends a local observation at that instant without modifying the imported dataset. Before entry, cash remains fictional capital; after entry, unresolved risk remains reserved; immediately before settlement publication, no settled P&L is recognized. At publication, explicit cash settlement can be recognized even if the dataset's next planned observation is later. [Saved before/after accounting windows](replay-window-experiment.json) preserve evidence for the rally fixture. Three regression tests verify future-event exclusion, exact settlement availability, input immutability, timezone requirements and equivalence to full replay at the final event. This is temporal accounting validation, not strategy performance analysis.

## Architectural boundary

There is no broker SDK, credential reader, account API, live market data API, external inference, or order endpoint. The Python core is pure local computation over bounded JSON. The HTTP server binds only `127.0.0.1`, checks loopback Host and same-origin requests, and serves one local analysis endpoint. JSON is limited to 2 MiB, 100 snapshots, 24 contracts per snapshot, and 200 events. No uploaded code is executed or stored by the server. No deployment was provisioned.
