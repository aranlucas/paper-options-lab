"""Hand-defined synthetic scenarios priced with QuantLib, never market history."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from .pricing import analytical

START = datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)
EXPIRY = START + timedelta(days=30, hours=6)


def iso(at):
    return at.isoformat().replace("+00:00", "Z")


def chain(at, spot, iv, name):
    contracts = []
    for kind in ("call", "put"):
        for strike in (90, 95, 100, 105, 110):
            price = analytical(kind, spot, strike, (EXPIRY - at).total_seconds() / (365 * 86400), iv, .04, .01)["price"]
            half = .05
            contracts.append({
                "id": f"DEMO-{kind}-{strike}", "kind": kind, "strike": strike,
                "expires_at": iso(EXPIRY), "last_trade_at": iso(EXPIRY),
                "exercise": "european", "settlement": "cash", "multiplier": 100,
                "adjusted": False, "bid": round(max(.01, price - half), 4),
                "ask": round(max(.02, price + half), 4), "bid_size": 12, "ask_size": 12,
                "volume": 120, "open_interest": 500, "liquidity_at": iso(at), "quote_at": iso(at), "iv": iv,
            })
    # Deliberately bad rows make fail-closed behavior inspectable.
    bad = deepcopy(next(q for q in contracts if q["id"] == "DEMO-call-110"))
    bad.update(id="DEMO-stale-call-115", strike=115, quote_at=iso(at - timedelta(minutes=10)))
    contracts.append(bad)
    bad = deepcopy(next(q for q in contracts if q["id"] == "DEMO-put-90"))
    bad.update(id="DEMO-missing-put-85", strike=85, bid=None)
    contracts.append(bad)
    bad = deepcopy(next(q for q in contracts if q["id"] == "DEMO-call-100"))
    bad.update(id="DEMO-american-call-120", strike=120, exercise="american", settlement="physical")
    contracts.append(bad)
    return {
        "id": name, "underlying": "DEMO-INDEX", "as_of": iso(at), "available_at": iso(at),
        "spot": spot, "spot_at": iso(at), "rate": .04, "dividend_yield": .01, "contracts": contracts,
    }


SCENARIOS = {
    "flat": ("Flat at expiration", 100, .25, "settle"),
    "rally": ("Rally +8%", 108, .28, "settle"),
    "selloff": ("Gap down −12%", 88, .45, "settle"),
    "vol-crush": ("Volatility crush + early close", 102, .12, "close"),
    "stale": ("Stale chain", 100, .25, "stale"),
    "missing": ("Missing bids", 100, .25, "missing"),
    "pending": ("Missing settlement value", 104, .25, "pending"),
}


def fixture(name="rally"):
    if name not in SCENARIOS:
        raise ValueError("unknown scenario")
    label, terminal, final_iv, mode = SCENARIOS[name]
    first = chain(START, 100, .25, "entry")
    middle = chain(START + timedelta(days=15), 104 if mode == "close" else (100 + terminal) / 2, final_iv, "day-15")
    if mode == "stale":
        for q in first["contracts"]:
            q["quote_at"] = iso(START - timedelta(minutes=10))
    if mode == "missing":
        for q in first["contracts"]:
            q["bid"] = None
    events = [
        {"at": iso(START + timedelta(seconds=1)), "action": "open", "long_id": "DEMO-call-100", "short_id": "DEMO-call-105", "quantity": 1},
        {"at": iso(START + timedelta(seconds=2)), "action": "open", "long_id": "DEMO-put-100", "short_id": "DEMO-put-95", "quantity": 1},
        {"at": iso(START + timedelta(seconds=3)), "action": "open", "long_id": "DEMO-call-95", "short_id": "DEMO-call-100", "quantity": 1},
        {"at": iso(START + timedelta(seconds=4)), "action": "open", "long_id": "DEMO-call-100", "short_id": "DEMO-call-105", "quantity": 1},
    ]
    if mode == "close":
        events.append({"at": iso(START + timedelta(days=15, seconds=1)), "action": "close", "position_id": "paper-001"})
    events.append({"at": iso(EXPIRY + timedelta(minutes=1)), "action": "observe"})
    return {
        "schema_version": 1,
        "source": {"kind": "synthetic", "name": label, "feed": "synthetic", "usage_rights": "Generated deterministic demonstration; no market data"},
        "snapshots": [first, middle],
        "settlements": [] if mode == "pending" else [{"underlying": "DEMO-INDEX", "expires_at": iso(EXPIRY), "value": terminal, "available_at": iso(EXPIRY + timedelta(seconds=30)), "method": "official_cash_value"}],
        "events": events,
    }
