"""Run FE Walter operations using accepted frozen inflow, without hydrology reruns."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from delaware_operations.operations import main

if __name__ == "__main__":
    raise SystemExit(main())
