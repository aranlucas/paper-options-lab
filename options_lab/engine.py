"""Deterministic paper spread screening and event replay; no outbound I/O."""
from dataclasses import asdict, dataclass, fields
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations

from .pricing import analytical, intrinsic
from .schema import InputError, number, timestamp, validate_dataset


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Policy:
    capital: float = 10000
    max_loss_per_position: float = 500
    max_portfolio_risk: float = 1500
    max_positions: int = 3
    max_quantity: int = 2
    max_abs_delta: float = 200
    max_quote_age_seconds: int = 120
    max_quote_skew_seconds: int = 5
    max_liquidity_age_seconds: int = 86400
    min_volume: int = 10
    min_open_interest: int = 100
    max_spread_fraction: float = .25
    max_spread_points: float = .6
    min_dte: float = 7
    max_dte: float = 60
    fee_per_contract: float = .65
    settlement_fee_per_contract: float = .05
    slippage_points: float = .02

    def __post_init__(self):
        integer_fields = {field.name for field in fields(self) if field.type is int}
        for field in fields(self):
            number(getattr(self, field.name), field.name, 0, 1e7, integer=field.name in integer_fields)
        if self.capital <= 0 or self.max_quantity < 1 or self.max_positions < 1:
            raise InputError("capital, max_quantity and max_positions must be positive")
        if self.min_dte >= self.max_dte or self.max_spread_fraction > 1:
            raise InputError("invalid DTE or spread policy")


def policy_from_dict(values=None):
    values = {} if values is None else values
    if not isinstance(values, dict) or values.keys() - asdict(Policy()).keys():
        raise InputError("unknown policy field")
    return Policy(**values)


def snapshot_reasons(snapshot, at):
    result = []
    as_of = timestamp(snapshot["as_of"])
    available = timestamp(snapshot["available_at"])
    spot_at = timestamp(snapshot["spot_at"])
    if as_of > at or available > at or spot_at > as_of or available < as_of:
        result.append("LOOKAHEAD_OR_INVALID_AVAILABILITY")
    return result


def quote_reasons(quote, snapshot, at, policy, quantity, entry=True):
    reasons = []
    as_of = timestamp(snapshot["as_of"])
    quote_at = timestamp(quote["quote_at"])
    liq_at = timestamp(quote["liquidity_at"])
    expiry = timestamp(quote["expires_at"])
    last_trade = timestamp(quote["last_trade_at"])
    if quote["exercise"] != "european":
        reasons.append("EARLY_ASSIGNMENT_UNSUPPORTED")
    if quote["settlement"] != "cash":
        reasons.append("PHYSICAL_DELIVERY_UNSUPPORTED")
    if quote["adjusted"]:
        reasons.append("ADJUSTED_DELIVERABLE_UNSUPPORTED")
    if quote_at > as_of or liq_at > as_of:
        reasons.append("FUTURE_QUOTE_OR_LIQUIDITY")
    if (at - quote_at).total_seconds() > policy.max_quote_age_seconds:
        reasons.append("STALE_QUOTE")
    if (at - timestamp(snapshot["spot_at"])).total_seconds() > policy.max_quote_age_seconds:
        reasons.append("STALE_UNDERLYING")
    if (at - liq_at).total_seconds() > policy.max_liquidity_age_seconds:
        reasons.append("STALE_LIQUIDITY")
    if last_trade > expiry:
        reasons.append("INVALID_TRADING_CUTOFF")
    if at >= last_trade or at >= expiry:
        reasons.append("CONTRACT_NOT_TRADABLE")
    dte = (expiry - at).total_seconds() / 86400
    if entry and not policy.min_dte <= dte <= policy.max_dte:
        reasons.append("DTE_OUTSIDE_WINDOW")
    bid, ask = quote["bid"], quote["ask"]
    if bid is None or ask is None:
        reasons.append("MISSING_QUOTE")
    elif bid <= 0 or ask < bid:
        reasons.append("ZERO_OR_CROSSED_MARKET")
    elif ask - bid > policy.max_spread_points or (ask - bid) / ((ask + bid) / 2) > policy.max_spread_fraction:
        reasons.append("WIDE_SPREAD")
    if quote["volume"] is None or quote["open_interest"] is None:
        reasons.append("MISSING_LIQUIDITY")
    elif quote["volume"] < policy.min_volume or quote["open_interest"] < policy.min_open_interest:
        reasons.append("LOW_LIQUIDITY")
    if quote["bid_size"] is None or quote["ask_size"] is None or min(quote["bid_size"] or 0, quote["ask_size"] or 0) < quantity:
        reasons.append("INSUFFICIENT_DISPLAYED_SIZE")
    if quote["iv"] is None:
        reasons.append("MISSING_IV")
    return reasons


