import { FormEvent, useEffect, useRef, useState } from "react";
import Inspector from "./Inspector";
import SpreadTable from "./SpreadTable";
import Ledger from "./Ledger";
import { Analysis, Dataset, num, reason } from "./types";

const labels = {
  rally: "Rally +8%",
  flat: "Flat at expiration",
  selloff: "Gap down −12%",
  "vol-crush": "Volatility crush + early close",
  stale: "Stale chain",
  missing: "Missing bids",
  pending: "Missing settlement value",
};

type Controls = {
  quantity: number;
  max_loss_per_position: number;
  max_portfolio_risk: number;
  max_positions: number;
  fee_per_contract: number;
  slippage_points: number;
};

const defaults: Controls = {
  quantity: 1,
  max_loss_per_position: 500,
  max_portfolio_risk: 1500,
  max_positions: 3,
  fee_per_contract: 0.65,
  slippage_points: 0.02,
};

function download(name: string, data: Dataset | Analysis | undefined) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [scenario, setScenario] = useState("rally");
  const [dataset, setDataset] = useState<Dataset>();
  const [at, setAt] = useState("");
  const [controls, setControls] = useState(defaults);
  const [analysis, setAnalysis] = useState<Analysis>();
  const [selected, setSelected] = useState("");
  const [kind, setKind] = useState("all");
  const [showRejected, setShowRejected] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const file = useRef<HTMLInputElement>(null);
  const generation = useRef(0);
  const request = useRef<AbortController | null>(null);

  async function analyze(data: Dataset, time: string, values: Controls) {
    request.current?.abort();
    const abort = new AbortController();
    request.current = abort;
    const token = ++generation.current;
    setLoading(true);
    setError("");
    setAnalysis(undefined);
    const { quantity, ...policy } = values;

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset: data, at: time, quantity, policy }),
        signal: abort.signal,
      });

      const body = await response.json();

      if (!response.ok) throw new Error(body.error ?? "Analysis failed");

      if (token !== generation.current) return;
      setAnalysis(body);
      setSelected(
        body.comparison.candidates.find((c: { eligible: boolean }) => c.eligible)?.id ??
          body.comparison.candidates[0]?.id ??
          "",
      );
    } catch (e) {
      if (!abort.signal.aborted && token === generation.current)
        setError(e instanceof Error ? e.message : "Unable to analyze data");
    } finally {
      if (token === generation.current) setLoading(false);
    }
  }

  useEffect(() => {
    if (scenario === "imported") return;
    const abort = new AbortController();
    setLoading(true);
    setError("");
    setAnalysis(undefined);
    setDataset(undefined);
    request.current?.abort();
    generation.current++;
    fetch(`/api/fixture/${scenario}`, { signal: abort.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unable to load scenario");
        const data: Dataset = await response.json();

        if (abort.signal.aborted) return;
        setDataset(data);
        setAt(data.snapshots[0].as_of);
        void analyze(data, data.snapshots[0].as_of, controls);
      })
      .catch((e) => {
        if (!abort.signal.aborted) {
          setError(e.message);
          setLoading(false);
        }
      });

    return () => abort.abort();
    // Scenario changes preserve user cost/risk controls; submit to recompute edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario]);

  const comparison = analysis?.comparison;
  const candidates = comparison?.candidates ?? [];

  const visible = candidates.filter(
    (c) => (kind === "all" || c.kind === kind) && (showRejected || c.eligible),
  );

  const chosen = visible.find((c) => c.id === selected) ?? visible[0];

  const invalidate = () => {
    request.current?.abort();
    generation.current++;
    setLoading(false);
    setAnalysis(undefined);
    setError("Inputs changed. Compare again to apply the new limits.");
  };

  const change = (key: keyof Controls, value: string) => {
    invalidate();
    setControls((previous) => ({ ...previous, [key]: Number(value) }));
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();

    if (dataset) void analyze(dataset, at, controls);
  };

  async function importFile(input: File) {
    request.current?.abort();
    generation.current++;
    setAnalysis(undefined);
    setLoading(false);

    try {
      if (input.size > 2 * 1024 * 1024) throw new Error("JSON file exceeds the 2 MiB limit.");
      const data = JSON.parse(await input.text());

      if (!data?.source || !Array.isArray(data?.snapshots) || !data.snapshots[0]?.as_of)
        throw new Error("Expected the documented option-chain schema.");
      setScenario("imported");
      setDataset(data);
      setAt(data.snapshots[0].as_of);
      void analyze(data, data.snapshots[0].as_of, controls);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON import");
      setDataset(undefined);
    }
  }

  return (
    <>
      <a className="skip-link" href="#research-workspace">
        Skip to research inputs
      </a>
      <header className="header">
        <a className="brand" href="/" aria-label="Paper Options Lab home">
          <svg width="29" height="29" viewBox="0 0 29 29" aria-hidden="true">
            <path
              d="M3 22V9h8v10h7V5h8"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinejoin="round"
            />
          </svg>
          <span>Paper Options Lab</span>
        </a>
        <div className="header-actions">
          <span className="paper-status">
            <i />
            Paper only · execution absent
          </span>
          <button className="import" onClick={() => file.current?.click()}>
            Import chain JSON
          </button>
          <input
            ref={file}
            className="sr-only"
            type="file"
            accept=".json,application/json"
            aria-label="Import option-chain dataset"
            onChange={(e) => {
              const f = e.target.files?.[0];

              if (f) void importFile(f);
              e.target.value = "";
            }}
          />
        </div>
      </header>
      <main id="research-workspace" tabIndex={-1}>
        <div className="title-row">
          <div>
            <h1>Compare defined-risk spreads.</h1>
            <p>
              Understand the risk before the outcome. Synthetic scenarios, not historical returns.
            </p>
          </div>
          <a className="text-link" href="#research">
            Research &amp; limits <span aria-hidden="true">↗</span>
          </a>
        </div>
        <section className="workspace-controls" aria-label="Research inputs">
          <label>
            Dataset
            <select
              aria-label="Dataset"
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {Object.entries(labels).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
              {scenario === "imported" && (
                <option value="imported">Imported · {dataset?.source.name}</option>
              )}
            </select>
          </label>
          <div className="dataset-meta">
            <strong>
              {dataset?.source.kind === "synthetic"
                ? "Synthetic · DEMO-INDEX"
                : "Imported · unverified"}
            </strong>
            <span>
              European cash-settled debit verticals ·{" "}
              {comparison?.spot ? num(comparison.spot) : "—"} spot
            </span>
          </div>
          <button
            className="secondary"
            disabled={!dataset}
            onClick={() => download(`paper-options-${scenario}.json`, dataset)}
          >
            Export dataset
          </button>
        </section>
        <form onSubmit={submit} className="risk-controls">
          <div className="section-title">
            <h2>Risk budget</h2>
            <span>Local screening rules</span>
          </div>
          <div className="control-grid">
            <label>
              Max loss / position ($)
              <input
                required
                type="number"
                min="1"
                max="100000"
                value={controls.max_loss_per_position}
                onChange={(e) => change("max_loss_per_position", e.target.value)}
              />
            </label>
            <label>
              Portfolio risk cap ($)
              <input
                required
                type="number"
                min="1"
                max="100000"
                value={controls.max_portfolio_risk}
                onChange={(e) => change("max_portfolio_risk", e.target.value)}
              />
            </label>
            <label>
              Position limit
              <input
                required
                type="number"
                min="1"
                max="20"
                step="1"
                value={controls.max_positions}
                onChange={(e) => change("max_positions", e.target.value)}
              />
            </label>
            <label>
              Screen quantity
              <input
                required
                type="number"
                min="1"
                max="100"
                step="1"
                value={controls.quantity}
                onChange={(e) => change("quantity", e.target.value)}
              />
            </label>
            <label>
              Fee / contract ($)
              <input
                required
                type="number"
                min="0"
                max="100"
                step=".01"
                value={controls.fee_per_contract}
                onChange={(e) => change("fee_per_contract", e.target.value)}
              />
            </label>
            <label>
              Slippage / leg (points)
              <input
                required
                type="number"
                min="0"
                max="10"
                step=".01"
                value={controls.slippage_points}
                onChange={(e) => change("slippage_points", e.target.value)}
              />
            </label>
          </div>
          <div className="decision-row">
            <label>
              Decision time (ISO-8601, UTC)
              <input
                required
                aria-label="Decision time"
                value={at}
                onChange={(e) => {
                  invalidate();
                  setAt(e.target.value);
                }}
              />
            </label>
            <button className="primary" type="submit" disabled={loading || !dataset}>
              {loading ? "Computing locally…" : "Compare & replay"}
            </button>
          </div>
        </form>
        {error && (
          <div className="error" role="alert">
            {error.startsWith("Inputs changed")
              ? error
              : `Input rejected: ${error}. Correct the input or load another scenario.`}
          </div>
        )}
        {comparison?.error && (
          <div className="error" role="alert">
            Comparison rejected: {reason(comparison.error)}. No eligible result is available.
          </div>
        )}
        <section className="comparison-section">
          <div className="comparison-main">
            <div className="section-title">
              <div>
                <h2>Spread comparison</h2>
                <p className="muted">
                  Sorted by reserved maximum loss. No expected-return ranking.
                </p>
              </div>
              <div className="counts">
                <span>{comparison?.eligible_count ?? 0} eligible</span>
                <span>{comparison?.rejected_count ?? 0} rejected</span>
              </div>
            </div>
            <div className="filters">
              <div className="segmented" aria-label="Option type">
                {["all", "call", "put"].map((k) => (
                  <button
                    key={k}
                    onClick={() => setKind(k)}
                    aria-pressed={kind === k}
                    className={kind === k ? "active" : ""}
                  >
                    {k === "all" ? "All spreads" : `${k === "call" ? "Call" : "Put"} spreads`}
                  </button>
                ))}
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  checked={showRejected}
                  onChange={(e) => setShowRejected(e.target.checked)}
                />
                Show rejected
              </label>
            </div>
            {loading ? (
              <div className="loading" role="status">
                Validating quotes and calculating bounded risks…
              </div>
            ) : (
              <SpreadTable
                candidates={visible}
                selected={chosen?.id ?? ""}
                onSelect={setSelected}
              />
            )}
            <p className="fine table-foot">
              Buy at ask + slippage; sell at bid − slippage. Limits: 7–60 DTE, 120s quotes, ≥100 OI,
              ≥10 volume, ≤25% bid/ask spread. Maximum 2 spreads per position.
            </p>
          </div>
          <Inspector candidate={loading ? undefined : chosen} spot={comparison?.spot ?? 100} />
        </section>
        {analysis && <Ledger replay={analysis.replay} />}
        {analysis && (
          <details className="rejection-log">
            <summary>Rejection log · {comparison?.rejected_count ?? 0} screened spreads</summary>
            <ul>
              {candidates
                .filter((c) => !c.eligible)
                .map((c) => (
                  <li key={c.id}>
                    <strong>
                      {c.kind} {c.long_strike}/{c.short_strike}
                    </strong>{" "}
                    — {c.reasons.map(reason).join("; ")}
                  </li>
                ))}
            </ul>
            <button
              className="secondary"
              onClick={() => download("paper-options-report.json", analysis)}
            >
              Export report
            </button>
          </details>
        )}
        <section className="research" id="research">
          <div>
            <h2>A research tool with a hard boundary.</h2>
            <p>
              The only positions here are entries in a local paper ledger. This app has no broker
              client, keys, trading adapter, order-routing code, or external inference.
            </p>
            <a className="text-link" href="/research.md" target="_blank" rel="noreferrer">
              Read the research brief ↗
            </a>
          </div>
          <div>
            <h3>What the model cannot tell you</h3>
            <p>
              Displayed quotes do not guarantee simultaneous fills. Black–Scholes–Merton Greeks
              assume European exercise, continuous yield and constant volatility. Volatility smiles,
              queues, market impact, margin, taxes, and early assignment are outside the model.
            </p>
            <p>
              American-style and physical delivery contracts are rejected. Settlement requires an
              explicit official cash value, never an underlying closing bar. Missing settlement
              keeps risk reserved.
            </p>
            <p>
              Imported quotes, IVs, contract metadata, entitlements and licensing must be verified
              independently. Synthetic P&amp;L illustrates mechanics; it is not evidence of a
              profitable strategy.
            </p>
          </div>
        </section>
        <footer>
          <span>Deterministic rules. Explicit assumptions. Paper only.</span>
          <span>QuantLib pricing · Local computation</span>
        </footer>
      </main>
    </>
  );
}
