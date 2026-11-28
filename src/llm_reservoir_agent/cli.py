"""Command-line interface for ``reservoir-experiment``."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import sysconfig
from pathlib import Path

import yaml

from .config.loader import UniqueLoader
from .hydrology.network import PROJECT_ROOT
from .simulation import workflow as _wf
from .simulation.trace import RunOutputExistsError


def _find_bundled_examples():
    """Locate bundled synthetic examples in the installed environment or checkout."""
    candidates = [
        Path(sysconfig.get_path("data")) / "share" / "llm-reservoir-agent" / "examples",
        Path(sys.prefix) / "share" / "llm-reservoir-agent" / "examples",
        PROJECT_ROOT / "examples",
    ]
    for candidate in candidates:
        if (candidate / "fe_walter" / "rule_based.yaml").is_file():
            return candidate
    raise FileNotFoundError("bundled examples directory was not found in the active Python environment")


def main(argv=None):
    """Dispatch check, prepare, run, verify, resume or init-examples from the CLI.

    check reads/pins/previews; prepare writes prepared coupled hydrology; run writes native results; verify reads completed evidence; resume preserves the source and creates a distinct output; init-examples copies bundled examples into a fresh directory. Live transport remains an explicit --allow-network choice.

    Parameters
    ----------
    argv : Sequence[str] or None, optional
        Arguments selecting a command and configuration/output paths; None reads process arguments.

    Returns
    -------
    int
        Zero after printing a successful JSON report, or one if the destination/output already exists.

    Raises
    ------
    SystemExit
        Argument parsing rejects input or displays help.
    ValueError
        A command/configuration or explicit live-request condition is invalid.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    parser = argparse.ArgumentParser(description="Configure daily HydroCNHS or explicit fixed-interval reservoir operations")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "prepare", "run"):
        command = sub.add_parser(name)
        command.add_argument("config", type=Path)
        if name == "run":
            command.add_argument("--allow-network", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("output", type=Path)
    verify.add_argument("--require-offline", action="store_true")
    init_examples = sub.add_parser("init-examples")
    init_examples.add_argument("destination", nargs="?", type=Path, default=Path("examples"))
    resume = sub.add_parser("resume")
    resume.add_argument("config", type=Path)
    resume.add_argument("--from-run", type=Path, required=True)
    resume.add_argument("--output", type=Path, required=True)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--allow-network", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "init-examples":
        if args.destination.exists():
            print(
                f"Examples destination already exists: {args.destination}\n"
                "Choose a fresh directory, e.g. reservoir-experiment init-examples my-examples.",
                file=sys.stderr,
            )
            return 1
        source = _find_bundled_examples()
        shutil.copytree(
            source,
            args.destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        result = {
            "destination": str(args.destination.resolve()),
            "source": str(source),
            "first_example": str(args.destination / "fe_walter" / "rule_based.yaml"),
        }
    elif args.command == "verify":
        from .simulation.verification import verify_run
        result = verify_run(args.output, require_offline=args.require_offline)
    elif args.command == "resume":
        from .simulation.recovery import resume_settings
        document = yaml.load(args.config.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
        if isinstance(document, dict) and document.get("schema_version") in ("hydroops-coupled-simulation.v1", "hydroops-coupled-simulation.v2"):
            from .hydrology.coupled import load_coupled_settings, prepared_experiment
            source = prepared_experiment(load_coupled_settings(args.config))
        else:
            source = args.config
        _, result = resume_settings(_wf.load_settings(source), args.from_run,
                                    output=args.output, run_id=args.run_id,
                                    allow_network=args.allow_network)
    else:
        document = yaml.load(args.config.read_text(encoding="utf-8-sig"), Loader=UniqueLoader)
        if isinstance(document, dict) and document.get("schema_version") in ("hydroops-coupled-simulation.v1", "hydroops-coupled-simulation.v2"):
            from .hydrology.coupled import load_coupled_settings, prepare_coupled, run_coupled
            settings = load_coupled_settings(args.config)
            runner = _wf.run_coupled if hasattr(_wf, 'run_coupled') else run_coupled
        else:
            if args.command == "prepare":
                raise ValueError("prepare requires a hydroops-coupled-simulation.v1 configuration")
            settings = _wf.load_settings(args.config)
            runner = _wf.run_settings

        if args.command == "check":
            result = settings.report
        elif args.command == "prepare":
            result = prepare_coupled(settings)
        else:
            try:
                _, result = runner(settings, allow_network=args.allow_network)
            except RunOutputExistsError as error:
                print(
                    f"Run output already exists: {error.filename}\n"
                    f"Set a new run_id and output in {args.config}, then run again.\n"
                    "Point reservoir-experiment verify at the new output directory.",
                    file=sys.stderr,
                )
                return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
