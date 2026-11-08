"""The manual has one current route and publishes new results without hiding history."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile
import json

ROOT = Path(__file__).resolve().parents[1]


def test_bethlehem_preparation_downloads_are_separate_from_saved_teaching(tmp_path):
    """Publish new preparation inputs without changing accepted teaching bundles."""
    spec = importlib.util.spec_from_file_location('bethlehem_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        builder.prepare(tmp_path)
    names = {'preparation.json', 'ratings_inventory.csv', 'data_requirements.csv',
             'prepare_observations.py', 'observation_inventory.csv'}
    assert set(builder.BETHLEHEM_DOWNLOADS.values()) == names
    for name in names:
        original = ROOT / 'examples/fe_walter_bethlehem' / name
        assert (tmp_path / '_bethlehem_downloads' / name).read_bytes() == original.read_bytes()
        assert not (tmp_path / '_tutorial_downloads/bethlehem' / name).exists()
        for locale in ('README.md', 'README.zh-TW.md'):
            page = (tmp_path / 'examples/fe_walter_bethlehem' / locale).read_text(encoding='utf-8')
            assert '../../_bethlehem_downloads/' + name in page
            assert not any('/blob/' in line and name in line for line in page.splitlines())


def test_manual_current_downloads_have_an_isolated_namespace(tmp_path):
    spec = importlib.util.spec_from_file_location('reader_route_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        builder.prepare(tmp_path, source_ref='codex/manual-research-guide')
    legacy = {source: name for source, name in builder.TUTORIAL_DOWNLOADS.items()
              if not name.startswith('operation/')}
    operation = {source: name for source, name in builder.TUTORIAL_DOWNLOADS.items()
                 if name.startswith('operation/')}
    assert len(legacy) == 11
    assert len(operation) == 21
    assert len(builder.TUTORIAL_DOWNLOADS) == 32
    assert {'reservoir_operations.png', 'reservoir_operations.svg',
            'reservoir_operations.pdf'} <= set(builder.TUTORIAL_DOWNLOADS.values())
    for source, name in builder.TUTORIAL_DOWNLOADS.items():
        assert (tmp_path / '_tutorial_downloads' / name).read_bytes() == (ROOT / source).read_bytes()
        assert (tmp_path / source).read_bytes() == (ROOT / source).read_bytes()
    historical = ROOT / 'tests/fixtures/fe_walter_history/coupled_outputs/daily.csv'
    assert (tmp_path / '_completed_downloads/daily.csv').read_bytes() == historical.read_bytes()
    assert (tmp_path / '_tutorial_downloads/daily.csv').read_bytes() != historical.read_bytes()
    for name in ('docs/TROUBLESHOOTING.md', 'docs/RECORDS.md', 'examples/fe_walter/results_history.md'):
        assert (tmp_path / name).is_file()
    # Primary vector links must download locally even while the repo is private.
    current_results = (tmp_path / 'examples/fe_walter/results.md').read_text(encoding='utf-8')
    for extension in ('svg', 'pdf'):
        name = 'reservoir_operations.' + extension
        assert '_tutorial_downloads/' + name in current_results
        assert not any('/blob/' in line and name in line for line in current_results.splitlines())


def test_manual_navigation_keeps_one_reader_route_without_right_toc():
    navigation = (ROOT / 'docs/_templates/navigation.html').read_text(encoding='utf-8')
    layout = (ROOT / 'docs/_templates/layout.html').read_text(encoding='utf-8')
    assert 'On this page' not in layout
    assert 'chapter-toc' not in layout
    for old in ('Weather-to-operation commands', 'Saved three-method comparison',
                'FE Walter saved decisions', 'Case evidence and reference'):
        assert old not in navigation
    sections = json.loads((ROOT / 'docs/navigation.json').read_text(encoding='utf-8'))
    paths = [page['path'] for section in sections for page in section['pages']]
    assert 'docs/TROUBLESHOOTING' in paths and 'docs/RECORDS' in paths
    assert 'manual_sections' in navigation
    for name in ('README.md', 'README.zh-TW.md', 'index.md', 'index.zh-TW.md'):
        page = (ROOT / 'docs' / name).read_text(encoding='utf-8')
        assert 'figures/hydrocnhs-coupling-framework-en.png' in page
        if name.startswith('index'):
            # Branding belongs on the landing page; the technical diagram stays
            # in the separate explanation of how the simulation works.
            assert page.index('figures/hydroopslm-cover.png') < page.index('figures/hydrocnhs-coupling-framework-en.png')
        else:
            assert 'figures/hydroopslm-cover.png' not in page


def test_generic_files_download_locally_and_main_route_reaches_cases_after_settings(tmp_path):
    spec = importlib.util.spec_from_file_location('template_route_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        builder.prepare(tmp_path, source_ref='codex/manual-research-guide')
    index = (tmp_path / 'index.md').read_text(encoding='utf-8')
    # Check actual generated toctree entries, not a sidebar label alone.
    positions = [index.index('\n' + name + '\n') for name in (
        'docs/GETTING_STARTED', 'docs/INPUT_OUTPUT', 'docs/GLOBAL_SETTINGS',
        'docs/HYDROLOGY_SETUP', 'docs/BUILD_SIMULATION', 'docs/CONFIGURATION',
        'docs/INFORMATION', 'docs/RUNNING', 'docs/RESULTS_GUIDE', 'docs/DAILY_EXAMPLES',
        'docs/MULTI_RESERVOIR', 'docs/CASE_STUDIES',
    )]
    assert positions == sorted(positions)
    for source, name in builder.TEMPLATE_DOWNLOADS.items():
        assert (tmp_path / '_template_downloads' / name).read_bytes() == (ROOT / source).read_bytes()
        assert (tmp_path / source).read_bytes() == (ROOT / source).read_bytes()
    with zipfile.ZipFile(tmp_path / '_template_downloads/coupled-configuration.zip') as bundle:
        assert not any('..' in Path(name).parts for name in bundle.namelist())
        for source, name in builder.TEMPLATE_DOWNLOADS.items():
            assert bundle.read('coupled/' + name) == (ROOT / source).read_bytes()
    for name in ('INPUT_OUTPUT', 'GLOBAL_SETTINGS', 'HYDROLOGY_SETUP', 'BUILD_SIMULATION', 'CONFIGURATION'):
        text = (tmp_path / 'docs' / (name + '.md')).read_text(encoding='utf-8')
        assert '_template_downloads/' in text
        assert '/blob/' not in '\n'.join(line for line in text.splitlines() if 'templates/coupled/' in line)
        assert 'FE Walter' not in text and 'F.E. Walter' not in text
    assert 'On this page' not in (tmp_path / '_templates/layout.html').read_text(encoding='utf-8')
    for name in ('prompt-review-data.json', 'seasonal-context-preview.json', 'prompt-review.js'):
        assert (tmp_path / '_static' / name).read_bytes() == (ROOT / 'docs/_static' / name).read_bytes()
    review = (tmp_path / 'examples/fe_walter/prompt_review.md').read_text(encoding='utf-8')
    assert '../../_static/prompt-review-data.json' in review
    assert '/blob/' not in '\n'.join(line for line in review.splitlines() if 'preview.json' in line)


def test_teaching_diagrams_have_accessible_editable_text():
    namespace = {'s': 'http://www.w3.org/2000/svg'}
    names = ('simulation-stages', 'reservoir-agent-mapping',
             'prompt-context-workflow', 'fe-walter-weather-workflow')
    for name in names:
        root = ET.parse(ROOT / 'docs/figures' / (name + '.svg')).getroot()
        assert root.get('role') == 'img'
        ids = {node.get('id') for node in root.iter()}
        assert set(root.get('aria-labelledby').split()) <= ids
        assert root.find('s:title', namespace).text
        assert root.find('s:desc', namespace).text
        assert len(root.findall('.//s:text', namespace)) >= 6
        assert not root.findall('.//s:image', namespace), 'Text must remain editable, not baked into a bitmap'
        graph = ET.parse(ROOT / 'docs/figures' / (name + '.drawio')).getroot()
        vertices = {cell.get('id') for cell in graph.iter('mxCell') if cell.get('vertex') == '1'}
        edges = [cell for cell in graph.iter('mxCell') if cell.get('edge') == '1']
        assert len(vertices) >= 6 and len(edges) >= 6
        assert all(edge.get('source') in vertices and edge.get('target') in vertices for edge in edges)