def evaluate_pair(long, short, snapshot, at, policy, quantity=1):
    reasons = snapshot_reasons(snapshot, at)
    reasons += [f"LONG:{r}" for r in quote_reasons(long, snapshot, at, policy, quantity)]
    reasons += [f"SHORT:{r}" for r in quote_reasons(short, snapshot, at, policy, quantity)]
    for field in ("kind", "expires_at", "multiplier", "exercise", "settlement", "last_trade_at"):
        if long[field] != short[field]:
            reasons.append(f"MISMATCH_{field.upper()}")
    if long["id"] == short["id"] or (long["kind"] == "call" and long["strike"] >= short["strike"]) or (long["kind"] == "put" and long["strike"] <= short["strike"]):
        reasons.append("NOT_A_DEBIT_VERTICAL")
    if abs((timestamp(long["quote_at"]) - timestamp(short["quote_at"])).total_seconds()) > policy.max_quote_skew_seconds:
        reasons.append("ASYNCHRONOUS_LEGS")
    if type(quantity) is not int or quantity < 1 or quantity > policy.max_quantity:
        reasons.append("QUANTITY_LIMIT")
    result = {
        "id": f"{long['id']}|{short['id']}", "long_id": long["id"], "short_id": short["id"],
        "kind": long["kind"], "long_strike": long["strike"], "short_strike": short["strike"],
        "expires_at": long["expires_at"], "quantity": quantity, "multiplier": long["multiplier"],
        "underlying": snapshot["underlying"], "exercise": long["exercise"], "settlement": long["settlement"], "reasons": reasons, "paper_only": True,
    }
    if reasons:
        result["eligible"] = False
        return result
    scale = long["multiplier"] * quantity
    long_fill = long["ask"] + policy.slippage_points
    short_fill = short["bid"] - policy.slippage_points
    debit_points = long_fill - short_fill
    width = abs(long["strike"] - short["strike"])
    if short_fill < 0 or not 0 < debit_points < width:
        reasons.append("INVALID_PACKAGE_PRICE")
        result["eligible"] = False
        return result
    debit = money(debit_points * scale)
    entry_fees = money(2 * quantity * policy.fee_per_contract)
    reserve_fees = money(2 * quantity * max(policy.fee_per_contract, policy.settlement_fee_per_contract))
    max_loss = money(debit + entry_fees + reserve_fees)
    years = (timestamp(long["expires_at"]) - at).total_seconds() / (365 * 86400)
    models = [analytical(q["kind"], snapshot["spot"], q["strike"], years, q["iv"], snapshot["rate"], snapshot["dividend_yield"]) for q in (long, short)]
    greeks = {key: round((models[0][key] - models[1][key]) * scale, 6) for key in ("delta", "gamma", "theta", "vega")}
    if max_loss > policy.max_loss_per_position:
        reasons.append("POSITION_RISK_LIMIT")
    if abs(greeks["delta"]) > policy.max_abs_delta:
        reasons.append("DELTA_LIMIT")
    if max_loss > policy.capital:
        reasons.append("CAPITAL_LIMIT")
    settlement_fees = money(2 * quantity * policy.settlement_fee_per_contract)
    total_expiry_cost = money(debit + entry_fees + settlement_fees)
    break_even = long["strike"] + (1 if long["kind"] == "call" else -1) * total_expiry_cost / scale
    result.update({
        "eligible": not reasons, "debit": debit, "entry_fees": entry_fees,
        "reserved_exit_fees": reserve_fees, "settlement_fees": settlement_fees,
        "max_loss": max_loss, "expiry_max_loss": total_expiry_cost,
        "expiry_max_profit": money(width * scale - total_expiry_cost),
        "break_even": round(break_even, 4), "greeks": greeks,
        "long_fill": long_fill, "short_fill": short_fill,
        "dte": round(years * 365, 2),
        "spread_drag": money(((long["ask"] - long["bid"]) + (short["ask"] - short["bid"])) / 2 * scale),
        "slippage_cost": money(2 * policy.slippage_points * scale),
    })
    lower = min(snapshot["spot"] * .88, long["strike"] - width * 2, short["strike"] - width * 2)
    upper = max(snapshot["spot"] * 1.12, long["strike"] + width * 2, short["strike"] + width * 2)
    grid = sorted(set([max(.001, lower + (upper - lower) * i / 60) for i in range(61)] + [long["strike"], short["strike"], break_even]))
    result["payoff"] = [{"spot": round(spot, 4), "pnl": money((intrinsic(long["kind"], spot, long["strike"]) - intrinsic(short["kind"], spot, short["strike"])) * scale - total_expiry_cost)} for spot in grid]
    return result


