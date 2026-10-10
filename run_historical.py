"""Run the accepted FE Walter 1996–2025 hydrology, optionally with offline Dam decisions."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from delaware_operations.historical import main

if __name__ == "__main__":
    raise SystemExit(main())
