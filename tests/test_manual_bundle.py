"""Published canonical files and the downloadable bundle retain source bytes."""
import importlib.util
import html
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def prepared_manual(tmp_path_factory):
    spec = importlib.util.spec_from_file_location('manual_bundle_test_builder', ROOT / 'docs/build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    output = tmp_path_factory.mktemp('manual-bundle')
    builder.prepare(output, source_ref='codex/weather-operation-entry')
    return builder, output


def test_all_canonical_example_assets_match_their_sources(prepared_manual):
    builder, output = prepared_manual
    missing = [name for name in builder.MULTI_RESERVOIR_DOWNLOADS if not (output / name).is_file()]
    assert missing == []
    for relative in builder.MULTI_RESERVOIR_DOWNLOADS:
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes(), relative


def test_shared_rule_source_is_not_replaced_by_another_asset(prepared_manual):
    builder, output = prepared_manual
    for relative in builder.MULTI_SHARED_RULES:
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes(), relative


def test_download_archive_keeps_every_declared_source_and_safe_relative_paths(prepared_manual):
    builder, output = prepared_manual
    expected = {f'multiple_reservoirs/{name}': ROOT / relative
                for relative, name in builder.MULTI_RESERVOIR_DOWNLOADS.items()}
    expected.update({Path(relative).relative_to('examples').as_posix(): ROOT / relative
                     for relative in builder.MULTI_SHARED_RULES})
    archive = output / '_multiple_reservoir_downloads/hydroopslm-multiple-reservoirs.zip'
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(expected)
        assert len(bundle.namelist()) == len(expected)
        for name, source in expected.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert bundle.read(name) == source.read_bytes(), name


def test_fe_walter_guide_links_the_notebook_and_preserves_configuration(prepared_manual):
    """The concise manual links the repository lesson and keeps exact downloads."""
    _, output = prepared_manual
    page = 'tutorials/main.md'
    assert (output / page).is_file()
    assert 'tutorials/main' in (output / 'index.md').read_text(encoding='utf-8')
    navigation = (output / '_templates/navigation.html').read_text(encoding='utf-8')
    assert "chapter('tutorials/main'" in navigation
    text = (output / page).read_text(encoding='utf-8')
    assets = (
        'coupled/experiment.yaml', 'coupled/llm_available.yaml',
        'coupled/llm_knowledge.yaml', 'coupled/hydrology.yaml', 'coupled/models.yaml',
        'coupled/agents.rule.yaml', 'coupled/agents.llm_available.yaml',
        'coupled/agents.llm_knowledge.yaml', 'coupled/auditors.yaml', 'coupled/reservoirs.json',
        'prompts/available_information.txt', 'prompts/retrieved_knowledge.txt',
    )
    for name in assets:
        relative = 'examples/fe_walter/' + name
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes(), relative
        download = output / '_config_downloads' / Path(name).name
        assert download.read_bytes() == (ROOT / relative).read_bytes(), relative
    assert '/tree/codex%2Fweather-operation-entry/tutorials' in text
    assert '/blob/codex%2Fweather-operation-entry/tutorials/main.ipynb' in text
    assert '{literalinclude}' not in text
    notebook = json.loads((output / '_notebook_downloads/main.ipynb').read_text(encoding='utf-8'))
    displayed = '\n'.join(''.join(o.get('data', {}).get('text/html', []))
                          for c in notebook['cells'] for o in c.get('outputs', []))
    for name in assets:
        assert html.escape((ROOT / 'examples/fe_walter' / name).read_text(encoding='utf-8')) in displayed
    landing = (output / 'examples/fe_walter/configuration.md').read_text(encoding='utf-8')
    assert '/tutorials/README.md' in landing
    assert '{literalinclude}' not in landing


def test_current_2016_exports_are_local_exact_and_do_not_replace_history(prepared_manual):
    # Exercise the real prepare() publication path using the accepted saved export.
    builder, output = prepared_manual
    current = (
        'daily.csv', 'summary.json', 'pins.json', 'pool_release.svg', 'pool_release.pdf',
        'pool_release.png', 'llm_available_decision.json', 'llm_knowledge_decision.json',
    )
    historical = (
        'daily.csv', 'summary.json', 'pool_release.svg', 'pool_release.pdf',
        'llm_available_decision.json', 'llm_knowledge_decision.json',
    )
    comparison = (
        'daily.csv', 'summary.json', 'pool_release.png', 'pool_release.svg',
        'pool_release.pdf', 'llm_available_pair.json', 'llm_knowledge_pair.json',
    )
    downloads = output / '_completed_downloads'
    assert {item.name for item in downloads.iterdir() if item.is_file()} == (
        set(historical) | {'2016-' + name for name in current}
        | {'gemma4-2016-' + name for name in comparison}
    )
    for name in current:
        relative = 'examples/fe_walter/coupled/outputs/2016/' + name
        expected = (ROOT / relative).read_bytes()
        assert (output / relative).read_bytes() == expected, relative
        assert (downloads / ('2016-' + name)).read_bytes() == expected, relative
    for name in historical:
        relative = 'examples/fe_walter/coupled/outputs/' + name
        assert (downloads / name).read_bytes() == (ROOT / relative).read_bytes(), relative
    for name in ('llm_available_reply.txt', 'llm_knowledge_reply.txt'):
        relative = 'examples/fe_walter/coupled/outputs/2016/' + name
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes()
    tutorial_downloads = output / '_tutorial_downloads'
    assert {item.relative_to(tutorial_downloads).as_posix()
            for item in tutorial_downloads.rglob('*') if item.is_file()} == set(
        builder.TUTORIAL_DOWNLOADS.values()
    )
    for relative, published_name in builder.TUTORIAL_DOWNLOADS.items():
        expected = (ROOT / relative).read_bytes()
        assert (output / relative).read_bytes() == expected, relative
        assert (tutorial_downloads / published_name).read_bytes() == expected, relative
    import os
    for page, names in (
        ('examples/fe_walter/coupled/README.md', current),
    ):
        published_page = output / page
        text = published_page.read_text(encoding='utf-8')
        for name in names:
            target = downloads / ('2016-' + name)
            href = Path(os.path.relpath(target, published_page.parent)).as_posix()
            assert '](' + href + ')' in text, (page, name)
    # The maintained tutorial must download the same combined rows as its figures,
    # while the separate historical namespace above remains byte-preserved.
    tutorial = (output / 'tutorials/main.md').read_text(encoding='utf-8')
    assert '[daily.csv](../_tutorial_downloads/daily.csv)' in tutorial
    assert '[daily.csv](../_completed_downloads/2016-daily.csv)' not in tutorial
