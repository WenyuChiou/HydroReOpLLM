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


def test_main_notebook_has_exactly_one_combined_result_figure():
    notebook = json.loads((ROOT / 'tutorials/main.ipynb').read_text(encoding='utf-8'))
    figures = [out for cell in notebook['cells'] for out in cell.get('outputs', [])
               if 'image/png' in out.get('data', {})]
    assert len(figures) == 1
    markdown = '\n'.join(''.join(cell['source']) for cell in notebook['cells'] if cell['cell_type'] == 'markdown')
    assert 'outputs/current_tutorial/reservoir_operations.png' not in markdown
    assert 'outputs/current_tutorial/daily_water_elevation.png' not in markdown
    assert 'outputs/current_tutorial/controlled_release_daily.png' not in markdown
    assert 'coupled/current/my-run.yaml' in markdown


def test_current_figure_manifest_covers_exact_published_bytes():
    import hashlib
    folder = OUTPUTS / 'current_tutorial'
    manifest = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    assert len(manifest['artifacts']) == 10
    for name, digest in manifest['artifacts'].items():
        path = folder / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        if path.suffix == '.svg':
            assert all(line == line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())


def test_result_figures_keep_paper_width_fonts_and_editable_labels():
    """Prevent export defaults from shrinking labels or rasterizing vector text."""
    import re
    import xml.etree.ElementTree as ET
    from PIL import Image

    folder = OUTPUTS / 'current_tutorial'
    for stem in ('reservoir_operations', 'daily_water_elevation', 'controlled_release_daily'):
        pdf = (folder / (stem + '.pdf')).read_bytes()
        box = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)', pdf)
        assert box is not None
        assert float(box.group(1)) / 72 * 25.4 == pytest.approx(180, abs=0.01)
        assert b'/FontFile2' in pdf, 'PDF must embed its TrueType font'
        svg = ET.parse(folder / (stem + '.svg')).getroot()
        text_nodes = svg.findall('.//{http://www.w3.org/2000/svg}text')
        # Matplotlib's SVG viewBox uses one unit per output point.
        assert svg.get('width', '').endswith('pt')
        assert float(svg.get('width')[:-2]) == pytest.approx(
            float(svg.get('viewBox').split()[2]))
        for node in text_nodes:
            size = re.search(r'font-size:\s*([\d.]+)px', node.get('style', ''))
            assert size is not None, 'Every text label needs an explicit size'
            assert float(size.group(1)) >= 9, 'Paper labels must be at least 9 pt'
        labels = ' '.join(''.join(node.itertext()) for node in text_nodes)
        for method in ('Rule-based', 'LLM with available information',
                       'LLM with retrieved knowledge'):
            assert method in labels, 'Method labels must remain editable text'
        with Image.open(folder / (stem + '.png')) as image:
            assert abs(image.width - 180 / 25.4 * 600) <= 1
            assert image.info['dpi'][0] == pytest.approx(600, abs=1)


def test_combined_figure_has_shared_calendar_exact_lines_grouped_bars_and_large_legend():
    """The paper figure must preserve every plotted daily value in its A/B layout."""
    import matplotlib.colors as mcolors
    import matplotlib.dates as mdates
    import numpy as np

    spec = importlib.util.spec_from_file_location(
        'current_combined_figure', ROOT / 'tutorials/build_notebooks.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    daily = pd.read_csv(OUTPUTS / 'current_tutorial/daily.csv')
    figure = builder.plot_reservoir_operations(daily)
    axes = figure.axes
    try:
        assert len(axes) == 2
        elevation, release = axes
        assert elevation.get_shared_x_axes().joined(elevation, release)
        assert elevation.get_title().startswith('(A)')
        assert release.get_title().startswith('(B)')

        expected_labels = [
            'Rule-based',
            'LLM with available information',
            'LLM with retrieved knowledge',
        ]
        data_lines = {line.get_label(): line for line in elevation.lines
                      if line.get_label() in expected_labels}
        assert list(data_lines) == expected_labels
        assert len(elevation.lines) == 5, 'Three method lines plus two dotted guides'
        assert sorted(line.get_ydata()[0] for line in elevation.lines
                      if line.get_linestyle() == ':') == [1300, 1370]

        bars = release.patches
        assert len(bars) == 3 * 366
        offsets = []
        for label in expected_labels:
            expected = daily.loc[daily['method_label'] == label].copy()
            expected_dates = mdates.date2num(pd.to_datetime(expected['date']))
            line = data_lines[label]
            np.testing.assert_allclose(line.get_ydata(), expected['pool_elevation_end_ft'],
                                       rtol=0, atol=0)
            color = mcolors.to_rgba(line.get_color())
            method_bars = sorted(
                (bar for bar in bars if np.allclose(bar.get_facecolor(), color)),
                key=lambda bar: bar.get_x() + bar.get_width() / 2,
            )
            assert len(method_bars) == 366
            centers = np.array([bar.get_x() + bar.get_width() / 2 for bar in method_bars])
            offsets.append(float(np.median(centers - expected_dates)))
            np.testing.assert_allclose(
                [bar.get_height() for bar in method_bars],
                expected['controlled_release_cms'], rtol=0, atol=0,
            )
        assert len({round(offset, 8) for offset in offsets}) == 3

        legends = [*figure.legends, elevation.get_legend(), release.get_legend()]
        legend = next(item for item in legends if item is not None)
        assert [text.get_text() for text in legend.get_texts()] == expected_labels
        assert min(text.get_fontsize() for text in legend.get_texts()) >= 10.5
    finally:
        import matplotlib.pyplot as plt
        plt.close(figure)
