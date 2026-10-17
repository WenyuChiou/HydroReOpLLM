"""The manual has one current route and publishes new results without hiding history."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_manual_current_downloads_have_an_isolated_namespace(tmp_path):
    spec = importlib.util.spec_from_file_location('reader_route_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
        builder.prepare(tmp_path, source_ref='codex/manual-research-guide')
    assert len(builder.TUTORIAL_DOWNLOADS) == 8
    for source, name in builder.TUTORIAL_DOWNLOADS.items():
        assert (tmp_path / '_tutorial_downloads' / name).read_bytes() == (ROOT / source).read_bytes()
        assert (tmp_path / source).read_bytes() == (ROOT / source).read_bytes()
    historical = ROOT / 'examples/fe_walter/coupled/outputs/daily.csv'
    assert (tmp_path / '_completed_downloads/daily.csv').read_bytes() == historical.read_bytes()
    assert (tmp_path / '_tutorial_downloads/daily.csv').read_bytes() != historical.read_bytes()
    for name in ('docs/TROUBLESHOOTING.md', 'docs/RECORDS.md', 'examples/fe_walter/results_history.md'):
        assert (tmp_path / name).is_file()


def test_manual_navigation_keeps_one_reader_route_without_right_toc():
    navigation = (ROOT / 'docs/_templates/navigation.html').read_text(encoding='utf-8')
    layout = (ROOT / 'docs/_templates/layout.html').read_text(encoding='utf-8')
    assert 'On this page' not in layout
    assert 'chapter-toc' not in layout
    for old in ('Weather-to-operation commands', 'Saved three-method comparison',
                'FE Walter saved decisions', 'Case evidence and reference'):
        assert old not in navigation
    assert "chapter('docs/TROUBLESHOOTING'" in navigation
    assert "chapter('docs/RECORDS'" in navigation
    assert 'figures/hydroopslm-cover.png' in (ROOT / 'docs/README.md').read_text(encoding='utf-8')
    assert 'figures/hydroopslm-cover.png' in (ROOT / 'docs/README.zh-TW.md').read_text(encoding='utf-8')


def test_teaching_diagrams_have_accessible_editable_text():
    namespace = {'s': 'http://www.w3.org/2000/svg'}
    names = ('reservoir-agent-mapping', 'prompt-context-workflow', 'fe-walter-weather-workflow')
    for name in names:
        root = ET.parse(ROOT / 'docs/figures' / (name + '.svg')).getroot()
        assert root.get('role') == 'img'
        ids = {node.get('id') for node in root.iter()}
        assert set(root.get('aria-labelledby').split()) <= ids
        assert root.find('s:title', namespace).text
        assert root.find('s:desc', namespace).text
        assert len(root.findall('.//s:text', namespace)) >= 6
        assert not root.findall('.//s:image', namespace), 'Text must remain editable, not baked into a bitmap'
