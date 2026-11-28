"""Backward-compatible import aliasing for reorganized subpackages.

Legacy flat module names (e.g. ``llm_reservoir_agent.workflow``) resolve directly to the
identical canonical module object in ``sys.modules``, preserving ``unittest.mock.patch``
and ``isinstance`` identity without leaving wrapper files in the package root.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from types import ModuleType

LEGACY_MODULE_MAP: dict[str, str] = {
    "configuration": "llm_reservoir_agent.config.loader",
    "agent_configuration": "llm_reservoir_agent.config.agent_config",
    "case": "llm_reservoir_agent.config.case",
    "time_axis": "llm_reservoir_agent.config.time_axis",
    "time_config": "llm_reservoir_agent.config.time_config",
    "extensions": "llm_reservoir_agent.config.extensions",
    "runtime": "llm_reservoir_agent.config.runtime_paths",
    "coupled": "llm_reservoir_agent.hydrology.coupled",
    "weather": "llm_reservoir_agent.hydrology.weather",
    "physics": "llm_reservoir_agent.hydrology.physics",
    "passive": "llm_reservoir_agent.hydrology.passive",
    "network": "llm_reservoir_agent.hydrology.network",
    "interval_network": "llm_reservoir_agent.hydrology.interval_network",
    "downstream": "llm_reservoir_agent.hydrology.downstream",
    "balance": "llm_reservoir_agent.hydrology.balance",
    "contracts": "llm_reservoir_agent.operators.contracts",
    "agent": "llm_reservoir_agent.operators.agent",
    "policy_adapter": "llm_reservoir_agent.operators.policy_adapter",
    "policies": "llm_reservoir_agent.operators.policies",
    "rule_based": "llm_reservoir_agent.operators.rule_based",
    "benchmark": "llm_reservoir_agent.operators.hanasaki",
    "benchmark_config": "llm_reservoir_agent.operators.hanasaki_config",
    "prompt": "llm_reservoir_agent.operators.prompt",
    "context": "llm_reservoir_agent.operators.context",
    "providers": "llm_reservoir_agent.operators.providers",
    "configured_backend": "llm_reservoir_agent.operators.llm_backend",
    "information_runtime": "llm_reservoir_agent.information.runtime",
    "information_verification": "llm_reservoir_agent.information.verify",
    "workflow": "llm_reservoir_agent.simulation.workflow",
    "experiment": "llm_reservoir_agent.simulation.runner",
    "recovery": "llm_reservoir_agent.simulation.recovery",
    "temporal_output": "llm_reservoir_agent.simulation.temporal",
    "trace": "llm_reservoir_agent.simulation.trace",
    "runtime_provenance": "llm_reservoir_agent.simulation.provenance",
    "audit": "llm_reservoir_agent.simulation.audit",
    "auditor": "llm_reservoir_agent.simulation.auditor",
    "configured_audit": "llm_reservoir_agent.simulation.configured_audit",
    "outcome": "llm_reservoir_agent.simulation.outcome",
    "verification": "llm_reservoir_agent.simulation.verification",
}


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target: str) -> None:
        self.target = target
        self._saved_spec = None

    def create_module(self, spec):
        canonical = importlib.import_module(self.target)
        # Preserve canonical __spec__ across module_from_spec() overwriting module.__spec__.
        self._saved_spec = getattr(canonical, "__spec__", None)
        short = spec.name.rpartition(".")[2]
        pkg = sys.modules.get("llm_reservoir_agent")
        if pkg is not None:
            setattr(pkg, short, canonical)
        return canonical

    def exec_module(self, module: ModuleType) -> None:
        if self._saved_spec is not None:
            module.__spec__ = self._saved_spec
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        prefix = "llm_reservoir_agent."
        if not fullname.startswith(prefix):
            return None
        short = fullname[len(prefix):]
        canonical_name = LEGACY_MODULE_MAP.get(short)
        if canonical_name is None:
            return None
        return importlib.util.spec_from_loader(fullname, _AliasLoader(canonical_name), is_package=False)


def install_legacy_aliases() -> None:
    """Install the idempotent MetaPathFinder ahead of default finders."""
    if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())
