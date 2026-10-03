import { Analysis, reason, usd } from "./types";

export default function Ledger({ replay: r }: { replay: Analysis["replay"] }) {
  return (
    <section className="ledger-section">
      <div className="section-title">
        <div>
          <h2>Local paper ledger</h2>
          <p className="muted">
            Replays the dataset’s predefined events. Screen quantity does not alter those events.
          </p>
        </div>
        <span>{r.complete ? "Settled / closed" : "Settlement or close pending"}</span>
      </div>
      <div className="ledger-stats">
        <div>
          <span>Paper cash</span>
          <strong>{usd(r.cash)}</strong>
        </div>
        <div>
          <span>Realized scenario P&amp;L</span>
          <strong className={r.realized_pnl >= 0 ? "positive" : "negative"}>
            {usd(r.realized_pnl)}
          </strong>
        </div>
        <div>
          <span>Reserved risk</span>
          <strong>{usd(r.reserved_risk)}</strong>
        </div>
        <div>
          <span>Open paper positions</span>
          <strong>{r.open_positions.length}</strong>
        </div>
      </div>
      <p className="provenance">
        {r.label}
        {!r.complete ? " · Equity is unreported while positions remain open." : ""}
      </p>
      <div
        className="table-scroll"
        role="region"
        aria-label="Local paper ledger table"
        tabIndex={0}
      >
        <table className="ledger">
          <thead>
            <tr>
              <th>Event time (UTC)</th>
              <th>Paper event</th>
              <th>Cash flow / reason</th>
              <th>Cash</th>
              <th>Risk reserved</th>
            </tr>
          </thead>
          <tbody>
            {r.ledger.map((row, i) => (
              <tr key={i}>
                <td className="mono">
                  {row.at.replace("T", " ").replace("Z", "").replace("+00:00", "")}
                </td>
                <td>
                  <strong>{row.action.replace("PAPER_", "").toLowerCase()}</strong>{" "}
                  <span className="muted">{row.position_id}</span>
                </td>
                <td>
                  {row.reasons ? (
                    <span className="negative">{row.reasons.map(reason).join("; ")}</span>
                  ) : row.debit != null ? (
                    <>−{usd(row.debit + (row.fees ?? 0))}</>
                  ) : row.credit != null ? (
                    <>
                      {usd(row.credit)} <span className="muted">({usd(row.pnl)} P&amp;L)</span>
                    </>
                  ) : (
                    "Observation only"
                  )}
                </td>
                <td className="mono">{usd(row.cash)}</td>
                <td className="mono">{usd(row.reserved_risk)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
