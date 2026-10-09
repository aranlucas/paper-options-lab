import argparse
import json
import os
from pathlib import Path

from .engine import compare, policy_from_dict, replay
from .fixtures import SCENARIOS, START, fixture, iso
from .schema import InputError, load_json, validate_dataset


def read_input(path):
    with path.open("rb") as file:
        content = file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise InputError("input exceeds 2 MiB")
    return load_json(content.decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Deterministic paper-only options research; no broker connectivity")
    parser.add_argument("command", choices=("compare", "replay", "fixture", "validate", "serve", "import-marketdata", "audit-marketdata"))
    parser.add_argument("--scenario", choices=SCENARIOS, default="rally")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--at")
    parser.add_argument("--metadata", type=Path, help="Offline MarketData contract/timestamp manifest")
    parser.add_argument("--through", help="Replay only through this timezone-aware ISO-8601 instant")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--port", type=int, default=os.environ.get("PORT", "8792"))
    args = parser.parse_args()
    if args.through is not None and args.command != "replay":
        parser.error("--through is supported only by replay")
    provider = args.command in ("import-marketdata", "audit-marketdata")
    if provider and (args.input is None or args.metadata is None):
        parser.error("MarketData conversion requires --input and --metadata local files")
    if provider and (args.policy is not None or args.quantity != 1):
        parser.error("MarketData conversion does not simulate fills or apply --policy/--quantity")
    if args.command == "import-marketdata" and args.at is not None:
        parser.error("use audit-marketdata --at for an as-of audit")
    if args.metadata is not None and not provider:
        parser.error("--metadata is supported only by MarketData conversion")
    if args.command == "serve":
        from .server import serve
        serve(args.port)
        return
    try:
        if provider:
            from .marketdata import convert_marketdata
            converted = convert_marketdata(read_input(args.input), read_input(args.metadata), args.at)
            result = converted["dataset" if args.command == "import-marketdata" else "audit"]
            print(json.dumps(result, indent=2, allow_nan=False))
            return
        data = validate_dataset(read_input(args.input) if args.input else fixture(args.scenario))
        policy = policy_from_dict(read_input(args.policy) if args.policy else {})
        if args.command == "fixture":
            result = data
        elif args.command == "compare":
            result = compare(data, args.at or iso(START), policy, args.quantity)
        elif args.command == "validate":
            result = {"valid": True, "paper_only": True, "source": data["source"], "snapshots": len(data["snapshots"])}
        else:
            result = replay(data, policy, through=args.through)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (InputError, OSError, ValueError) as exc:
        parser.exit(2, f"Input rejected: {exc}\n")


if __name__ == "__main__":
    main()
