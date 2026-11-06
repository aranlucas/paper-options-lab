export type { Scenario, Source, Dataset, Candidate, LedgerRow, Analysis } from "./parse-data";

export const usd = (n?: number | null) =>
  n === null || n === undefined
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(n);

export const num = (n?: number | null, digits = 2) =>
  n === null || n === undefined ? "—" : n.toFixed(digits);

export const reason = (code: string) => code.toLowerCase().replaceAll("_", " ").replace(":", ": ");
