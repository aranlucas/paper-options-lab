import type { LedgerRow } from "./types";

export function keyedLedgerRows(rows: readonly LedgerRow[]) {
  const occurrences = new Map<string, number>();

  return rows.map((row) => {
    const identity = JSON.stringify(row);
    const occurrence = occurrences.get(identity) ?? 0;
    occurrences.set(identity, occurrence + 1);

    return { key: `${identity}:${occurrence}`, row };
  });
}
