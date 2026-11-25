"""Run a F.E. Walter study case with explicit seeds and a fresh output path."""

import argparse
import json
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

import yaml

from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, run_settings

from model import verify_serving


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("rule_based", "seasonal_target", "dkp"))
    parser.add_argument("--seed", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--full", action="store_true", help="Run the full 2021–2025 study period")
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--ollama-port", type=int, choices=range(1, 65536), default=11434, metavar="PORT")
    parser.add_argument("--allow-network", action="store_true", help="Allow inference on local Ollama")
    args = parser.parse_args()
    use_llm = args.case != "rule_based"
    if use_llm and not args.allow_network:
        parser.error("LLM cases require --allow-network for local Ollama")
    if args.output.exists():
        parser.error("--output must be a fresh directory")
    base_url = f"http://127.0.0.1:{args.ollama_port}"
    example = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="walter-study-") as temporary:
        stage = Path(temporary) / "fe_walter"
        copytree(example, stage)
        path = stage / f"{args.case}.yaml"
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        config["output"] = str(args.output.resolve())
        config["run_id"] = f"fe-walter-study-{args.case}" + (f"-seed-{args.seed}" if use_llm else "")
        if args.full:
            config["end_date"] = "2025-12-31"
            config["max_calls"] = 3652 if use_llm else 0
        if use_llm:
            config["models"]["local"].update(seed=args.seed, base_url=base_url)
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        settings = load_settings(path)
        if use_llm:
            verify_serving(base_url)
        run_settings(settings, allow_network=use_llm)
        if use_llm:
            verify_serving(base_url)
        print(json.dumps(verify_run(args.output, require_offline=not use_llm), indent=2))


if __name__ == "__main__":
    main()