def latest_snapshot(data, at):
    visible = [snap for snap in data["snapshots"] if timestamp(snap["available_at"]) <= at and timestamp(snap["as_of"]) <= at]
    return max(visible, key=lambda snap: (timestamp(snap["as_of"]), timestamp(snap["available_at"]), snap["id"])) if visible else None


def compare(data, at, policy=Policy(), quantity=1, snapshot_id=None):
    validate_dataset(data)
    at = timestamp(at) if isinstance(at, str) else at
    if type(quantity) is not int or not 1 <= quantity <= 100:
        raise InputError("quantity must be integer in [1, 100]")
    snapshot = next((snap for snap in data["snapshots"] if snap["id"] == snapshot_id), None) if snapshot_id else latest_snapshot(data, at)
    result = {"paper_only": True, "source": data["source"], "as_of": at.isoformat(), "policy": asdict(policy), "candidates": [], "snapshot_id": snapshot["id"] if snapshot else None}
    if data["source"]["feed"] in ("indicative", "unknown"):
        result["error"] = "NON_EXECUTABLE_OR_UNKNOWN_FEED"
        return result
    if snapshot is None:
        result["error"] = "NO_AVAILABLE_CHAIN"
        return result
    result["spot"] = snapshot["spot"]
    if snapshot_reasons(snapshot, at):
        result["error"] = snapshot_reasons(snapshot, at)[0]
        return result
    for a, b in combinations(sorted(snapshot["contracts"], key=lambda q: q["id"]), 2):
        if a["kind"] != b["kind"] or a["expires_at"] != b["expires_at"] or a["strike"] == b["strike"]:
            continue
        long, short = sorted((a, b), key=lambda q: q["strike"], reverse=a["kind"] == "put")
        result["candidates"].append(evaluate_pair(long, short, snapshot, at, policy, quantity))
    result["candidates"].sort(key=lambda c: (not c["eligible"], c.get("max_loss", float("inf")), c["id"]))
    result["eligible_count"] = sum(c["eligible"] for c in result["candidates"])
    result["rejected_count"] = len(result["candidates"]) - result["eligible_count"]
    return result


