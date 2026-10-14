import { describe, expect, it } from "vitest";
import { apiError, parseAnalysis, parseDataset } from "@/parse-data";
import analysis from "@test/fixtures/analysis.json";
import rally from "../fixtures/rally.json";
import flat from "../fixtures/flat.json";
import selloff from "../fixtures/selloff.json";
import volCrush from "../fixtures/vol-crush.json";
import stale from "../fixtures/stale.json";
import missing from "../fixtures/missing.json";
import pending from "../fixtures/pending.json";

describe("dataset boundary", () => {
  it.each([
    { name: "rally", fixture: rally },
    { name: "flat", fixture: flat },
    { name: "selloff", fixture: selloff },
    { name: "volatility crush", fixture: volCrush },
    { name: "stale", fixture: stale },
    { name: "missing", fixture: missing },
    { name: "pending", fixture: pending },
  ])("preserves the full $name dataset, including contracts and events", ({ fixture }) => {
    expect(parseDataset(JSON.stringify(fixture))).toEqual(fixture);
  });

  it("rejects malformed JSON", () => {
    expect(() => parseDataset("{")).toThrow("JSON");
  });

  it("rejects unsupported versions", () => {
    expect(() => parseDataset(JSON.stringify({ ...rally, schema_version: 2 }))).toThrow(
      "schema_version",
    );
  });

  it("rejects empty snapshots before UI state can use the first timestamp", () => {
    expect(() => parseDataset(JSON.stringify({ ...rally, snapshots: [] }))).toThrow("snapshots");
  });

  it("rejects wrong snapshot types", () => {
    expect(() =>
      parseDataset(
        JSON.stringify({ ...rally, snapshots: [{ id: "entry", as_of: false, spot: "100" }] }),
      ),
    ).toThrow("as_of");
  });
});

describe("analysis boundary", () => {
  it("preserves the complete server report, including provenance and policy metadata", () => {
    expect(parseAnalysis(JSON.stringify(analysis))).toEqual(analysis);
  });

  it("accepts incomplete settlement reports with null equity", () => {
    const report = { ...analysis, replay: { ...analysis.replay, complete: false, equity: null } };

    expect(parseAnalysis(JSON.stringify(report))).toEqual(report);
  });

  it("rejects malformed candidate arrays", () => {
    const report = { ...analysis, comparison: { ...analysis.comparison, candidates: [false] } };

    expect(() => parseAnalysis(JSON.stringify(report))).toThrow("candidates");
  });

  it("rejects an error response in place of a report", () => {
    expect(() => parseAnalysis('{"error":"invalid data"}')).toThrow("comparison");
  });

  it("rejects unrenderable ledger entries", () => {
    const report = { ...analysis, replay: { ...analysis.replay, ledger: [{ at: false }] } };

    expect(() => parseAnalysis(JSON.stringify(report))).toThrow("ledger");
  });
});

describe("API error boundary", () => {
  it("preserves the server's textual error", () => {
    expect(apiError('{"error":"dataset rejected"}', "Analysis failed")).toBe("dataset rejected");
  });

  it.each(["not JSON", "{}", '{"error":{"private":"details"}}', "null"])(
    "uses a safe fallback for %s",
    (text) => {
      expect(apiError(text, "Analysis failed")).toBe("Analysis failed");
    },
  );
});

describe("original JSON property preservation", () => {
  it.each(["__proto__", "constructor", "prototype"])(
    "retains dataset properties named %s for authoritative backend validation",
    (key) => {
      const extra = { [key]: { marker: "must reach the server" } };

      const payloads = [
        { ...rally, ...extra },
        { ...rally, source: { ...rally.source, ...extra } },
        { ...rally, snapshots: [{ ...rally.snapshots[0], ...extra }] },
      ];

      for (const payload of payloads) {
        const text = JSON.stringify(payload);
        expect(JSON.stringify(parseDataset(text))).toBe(text);
      }
    },
  );

  it.each(["__proto__", "constructor", "prototype"])(
    "retains analysis properties named %s at every parsed level",
    (key) => {
      const extra = { [key]: { marker: "must survive report export" } };

      const payloads = [
        { ...analysis, ...extra },
        { ...analysis, comparison: { ...analysis.comparison, ...extra } },
        {
          ...analysis,
          comparison: {
            ...analysis.comparison,
            source: { ...analysis.comparison.source, ...extra },
          },
        },
        {
          ...analysis,
          comparison: {
            ...analysis.comparison,
            candidates: [{ ...analysis.comparison.candidates[0], ...extra }],
          },
        },
        { ...analysis, replay: { ...analysis.replay, ...extra } },
        {
          ...analysis,
          replay: { ...analysis.replay, ledger: [{ ...analysis.replay.ledger[0], ...extra }] },
        },
      ];

      for (const payload of payloads) {
        const text = JSON.stringify(payload);
        expect(JSON.stringify(parseAnalysis(text))).toBe(text);
      }
    },
  );
});
