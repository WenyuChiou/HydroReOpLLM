"""Build commands that isolate generated wheel inputs from repository state."""
from pathlib import Path
from tempfile import TemporaryDirectory

from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
from setuptools.errors import OptionError


class FreshWheel(_bdist_wheel):
    """Build a wheel from a fresh private staging tree on every invocation."""

    def run(self):
        if self.skip_build:
            raise OptionError("FreshWheel does not support --skip-build")
        with TemporaryDirectory(prefix="hydroopslm-wheel-") as staging:
            private = Path(staging)
            build = self.reinitialize_command("build", reinit_subcommands=True)
            build.build_base = str(private / "build")
            self.bdist_dir = str(private / "wheel")
            super().run()
