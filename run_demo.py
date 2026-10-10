"""Run from a source checkout without installation or downloads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from delaware_operations.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
