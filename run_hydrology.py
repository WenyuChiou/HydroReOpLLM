"""Run the accepted FE Walter semi-distributed model on two weather months."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from delaware_operations.hydrology import main

if __name__ == "__main__":
    raise SystemExit(main())
