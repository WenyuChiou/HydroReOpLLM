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
CRITERIA = ROOT / 'examples/fe_walter/seasonal_pool_criteria.json'


def _temporary_builder(tmp_path):
    spec = importlib.util.spec_from_file_location(
        'temporary_current_figure_builder', ROOT / 'tutorials/build_notebooks.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    builder.CURRENT = tmp_path / 'new-teaching-output'
    builder.SEASONAL_CRITERIA = tmp_path / 'examples/fe_walter/seasonal_pool_criteria.json'
    relative = Path('examples/fe_walter/coupled/outputs')
    for name in ('2016/daily.csv', '2016/summary.json', 'gemma4_2016_comparison/daily.csv'):
        destination = tmp_path / relative / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUTPUTS / name, destination)
    builder.SEASONAL_CRITERIA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CRITERIA, builder.SEASONAL_CRITERIA)
    return builder


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
    builder = _temporary_builder(tmp_path)
    relative = Path('examples/fe_walter/coupled/outputs')
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


def test_secondary_formats_never_reuse_stale_source_or_renderer_outputs(tmp_path, monkeypatch):
    from matplotlib.figure import Figure

    builder = _temporary_builder(tmp_path)
    secondary = [
        f'{stem}.{ext}'
        for stem in ('daily_water_elevation', 'controlled_release_daily')
        for ext in ('png', 'svg', 'pdf')
    ]
    marker = {'value': 'renderer-v1'}

    def fake_savefig(_figure, path, **_kwargs):
        Path(path).write_text(f"{marker['value']}:{Path(path).name}\n", encoding='utf-8')

    monkeypatch.setattr(Figure, 'savefig', fake_savefig)
    builder._prepare_current_outputs()
    assert all((builder.CURRENT / name).read_text().startswith('renderer-v1:') for name in secondary)

    # A valid source change must not leave any of the six prior files in place.
    source = tmp_path / 'examples/fe_walter/coupled/outputs/gemma4_2016_comparison/daily.csv'
    frame = pd.read_csv(source)
    row = frame.index[(frame['engine'] == 'framework') & (frame['method'] == 'llm_knowledge')][0]
    frame.loc[row, 'pool_elevation_end_ft'] += 0.01
    frame.to_csv(source, index=False)
    for name in secondary:
        (builder.CURRENT / name).write_text('stale-source', encoding='utf-8')
    builder._prepare_current_outputs()
    assert all((builder.CURRENT / name).read_text().startswith('renderer-v1:') for name in secondary)

    # A renderer/settings revision likewise replaces every format.
    marker['value'] = 'renderer-v2'
    for name in secondary:
        (builder.CURRENT / name).write_text('stale-renderer', encoding='utf-8')
    builder._prepare_current_outputs()
    assert all((builder.CURRENT / name).read_text().startswith('renderer-v2:') for name in secondary)


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
    assert 'coupled/my-run.yaml' in markdown


def test_current_figure_manifest_covers_exact_published_bytes():
    import hashlib
    folder = OUTPUTS / 'current_tutorial'
    manifest = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    expected = {'daily.csv'} | {
        stem + suffix
        for stem in ('reservoir_operations', 'daily_water_elevation',
                     'controlled_release_daily')
        for suffix in ('.png', '.svg', '.pdf')
    }
    assert set(manifest['artifacts']) == expected
    assert manifest['figure_layout']['primary_height_mm'] == 160
    assert 'no new daily or live-date context' in manifest['provenance_note']
    for name, digest in manifest['artifacts'].items():
        path = folder / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        if path.suffix == '.svg':
            assert all(line == line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())
    assert hashlib.sha256((folder / 'daily.csv').read_bytes()).hexdigest() == (
        'e29ffa3375d2090611d928c2c06e81550e71ca995bf994d7af6d0a31b2f27b1b')


def test_result_figures_keep_paper_width_fonts_and_editable_labels():
    """Prevent export defaults from shrinking labels or rasterizing vector text."""
    import re
    import xml.etree.ElementTree as ET
    from PIL import Image

    folder = OUTPUTS / 'current_tutorial'
    for stem in ('reservoir_operations', 'daily_water_elevation', 'controlled_release_daily'):
        pdf = (folder / (stem + '.pdf')).read_bytes()
        box = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)', pdf)
        assert box is not None
        assert float(box.group(1)) / 72 * 25.4 == pytest.approx(180, abs=0.01)
        if stem == 'reservoir_operations':
            assert float(box.group(2)) / 72 * 25.4 == pytest.approx(160, abs=0.01)
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
        for method in ('Rule-based', 'LLM without knowledge retrieval',
                       'LLM with knowledge retrieval'):
            assert method in labels, 'Method labels must remain editable text'
        if stem == 'daily_water_elevation':
            assert 'Winter target: 1300 ft' in labels
            assert 'Summer limit: 1370 ft' in labels
        if stem == 'reservoir_operations':
            assert 'Seasonal reference (schematic)' in labels
            assert 'Summer upper limit: 1370 ft' in labels
        with Image.open(folder / (stem + '.png')) as image:
            assert abs(image.width - 180 / 25.4 * 600) <= 1
            if stem == 'reservoir_operations':
                assert abs(image.height - 160 / 25.4 * 600) <= 1
            assert image.info['dpi'][0] == pytest.approx(600, abs=1)


