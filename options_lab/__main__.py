import argparse
import json
from pathlib import Path

from .engine import compare, policy_from_dict, replay
from .fixtures import SCENARIOS, START, fixture, iso
from .schema import InputError, load_json, validate_dataset


def main():
    parser = argparse.ArgumentParser(description="Deterministic paper-only options research; no broker connectivity")
    parser.add_argument("command", choices=("compare", "replay", "fixture", "validate", "serve"))
    parser.add_argument("--scenario", choices=SCENARIOS, default="rally")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--at", default=iso(START))
    parser.add_argument("--through", help="Replay only through this timezone-aware ISO-8601 instant")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--port", type=int, default=8792)
    args = parser.parse_args()
    if args.through is not None and args.command != "replay":
        parser.error("--through is supported only by replay")
    if args.command == "serve":
        from .server import serve
        serve(args.port)
        return
    try:
        if args.input and args.input.stat().st_size > 2 * 1024 * 1024:
            raise InputError("input exceeds 2 MiB")
        data = validate_dataset(load_json(args.input.read_text()) if args.input else fixture(args.scenario))
        policy = policy_from_dict(load_json(args.policy.read_text()) if args.policy else {})
        if args.command == "fixture":
            result = data
        elif args.command == "compare":
            result = compare(data, args.at, policy, args.quantity)
        elif args.command == "validate":
            result = {"valid": True, "paper_only": True, "source": data["source"], "snapshots": len(data["snapshots"])}
        else:
            result = replay(data, policy, through=args.through)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (InputError, OSError, ValueError) as exc:
        parser.exit(2, f"Input rejected: {exc}\n")


if __name__ == "__main__":
    main()
