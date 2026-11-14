import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="python -m persist_diff")
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="save a Windows snapshot")
    snapshot.add_argument("output", type=Path)
    args = parser.parse_args()

    if sys.platform != "win32":
        parser.error("Snapshot collection requires Windows.")

    from . import run_keys, scheduled_tasks

    try:
        entries = run_keys.collect() | scheduled_tasks.collect()
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(entries, output, indent=2, sort_keys=True)
            output.write("\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Snapshot failed: {error}\n")

    print(f"Saved {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()