def test_combined_figure_has_shared_calendar_exact_lines_and_three_release_rows():
    """The four panels must share dates and preserve every saved daily value."""
    import matplotlib.colors as mcolors
    import matplotlib.dates as mdates
    import numpy as np

    spec = importlib.util.spec_from_file_location(
        'current_combined_figure', ROOT / 'tutorials/build_notebooks.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    daily = pd.read_csv(OUTPUTS / 'current_tutorial/daily.csv')
    criteria = json.loads(CRITERIA.read_text(encoding='utf-8'))
    figure = builder.plot_reservoir_operations(daily, criteria)
    axes = figure.axes
    try:
        assert len(axes) == 4
        elevation, *release_axes = axes
        assert all(elevation.get_shared_x_axes().joined(elevation, release)
                   for release in release_axes)
        assert elevation.get_title().startswith('(a)')

        expected_labels = [
            'Rule-based',
            'LLM without knowledge retrieval',
            'LLM with knowledge retrieval',
        ]
        data_lines = {line.get_label(): line for line in elevation.lines
                      if line.get_label() in expected_labels}
        assert list(data_lines) == expected_labels
        assert len(elevation.lines) == 4, 'Three methods and one seasonal schematic'
        seasonal = next(line for line in elevation.lines
                        if line.get_label() == 'Seasonal reference (schematic)')
        assert pd.DatetimeIndex(seasonal.get_xdata()).strftime('%m-%d').tolist() == [
            '01-01', '04-01', '05-10', '10-15', '11-01', '12-31']
        assert list(seasonal.get_ydata()) == [1300, 1300, 1370, 1370, 1300, 1300]
        guides = {text.get_text(): text for text in elevation.texts}
        for label in ('Winter target: 1300 ft', 'Summer upper limit: 1370 ft'):
            assert guides[label].get_fontsize() >= 9

        release_limits = [release.get_ylim() for release in release_axes]
        release_ticks = [release.get_yticks() for release in release_axes]
        assert all(limits == release_limits[0] for limits in release_limits)
        assert all(np.array_equal(ticks, release_ticks[0]) for ticks in release_ticks)
        for index, (release, label) in enumerate(zip(release_axes, expected_labels, strict=True)):
            assert release.get_title(loc='left') == f'({chr(98 + index)}) Water release ({label})'
            assert release.get_ylabel() == 'Water release\n(m³/s)'
            method = tuple(builder.LABELS)[index]
            expected = daily.loc[daily['method'] == method].copy()
            expected_dates = mdates.date2num(pd.to_datetime(expected['date']))
            line = data_lines[label]
            np.testing.assert_allclose(line.get_ydata(), expected['pool_elevation_end_ft'],
                                       rtol=0, atol=0)
            color = mcolors.to_rgba(line.get_color())
            assert len(release.patches) == 366
            assert all(bar.get_width() == pytest.approx(0.72) for bar in release.patches)
            assert all(np.allclose(bar.get_facecolor(), color) for bar in release.patches)
            centers = np.array([
                bar.get_x() + bar.get_width() / 2 for bar in release.patches])
            np.testing.assert_allclose(centers, expected_dates, rtol=0, atol=1e-10)
            np.testing.assert_allclose(
                [bar.get_height() for bar in release.patches],
                expected['controlled_release_cms'], rtol=0, atol=0,
            )
            assert not release.texts, 'Method names belong in panel titles, not over the data'

        legends = [*figure.legends, elevation.get_legend(),
                   *(axis.get_legend() for axis in release_axes)]
        legend = next(item for item in legends if item is not None)
        assert [text.get_text() for text in legend.get_texts()] == expected_labels + [
            'Seasonal reference (schematic)']
        assert min(text.get_fontsize() for text in legend.get_texts()) >= 9
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        assert not legend.get_window_extent(renderer).overlaps(
            elevation.title.get_window_extent(renderer))
    finally:
        import matplotlib.pyplot as plt
        plt.close(figure)


@pytest.mark.parametrize('method', ['llm_available', 'llm_knowledge'])
def test_saved_storage_gap_equals_cumulative_outflow_gap(method):
    """Shared inflow and initial storage leave only the accumulated outflow gap."""
    import numpy as np

    daily = pd.read_csv(OUTPUTS / 'current_tutorial/daily.csv')
    rule = daily.loc[daily['method'].eq('rule')].set_index('date')
    other = daily.loc[daily['method'].eq(method)].set_index('date')
    assert rule.index.equals(other.index)
    np.testing.assert_allclose(rule['inflow_cms'], other['inflow_cms'],
                               rtol=0, atol=1e-10)
    cumulative_extra_outflow = (
        other['controlled_release_cms'] + other['spill_cms']
        - rule['controlled_release_cms'] - rule['spill_cms']
    ).cumsum() * 86400.0
    np.testing.assert_allclose(
        rule['storage_end_m3'] - other['storage_end_m3'],
        cumulative_extra_outflow, rtol=0, atol=1e-5,
    )
