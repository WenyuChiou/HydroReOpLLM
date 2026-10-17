"""The publication figure builder must preserve the reviewed editable workflow."""
import importlib.util
import json
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / 'docs/figures'


def test_figure_builder_preserves_reviewed_source_and_information_flows(tmp_path):
    spec = importlib.util.spec_from_file_location(
        'figure1_source_builder', FIGURES / 'source/build_coupling_drawio.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.build(tmp_path)
    name = 'hydrocnhs-coupling-framework-en.drawio'
    assert (tmp_path / name).read_bytes() == (FIGURES / name).read_bytes()
    cells = list(ET.parse(FIGURES / name).iter('mxCell'))
    ids = {cell.get('id') for cell in cells}
    expected = {(cell.get('id'), cell.get('source'), cell.get('target'))
                for cell in cells if cell.get('edge') == '1'}
    manifest = json.loads((tmp_path / 'relationship-map.json').read_text(encoding='utf-8'))
    assert {(edge['id'], edge['source'], edge['target'])
            for edge in manifest['edges']} == expected
    assert all(source in ids and target in ids for _, source, target in expected)
    assert manifest['source_sha256'] == hashlib.sha256((FIGURES / name).read_bytes()).hexdigest()
    assert manifest['execution']['hydrology'] == 'precomputed continuous upstream hydrology'
    assert manifest['execution']['operation'] == 'daily decision, physics, downstream routing and commit'
