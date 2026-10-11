"""Source-checkout entry point; see docs/USER_GUIDE.md for configuration."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from llm_reservoir_agent.workflow import main

if __name__ == "__main__":
    raise SystemExit(main())
