# Import schema v1

Use `fixtures/rally.json` as the complete reproducible example. Export it from the dashboard, or run `.venv/bin/python -m options_lab fixture --scenario rally`. Every object rejects unknown keys; duplicate keys, nonfinite numbers, and naive timestamps are rejected. UTC ISO-8601 strings with `Z` are recommended. Equivalent offsets parse as UTC, but identity metadata strings should remain identical across snapshots.

The root object has exactly `schema_version`, `source`, `snapshots`, `settlements`, `events`.

| Object | Required fields |
| --- | --- |
| Source | `kind`: `synthetic` or `imported`; `name`; `feed`: synthetic for fixtures, `opra`/`licensed`/`indicative`/`unknown` for imports; `usage_rights`: human-readable rights/provenance assertion |
| Snapshot | `id`, `underlying`, `as_of`, `available_at`, `spot`, `spot_at`, `rate`, `dividend_yield`, `contracts` |
| Contract quote | `id`, `kind` (`call`/`put`), `strike`, `expires_at`, `last_trade_at`, `exercise` (`european`/`american`), `settlement` (`cash`/`physical`), integer `multiplier`, boolean `adjusted`, `bid`, `ask`, integer `bid_size`, `ask_size`, `volume`, `open_interest`, `liquidity_at`, `quote_at`, `iv` |
| Cash settlement | `underlying`, `expires_at`, `value`, `available_at`, `method`: `official_cash_value` |
| Open event | `at`, `action`: `open`, `long_id`, `short_id`, integer `quantity` |
| Close event | `at`, `action`: `close`, `position_id`: e.g. `paper-001` |
| Observation | `at`, `action`: `observe` |

Prices, strikes and spot use underlying price/index points. Multiplier converts one premium point to dollars. IV and rates are decimal annualized values (0.25 = 25% IV). Volume, OI and sizes count contracts. `bid`, `ask`, sizes, volume, OI and IV may be null; the spread is then rejected with missing-data reasons. Expiration and final trading cutoff are exact instants, not date-only values.

`as_of` is the chain observation instant; `available_at` is when the whole snapshot and its supplied metadata/IV/rates became knowable. Quotes, underlying and liquidity timestamps must be no later than `as_of`. Liquidity time should reflect when that volume/OI information was actually published and knowable, especially previous-day OI. Never put end-of-day totals into a morning decision. Future availability, negative ages, stale data and expired cutoffs fail closed. Snapshot selection uses the latest visible `as_of`, then availability and ID; it does not fall back to older chains to find a favorable quote.

Contract identity must not change across snapshots, including underlying, kind, strikes, exact timestamps, style, delivery, multiplier and adjustments. Each snapshot ID and its contract IDs must be unique. Include at most 24 contract quotes per snapshot; preselect a relevant strike/expiration window when importing. Missing contracts at an entry or close are rejected; missing current portfolio marks block further opens.

Events must be strictly increasing. Paper position IDs are assigned sequentially only on successful opens. Atomic spread quantity is equal across its two legs. Settlements are unique per underlying/expiration and cannot become available before expiration. A later `observe` event recognizes available settlements. Early close requests after expiry reject while settlement is pending. No settlement is inferred from spot, and no position is quietly dropped.

`usage_rights`, feed labels and imported values are not verified by the app. This schema is for contract observations, not broker accounts, orders, credentials or personal financial data. Only import data you are permitted to use locally; source JSON and reports may contain proprietary market data.
