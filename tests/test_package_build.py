from pathlib import Path

import pytest
from setuptools import Distribution
from setuptools.errors import OptionError

from scripts import package_build


def _command(tmp_path):
    distribution = Distribution({
        "name": "fresh-wheel-test", "version": "1", "packages": ["sample"]
    })
    stale_build = distribution.get_command_obj("build")
    stale_build.build_base = str(tmp_path / "build")
    stale_build.ensure_finalized()
    stale_build_py = distribution.get_command_obj("build_py")
    stale_build_py.build_lib = str(tmp_path / "build" / "lib")
    stale_build_py.ensure_finalized()
    command = package_build.FreshWheel(distribution)
    command.ensure_finalized()
    return command, distribution, stale_build, stale_build_py


@pytest.mark.parametrize("fail", (False, True))
def test_wheel_uses_fresh_private_build_tree_and_always_cleans_up(tmp_path, monkeypatch, fail):
    old_build = tmp_path / "build"
    old_build.mkdir()
    sentinel = old_build / "stale-module.py"
    sentinel.write_text("must survive", encoding="utf-8")
    command, distribution, stale_build, stale_build_py = _command(tmp_path)
    observed = {}

    def inspect_private_staging(active):
        build = distribution.get_command_obj("build")
        build_py = distribution.get_command_obj("build_py")
        observed.update(
            root=Path(build.build_base).parent,
            build_base=Path(build.build_base),
            bdist_dir=Path(active.bdist_dir),
            build_py_lib=build_py.build_lib,
            build_finalized=build.finalized,
            build_py_finalized=build_py.finalized,
        )
        assert build is stale_build
        assert build_py is stale_build_py
        assert observed["root"].name.startswith("hydroopslm-wheel-")
        assert observed["build_base"] == observed["root"] / "build"
        assert observed["bdist_dir"] == observed["root"] / "wheel"
        assert not build.finalized
        assert not build_py.finalized
        build.ensure_finalized()
        build_py.ensure_finalized()
        assert Path(build_py.build_lib) == observed["build_base"] / "lib"
        if fail:
            raise RuntimeError("synthetic wheel failure")

    monkeypatch.setattr(package_build._bdist_wheel, "run", inspect_private_staging)
    if fail:
        with pytest.raises(RuntimeError, match="synthetic wheel failure"):
            command.run()
    else:
        command.run()

    assert not observed["root"].exists()
    assert sentinel.read_text(encoding="utf-8") == "must survive"


def test_skip_build_is_rejected_before_creating_staging(tmp_path, monkeypatch):
    command, *_ = _command(tmp_path)
    command.skip_build = True
    entered = []

    class UnexpectedTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            entered.append((args, kwargs))

    monkeypatch.setattr(package_build, "TemporaryDirectory", UnexpectedTemporaryDirectory)
    with pytest.raises(OptionError, match="does not support --skip-build"):
        command.run()
    assert entered == []
