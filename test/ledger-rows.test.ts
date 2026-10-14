import { describe, expect, it } from "vitest";
import { keyedLedgerRows } from "@/ledger-rows";
import type { LedgerRow } from "@/types";

const open: LedgerRow = {
  at: "2026-01-02T15:00:00Z",
  action: "PAPER_OPEN",
  position_id: "spread-1",
  cash: 900,
  reserved_risk: 100,
};

const close: LedgerRow = { ...open, action: "PAPER_CLOSE", cash: 1100, reserved_risk: 0 };

describe("ledger row identity", () => {
  it("preserves rows and their order", () => {
    const rows = [open, close];
    expect(keyedLedgerRows(rows).map(({ row }) => row)).toEqual(rows);
  });

  it("retains distinct keys for identical repeated observations", () => {
    const rows = keyedLedgerRows([open, open, close]);
    expect(new Set(rows.map(({ key }) => key)).size).toBe(3);
  });

  it("keeps existing keys when unrelated events are inserted", () => {
    const original = keyedLedgerRows([open, open]);
    const inserted = keyedLedgerRows([close, open, open]);
    expect(inserted.slice(1).map(({ key }) => key)).toEqual(original.map(({ key }) => key));
  });
});
