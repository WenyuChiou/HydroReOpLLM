"""Tests for framework-neutral runtime environment and Ollama/cloud model provenance in summary.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from llm_reservoir_agent.runtime_provenance import (
    probe_live_model_snapshots,
    probe_ollama_runtime_snapshot,
)
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings, main, run_settings


def _write_llm_yaml_case(tmp_path: Path) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "sys.txt").write_text("Operate ResA carefully.", encoding="utf-8")
    (prompts_dir / "usr.txt").write_text("Inflow and storage: $observation", encoding="utf-8")
    inflows_path = tmp_path / "inflows.csv"
    inflows_path.write_text(
        "date,node,local_inflow_cms\n"
        "2021-01-01,N_IN,10.0\n"
        "2021-01-01,N_OUT,0.0\n"
        "2021-01-02,N_IN,12.0\n"
        "2021-01-02,N_OUT,0.0\n"
        "2021-01-03,N_IN,11.0\n"
        "2021-01-03,N_OUT,0.0\n",
        encoding="utf-8",
    )
    inflow_sha = hashlib.sha256(inflows_path.read_bytes()).hexdigest()
    case_doc = {
        "schema_version": "llm-reservoir-network-case.v1",
        "data_kind": "synthetic_fixture",
        "live_readiness": {"ready": True},
        "network": {
            "schema_version": "llm-reservoir-network.v1",
            "start_date": "2021-01-01",
            "reservoirs": {
                "ResA": {
                    "inflow_node": "N_IN",
                    "physical": {
                        "reservoir_id": "res_a",
                        "capacity_m3": 10_000_000.0,
                        "dead_storage_m3": 0.0,
                        "initial_storage_m3": 5_000_000.0,
                        "minimum_release_cms": 0.0,
                        "maximum_release_cms": 100.0,
                        "dt_seconds": 86400.0,
                    },
                }
            },
            "connections": [{"source": "ResA", "target": "N_OUT", "unit_hydrograph": [1.0]}],
            "outlet": "N_OUT",
        },
        "inflow_source": {"path": "inflows.csv", "sha256": inflow_sha, "format": "daily-node-local-cms.v1"},
    }
    (tmp_path / "case.json").write_text(json.dumps(case_doc, indent=2), encoding="utf-8")
    cfg = {
        "schema_version": "llm-reservoir-experiment.v1",
        "run_id": "runtime-provenance-test",
        "output": str(tmp_path / "run_out"),
        "case": "case.json",
        "start_date": "2021-01-01",
        "end_date": "2021-01-03",
        "max_calls": 10,
        "models": {
            "local_ollama": {
                "provider": "ollama",
                "model": "gemma4:12b",
                "base_url": "http://127.0.0.1:11434",
                "temperature": 0.0,
                "seed": 7,
                "max_tokens": 512,
                "num_ctx": 8192,
                "max_attempts": 1,
                "retry_delay_seconds": 0.0,
            },
            "cloud_backup": {
                "provider": "openai_compatible",
                "model": "gpt-4o",
                "base_url": "https://api.example.test/v1",
                "api_key_env": "TEST_PROVENANCE_API_KEY",
                "temperature": 0.0,
                "max_tokens": 512,
                "max_attempts": 1,
                "retry_delay_seconds": 0.0,
            },
        },
        "agents": {
            "res_a_agent": {
                "reservoir_id": "ResA",
                "type": "llm",
                "model_profile": "local_ollama",
                "prompt_file": "prompts/usr.txt",
                "customization": {
                    "system_prompt_file": "prompts/sys.txt",
                    "fallback_models": ["cloud_backup"],
                },
            }
        },
    }
    cfg_path = tmp_path / "experiment.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return cfg_path


def test_ollama_probe_caches_by_url_and_handles_offline():
    def always_fail(*_args):
        raise OSError("connection refused")

    unavail = probe_ollama_runtime_snapshot("http://127.0.0.1:11434", "gemma4:12b", fetcher=always_fail)
    assert unavail["probe_status"] == "unavailable"
    assert unavail["server_version"] is None

    probe_calls: list[tuple[str, str]] = []

    def counting_fetcher(method, url, payload, headers, timeout):
        probe_calls.append((method, url))
        if url.endswith("/api/version"):
            return {"version": "0.17.4"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "gemma4:12b", "digest": "sha256:" + ("c" * 64)}]}
        return {"details": {"quantization_level": "Q4_K_M", "parameter_size": "12.2B"}}

    agents = {
        "a1": {
            "reservoir": "Res1",
            "mode": "llm",
            "model": {"provider": "ollama", "model": "gemma4:12b", "base_url": "http://127.0.0.1:11434"},
            "fallback_models": [],
        },
        "a2": {
            "reservoir": "Res2",
            "mode": "llm",
            "model": {"provider": "ollama", "model": "gemma4:12b", "base_url": "http://127.0.0.1:11434/"},
            "fallback_models": [],
        },
        "a3": {
            "reservoir": "Res3",
            "mode": "offline",
            "model": {"provider": "ollama", "model": "gemma4:12b", "base_url": "http://127.0.0.1:11434"},
        },
    }
    snaps = probe_live_model_snapshots(agents, fetcher=counting_fetcher)
    assert set(snaps) == {"Res1", "Res2"}
    assert len(probe_calls) == 3
    assert snaps["Res1"]["primary"]["server_version"] == "0.17.4"
    assert snaps["Res2"]["primary"]["model_digest_sha256"] == "sha256:" + ("c" * 64)


def test_live_run_records_runtime_environment_in_summary_without_leaking_secrets(tmp_path, monkeypatch):
    secret = "sk-super-secret-do-not-persist"
    monkeypatch.setenv("TEST_PROVENANCE_API_KEY", secret)
    cfg_path = _write_llm_yaml_case(tmp_path)
    settings = load_settings(cfg_path)
    ollama_digest = "sha256:1278394b693672ac2799eadc9a83fd98259a6a88a40acfb1dcaa6c6fc895a606"

    def mock_probe(method, url, payload, headers, timeout):
        if url.endswith("/api/version"):
            return {"version": "0.40.6"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "gemma4:12b", "digest": ollama_digest, "size": 7_381_382_048}]}
        return {
            "details": {"family": "gemma4", "parameter_size": "12B", "quantization_level": "Q4_K_M", "format": "gguf"},
            "modelfile": "FROM gemma4:12b\n",
            "template": "{{ .Prompt }}",
        }

    call_idx = 0

    def mock_transport(url, payload, headers, timeout):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 1:
            raise ConnectionError("ollama busy")
        if call_idx == 2:
            return {
                "id": "resp-cloud-1",
                "model": "gpt-4o-2024-11-20",
                "system_fingerprint": "fp_abc123def4",
                "choices": [
                    {"message": {"content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0})}}
                ],
            }
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0})},
        }

    _, result = run_settings(settings, allow_network=True, transport=mock_transport, provenance_probe=mock_probe)
    output = tmp_path / "run_out"
    assert not (output / "odd_llm_manifest.json").exists()
    assert verify_run(output)["status"] == "PASS"

    summary_text = (output / "summary.json").read_text(encoding="utf-8")
    assert secret not in summary_text
    summary = json.loads(summary_text)["summary"]
    runtime_env = summary["runtime_environment"]
    assert set(runtime_env["key_dependencies"]) == {"numpy", "pandas", "scipy", "PyYAML", "deap", "matplotlib"}

    agent_env = runtime_env["agents"]["ResA"]
    assert agent_env["seed"] == 7
    assert agent_env["random_seed_configured"] is True
    assert agent_env["server_runtime_snapshot"]["primary"]["server_version"] == "0.40.6"
    assert agent_env["server_runtime_snapshot"]["primary"]["model_digest_sha256"] == ollama_digest
    assert agent_env["server_runtime_snapshot"]["primary"]["quantization_level"] == "Q4_K_M"
    assert agent_env["observed_model_versions"] == ["gemma4:12b", "gpt-4o-2024-11-20"]
    assert agent_env["observed_system_fingerprints"] == ["fp_abc123def4"]


def test_export_odd_cli_subcommand_is_removed():
    import pytest

    with pytest.raises(SystemExit):
        main(["export-odd", "runs/nonexistent"])
