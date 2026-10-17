"""Current figures must use matched saved arms and reject incompatible inputs."""
import importlib.util
import json
import math
from pathlib import Path
import shutil

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / 'examples/fe_walter/coupled/outputs'


def test_current_tutorial_rows_are_exact_saved_framework_and_rule_rows():
    current = pd.read_csv(OUTPUTS / 'current_tutorial/daily.csv')
    prior = pd.read_csv(OUTPUTS / '2016/daily.csv')
    paired = pd.read_csv(OUTPUTS / 'gemma4_2016_comparison/daily.csv')
    assert set(current['method']) == {'rule', 'llm_available', 'llm_knowledge'}
    assert set(current.loc[current['method'] != 'rule', 'source_engine']) == {'framework'}
    for method, rows in current.groupby('method', sort=False):
        source = prior.loc[prior['method'] == 'rule'] if method == 'rule' else paired.loc[
            (paired['engine'] == 'framework') & (paired['method'] == method)]
        assert len(rows) == rows['date'].nunique() == 366
        assert rows['date'].tolist() == source['date'].tolist()
        for column in ('inflow_cms', 'pool_elevation_end_ft', 'controlled_release_cms',
                       'spill_cms', 'storage_end_m3'):
            # CSV serialization can change the last binary digit; it must not
            # introduce a meaningful new value, interpolation or another arm.
            assert all(math.isclose(a, b, rel_tol=1e-14, abs_tol=1e-12)
                       for a, b in zip(rows[column], source[column], strict=True)), (method, column)


@pytest.mark.parametrize('corruption', [
    'missing_date', 'different_inflow', 'different_initial_storage',
    'nan_inflow', 'nan_initial_storage', 'nan_elevation', 'infinite_release', 'nan_summary',
])
def test_current_tutorial_rejects_unmatched_saved_inputs(tmp_path, corruption):
    spec = importlib.util.spec_from_file_location('current_figure_validation', ROOT / 'tutorials/build_notebooks.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    builder.CURRENT = tmp_path / 'new-teaching-output'
    relative = Path('examples/fe_walter/coupled/outputs')
    for name in ('2016/daily.csv', '2016/summary.json', 'gemma4_2016_comparison/daily.csv'):
        destination = tmp_path / relative / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUTPUTS / name, destination)
    path = tmp_path / relative / 'gemma4_2016_comparison/daily.csv'
    daily = pd.read_csv(path)
    index = daily.index[(daily['engine'] == 'framework') & (daily['method'] == 'llm_knowledge')][0]
    if corruption == 'missing_date':
        daily = daily.drop(index)
    elif corruption == 'different_inflow':
        daily.loc[index, 'inflow_cms'] += 1
    elif corruption == 'different_initial_storage':
        daily.loc[index, 'storage_start_m3'] += 1
    elif corruption == 'nan_summary':
        summary_path = tmp_path / relative / '2016/summary.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        summary['initial_storage_m3'] = float('nan')
        summary_path.write_text(json.dumps(summary), encoding='utf-8')
    else:
        column = {'nan_inflow': 'inflow_cms', 'nan_initial_storage': 'storage_start_m3',
                  'nan_elevation': 'pool_elevation_end_ft',
                  'infinite_release': 'controlled_release_cms'}[corruption]
        daily.loc[index, column] = float('inf') if corruption == 'infinite_release' else float('nan')
    daily.to_csv(path, index=False)
    with pytest.raises((AssertionError, ValueError)):
        builder._prepare_current_outputs()
    assert not builder.CURRENT.exists(), 'Validation must fail before publishing figures'


def test_tutorial_check_rejects_changed_source_pins(monkeypatch):
    spec = importlib.util.spec_from_file_location('current_source_validation', ROOT / 'tutorials/build_notebooks.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    actual_sha = builder._sha
    source = OUTPUTS / '2016/daily.csv'
    monkeypatch.setattr(builder, '_sha', lambda path: 'changed' if path.resolve() == source.resolve() else actual_sha(path))
    with pytest.raises(AssertionError):
        builder.check()


def test_main_notebook_has_exactly_two_result_figures():
    notebook = json.loads((ROOT / 'tutorials/main.ipynb').read_text(encoding='utf-8'))
    figures = [out for cell in notebook['cells'] for out in cell.get('outputs', [])
               if 'image/png' in out.get('data', {})]
    assert len(figures) == 2
    markdown = '\n'.join(''.join(cell['source']) for cell in notebook['cells'] if cell['cell_type'] == 'markdown')
    assert 'outputs/current_tutorial/daily_water_elevation.png' not in markdown
    assert 'outputs/current_tutorial/controlled_release_daily.png' not in markdown
    assert 'coupled/current/my-run.yaml' in markdown


def test_current_figure_manifest_covers_exact_published_bytes():
    import hashlib
    folder = OUTPUTS / 'current_tutorial'
    manifest = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    assert len(manifest['artifacts']) == 7
    for name, digest in manifest['artifacts'].items():
        path = folder / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        if path.suffix == '.svg':
            assert all(line == line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())
