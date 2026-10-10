"""Neutral public entrypoint; supplied responses exercise the LLM interface."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from llm_reservoir_agent.experiment import main

if __name__ == "__main__":
    raise SystemExit(main())