def replay(data, policy=Policy(), through=None):
    validate_dataset(data)
    cutoff = timestamp(through) if through is not None else None
    events = [event for event in data["events"] if cutoff is None or timestamp(event["at"]) <= cutoff]
    # An explicit observation evaluates settlement availability at the cutoff,
    # even when no preplanned dataset event occurs at that exact instant.
    if cutoff is not None and (not events or timestamp(events[-1]["at"]) < cutoff):
        events = [*events, {"at": cutoff.isoformat(), "action": "observe"}]
    cash = money(policy.capital)
    positions = {}
    ledger = []
    counter = 0
    realized = 0.0

    def record(event, action, **values):
        ledger.append({"at": event["at"], "action": action, "cash": cash, "reserved_risk": money(sum(p["max_loss"] for p in positions.values())), "paper_only": True, **values})

    for event in events:
        at = timestamp(event["at"])
        for position_id, position in list(positions.items()):
            expiry = timestamp(position["expires_at"])
            if at < expiry:
                continue
            settlement = next((s for s in data["settlements"] if s["underlying"] == position["underlying"] and timestamp(s["expires_at"]) == expiry and timestamp(s["available_at"]) <= at), None)
            if settlement is None:
                continue  # Exposure remains reserved; no fabricated settlement or P&L.
            gross = money((intrinsic(position["kind"], settlement["value"], position["long_strike"]) - intrinsic(position["kind"], settlement["value"], position["short_strike"])) * position["multiplier"] * position["quantity"])
            credit = money(gross - position["settlement_fees"])
            pnl = money(credit - position["debit"] - position["entry_fees"])
            cash = money(cash + credit)
            realized = money(realized + pnl)
            del positions[position_id]
            record(event, "PAPER_SETTLED", position_id=position_id, credit=credit, pnl=pnl, settlement_value=settlement["value"])
        if event["action"] == "observe":
            record(event, "PAPER_OBSERVED")
            continue
        snapshot = latest_snapshot(data, at)
        if event["action"] == "open":
            reasons = []
            candidate = None
            if data["source"]["feed"] in ("indicative", "unknown"):
                reasons.append("NON_EXECUTABLE_OR_UNKNOWN_FEED")
            elif snapshot is None:
                reasons.append("NO_AVAILABLE_CHAIN")
            else:
                quotes = {q["id"]: q for q in snapshot["contracts"]}
                if event["long_id"] not in quotes or event["short_id"] not in quotes:
                    reasons.append("MISSING_CONTRACT")
                else:
                    candidate = evaluate_pair(quotes[event["long_id"]], quotes[event["short_id"]], snapshot, at, policy, event["quantity"])
                    reasons += candidate["reasons"]
            if candidate and candidate.get("max_loss") is not None:
                if len(positions) >= policy.max_positions:
                    reasons.append("POSITION_COUNT_LIMIT")
                if money(sum(p["max_loss"] for p in positions.values()) + candidate["max_loss"]) > policy.max_portfolio_risk:
                    reasons.append("PORTFOLIO_RISK_LIMIT")
                # Conservative gross delta budget, refreshed from current visible data.
                gross_delta = abs(candidate["greeks"]["delta"])
                for p in positions.values():
                    ql = quotes.get(p["long_id"])
                    qs = quotes.get(p["short_id"])
                    if not ql or not qs or snapshot_reasons(snapshot, at) or quote_reasons(ql, snapshot, at, policy, p["quantity"], False) or quote_reasons(qs, snapshot, at, policy, p["quantity"], False):
                        reasons.append("PORTFOLIO_MARK_UNAVAILABLE")
                        break
                    years = (timestamp(p["expires_at"]) - at).total_seconds() / (365 * 86400)
                    dl = analytical(p["kind"], snapshot["spot"], ql["strike"], years, ql["iv"], snapshot["rate"], snapshot["dividend_yield"])["delta"]
                    ds = analytical(p["kind"], snapshot["spot"], qs["strike"], years, qs["iv"], snapshot["rate"], snapshot["dividend_yield"])["delta"]
                    gross_delta += abs((dl - ds) * p["multiplier"] * p["quantity"])
                if gross_delta > policy.max_abs_delta:
                    reasons.append("PORTFOLIO_DELTA_LIMIT")
                future_fees = sum(p["reserved_exit_fees"] for p in positions.values())
                if money(candidate["max_loss"] + future_fees) > cash:
                    reasons.append("INSUFFICIENT_PAPER_CASH")
            if reasons:
                record(event, "PAPER_REJECTED", reasons=sorted(set(reasons)))
                continue
            counter += 1
            position_id = f"paper-{counter:03}"
            cash = money(cash - candidate["debit"] - candidate["entry_fees"])
            positions[position_id] = {**candidate, "position_id": position_id, "opened_at": event["at"]}
            record(event, "PAPER_OPENED", position_id=position_id, spread=candidate["id"], debit=candidate["debit"], fees=candidate["entry_fees"])
        elif event["action"] == "close":
            position = positions.get(event["position_id"])
            reasons = []
            if position is None:
                reasons.append("POSITION_NOT_OPEN")
            elif at >= timestamp(position["expires_at"]):
                reasons.append("SETTLEMENT_PENDING")
            elif snapshot is None:
                reasons.append("NO_AVAILABLE_CHAIN")
            else:
                reasons += snapshot_reasons(snapshot, at)
                quotes = {q["id"]: q for q in snapshot["contracts"]}
                legs = [quotes.get(position[field]) for field in ("long_id", "short_id")]
                if any(q is None for q in legs):
                    reasons.append("MISSING_CONTRACT")
                else:
                    for q in legs:
                        reasons += quote_reasons(q, snapshot, at, policy, position["quantity"], False)
                    if abs((timestamp(legs[0]["quote_at"]) - timestamp(legs[1]["quote_at"])).total_seconds()) > policy.max_quote_skew_seconds:
                        reasons.append("ASYNCHRONOUS_LEGS")
                    if not reasons:
                        exit_points = legs[0]["bid"] - legs[1]["ask"] - 2 * policy.slippage_points
                        width = abs(position["long_strike"] - position["short_strike"])
                        if not 0 <= exit_points <= width:
                            reasons.append("NO_NONNEGATIVE_PACKAGE_EXIT")
            if reasons:
                record(event, "PAPER_REJECTED", position_id=event["position_id"], reasons=sorted(set(reasons)))
                continue
            fee = money(2 * position["quantity"] * policy.fee_per_contract)
            credit = money(exit_points * position["multiplier"] * position["quantity"] - fee)
            pnl = money(credit - position["debit"] - position["entry_fees"])
            cash = money(cash + credit)
            realized = money(realized + pnl)
            del positions[event["position_id"]]
            record(event, "PAPER_CLOSED", position_id=event["position_id"], credit=credit, fees=fee, pnl=pnl)
    return {
        "paper_only": True, "source": data["source"], "policy": asdict(policy),
        "through": cutoff.isoformat() if cutoff is not None else None,
        "label": "Synthetic scenario replay — not historical performance" if data["source"]["kind"] == "synthetic" else "User-supplied chain replay — provenance and licensing unverified",
        "cash": cash, "realized_pnl": realized, "reserved_risk": money(sum(p["max_loss"] for p in positions.values())),
        "open_positions": list(positions.values()), "ledger": ledger,
        "complete": not positions, "equity": cash if not positions else None,
    }
