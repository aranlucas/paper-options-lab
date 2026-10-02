# Offline MarketData-shaped import

This adapter converts saved JSON into the lab's strict local schema and produces a compatibility audit. It has no HTTP client, credential reader, account integration or implied-volatility inversion. No provider account is required to run the fictional fixtures.

```sh
.venv/bin/python -m options_lab import-marketdata --input fixtures/providers/marketdata-historical.json --metadata fixtures/providers/marketdata-historical.meta.json > /tmp/marketdata-offline.json
.venv/bin/python -m options_lab validate --input /tmp/marketdata-offline.json
.venv/bin/python -m options_lab audit-marketdata --input fixtures/providers/marketdata-historical.json --metadata fixtures/providers/marketdata-historical.meta.json
.venv/bin/python -m options_lab audit-marketdata --input fixtures/providers/marketdata-latest_eod.json --metadata fixtures/providers/marketdata-latest_eod.meta.json
```

`import-marketdata` writes only normalized dataset JSON to stdout. `audit-marketdata` writes diagnostics and defaults to the manifest retrieval instant; `--at` can audit another timezone-aware instant. Redirects are explicit local writes. The normalized dataset can be imported through the dashboard's existing JSON control, where it reports `OBSERVATION_ONLY_DATA` and no positions.

All four files in `fixtures/providers/` are synthetic. The historical example preserves null IV/Greeks. The latest-EOD example includes known synthetic inputs and supplied synthetic sensitivities. Neither contains actual Market Data observations, exchange contracts or returns.

## Observation boundary

Every conversion sets `source.observation_only` to true. Comparison and replay refuse entries independently of quote-age or other policy overrides. The adapter creates no events or cash settlement values. Historical missing IV remains null, and nonnull historical IV/Greeks are rejected instead of accepted as provider history. Latest-EOD values are preserved in the audit; they do not substitute for missing IV or become model Greeks. Zero remains zero rather than becoming null.

The audit lists per-contract stale, future, missing, liquidity and unsupported-mechanics reasons. This is data inspection, not a performance report. Sparse EOD observations and delayed retrieval cannot establish current or intraday executable fills. The lab's original synthetic replay remains available separately.

## Packet and manifest

Each local input is limited to 2 MiB. The packet must have status `s: "ok"` and 1–24 aligned rows; no-data/error responses fail closed. Required columns are `optionSymbol`, `underlying`, `expiration`, `side`, `strike`, `updated`, and `underlyingPrice`. Optional market fields may be omitted or null. Unknown fields, differing column lengths, nonfinite values, mixed underlyings, asynchronous timestamps and differing spot values fail. There is no averaging, merging or forward fill.

The complete sidecar example is `fixtures/providers/marketdata-historical.meta.json`. All fields below are required; unknown keys fail.

| Manifest field | Local rule |
| --- | --- |
| `adapter_version` | Integer 1 |
| `source` | Strict kind/name/feed/usage_rights assertion; no token field |
| `request_kind` | `historical` or `latest_eod` |
| `request_date` | Exact YYYY-MM-DD for historical; null for latest-EOD |
| `delivery` | `free_24h` only |
| `retrieved_at` | Actual timezone-aware local retrieval instant; at least 24 hours after observation |
| `underlying` | Must agree across all rows and specs |
| `rate`, `dividend_yield` | Explicit decimal annualized model assumptions |
| `inputs_available_at` | When those assumptions were knowable; no later than observation |
| `open_interest_available_at` | Publication instant if any OI is supplied; null otherwise allowed; no later than observation and no more than 24 hours old |
| `iv_units` | Explicit `decimal`; no guessing percentage units |
| `contracts` | Exact mapping from each raw option symbol to its mechanics |

Each contract spec requires `root`, `underlying`, `expires_at`, `last_trade_at`, `exercise`, `settlement`, `multiplier`, `adjusted`, and `reference`. Supply product-specific official contract documentation in `reference`; the app does not fetch or independently verify it. The fictional fixture's reference explicitly identifies its invented mechanics. Exercise style, delivery and multiplier cannot be inferred safely from the provider packet. American, physical and adjusted contracts are retained for inspection and expose the core's rejection reasons.

Compact OCC identities and roots padded to exactly six characters are supported. Symbol date, C/P and strike must agree with columns and metadata. Padded/compact aliases count as duplicates. The exact manifest expiry and final trading cutoff are retained; cutoff must not exceed expiry. A different provider expiration clock on the same Eastern date produces `PROVIDER_EXPIRATION_TIME_DIFFERS`. Conflicting dates fail. Reference strings and feed/rights labels remain user assertions.

## Time and provenance

Unix seconds are parsed as absolute UTC instants; Eastern conversion is used only for session-date and clock checks. Historical rows must match the requested date at 16:00 America/New_York, including DST. This narrow adapter does not normalize half-day or other unsupported timestamps. It requires one uniform observation rather than silently relabeling different rows.

Retrieval becomes snapshot `available_at`, never quote time. The adapter conservatively enforces a 24-hour floor; it does not implement a holiday/rollover calendar or certify provider delivery entitlement. Older weekend observations remain older. Rate/yield availability and OI publication must be supplied honestly. Full-session volume keeps the later observation timestamp, while OI's distinct publication instant is retained in the audit. Nothing is backdated into an intraday decision.

See the [primary-source research brief](research.md#free-api-follow-up) for provider plan, chain, timestamp and freshness links. User-imported observations still require permission to use locally and independent provenance/contract checks. Do not include credentials or financial account data in either JSON file.
