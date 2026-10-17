"""Published canonical files and the downloadable bundle retain source bytes."""
import importlib.util
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


def test_fe_walter_walkthrough_publishes_the_actual_configuration(prepared_manual):
    """Readers can reach the walkthrough and copy the maintained experiment bytes."""
    _, output = prepared_manual
    page = 'tutorials/fe_walter.md'
    assert (output / page).is_file()
    assert 'tutorials/fe_walter' in (output / 'index.md').read_text(encoding='utf-8')
    navigation = (output / '_templates/navigation.html').read_text(encoding='utf-8')
    assert "chapter('tutorials/fe_walter'" in navigation
    text = (output / page).read_text(encoding='utf-8')
    assets = (
        'coupled/experiment.yaml', 'coupled/rule.yaml', 'coupled/llm_available.yaml',
        'coupled/llm_knowledge.yaml', 'coupled/hydrology.yaml', 'coupled/models.yaml',
        'coupled/agents.rule.yaml', 'coupled/agents.llm_available.yaml',
        'coupled/agents.llm_knowledge.yaml', 'coupled/auditors.yaml', 'coupled/reservoirs.json',
        'prompts/zeroshot_seasonal_v1_system.txt', 'prompts/dkp_seasonal_v1_system.txt',
        'prompts/dkp_seasonal_v2_system.txt',
    )
    for name in assets:
        relative = 'examples/fe_walter/' + name
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes(), relative
        download = output / '_config_downloads' / Path(name).name
        assert download.read_bytes() == (ROOT / relative).read_bytes(), relative
    # Literalinclude directives must resolve from the canonical tutorial's location.
    import re
    includes = re.findall(r'\{literalinclude\}\s+(\S+)', text)
    assert '../examples/fe_walter/coupled/experiment.yaml' in includes
    assert '../examples/fe_walter/coupled/agents.llm_available.yaml' in includes
    assert '../examples/fe_walter/prompts/zeroshot_seasonal_v1_system.txt' in includes
    assert '../examples/fe_walter/prompts/dkp_seasonal_v2_system.txt' in includes
    for name in includes:
        published = (output / page).parent / name
        source = (ROOT / page).parent / name
        assert published.read_bytes() == source.read_bytes(), name
    landing = (output / 'examples/fe_walter/configuration.md').read_text(encoding='utf-8')
    assert '../../tutorials/fe_walter.md' in landing
    assert '{literalinclude}' not in landing


def test_current_2016_exports_are_local_exact_and_do_not_replace_history(prepared_manual):
    # Exercise the real prepare() publication path using the accepted saved export.
    _, output = prepared_manual
    current = (
        'daily.csv', 'summary.json', 'pins.json', 'pool_release.svg', 'pool_release.pdf',
        'llm_available_decision.json', 'llm_knowledge_decision.json',
    )
    historical = (
        'daily.csv', 'summary.json', 'pool_release.svg', 'pool_release.pdf',
        'llm_available_decision.json', 'llm_knowledge_decision.json',
    )
    downloads = output / '_completed_downloads'
    assert {item.name for item in downloads.iterdir() if item.is_file()} == (
        set(historical) | {'2016-' + name for name in current}
    )
    for name in current:
        relative = 'examples/fe_walter/coupled/outputs/2016/' + name
        expected = (ROOT / relative).read_bytes()
        assert (output / relative).read_bytes() == expected, relative
        assert (downloads / ('2016-' + name)).read_bytes() == expected, relative
    for name in historical:
        relative = 'examples/fe_walter/coupled/outputs/' + name
        assert (downloads / name).read_bytes() == (ROOT / relative).read_bytes(), relative
    # PNG follows the existing image publication path, outside the download map.
    png = 'examples/fe_walter/coupled/outputs/2016/pool_release.png'
    assert (output / png).read_bytes() == (ROOT / png).read_bytes()
    for name in ('llm_available_reply.txt', 'llm_knowledge_reply.txt'):
        relative = 'examples/fe_walter/coupled/outputs/2016/' + name
        assert (output / relative).read_bytes() == (ROOT / relative).read_bytes()
    import os
    for page, names in (
        ('examples/fe_walter/coupled/README.md', current),
        ('tutorials/fe_walter.md', (
            'daily.csv', 'summary.json', 'pins.json',
            'llm_available_decision.json', 'llm_knowledge_decision.json',
        )),
    ):
        published_page = output / page
        text = published_page.read_text(encoding='utf-8')
        for name in names:
            target = downloads / ('2016-' + name)
            href = Path(os.path.relpath(target, published_page.parent)).as_posix()
            assert '](' + href + ')' in text, (page, name)
