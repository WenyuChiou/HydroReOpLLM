import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path[:0] = [str(SRC), str(ROOT)]


class ExampleBoundaryTests(unittest.TestCase):
    def test_core_sources_do_not_import_example_package_or_removed_package(self):
        violations = []
        for path in (SRC / "llm_reservoir_agent").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if name == "examples" or name.startswith("examples.") or name == "delaware_operations" or name.startswith("delaware_operations."):
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{name}")
        self.assertEqual(violations, [])

    def test_installed_core_import_isolated_from_repository_examples(self):
        code = f"""import importlib.abc
import sys
sys.path.insert(0, {str(SRC)!r})
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "examples" or fullname.startswith("examples.") or fullname.startswith("delaware_operations"):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
import llm_reservoir_agent
assert not any(name == "examples" or name.startswith("examples.") for name in sys.modules)
"""
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run([sys.executable, "-c", code], cwd=directory,
                                    env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_optional_anik_plugin_imports(self):
        from examples.fe_walter.extensions.anik_v3_7 import AnikPolicyAdapter, load_anik
        from llm_reservoir_agent.experiment import _adapter_implementation_files, _implementation_files

        self.assertTrue(callable(load_anik))
        self.assertEqual(AnikPolicyAdapter.policy_id, "anik_v3_7_dkp")
        from llm_reservoir_agent.extensions import extension_registry
        _, pins = extension_registry({"reference": str(ROOT/"examples/fe_walter/extensions/__init__.py")}, base_path=ROOT)
        self.assertIn(str(ROOT/"examples/fe_walter/extensions/anik_v3_7.py"), pins)
        implementation = _implementation_files()
        self.assertIn("experiment.py", implementation)
        self.assertNotIn("plugins/anik_v3_7.py", implementation)
        self.assertTrue(all("anik" not in path for path in implementation))

    def test_optional_historical_helper_imports(self):
        from tests.fixtures.fe_walter_legacy.historical import run_historical

        self.assertTrue(callable(run_historical))


if __name__ == "__main__":
    unittest.main()
