import Payoff from './Payoff';
import {Candidate,num,reason,usd} from './types';
export default function Inspector({candidate:c,spot}:{candidate?:Candidate;spot:number}) {
 if(!c) return <aside className="inspector"><h2>Spread detail</h2><p className="muted">Choose a spread to inspect its risk, costs, and rejection reasons.</p></aside>;
 return <aside className="inspector">
   <div className="section-title"><h2>{c.kind==='call'?'Call':'Put'} {num(c.long_strike,0)} / {num(c.short_strike,0)}</h2><span className={`status ${c.eligible?'eligible':'rejected'}`}>{c.eligible?'Eligible · PAPER':'Rejected'}</span></div>
   <p className="muted detail-sub">Buy {num(c.long_strike,0)}, sell {num(c.short_strike,0)} · {c.quantity} × {c.multiplier} · {c.exercise==='european'?'European':'American'} {c.settlement==='cash'?'cash settlement':'physical delivery'}</p>
   {c.reasons.length>0&&<div className="reasons"><h3>Why it was rejected</h3><ul>{c.reasons.map(r=><li key={r}>{reason(r)}</li>)}</ul></div>}
   {c.payoff&&<>
     <div className="risk-pair"><div><span>Reserved maximum loss</span><strong>{usd(c.max_loss)}</strong></div><div><span>Expiration break-even</span><strong>{num(c.break_even)}</strong></div></div>
     <Payoff candidate={c} spot={spot}/>
     <div className="section-title"><h3>Model Greeks</h3><span>QuantLib · at decision time</span></div>
     <dl className="greeks"><div><dt>Delta</dt><dd><span>{num(c.greeks?.delta,2)}</span><small>underlying units</small></dd></div><div><dt>Gamma</dt><dd><span>{num(c.greeks?.gamma,3)}</span><small>Δ units / point</small></dd></div><div><dt>Theta</dt><dd><span>{usd(c.greeks?.theta)}</span><small>per calendar day</small></dd></div><div><dt>Vega</dt><dd><span>{usd(c.greeks?.vega)}</span><small>per 1pp IV</small></dd></div></dl>
     <details><summary>Fill and cost assumptions</summary><dl className="costs"><div><dt>Long: ask + slippage</dt><dd>{num(c.long_fill,4)}</dd></div><div><dt>Short: bid − slippage</dt><dd>{num(c.short_fill,4)}</dd></div><div><dt>Bid/ask drag versus mid</dt><dd>{usd(c.spread_drag)}</dd></div><div><dt>Additional entry slippage</dt><dd>{usd(c.slippage_cost)}</dd></div><div><dt>Entry fees</dt><dd>{usd(c.entry_fees)}</dd></div><div><dt>Exit fee reserve</dt><dd>{usd(c.reserved_exit_fees)}</dd></div><div><dt>Expiration fee</dt><dd>{usd(c.settlement_fees)}</dd></div></dl><p className="fine">Maximum risk reserves the larger of close or settlement fees. Payoff uses settlement fees. Atomic package fills are assumed; they are not guaranteed by displayed quotes.</p></details>
   </>}
 </aside>;
}
