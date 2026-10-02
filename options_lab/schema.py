"""Bounded JSON validation. Timestamps are UTC-aware and inputs never execute code."""
import json
import math
from datetime import datetime, timezone


class InputError(ValueError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise InputError("timestamp must be an ISO-8601 string with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError("invalid ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise InputError("naive timestamps are forbidden")
    return result.astimezone(timezone.utc)


def number(value, path, low=0, high=1e8, optional=False, integer=False):
    if value is None and optional:
        return
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise InputError(f"{path}: expected finite number in [{low}, {high}]")
    if integer and type(value) is not int:
        raise InputError(f"{path}: expected integer")


def text(value, path):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise InputError(f"{path}: expected nonempty text, at most 200 characters")


def keys(obj, required, optional, path):
    if not isinstance(obj, dict):
        raise InputError(f"{path}: expected object")
    missing = set(required) - obj.keys()
    extra = obj.keys() - set(required) - set(optional)
    if missing or extra:
        raise InputError(f"{path}: missing {sorted(missing)}, unknown {sorted(extra)}")


def load_json(data):
    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InputError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=lambda x: (_ for _ in ()).throw(InputError(f"nonfinite {x}")))
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise InputError("invalid JSON") from exc


def validate_dataset(data):
    keys(data, ("schema_version", "source", "snapshots", "settlements", "events"), (), "dataset")
    if data["schema_version"] != 1 or type(data["schema_version"]) is not int:
        raise InputError("schema_version must be 1")
    source = data["source"]
    keys(source, ("kind", "name", "feed", "usage_rights"), (), "source")
    if source["kind"] not in ("synthetic", "imported"):
        raise InputError("source.kind must be synthetic or imported")
    for field in ("name", "feed", "usage_rights"):
        text(source[field], f"source.{field}")
    if source["kind"] == "synthetic" and source["feed"] != "synthetic":
        raise InputError("synthetic datasets must use synthetic feed")
    if source["kind"] == "imported" and source["feed"] not in ("opra", "licensed", "indicative", "unknown"):
        raise InputError("imported feed must be opra, licensed, indicative or unknown")
    for field, limit in (("snapshots", 100), ("settlements", 100), ("events", 200)):
        if not isinstance(data[field], list) or len(data[field]) > limit:
            raise InputError(f"{field}: expected list, at most {limit} entries")
    if not data["snapshots"]:
        raise InputError("at least one option-chain snapshot is required")
    seen = set()
    identities = {}
    for i, snap in enumerate(data["snapshots"]):
        path = f"snapshots[{i}]"
        keys(snap, ("id", "underlying", "as_of", "available_at", "spot", "spot_at", "rate", "dividend_yield", "contracts"), (), path)
        for field in ("id", "underlying"):
            text(snap[field], f"{path}.{field}")
        if snap["id"] in seen:
            raise InputError("duplicate snapshot id")
        seen.add(snap["id"])
        for field in ("as_of", "available_at", "spot_at"):
            timestamp(snap[field])
        number(snap["spot"], f"{path}.spot", .001, 100000)
        number(snap["rate"], f"{path}.rate", -.1, .5)
        number(snap["dividend_yield"], f"{path}.dividend_yield", 0, .5)
        if not isinstance(snap["contracts"], list) or len(snap["contracts"]) > 24:
            raise InputError("snapshot supports at most 24 contracts")
        contracts_seen = set()
        for j, quote in enumerate(snap["contracts"]):
            qp = f"{path}.contracts[{j}]"
            keys(quote, ("id", "kind", "strike", "expires_at", "last_trade_at", "exercise", "settlement", "multiplier", "adjusted", "bid", "ask", "bid_size", "ask_size", "volume", "open_interest", "liquidity_at", "quote_at", "iv"), (), qp)
            text(quote["id"], f"{qp}.id")
            if quote["id"] in contracts_seen:
                raise InputError("duplicate contract id within snapshot")
            contracts_seen.add(quote["id"])
            if quote["kind"] not in ("call", "put") or quote["exercise"] not in ("european", "american") or quote["settlement"] not in ("cash", "physical"):
                raise InputError("invalid option kind, exercise or settlement")
            if type(quote["adjusted"]) is not bool:
                raise InputError("adjusted must be boolean")
            for field in ("expires_at", "last_trade_at", "quote_at", "liquidity_at"):
                timestamp(quote[field])
            number(quote["strike"], f"{qp}.strike", .001, 100000)
            number(quote["multiplier"], f"{qp}.multiplier", 1, 1000, integer=True)
            for field in ("bid", "ask"):
                number(quote[field], f"{qp}.{field}", 0, 100000, optional=True)
            for field in ("bid_size", "ask_size", "volume", "open_interest"):
                number(quote[field], f"{qp}.{field}", 0, 100000000, optional=True, integer=True)
            number(quote["iv"], f"{qp}.iv", .0001, 5, optional=True)
            identity = (snap["underlying"],) + tuple(quote[field] for field in ("kind", "strike", "expires_at", "last_trade_at", "exercise", "settlement", "multiplier", "adjusted"))
            if quote["id"] in identities and identities[quote["id"]] != identity:
                raise InputError(f"contract identity changed across snapshots: {quote['id']}")
            identities[quote["id"]] = identity
    settlement_seen = set()
    for item in data["settlements"]:
        keys(item, ("underlying", "expires_at", "value", "available_at", "method"), (), "settlement")
        text(item["underlying"], "settlement.underlying")
        for field in ("expires_at", "available_at"):
            timestamp(item[field])
        number(item["value"], "settlement.value", 0, 100000)
        if item["method"] != "official_cash_value":
            raise InputError("settlement requires official_cash_value, never a stock closing bar")
        key = (item["underlying"], timestamp(item["expires_at"]))
        if key in settlement_seen:
            raise InputError("duplicate settlement")
        settlement_seen.add(key)
        if timestamp(item["available_at"]) < key[1]:
            raise InputError("settlement cannot be available before expiration")
    previous = None
    for event in data["events"]:
        keys(event, ("at", "action"), ("long_id", "short_id", "quantity", "position_id"), "event")
        at = timestamp(event["at"])
        if previous is not None and at <= previous:
            raise InputError("events must have strictly increasing timestamps")
        previous = at
        if event["action"] == "open":
            keys(event, ("at", "action", "long_id", "short_id", "quantity"), (), "open event")
            text(event["long_id"], "long_id")
            text(event["short_id"], "short_id")
            number(event["quantity"], "quantity", 1, 100, integer=True)
        elif event["action"] == "close":
            keys(event, ("at", "action", "position_id"), (), "close event")
            text(event["position_id"], "position_id")
        elif event["action"] == "observe":
            keys(event, ("at", "action"), (), "observe event")
        else:
            raise InputError("only local paper open, close and observe events are supported")
    return data
