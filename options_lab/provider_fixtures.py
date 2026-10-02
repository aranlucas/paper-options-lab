"""Explicitly fictional MarketData-shaped examples, generated without data access."""
from datetime import datetime, timedelta, timezone

from .marketdata import EASTERN, iso
from .pricing import analytical


def marketdata_fixture(request_kind="historical", at=None):
    if request_kind not in ("historical", "latest_eod"):
        raise ValueError("unknown fixture request kind")
    at = at or datetime(2026, 10, 2, 20, tzinfo=timezone.utc)
    expiry = at + timedelta(days=28)
    packet = {"s": "ok"}
    specs = {}
    for kind, strike in (("call", 100), ("call", 105), ("put", 100), ("put", 95)):
        symbol = f"DEMO{expiry.astimezone(EASTERN):%y%m%d}{'C' if kind == 'call' else 'P'}{strike * 1000:08}"
        model = analytical(kind, 100, strike, 28 / 365, .25, .04, .01)
        # Quantize fictional export fields for exact Mac/Linux regeneration.
        # Pricing calculations retain their native precision.
        greeks = {field: None if request_kind == "historical" else round(model[field], 10) for field in ("delta", "gamma", "theta", "vega")}
        row = {"optionSymbol": symbol, "underlying": "DEMO-INDEX", "expiration": int((expiry + timedelta(minutes=15)).timestamp()), "side": kind, "strike": strike, "updated": int(at.timestamp()), "underlyingPrice": 100, "bid": round(model["price"] - .05, 4), "ask": round(model["price"] + .05, 4), "bidSize": 12, "askSize": 12, "volume": 120, "openInterest": 500, "iv": None if request_kind == "historical" else .25, **greeks}
        for field, value in row.items():
            packet.setdefault(field, []).append(value)
        specs[symbol] = {"root": "DEMO", "underlying": "DEMO-INDEX", "expires_at": iso(expiry), "last_trade_at": iso(expiry), "exercise": "european", "settlement": "cash", "multiplier": 100, "adjusted": False, "reference": "Fictional fixture convention; not a real exchange contract"}
    manifest = {"adapter_version": 1, "source": {"kind": "synthetic", "name": "Fictional MarketData-shaped EOD", "feed": "synthetic", "usage_rights": "Generated offline demonstration; no vendor market data"}, "request_kind": request_kind, "request_date": at.astimezone(EASTERN).date().isoformat() if request_kind == "historical" else None, "delivery": "free_24h", "retrieved_at": iso(at + timedelta(hours=24)), "underlying": "DEMO-INDEX", "rate": .04, "dividend_yield": .01, "inputs_available_at": iso(at), "open_interest_available_at": iso(at.astimezone(EASTERN).replace(hour=9, minute=30).astimezone(timezone.utc)), "iv_units": "decimal", "contracts": specs}
    return packet, manifest
