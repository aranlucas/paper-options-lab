import { useState } from "react";
import type { Candidate } from "./types";
import { num, usd } from "./types";

type PayoffProps = { candidate: Candidate; spot: number };

export default function Payoff({ candidate: c, spot }: PayoffProps) {
  const [value, setValue] = useState(spot);
  const data = c.payoff;
  const first = data?.at(0);
  const last = data?.at(-1);
  const loss = c.expiry_max_loss;

  if (!data || !first || !last || first.spot >= last.spot || loss === undefined) {
    return null;
  }

  const xmin = first.spot;
  const xmax = last.spot;

  const ymin = Math.min(...data.map((p) => p.pnl), 0) - 35;
  const ymax = Math.max(...data.map((p) => p.pnl), 0) + 35;

  const x = (s: number) => 48 + ((s - xmin) / (xmax - xmin)) * 464;
  const y = (p: number) => 24 + ((ymax - p) / (ymax - ymin)) * 186;
  const path = data.map((p, i) => `${i ? "L" : "M"}${x(p.spot)},${y(p.pnl)}`).join(" ");
  const intrinsic = (s: number, k: number) => Math.max(0, c.kind === "call" ? s - k : k - s);

  const pnl =
    (intrinsic(value, c.long_strike) - intrinsic(value, c.short_strike)) *
      c.multiplier *
      c.quantity -
    loss;

  return (
    <div className="payoff">
      <div className="section-title">
        <h3>Expiration payoff</h3>
        <span>After costs · PAPER</span>
      </div>
      <svg
        viewBox="0 0 540 246"
        role="img"
        aria-label={`Expiration payoff of ${c.kind} spread. Maximum loss ${usd(c.expiry_max_loss)}, maximum gain ${usd(c.expiry_max_profit)}, break-even ${num(c.break_even)}`}
      >
        {[0, 1, 2, 3].map((i) => {
          const p = ymin + ((ymax - ymin) * i) / 3;

          return (
            <g key={i}>
              <line x1="48" x2="512" y1={y(p)} y2={y(p)} className="gridline" />
              <text x="40" y={y(p) + 4} textAnchor="end">
                {Math.round(p)}
              </text>
            </g>
          );
        })}
        <line x1="48" x2="512" y1={y(0)} y2={y(0)} className="zero" />
        <path d={`${path} L512,${y(0)} L48,${y(0)} Z`} className="area" />
        <path d={path} className="payline" />
        <line x1={x(value)} x2={x(value)} y1="24" y2="210" className="crosshair" />
        <circle cx={x(value)} cy={y(pnl)} r="5" className="point" />
        {[
          { id: "minimum", value: xmin },
          { id: "long-strike", value: c.long_strike },
          { id: "short-strike", value: c.short_strike },
          { id: "maximum", value: xmax },
        ]
          .toSorted((a, b) => a.value - b.value)
          .map((tick) => (
            <text key={tick.id} x={x(tick.value)} y="231" textAnchor="middle">
              {num(tick.value, 0)}
            </text>
          ))}
      </svg>
      <div className="scenario-readout">
        <span>
          Settlement value <strong>{num(value)}</strong>
        </span>
        <span className={pnl >= 0 ? "positive" : "negative"}>
          {usd(pnl)} <small>scenario P&amp;L</small>
        </span>
      </div>
      <label className="sr-only" htmlFor="settlement-slider">
        Hypothetical settlement value
      </label>
      <input
        id="settlement-slider"
        type="range"
        min={xmin}
        max={xmax}
        step=".1"
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
      />
      <p className="fine">
        The slider changes a hypothetical terminal value, not a forecast or a historical result.
      </p>
    </div>
  );
}
