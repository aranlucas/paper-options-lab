export type Source = {
  kind: "synthetic" | "imported";
  name: string;
  feed: string;
  usage_rights: string;
  observation_only?: true;
};

export type Dataset = {
  schema_version: number;
  source: Source;
  snapshots: { id: string; as_of: string; spot: number }[];
  settlements: unknown[];
  events: unknown[];
};

export type Candidate = {
  id: string;
  long_id: string;
  short_id: string;
  kind: "call" | "put";
  exercise: "european" | "american";
  settlement: "cash" | "physical";
  long_strike: number;
  short_strike: number;
  expires_at: string;
  quantity: number;
  multiplier: number;
  reasons: string[];
  eligible: boolean;
  debit?: number;
  entry_fees?: number;
  reserved_exit_fees?: number;
  settlement_fees?: number;
  max_loss?: number;
  expiry_max_loss?: number;
  expiry_max_profit?: number;
  break_even?: number;
  dte?: number;
  greeks?: { delta: number; gamma: number; theta: number; vega: number };
  payoff?: { spot: number; pnl: number }[];
  long_fill?: number;
  short_fill?: number;
  slippage_cost?: number;
  spread_drag?: number;
};

export type LedgerRow = {
  at: string;
  action: string;
  cash: number;
  reserved_risk: number;
  position_id?: string;
  spread?: string;
  debit?: number;
  credit?: number;
  pnl?: number;
  fees?: number;
  reasons?: string[];
};

export type Analysis = {
  comparison: {
    source: Source;
    as_of: string;
    snapshot_id: string | null;
    spot?: number;
    candidates: Candidate[];
    eligible_count?: number;
    rejected_count?: number;
    error?: string;
  };
  replay: {
    label: string;
    cash: number;
    realized_pnl: number;
    reserved_risk: number;
    complete: boolean;
    equity: number | null;
    open_positions: Candidate[];
    ledger: LedgerRow[];
  };
};

export const usd = (n?: number | null) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(n);

export const num = (n?: number | null, digits = 2) => (n == null ? "—" : n.toFixed(digits));

export const reason = (code: string) => code.toLowerCase().replaceAll("_", " ").replace(":", ": ");
