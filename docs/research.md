# Paper Options Lab research brief

This is a local, paper-only research prototype. Synthetic scenario outputs are illustrations, not historical investment performance, investment advice, or evidence of profitable recommendations.

## Bounded workflow

Compare call debit verticals (long lower strike, short higher strike) and put debit verticals (long higher strike, short lower strike), with equal quantity, expiration, underlying, multiplier, exercise style and trading cutoff. The UI orders eligible candidates by reserved maximum loss, never expected return. Rejected candidates expose machine-readable reasons.

The OIC’s [bull call spread](https://www.optionseducation.org/strategies/all-strategies/bull-call-spread-debit-call-spread) and [bear put spread](https://www.optionseducation.org/strategies/all-strategies/bear-put-spread) describe limited-loss, limited-gain structures. This prototype’s cash-settled terminal value is the difference of two intrinsic values times multiplier and quantity, less the entry debit and fees. For physically settled positions, that convenient diagram alone does not model operational exercise/assignment exposure.

## Exercise, assignment, and expiration

Cboe identifies [SPX options](https://www.cboe.com/tradable-products/sp-500/spx-options/) as European and cash settled. Its [contract specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications/) state a 100 multiplier and distinguish the final trading times of SPX and SPXW. This motivates an explicitly European cash-settlement scope; DEMO-INDEX is fictional and is not an actual SPX chain.

The [OIC exercise FAQ](https://www.optionseducation.org/referencelibrary/faq/options-exercise) explains that American-style assignment may occur before expiration and that dividends can raise call exercise incentives. Offsetting option legs are not a guarantee of synchronized assignment. Therefore all American-style contracts, physical delivery, and adjusted deliverables are rejected, rather than passed through a European payoff engine. The [OCC disclosure document landing page](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document) is the authoritative starting point for standardized option characteristics and risks.

Expiration is an exact timezone-aware instant; last trading time is a separate field. Settlement consumes an explicit cash exercise-settlement value matching underlying and expiration. Ordinary underlying closing prices are not substituted for exchange settlement values. Availability timestamps delay settlement recognition. Missing values leave positions open, cash unchanged, equity unreported, and risk reserved. Exchange holidays, half days, AM/PM settlement conventions, publication schedules and contract metadata must be supplied correctly; there is no built-in exchange calendar.

## Data constraints

The included fixtures construct explicit synthetic spot/volatility scenarios and price fictional contracts using QuantLib. They are not historical chains reconstructed from stock bars. Fill simulation needs timestamped contract-level bid/ask observations, IV, size/liquidity fields, metadata and provenance. Indicative and unknown feeds are rejected. Imported `opra` or `licensed` labels are user assertions, not verified rights or quality certifications. Do not redistribute imported data without appropriate rights.

## Free API follow-up

The offline adapter was scoped from Market Data documentation reviewed October 1, 2026 Pacific: [historical chains](https://www.marketdata.app/docs/api/options/chain/) omit IV and Greeks, quote/volume observations use 16:00 ET, and OI reflects the prior session. Full-session volume would introduce lookahead into a morning decision. [Timestamp conventions](https://www.marketdata.app/docs/api/dates-and-times/) distinguish Unix instants from Eastern session dates; [freshness rules](https://www.marketdata.app/docs/account/data-freshness/) can leave weekend or pre-open observations older than one day. These are the adapter's bounded assumptions, not a guarantee of current provider coverage or entitlement.

The [offline converter and audit](marketdata-import.md) requires explicit mechanics and timing metadata rather than inferring them from symbols or a provider expiration clock. Missing IV stays missing; supplied latest-EOD Greeks are audit observations, not model-derived sensitivities. Delayed EOD observations cannot establish intraday fills, so converted datasets are always observation-only. [Saved compatibility evidence](provider-import-evidence.json) illustrates the missing-data and fill gates using fictional contracts.

Alpaca's [indicative option feed](https://docs.alpaca.markets/us/reference/optionchain) was excluded because modified quotes do not support the lab's fill assumptions. ThetaData's [EOD Greeks endpoint](https://thetadata.net/docs/operations_python/option_history_greeks_eod.html) required paid access in that review and did not solve the missing free historical Greeks problem. No provider is accessed by this app; permission and provenance remain the importer's responsibility.

## Library choices

| Project | Fit and decision |
| --- | --- |
| [QuantLib](https://github.com/lballabio/QuantLib) and [QuantLib-SWIG](https://github.com/lballabio/QuantLib-SWIG) | Selected. Mature pricing library and official Python bindings. Analytical option valuation and coherent Greeks add real value without reinventing numerical finance. |
| [vollib](https://github.com/vollib/vollib) | Focused Black / Black–Scholes / Black–Scholes–Merton and implied-volatility tooling; a reasonable lighter alternative. Not included: the prototype imports IV and QuantLib already provides the required analytical calculations. |
| [backtesting.py](https://github.com/kernc/backtesting.py) | Useful strategy testing framework, whose README illustrates OHLCV-style stock strategies. Not used to imply options-chain history exists. A small contract/event replay engine makes quote availability, contract identity and cash settlement explicit. |

QuantLib's [official BlackCalculator header](https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/blackcalculator.hpp) defines the sensitivities used here. Pricing uses ACT/365 continuous time, continuously compounded rates and a continuous dividend yield. Delta and gamma are spot sensitivities, theta is per calendar day, and vega is per one percentage-point IV change. Net spread Greeks scale by multiplier and quantity. The server uses one worker and independent `BlackCalculator` objects without changing QuantLib's global evaluation date.

## Deterministic assumptions and limits

- Entry: long at ask plus configurable adverse slippage; short at bid minus slippage. Per-contract fees apply to both legs. No midpoint fills. Debit must be strictly positive and below strike width.
- Close: reverse bid/ask and adverse slippage, both-leg fees. Atomic package exit must have nonnegative credit within strike width, otherwise it is rejected with no fill. This permits a loss bound but can leave the paper position open. No legging or stock position is simulated.
- Risk: reserve entry debit, entry fees and the greater of close/settlement fees. Portfolio limits use the sum of individual worst losses without correlation offsets. Existing gross absolute delta is refreshed from current visible quotes before new entries; unavailable marks reject new entries. Limits gate entries; changing markets do not trigger automatic liquidation.
- Liquidity thresholds and illustrative fee/risk defaults live in [`Policy`](../options_lab/engine.py). Passing them is a screening heuristic, not proof of executable liquidity or a broker fee quote.
- Greeks are local European model sensitivities, not probabilities of real-world profits. Inputs are not calibrated to a volatility surface. Constant IV, continuous yield, no discrete dividends, no stochastic rates, no jumps within pricing, no queues/latency, no market impact or partial fills, no margin/tax/funding modeling. The synthetic gap scenario tests a changed terminal outcome, not an estimated jump process.
- The replay is an event-accounting harness for user-specified spread plans. It does not optimize a strategy, construct a survivorship-free historical universe, perform statistical validation, calculate Sharpe ratios, or report a mark-to-market equity curve. Open equity is deliberately unavailable; realized P&L excludes unresolved positions.

## Replay time boundary

Full replay evaluates the entire plan. CLI `--through` evaluates only events and published settlement available by one instant, appending an observation at the cutoff without modifying the dataset. Unresolved risk remains reserved and no settled P&L is recognized before publication. At publication, explicit cash settlement can be recognized even if the next planned observation is later. [Saved accounting windows](replay-window-experiment.json) illustrate this boundary for the synthetic rally fixture; they are temporal accounting examples, not strategy performance.

## Architectural boundary

There is no broker SDK, credential reader, account API, live market data API, external inference, or order endpoint. The Python core is pure local computation over bounded JSON. The HTTP server binds only `127.0.0.1` and accepts local Host/Origin values plus the exact origin assigned by Portless. Analysis requests are limited to 2 MiB; datasets allow at most 100 snapshots, 100 settlements, 24 contracts per snapshot, and 200 events. Uploaded data is neither executed nor stored by the server. Keep the server local; these controls are not authentication for a public deployment.
