"""Tests for ODD+LLM reproducibility manifests, verification, Markdown rendering, and CLI export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled
from llm_reservoir_agent.experiment import run_experiment
from llm_reservoir_agent.odd_llm import (
    ODD_LLM_SCHEMA_VERSION,
    build_odd_llm_manifest,
    export_odd_report,
    probe_live_model_snapshots,
    probe_ollama_runtime_snapshot,
    render_odd_llm_markdown,
)
from llm_reservoir_agent.verification import _OUTPUTS, verify_run
from llm_reservoir_agent.workflow import load_settings, main, run_settings
from tests.reservoir_fixtures import copy_coupled_fixture


ROOT = Path(__file__).resolve().parents[1]


def _write_llm_yaml_case(tmp_path: Path, *, with_fallback: bool = True) -> Path:
    """Create a minimal live-ready daily synthetic YAML experiment with knowledge, prompts, and models."""
    case = {
        "schema_version": "llm-reservoir-network-case.v1",
        "data_kind": "synthetic_fixture",
        "network": {
            "schema_version": "llm-reservoir-network.v1",
            "data_kind": "synthetic_fixture",
            "start_date": "2024-01-01",
            "reservoirs": {
                "ResA": {
                    "inflow_node": "InA",
                    "physical": {
                        "reservoir_id": "res_a",
                        "capacity_m3": 1_000_000.0,
                        "dead_storage_m3": 100_000.0,
                        "initial_storage_m3": 950_000.0,
                        "minimum_release_cms": 1.0,
                        "maximum_release_cms": 10.0,
                        "dt_seconds": 86400.0,
                    },
                }
            },
            "connections": [
                {"source": "ResA", "target": "Out", "unit_hydrograph": [1.0]}
            ],
            "outlet": "Out",
        },
        "inflow_records": [
            {"date": "2024-01-01", "local_inflow_cms": {"InA": 15.0, "Out": 0.0}},
            {"date": "2024-01-02", "local_inflow_cms": {"InA": 5.0, "Out": 0.0}},
            {"date": "2024-01-03", "local_inflow_cms": {"InA": 5.0, "Out": 0.0}},
        ],
    }
    (tmp_path / "case.json").write_text(json.dumps(case, indent=2), encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "sys.txt").write_text(
        "You are an expert reservoir operator for ResA. Follow operational rules strictly.",
        encoding="utf-8",
    )
    (prompts_dir / "usr.txt").write_text(
        "Obs: $observation\nKnowledge: $knowledge\nHistory: $completed_history\nVar: $station_note",
        encoding="utf-8",
    )
    (tmp_path / "ops_manual.md").write_text("# Operations Manual\nMaintain safe pool levels.\n", encoding="utf-8")

    models: dict[str, object] = {
        "primary": {
            "provider": "openai",
            "model": "gpt-test-primary",
            "base_url": "https://api.example.test/v1",
            "api_key_env": "TEST_ODD_API_KEY",
            "temperature": 0.2,
            "max_tokens": 256,
            "max_attempts": 2,
            "retry_delay_seconds": 0.0,
        }
    }
    if with_fallback:
        models["backup"] = {
            "provider": "ollama",
            "model": "gemma4:12b",
            "base_url": "http://127.0.0.1:11434",
            "temperature": 0.0,
            "seed": 7,
            "num_ctx": 4096,
            "think": False,
            "keep_alive": "5m",
            "max_attempts": 1,
            "retry_delay_seconds": 0.0,
        }

    agent: dict[str, object] = {
        "reservoir": "ResA",
        "mode": "llm",
        "model": "primary",
        "prompt": {"system": "prompts/sys.txt", "user": "prompts/usr.txt"},
        "prompt_version": "2.1",
        "knowledge": {"ops_manual": "ops_manual.md"},
        "prompt_variables": {"station_note": "Gauge 001"},
        "history_steps": 2,
        "auditors": ["bounds"],
    }
    if with_fallback:
        agent["fallback_models"] = ["backup"]

    experiment_cfg = {
        "schema_version": "llm-reservoir-experiment.v1",
        "case": "case.json",
        "run_id": "odd-llm-telemetry-test",
        "output": "run_out",
        "start_date": "2024-01-01",
        "end_date": "2024-01-03",
        "max_calls": 10,
        "models": models,
        "auditors": {"bounds": {"type": "release_bounds", "version": "1"}},
        "agents": {"res_a_agent": agent},
    }
    cfg_path = tmp_path / "experiment.yaml"
    cfg_path.write_text(yaml.safe_dump(experiment_cfg, sort_keys=False), encoding="utf-8")
    return cfg_path


def test_odd_llm_manifest_persisted_verified_and_redacted(tmp_path, monkeypatch):
    secret = "sk-super-secret-token-987654321"
    monkeypatch.setenv("TEST_ODD_API_KEY", secret)
    cfg_path = _write_llm_yaml_case(tmp_path, with_fallback=True)
    settings = load_settings(cfg_path)

    call_index = 0

    def mock_transport(url, payload, headers, timeout):
        nonlocal call_index
        call_index += 1
        # Day 1, attempt 1: fail with ConnectionError -> triggers retry on primary
        if call_index == 1:
            raise ConnectionError("transient timeout")
        # Day 1, attempt 2 (primary succeeds): request 20 m3/s (> max 10 -> clipping!) and high inflow triggers spill
        if call_index == 2:
            return {
                "id": "req-day1",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 20.0}),
                            }
                        ],
                    }
                ],
            }
        # Day 2, attempts 1 & 2 on primary fail -> triggers fallback to ollama backup!
        if call_index in (3, 4):
            raise ConnectionError("primary down")
        if call_index == 5:
            return {
                "model": "gemma4:12b",
                "done": True,
                "done_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0}),
                },
            }
        # Day 3, primary succeeds cleanly with feasible release
        return {
            "id": "req-day3",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0}),
                        }
                    ],
                }
            ],
        }

    _, result = run_settings(settings, allow_network=True, transport=mock_transport)
    output = tmp_path / "run_out"
    manifest_path = output / "odd_llm_manifest.json"
    assert manifest_path.is_file()

    # Core output_files unchanged; manifest hash stored in additional_output_files
    assert set(result["summary"]["output_files"]) == _OUTPUTS
    expected_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert result["summary"]["additional_output_files"]["odd_llm_manifest.json"] == expected_sha

    # Verification passes without changing verify_run keys
    verified = verify_run(output)
    assert verified["status"] == "PASS"
    assert verified["days"] == 3

    # Redaction check: raw secret must never appear in manifest or rendered markdown
    raw_text = manifest_path.read_text(encoding="utf-8")
    assert secret not in raw_text
    manifest = json.loads(raw_text)
    md = render_odd_llm_markdown(manifest)
    assert secret not in md

    assert manifest["schema_version"] == ODD_LLM_SCHEMA_VERSION
    assert manifest["run_id"] == "odd-llm-telemetry-test"
    assert manifest["time_axis"] == {
        "step_type": "daily",
        "dt_seconds": 86400.0,
        "start": "2024-01-01",
        "end": "2024-01-03",
        "steps": 3,
    }
    assert set(manifest["blocks"]) == {
        "A_cognitive_architecture",
        "B_identity",
        "C_inference_configuration",
        "D_behavioral_submodel",
        "E_validation",
    }

    # Block A
    a_res = manifest["blocks"]["A_cognitive_architecture"]["ResA"]
    assert a_res["reservoir_id"] == "res_a"
    assert a_res["agent_id"] == "res_a_agent"
    assert a_res["agent_type"] == "llm"
    assert a_res["working_memory"]["history_steps"] == 2
    assert a_res["working_memory"]["previous_transition_included"] is True
    assert a_res["long_term_knowledge"]["package_ids"] == ["ops_manual"]
    assert "ops_manual" in a_res["long_term_knowledge"]["sha256"]
    assert a_res["action_space"]["unit"] == "m3/s"
    assert a_res["action_space"]["maximum_release_cms"] == 10.0

    # Block B
    b_res = manifest["blocks"]["B_identity"]["ResA"]
    assert b_res["prompt_version"] == "2.1"
    assert b_res["system_prompt_file"] == "prompts/sys.txt"
    assert b_res["user_prompt_file"] == "prompts/usr.txt"
    assert "expert reservoir operator" in (b_res["system_prompt_preview"] or "")
    assert b_res["source_files_pinned_count"] >= 4
    assert str(tmp_path) not in raw_text

    # Block C
    c_block = manifest["blocks"]["C_inference_configuration"]
    assert c_block["runtime"]["hydrocnhs_core_commit"]
    assert c_block["runtime"]["hydroreopllm_version"]
    c_agent = c_block["agents"]["ResA"]
    assert c_agent["provider"] == "openai"
    assert c_agent["model"] == "gpt-test-primary"
    assert c_agent["api_key_env"] == "TEST_ODD_API_KEY"
    assert c_agent["automatic_retry"] is True
    assert c_agent["offline_only"] is False
    assert len(c_agent["fallback_models"]) == 1
    assert c_agent["fallback_models"][0]["model"] == "gemma4:12b"
    assert c_agent["fallback_models"][0]["seed"] == 7

    # Block D
    d_block = manifest["blocks"]["D_behavioral_submodel"]
    assert d_block["signature"]["ResA"]["response_schema"] == "reservoir-action.v1"
    assert len(d_block["signature"]["ResA"]["auditor_specs"]) == 1
    assert d_block["binding"]["ResA"]["history_steps"] == 2
    assert "station_note" in d_block["binding"]["ResA"]["prompt_variable_names"]
    res = d_block["resolution"]
    assert res["total_decisions"] == 3
    assert res["observed_network_calls"] == 6
    assert res["provider_started_attempts"] == 6
    assert res["provider_failed_attempts"] == 3
    assert res["retry_attempts"] == 3
    assert res["fallback_served_decisions"] == 1
    assert res["fallback_used"] is True
    assert res["physical_clipping_steps"] == 1
    assert res["physical_clipping_rate"] == pytest.approx(1 / 3, abs=1e-5)
    assert res["spill_steps"] >= 1

    # Block E
    e_block = manifest["blocks"]["E_validation"]
    assert e_block["verification_command"] == "reservoir-experiment verify <output>"
    assert set(e_block["output_files_sha256"]) == _OUTPUTS
    assert e_block["provider_attempts_sha256"] is not None
    assert e_block["offline_replay_capable"] is True

    # Markdown report checks
    for heading in (
        "## Agents Summary",
        "## Block A — Cognitive Architecture",
        "## Block B — Identity",
        "## Block C — Inference Configuration",
        "## Block D — Behavioral Submodel",
        "### Empirical Resolution Telemetry",
        "## Block E — Validation & SHA-256 Verification Summary",
    ):
        assert heading in md


def test_verification_backward_compatible_and_detects_manifest_tampering(tmp_path):
    """Historical runs without odd_llm_manifest.json still pass; tampered manifests fail."""
    config = {
        "schema_version": "llm-reservoir-network.v3",
        "data_kind": "synthetic_fixture",
        "start_time": "2020-01-01T00:00:00Z",
        "dt_seconds": 3600,
        "outlets": ["Outlet"],
        "reservoirs": {
            "PassiveRes": {
                "inflow_node": "Inlet",
                "operation_mode": "passive_outlet",
                "physical": {
                    "reservoir_id": "passive_1",
                    "capacity_m3": 1_000_000.0,
                    "dead_storage_m3": 0.0,
                    "initial_storage_m3": 100_000.0,
                    "minimum_release_cms": 0.0,
                    "maximum_release_cms": 50.0,
                    "dt_seconds": 3600,
                },
                "passive_outlet": {
                    "schema_version": "passive-storage-discharge.v1",
                    "storage_m3": [0.0, 1_000_000.0],
                    "discharge_cms": [0.0, 20.0],
                    "provenance": {"source": "synthetic"},
                },
            }
        },
        "connections": [{"source": "PassiveRes", "target": "Outlet", "unit_hydrograph": [1.0]}],
    }
    rows = [
        {"timestamp": f"2020-01-01T0{i}:00:00Z", "local_inflow_cms": {"Inlet": 2.0, "Outlet": 0.0}}
        for i in range(3)
    ]
    output = tmp_path / "hourly-passive"
    run_experiment(config, rows, {}, output=output, run_id="hourly-passive")

    # Verify passive + interval classification
    saved = json.loads((output / "odd_llm_manifest.json").read_text(encoding="utf-8"))
    assert saved["time_axis"]["step_type"] == "interval"
    assert saved["time_axis"]["dt_seconds"] == 3600.0
    assert saved["blocks"]["A_cognitive_architecture"]["PassiveRes"]["agent_type"] == "passive_outlet"
    assert saved["blocks"]["C_inference_configuration"]["agents"]["PassiveRes"]["offline_only"] is True
    assert verify_run(output, require_offline=True)["status"] == "PASS"

    # 1. Tamper bytes -> hash mismatch
    manifest_file = output / "odd_llm_manifest.json"
    original_bytes = manifest_file.read_bytes()
    manifest_file.write_bytes(original_bytes + b" ")
    with pytest.raises(ValueError, match="ODD\\+LLM manifest hash mismatch"):
        verify_run(output, require_offline=True)

    # 2. Tamper schema_version AND update hash -> schema mismatch
    tampered = json.loads(original_bytes.decode("utf-8"))
    tampered["schema_version"] = "wrong.v99"
    manifest_file.write_text(json.dumps(tampered), encoding="utf-8")
    summary_doc = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    original_summary = (output / "summary.json").read_bytes()
    summary_doc["summary"]["additional_output_files"]["odd_llm_manifest.json"] = hashlib.sha256(
        manifest_file.read_bytes()
    ).hexdigest()
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(summary_doc), encoding="utf-8")
    with pytest.raises(ValueError, match="ODD\\+LLM manifest schema mismatch"):
        verify_run(output, require_offline=True)

    # 3. Tamper missing block AND update hash -> blocks mismatch
    tampered_blocks = json.loads(original_bytes.decode("utf-8"))
    del tampered_blocks["blocks"]["E_validation"]
    manifest_file.write_text(json.dumps(tampered_blocks), encoding="utf-8")
    summary_doc["summary"]["additional_output_files"]["odd_llm_manifest.json"] = hashlib.sha256(
        manifest_file.read_bytes()
    ).hexdigest()
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(summary_doc), encoding="utf-8")
    with pytest.raises(ValueError, match="ODD\\+LLM manifest blocks mismatch"):
        verify_run(output, require_offline=True)

    # 4. Historical run without odd_llm_manifest.json still passes verify_run AND export_odd_report computes on the fly
    manifest_file.unlink()
    legacy_summary = json.loads(original_summary.decode("utf-8"))
    legacy_summary["summary"].pop("additional_output_files", None)
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(legacy_summary), encoding="utf-8")
    assert verify_run(output, require_offline=True)["status"] == "PASS"

    computed_export = export_odd_report(output)
    assert computed_export["source"] == "computed"
    assert computed_export["schema_version"] == ODD_LLM_SCHEMA_VERSION
    assert computed_export["run_id"] == "hourly-passive"


def test_coupled_cli_export_odd_sanitizes_paths_and_writes_outputs(tmp_path, capsys):
    folder = copy_coupled_fixture(tmp_path / "example")
    cfg = folder / "experiment.yaml"
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    coupled_root = tmp_path / "coupled-run"
    data["output"] = str(coupled_root)
    cfg.write_text(yaml.safe_dump(data), encoding="utf-8")
    run_coupled(load_coupled_settings(cfg))

    assert verify_run(coupled_root, require_offline=True)["status"] == "PASS"

    json_out = tmp_path / "exports" / "odd.json"
    md_out = tmp_path / "exports" / "odd.md"
    rc = main([
        "export-odd",
        str(coupled_root),
        "--json-out",
        str(json_out),
        "--markdown-out",
        str(md_out),
    ])
    assert rc == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["schema_version"] == ODD_LLM_SCHEMA_VERSION
    assert stdout_payload["source"] == "saved"
    assert Path(stdout_payload["json_out"]) == json_out.resolve()
    assert Path(stdout_payload["markdown_out"]) == md_out.resolve()
    assert json_out.is_file()
    assert md_out.is_file()

    # Rebased absolute prompt paths in coupled settings must be sanitized to basenames
    manifest = json.loads(json_out.read_text(encoding="utf-8"))
    for b_entry in manifest["blocks"]["B_identity"].values():
        for field in ("system_prompt_file", "user_prompt_file"):
            val = b_entry[field]
            if val is not None:
                assert not Path(val).is_absolute()
                assert str(tmp_path) not in val
    md_text = md_out.read_text(encoding="utf-8")
    assert "# ODD+LLM Reproducibility Report:" in md_text
    assert "## Block E — Validation & SHA-256 Verification Summary" in md_text


def test_shipped_example_odd_llm_protocol_cards():
    fe_card = (ROOT / "examples" / "fe_walter" / "ODD_LLM.md").read_text(encoding="utf-8")
    for token in (
        "Block A",
        "Block B",
        "Block C",
        "Block D",
        "Block E",
        "dkp.md",
        "ollama-manifest.json",
        "replay.py",
        "export-odd",
    ):
        assert token in fe_card

    mr_card = (ROOT / "examples" / "multi_reservoir" / "ODD_LLM.md").read_text(encoding="utf-8")
    for token in (
        "Block A",
        "Block B",
        "Block C",
        "Block D",
        "Block E",
        "rule_curve.csv",
        "cv_summary.json",
        "replay.py",
        "export-odd",
    ):
        assert token in mr_card


def test_probe_ollama_runtime_snapshot_full_partial_and_unavailable():
    secret = "ollama-probe-secret-token-xyz"
    long_params = "temperature 0.7\n" + ("num_ctx 16384 " * 60)
    modelfile_text = "FROM gemma4:12b\nPARAMETER num_ctx 16384\n"
    template_text = "{{ .System }}\n{{ .Prompt }}"
    bare_digest = "a" * 64

    def full_fetcher(method, url, payload, headers, timeout):
        if method == "GET" and url.endswith("/api/version"):
            return {"version": "0.17.4"}
        if method == "GET" and url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "gemma4:latest",
                        "digest": bare_digest,
                        "size": 7_381_382_048,
                        "modified_at": "2026-04-01T12:00:00Z",
                    }
                ]
            }
        if method == "POST" and url.endswith("/api/show"):
            assert payload == {"name": "gemma4"}
            return {
                "details": {
                    "family": "gemma4",
                    "families": ["gemma4", "clip"],
                    "parameter_size": "12.2B",
                    "quantization_level": "Q4_K_M",
                    "format": "gguf",
                },
                "modelfile": modelfile_text,
                "template": template_text,
                "parameters": long_params,
            }
        raise AssertionError(f"unexpected probe call: {method} {url}")

    snap = probe_ollama_runtime_snapshot(
        "http://user:pass@127.0.0.1:11434",
        "gemma4",
        headers={"Authorization": f"Bearer {secret}"},
        fetcher=full_fetcher,
    )
    assert snap["provider"] == "ollama"
    assert snap["base_url"] == "http://127.0.0.1:11434"
    assert snap["requested_model"] == "gemma4"
    assert snap["probe_status"] == "ok"
    assert snap["probed_at_utc"].endswith("Z")
    assert snap["server_version"] == "0.17.4"
    assert snap["model_digest_sha256"] == f"sha256:{bare_digest}"
    assert snap["model_size_bytes"] == 7_381_382_048
    assert snap["modified_at"] == "2026-04-01T12:00:00Z"
    assert snap["model_family"] == "gemma4"
    assert snap["model_families"] == ["gemma4", "clip"]
    assert snap["parameter_size"] == "12.2B"
    assert snap["quantization_level"] == "Q4_K_M"
    assert snap["model_format"] == "gguf"
    assert snap["modelfile_sha256"] == hashlib.sha256(modelfile_text.encode("utf-8")).hexdigest()
    assert snap["template_sha256"] == hashlib.sha256(template_text.encode("utf-8")).hexdigest()
    assert snap["model_parameters_raw"] is not None
    assert len(snap["model_parameters_raw"]) <= 500
    assert secret not in json.dumps(snap)
    assert "user:pass" not in json.dumps(snap)

    # Partial failure: only /api/version succeeds -> "partial"
    def version_only_fetcher(method, url, payload, headers, timeout):
        if url.endswith("/api/version"):
            return {"version": "0.17.4"}
        raise ConnectionError("endpoint unreachable")

    partial = probe_ollama_runtime_snapshot("http://127.0.0.1:11434", "gemma4:12b", fetcher=version_only_fetcher)
    assert partial["probe_status"] == "partial"
    assert partial["server_version"] == "0.17.4"
    assert partial["model_digest_sha256"] is None

    # /api/tags fails, /api/show provides fallback digest & modified_at -> "ok"
    def show_fallback_fetcher(method, url, payload, headers, timeout):
        if url.endswith("/api/version"):
            return {"version": "0.18.0"}
        if url.endswith("/api/tags"):
            raise TimeoutError("tags timeout")
        if url.endswith("/api/show"):
            return {
                "digest": "sha256:" + ("b" * 64),
                "modified_at": "2026-05-01T00:00:00Z",
                "details": {"quantization_level": "Q8_0", "parameter_size": "27B"},
            }
        raise AssertionError("unexpected")

    fallback_ok = probe_ollama_runtime_snapshot("http://127.0.0.1:11434", "gemma4:27b", fetcher=show_fallback_fetcher)
    assert fallback_ok["probe_status"] == "ok"
    assert fallback_ok["model_digest_sha256"] == "sha256:" + ("b" * 64)
    assert fallback_ok["modified_at"] == "2026-05-01T00:00:00Z"
    assert fallback_ok["quantization_level"] == "Q8_0"

    # Full failure: all 3 fail -> "unavailable", never raises
    def always_fail(method, url, payload, headers, timeout):
        raise OSError("connection refused")

    unavail = probe_ollama_runtime_snapshot("http://127.0.0.1:11434", "gemma4:12b", fetcher=always_fail)
    assert unavail["probe_status"] == "unavailable"
    assert unavail["server_version"] is None
    assert unavail["model_digest_sha256"] is None

    # probe_live_model_snapshots caches per unique (base_url, model) and skips offline/non-ollama
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
        "a4": {
            "reservoir": "Res4",
            "mode": "llm",
            "model": {"provider": "openai", "model": "gpt-4o", "base_url": "https://api.openai.com/v1"},
            "fallback_models": [],
        },
    }
    snaps = probe_live_model_snapshots(agents, fetcher=counting_fetcher)
    assert set(snaps) == {"Res1", "Res2"}
    assert len(probe_calls) == 3  # probed once, cached for Res2
    assert snaps["Res1"]["primary"]["server_version"] == "0.17.4"
    assert snaps["Res2"]["primary"]["model_digest_sha256"] == "sha256:" + ("c" * 64)


def test_live_run_persists_server_runtime_snapshots_and_exports_markdown(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TEST_ODD_API_KEY", "sk-test-live-provenance-key")
    cfg_path = _write_llm_yaml_case(tmp_path, with_fallback=True)
    # Make Ollama the primary with seed=7, temperature=0.0, and OpenAI a fallback (or test both!)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["agents"]["res_a_agent"]["model"] = "backup"
    cfg["agents"]["res_a_agent"]["fallback_models"] = ["primary"]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    settings = load_settings(cfg_path)

    ollama_digest = "sha256:1278394b693672ac2799eadc9a83fd98259a6a88a40acfb1dcaa6c6fc895a606"
    probe_urls: list[str] = []

    def mock_probe(method, url, payload, headers, timeout):
        probe_urls.append(f"{method} {url}")
        if url.endswith("/api/version"):
            return {"version": "0.17.4"}
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "gemma4:12b",
                        "digest": ollama_digest,
                        "size": 7_381_382_048,
                        "modified_at": "2026-04-10T08:30:00Z",
                    }
                ]
            }
        if url.endswith("/api/show"):
            return {
                "details": {
                    "family": "gemma4",
                    "families": ["gemma4"],
                    "parameter_size": "12.2B",
                    "quantization_level": "Q4_K_M",
                    "format": "gguf",
                },
                "modelfile": "FROM gemma4:12b\n",
                "template": "{{ .Prompt }}",
                "parameters": "temperature 0\nseed 7",
            }
        raise AssertionError(f"unexpected probe: {method} {url}")

    call_idx = 0

    def mock_transport(url, payload, headers, timeout):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 1:
            # Primary Ollama fails once -> triggers fallback to OpenAI!
            raise ConnectionError("ollama busy")
        if call_idx == 2:
            # Fallback OpenAI succeeds with immutable model snapshot + system_fingerprint
            return {
                "id": "resp-openai-1",
                "status": "completed",
                "model": "gpt-4o-2024-11-20",
                "system_fingerprint": "fp_abc123def4",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0}),
                            }
                        ],
                    }
                ],
            }
        # Remaining days: primary Ollama succeeds
        return {
            "model": "gemma4:12b",
            "done": True,
            "done_reason": "stop",
            "message": {
                "role": "assistant",
                "content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0}),
            },
        }

    _, result = run_settings(
        settings,
        allow_network=True,
        transport=mock_transport,
        provenance_probe=mock_probe,
    )
    output = tmp_path / "run_out"
    assert len(probe_urls) == 3

    # Probing must NOT alter observed_network_calls or provider_attempts.jsonl
    assert result["summary"]["observed_network_calls"] == 4
    verified = verify_run(output)
    assert verified["status"] == "PASS"

    # experiment.json provenance holds server_runtime_snapshots
    exp_doc = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
    assert "server_runtime_snapshots" in exp_doc["provenance"]
    assert exp_doc["provenance"]["server_runtime_snapshots"]["ResA"]["primary"]["server_version"] == "0.17.4"

    # odd_llm_manifest.json Block C holds runtime metadata, snapshot, observed versions & fingerprints
    manifest = json.loads((output / "odd_llm_manifest.json").read_text(encoding="utf-8"))
    c_runtime = manifest["blocks"]["C_inference_configuration"]["runtime"]
    assert c_runtime["deterministic_physics"] is True
    assert c_runtime["python_implementation"]
    assert c_runtime["machine"]
    assert set(c_runtime["key_dependencies"]) == {"numpy", "pandas", "scipy", "PyYAML", "deap", "matplotlib"}
    assert c_runtime["key_dependencies"]["numpy"] is not None
    assert c_runtime["key_dependencies"]["PyYAML"] is not None

    c_agent = manifest["blocks"]["C_inference_configuration"]["agents"]["ResA"]
    assert c_agent["random_seed_configured"] is True
    assert c_agent["deterministic_decoding_requested"] is True
    assert c_agent["server_runtime_snapshot"]["primary"]["server_version"] == "0.17.4"
    assert c_agent["server_runtime_snapshot"]["primary"]["model_digest_sha256"] == ollama_digest
    assert c_agent["server_runtime_snapshot"]["primary"]["quantization_level"] == "Q4_K_M"
    assert c_agent["server_runtime_snapshot"]["primary"]["parameter_size"] == "12.2B"
    assert c_agent["observed_model_versions"] == ["gemma4:12b", "gpt-4o-2024-11-20"]
    assert c_agent["observed_system_fingerprints"] == ["fp_abc123def4"]

    # export-odd CLI Markdown contains Ollama version, sha256: digest, quantization, and seed
    md_out = tmp_path / "exported_odd.md"
    rc = main(["export-odd", str(output), "--markdown-out", str(md_out)])
    assert rc == 0
    _ = capsys.readouterr()
    md_text = md_out.read_text(encoding="utf-8")
    for token in (
        "0.17.4",
        ollama_digest,
        "Q4_K_M",
        "12.2B",
        "7",
        "gpt-4o-2024-11-20",
        "fp_abc123def4",
        "Deterministic Physics",
        "Key Dependencies",
        "Deterministic Decoding Requested",
    ):
        assert token in md_text


def test_observed_model_versions_and_fingerprints_openai_and_gemini(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_ODD_API_KEY", "sk-test-gemini-openai")
    cfg_path = _write_llm_yaml_case(tmp_path, with_fallback=False)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    # Primary: Gemini (no seed), Fallback: OpenAI-compatible (seed=42, temp=0.7 -> non-deterministic decoding)
    cfg["models"]["gemini_primary"] = {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key_env": "TEST_ODD_API_KEY",
        "temperature": 0.0,
        "max_tokens": 256,
        "max_attempts": 1,
        "retry_delay_seconds": 0.0,
    }
    cfg["models"]["openai_fb"] = {
        "provider": "openai_compatible",
        "model": "gpt-4o",
        "base_url": "https://api.example.test/v1",
        "api_key_env": "TEST_ODD_API_KEY",
        "temperature": 0.7,
        "seed": 42,
        "max_tokens": 256,
        "max_attempts": 1,
        "retry_delay_seconds": 0.0,
    }
    cfg["agents"]["res_a_agent"]["model"] = "gemini_primary"
    cfg["agents"]["res_a_agent"]["fallback_models"] = ["openai_fb"]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    settings = load_settings(cfg_path)

    call_idx = 0

    def mock_transport(url, payload, headers, timeout):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 1:
            return {
                "responseId": "gem-resp-1",
                "modelVersion": "gemini-2.5-flash-001",
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {"text": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0})}
                            ]
                        },
                    }
                ],
            }
        if call_idx == 2:
            # Force fallback to openai_compatible on Day 2
            raise ConnectionError("gemini transient failure")
        if call_idx == 3:
            return {
                "id": "chatcmpl-2",
                "model": "gpt-4o-2024-11-20",
                "system_fingerprint": "fp_9876543210",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0}),
                        },
                    }
                ],
            }
        return {
            "responseId": "gem-resp-3",
            "modelVersion": "gemini-2.5-flash-002",
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"text": json.dumps({"schema_version": "reservoir-action.v1", "release_cms": 5.0})}
                        ]
                    },
                }
            ],
        }

    run_settings(settings, allow_network=True, transport=mock_transport)
    output = tmp_path / "run_out"
    manifest = json.loads((output / "odd_llm_manifest.json").read_text(encoding="utf-8"))
    c_agent = manifest["blocks"]["C_inference_configuration"]["agents"]["ResA"]
    assert c_agent["observed_model_versions"] == [
        "gemini-2.5-flash-001",
        "gemini-2.5-flash-002",
        "gpt-4o-2024-11-20",
    ]
    assert c_agent["observed_system_fingerprints"] == ["fp_9876543210"]
    # Primary Gemini has temperature=0.0 but no seed configured -> random_seed_configured=False, deterministic=False
    assert c_agent["random_seed_configured"] is False
    assert c_agent["deterministic_decoding_requested"] is False
    assert c_agent["server_runtime_snapshot"] is None

    # Also verify harvesting still works from raw/*.json alone if provider_attempts.jsonl is absent
    (output / "provider_attempts.jsonl").unlink()
    rebuilt = build_odd_llm_manifest(output)
    rebuilt_agent = rebuilt["blocks"]["C_inference_configuration"]["agents"]["ResA"]
    assert rebuilt_agent["observed_model_versions"] == [
        "gemini-2.5-flash-001",
        "gemini-2.5-flash-002",
        "gpt-4o-2024-11-20",
    ]
    assert rebuilt_agent["observed_system_fingerprints"] == ["fp_9876543210"]


def test_offline_run_skips_probing_and_sets_null_server_runtime_snapshot(tmp_path):
    cfg_path = _write_llm_yaml_case(tmp_path, with_fallback=False)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["agents"]["res_a_agent"]["mode"] = "offline"
    cfg["agents"]["res_a_agent"]["release_cms"] = 5.0
    cfg["agents"]["res_a_agent"].pop("model", None)
    cfg["max_calls"] = 0
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    settings = load_settings(cfg_path)

    probe_calls = 0

    def spy_probe(method, url, payload, headers, timeout):
        nonlocal probe_calls
        probe_calls += 1
        return {"version": "should-never-be-called"}

    run_settings(settings, allow_network=False, provenance_probe=spy_probe)
    assert probe_calls == 0

    output = tmp_path / "run_out"
    assert verify_run(output, require_offline=True)["status"] == "PASS"
    exp_doc = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
    assert "server_runtime_snapshots" not in exp_doc["provenance"]

    manifest = json.loads((output / "odd_llm_manifest.json").read_text(encoding="utf-8"))
    c_runtime = manifest["blocks"]["C_inference_configuration"]["runtime"]
    assert c_runtime["deterministic_physics"] is True
    assert set(c_runtime["key_dependencies"]) == {"numpy", "pandas", "scipy", "PyYAML", "deap", "matplotlib"}

    c_agent = manifest["blocks"]["C_inference_configuration"]["agents"]["ResA"]
    assert c_agent["offline_only"] is True
    assert c_agent["server_runtime_snapshot"] is None
    assert c_agent["observed_model_versions"] == []
    assert c_agent["observed_system_fingerprints"] == []
    assert c_agent["random_seed_configured"] is False
    assert c_agent["deterministic_decoding_requested"] is True

