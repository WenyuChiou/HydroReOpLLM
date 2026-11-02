"""Run the shipped Daily single/cascade fixtures outside an installed checkout.

This acceptance script copies explicit example files into a temporary directory,
then invokes the existing CLI. All decisions are deterministic offline fixtures.
It rejects source-checkout imports and retains the analytic storage assertions.
No service, model download or live inference is involved.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile

from llm_reservoir_agent import workflow
from llm_reservoir_agent.verification import verify_run


def main() -> None:
    """Copy and execute both examples with installed CLI and independent results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, required=True,
                        help='Directory containing the published Daily YAML/JSON fixtures.')
    args = parser.parse_args()
    installed = Path(sysconfig.get_path('purelib')).resolve()
    if not Path(workflow.__file__).resolve().is_relative_to(installed):
        raise RuntimeError('Acceptance imported a source checkout instead of the installed wheel')
    command = Path(sysconfig.get_path('scripts')) / ('reservoir-experiment.exe' if os.name == 'nt' else 'reservoir-experiment')
    reports = []
    with tempfile.TemporaryDirectory(prefix='daily-wheel-outside-checkout-') as directory:
        root = Path(directory)
        fixtures = root / 'examples/daily_offline'
        fixtures.mkdir(parents=True)
        for name in ('single.yaml', 'single.json', 'cascade.yaml', 'cascade.json', 'operator.txt'):
            shutil.copyfile(args.examples.resolve() / name, fixtures / name)
        for label, expected in [('single', [1_345_600.]), ('cascade', [1_345_600., 1_086_400., 1_086_400.])]:
            entry = fixtures / f'{label}.yaml'
            for action, target in [('check', entry), ('run', entry), ('verify', root / f'runs/daily-{label}')]:
                subprocess.run([str(command), action, str(target)], cwd=root, check=True)
            proof = verify_run(root / f'runs/daily-{label}', require_offline=True)
            # The trajectory is the public physical output, independent of the
            # workflow's compact summary presentation structure.
            with (root / f'runs/daily-{label}/reservoir_trajectory.csv').open(newline='') as handle:
                actual = {row['reservoir_id']: float(row['storage_end_m3']) for row in csv.DictReader(handle)}
            if any(abs(actual[f'Lake_{i+1}'] - value) > 1e-6 for i, value in enumerate(expected)):
                raise RuntimeError(f'{label}: installed analytic storage mismatch: {actual}')
            if proof['days'] != 4 or proof['observed_network_calls'] != 0:
                raise RuntimeError(f'{label}: unexpected dates or provider calls')
            reports.append({'example': label, 'status': proof['status'], 'days': proof['days'],
                            'model_calls': proof['observed_network_calls'], 'final_storage_m3': actual,
                            'max_system_balance_residual_m3': proof['max_system_balance_residual_m3']})
    print(json.dumps({'installed_module': str(workflow.__file__), 'examples': reports}, indent=2))


if __name__ == '__main__':
    main()
