"""Verify an existing offline artifact without rerunning its simulation."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from llm_reservoir_agent.verification import verify_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_run(args.output, require_offline=True), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
