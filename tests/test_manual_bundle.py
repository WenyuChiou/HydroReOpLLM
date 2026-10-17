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
