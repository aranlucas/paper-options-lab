import { Candidate, num, reason, usd } from "./types";

export default function SpreadTable({
  candidates,
  selected,
  onSelect,
}: {
  candidates: Candidate[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="table-scroll" role="region" aria-label="Spread comparison table" tabIndex={0}>
      <table className="spread-table">
        <thead>
          <tr>
            <th>Spread</th>
            <th>Max risk</th>
            <th>Debit</th>
            <th>Δ units</th>
            <th>Screen</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.id} className={c.id === selected ? "selected" : ""}>
              <td>
                <button
                  className="row-select"
                  onClick={() => onSelect(c.id)}
                  aria-pressed={c.id === selected}
                >
                  <strong>
                    {c.kind === "call" ? "Call" : "Put"} {num(c.long_strike, 0)} /{" "}
                    {num(c.short_strike, 0)}
                  </strong>
                  <span>
                    {c.quantity} spread · ×{c.multiplier} ·{" "}
                    {new Date(c.expires_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      timeZone: "UTC",
                    })}
                  </span>
                </button>
              </td>
              <td className="mono">{usd(c.max_loss)}</td>
              <td className="mono">{usd(c.debit)}</td>
              <td className="mono">{num(c.greeks?.delta, 1)}</td>
              <td>
                {c.eligible ? (
                  <span className="status eligible">Eligible</span>
                ) : (
                  <span className="status rejected" title={c.reasons.map(reason).join("; ")}>
                    Rejected · {c.reasons.length}
                  </span>
                )}
              </td>
            </tr>
          ))}
          {!candidates.length && (
            <tr>
              <td colSpan={5} className="empty">
                No spreads match this view. Change the filter or inspect the data error.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
