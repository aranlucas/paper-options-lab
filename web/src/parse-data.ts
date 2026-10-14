import { z } from "zod";
import type { Analysis, Dataset } from "./types";

const sourceSchema = z.looseObject({
  kind: z.enum(["synthetic", "imported"]),
  name: z.string(),
  feed: z.string(),
  usage_rights: z.string(),
  observation_only: z.literal(true).optional(),
});

const datasetSchema = z.looseObject({
  schema_version: z.literal(1),
  source: sourceSchema,
  snapshots: z
    .array(z.looseObject({ id: z.string(), as_of: z.string().min(1), spot: z.number() }))
    .min(1),
  settlements: z.array(z.unknown()),
  events: z.array(z.unknown()),
});

const candidateSchema = z.looseObject({
  id: z.string(),
  long_id: z.string(),
  short_id: z.string(),
  kind: z.enum(["call", "put"]),
  exercise: z.enum(["european", "american"]),
  settlement: z.enum(["cash", "physical"]),
  long_strike: z.number(),
  short_strike: z.number(),
  expires_at: z.string(),
  quantity: z.number(),
  multiplier: z.number(),
  reasons: z.array(z.string()),
  eligible: z.boolean(),
  debit: z.number().optional(),
  entry_fees: z.number().optional(),
  reserved_exit_fees: z.number().optional(),
  settlement_fees: z.number().optional(),
  max_loss: z.number().optional(),
  expiry_max_loss: z.number().optional(),
  expiry_max_profit: z.number().optional(),
  break_even: z.number().optional(),
  dte: z.number().optional(),
  greeks: z
    .looseObject({ delta: z.number(), gamma: z.number(), theta: z.number(), vega: z.number() })
    .optional(),
  payoff: z.array(z.looseObject({ spot: z.number(), pnl: z.number() })).optional(),
  long_fill: z.number().optional(),
  short_fill: z.number().optional(),
  slippage_cost: z.number().optional(),
  spread_drag: z.number().optional(),
});

const ledgerRowSchema = z.looseObject({
  at: z.string(),
  action: z.string(),
  cash: z.number(),
  reserved_risk: z.number(),
  position_id: z.string().optional(),
  spread: z.string().optional(),
  debit: z.number().optional(),
  credit: z.number().optional(),
  pnl: z.number().optional(),
  fees: z.number().optional(),
  reasons: z.array(z.string()).optional(),
});

const analysisSchema = z.looseObject({
  comparison: z.looseObject({
    source: sourceSchema,
    as_of: z.string(),
    snapshot_id: z.string().nullable(),
    spot: z.number().optional(),
    candidates: z.array(candidateSchema),
    eligible_count: z.number().optional(),
    rejected_count: z.number().optional(),
    error: z.string().optional(),
  }),
  replay: z.looseObject({
    label: z.string(),
    cash: z.number(),
    realized_pnl: z.number(),
    reserved_risk: z.number(),
    complete: z.boolean(),
    equity: z.number().nullable(),
    open_positions: z.array(candidateSchema),
    ledger: z.array(ledgerRowSchema),
  }),
});

const errorSchema = z.object({ error: z.string() });

export function parseDataset(text: string): Dataset {
  const data: unknown = JSON.parse(text);

  // Validate without returning Zod's normalized copy: the server must see every original key.
  if (datasetSchema.validate(data)) {
    return data;
  }

  return datasetSchema.parse(data);
}

export function parseAnalysis(text: string): Analysis {
  const data: unknown = JSON.parse(text);

  // Retain the original report, including metadata and unusual own-property names.
  if (analysisSchema.validate(data)) {
    return data;
  }

  return analysisSchema.parse(data);
}

export function apiError(text: string, fallback: string): string {
  try {
    const parsed = errorSchema.safeParse(JSON.parse(text));

    return parsed.success ? parsed.data.error : fallback;
  } catch {
    return fallback;
  }
}
