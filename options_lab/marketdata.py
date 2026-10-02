"""Offline conversion of bounded MarketData-shaped JSON; no network or credentials."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
from zoneinfo import ZoneInfo

from .engine import Policy, quote_reasons
from .schema import InputError, keys, number, text, timestamp, validate_dataset

EASTERN = ZoneInfo("America/New_York")
IDENTITY = ("optionSymbol", "underlying", "expiration", "side", "strike", "updated", "underlyingPrice")
NUMERIC = ("bid", "ask", "mid", "last", "volume", "openInterest", "bidSize", "askSize", "iv", "delta", "gamma", "theta", "vega", "intrinsicValue", "extrinsicValue", "dte", "firstTraded")
OPTIONAL = (*NUMERIC, "inTheMoney")
GREEKS = ("delta", "gamma", "theta", "vega")
SYMBOL = re.compile(r"([A-Z][A-Z0-9]{0,5}) *(\d{6})([CP])(\d{8})\Z")


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def epoch(value, field):
    # Unix seconds identify an absolute UTC instant; never reinterpret as ET.
    number(value, field, 0, 4102444800, integer=True)
    return datetime.fromtimestamp(value, timezone.utc)


def occ_identity(value):
    text(value, "optionSymbol")
    match = SYMBOL.fullmatch(value)
    if match is None:
        raise InputError("unsupported OCC symbol; expected compact or padded root, YYMMDD, C/P and eight strike digits")
    root, day, side, strike = match.groups()
    if value[:-15] not in (root, root.ljust(6)):
        raise InputError("OCC root must be compact or padded to exactly six characters")
    try:
        date = datetime.strptime("20" + day, "%Y%m%d").date()
    except ValueError as exc:
        raise InputError("invalid OCC expiration date") from exc
    return root + day + side + strike, root, date, "call" if side == "C" else "put", Decimal(strike) / 1000


def convert_marketdata(packet, manifest, audit_at=None):
    """Return strict schema plus diagnostics. User metadata remains unverified."""
    keys(packet, ("s", *IDENTITY), OPTIONAL, "MarketData response")
    if packet["s"] != "ok":
        raise InputError("MarketData response status must be ok")
    symbols = packet["optionSymbol"]
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 24:
        raise InputError("preselect 1–24 contracts before offline import")
    size = len(symbols)
    for field in (*IDENTITY, *OPTIONAL):
        if field in packet and (not isinstance(packet[field], list) or len(packet[field]) != size):
            raise InputError(f"{field}: column length must match optionSymbol")
    identities = [occ_identity(value) for value in symbols]
    keys(manifest, ("adapter_version", "source", "request_kind", "request_date", "delivery", "retrieved_at", "underlying", "rate", "dividend_yield", "inputs_available_at", "open_interest_available_at", "iv_units", "contracts"), (), "manifest")
    if type(manifest["adapter_version"]) is not int or manifest["adapter_version"] != 1:
        raise InputError("adapter_version must be 1")
    keys(manifest["source"], ("kind", "name", "feed", "usage_rights"), (), "manifest.source")
    if manifest["delivery"] != "free_24h" or manifest["request_kind"] not in ("historical", "latest_eod"):
        raise InputError("adapter supports free_24h historical or latest_eod observations only")
    if manifest["iv_units"] != "decimal":
        raise InputError("iv_units must explicitly be decimal; no percentage guessing")
    text(manifest["underlying"], "manifest.underlying")
    retrieved = timestamp(manifest["retrieved_at"])
    updated = [epoch(value, "updated") for value in packet["updated"]]
    if len(set(updated)) != 1:
        raise InputError("preselect a uniform updated instant; asynchronous rows are not merged")
    as_of = updated[0]
    if retrieved < as_of + timedelta(hours=24):
        raise InputError("free_24h retrieval must be at least 24 hours after quote time")
    if timestamp(manifest["inputs_available_at"]) > as_of:
        raise InputError("rate/yield assumptions cannot use future information")
    oi_at = timestamp(manifest["open_interest_available_at"]) if manifest["open_interest_available_at"] is not None else None
    if oi_at is not None and oi_at > as_of:
        raise InputError("open interest publication cannot be after the quote observation")
    if oi_at is not None and as_of - oi_at > timedelta(hours=24):
        raise InputError("open interest publication is stale relative to the observation")
    historical = manifest["request_kind"] == "historical"
    if historical:
        day = manifest["request_date"]
        if not isinstance(day, str):
            raise InputError("historical request_date must be YYYY-MM-DD")
        try:
            requested_day = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError as exc:
            raise InputError("invalid historical request_date") from exc
        local = as_of.astimezone(EASTERN)
        if day != requested_day.isoformat() or local.date() != requested_day or (local.hour, local.minute, local.second) != (16, 0, 0):
            raise InputError("historical row must match request_date at documented 16:00 America/New_York")
    elif manifest["request_date"] is not None:
        raise InputError("latest_eod request_date must be null")
    specs = manifest["contracts"]
    if not isinstance(specs, dict) or set(specs) != set(symbols):
        raise InputError("contract metadata must cover exactly the supplied option symbols")
    rows, audits, seen = [], [], set()
    spot = None
    for i, raw_id in enumerate(symbols):
        get = lambda field: packet.get(field, [None] * size)[i]
        canonical, root, contract_day, kind, strike = identities[i]
        if canonical in seen:
            raise InputError("duplicate contract identity, including padded/compact aliases")
        seen.add(canonical)
        number(get("strike"), "strike", .001, 100000)
        if get("side") != kind or Decimal(str(get("strike"))) != strike:
            raise InputError("OCC side/strike does not match response columns")
        if get("underlying") != manifest["underlying"]:
            raise InputError("underlying mismatch; mixed chains are not supported")
        number(get("underlyingPrice"), "underlyingPrice", .001, 100000)
        if spot is not None and spot != get("underlyingPrice"):
            raise InputError("underlyingPrice differs within one observation; no averaging or forward fill")
        spot = get("underlyingPrice")
        provider_expiry = epoch(get("expiration"), "expiration")
        if provider_expiry.astimezone(EASTERN).date() != contract_day:
            raise InputError("provider expiration date does not match OCC identity")
        spec = specs[raw_id]
        keys(spec, ("root", "underlying", "expires_at", "last_trade_at", "exercise", "settlement", "multiplier", "adjusted", "reference"), (), "contract metadata")
        text(spec["reference"], "contract reference")
        expiry, cutoff = timestamp(spec["expires_at"]), timestamp(spec["last_trade_at"])
        if spec["root"] != root or spec["underlying"] != get("underlying") or expiry.astimezone(EASTERN).date() != contract_day:
            raise InputError("contract metadata conflicts with OCC root, underlying or date")
        if cutoff > expiry:
            raise InputError("final trading cutoff must not be after expiration")
        for field in NUMERIC:
            value = get(field)
            integer = field in ("volume", "openInterest", "bidSize", "askSize", "dte", "firstTraded")
            low = -1e8 if field in GREEKS else 0
            number(value, field, low, 1e8 if field != "firstTraded" else 4102444800, optional=True, integer=integer)
        if get("firstTraded") is not None and epoch(get("firstTraded"), "firstTraded") > as_of:
            raise InputError("firstTraded cannot be in the future")
        if get("inTheMoney") is not None and type(get("inTheMoney")) is not bool:
            raise InputError("inTheMoney must be boolean or null")
        if historical and any(get(field) is not None for field in ("iv", *GREEKS)):
            raise InputError("historical response must not contain IV/Greeks; provider documents these as null")
        if get("openInterest") is not None and oi_at is None:
            raise InputError("known open interest requires its publication timestamp")
        row = {
            "id": canonical, "kind": kind, "strike": get("strike"),
            "expires_at": iso(expiry), "last_trade_at": iso(cutoff),
            "exercise": spec["exercise"], "settlement": spec["settlement"],
            "multiplier": spec["multiplier"], "adjusted": spec["adjusted"],
            "bid": get("bid"), "ask": get("ask"), "bid_size": get("bidSize"), "ask_size": get("askSize"),
            "volume": get("volume"), "open_interest": get("openInterest"),
            # Volume is full-session/as-of updated. Using OI's earlier time for
            # this aggregate field would allow morning lookahead.
            "liquidity_at": iso(as_of), "quote_at": iso(as_of), "iv": get("iv"),
        }
        rows.append(row)
        audits.append({"id": canonical, "provider_iv": get("iv"), "iv_origin": "missing" if get("iv") is None else "supplied; not model-derived", "provider_greeks": {field: get(field) for field in GREEKS}, "provider_expiration": iso(provider_expiry), "contract_reference": spec["reference"], "warnings": ["PROVIDER_EXPIRATION_TIME_DIFFERS"] if provider_expiry != expiry else []})
    snapshot = {"id": "marketdata-offline-1", "underlying": manifest["underlying"], "as_of": iso(as_of), "available_at": iso(retrieved), "spot": spot, "spot_at": iso(as_of), "rate": manifest["rate"], "dividend_yield": manifest["dividend_yield"], "contracts": rows}
    # Never create a plan, settlement value or execution from a quote packet.
    source = {**manifest["source"], "observation_only": True}
    dataset = validate_dataset({"schema_version": 1, "source": source, "snapshots": [snapshot], "settlements": [], "events": []})
    at = timestamp(audit_at) if audit_at is not None else retrieved
    for row, audit in zip(rows, audits):
        reasons = ["OBSERVATION_ONLY_DATA", *quote_reasons(row, snapshot, at, Policy(), 1)]
        if at < retrieved:
            reasons.append("SNAPSHOT_NOT_YET_AVAILABLE")
        if at < as_of:
            reasons.append("FUTURE_OBSERVATION")
        if dataset["source"]["feed"] in ("indicative", "unknown"):
            reasons.append("NON_EXECUTABLE_OR_UNKNOWN_FEED")
        audit["screen_reasons"] = sorted(set(reasons))
    audit = {"paper_only": True, "label": "Offline quote compatibility audit; not a backtest or performance report", "source": dataset["source"], "at": iso(at), "quote_as_of": iso(as_of), "available_at": iso(retrieved), "open_interest_available_at": iso(oi_at) if oi_at else None, "delivery": manifest["delivery"], "metadata": "User-supplied contract references and rights are not independently verified", "fills_created": 0, "iv_inversion": "absent; missing IV remains null", "contracts": audits}
    return {"dataset": dataset, "audit": audit}
