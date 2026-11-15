"""Record which model profile answered each decision: decisions.jsonl, summary counts, verification and resume."""
import hashlib
import json
from urllib.error import HTTPError

import pytest
import yaml

from llm_reservoir_agent.coupled import load_coupled_settings, prepared_experiment, run_coupled
from llm_reservoir_agent.recovery import resume_settings
from llm_reservoir_agent.trace import served_by_from_raw
from llm_reservoir_agent.verification import verify_run
from llm_reservoir_agent.workflow import load_settings
from tests.test_provider_workflow import reply, setup_case

KEYS = ("serving_profiles", "fallback_served_decisions", "fallback_used")


def with_backup(tmp_path, monkeypatch):
    """Primary profile is openai; one backup profile is anthropic."""
    monkeypatch.setenv("OFFLINE_PROVIDER_KEY", "never-save-this-secret")
    path, data = setup_case(tmp_path, "openai")
    data["models"]["backup"] = dict(data["models"]["chosen"], provider="anthropic", model="backup-model")
    agents_path = path.parent / "agents.llm.yaml"
    agents = yaml.safe_load(agents_path.read_text())
    agents["operator_a"]["customization"]["fallback_models"] = ["backup"]
    agents_path.write_text(yaml.safe_dump(agents))
    path.write_text(yaml.safe_dump(data))
    return path


def server_error(url):
    return HTTPError(url, 500, "fixture server error", {}, None)


def transport_failing(primary_fails):
    """Primary (openai) call number n fails with HTTP 500 when primary_fails(n); the backup always answers."""
    seen = {"primary": 0}

    def transport(url, payload, headers, timeout):
        if url.endswith("/responses"):
            seen["primary"] += 1
            if primary_fails(seen["primary"]):
                raise server_error(url)
            return reply("openai")
        return reply("anthropic")
    return transport


def decisions(output):
    return [json.loads(line) for line in (output / "decisions.jsonl").read_text().splitlines()]


def summary_of(output):
    return json.loads((output / "summary.json").read_text())["summary"]


def llm_decisions(output):
    return [event for event in decisions(output) if "served_by" in event]


def rewrite(output, mutate_decisions=None, mutate_summary=None):
    """Edit saved files and refresh the stream hash, so only the content check can catch the edit."""
    if mutate_decisions is not None:
        events = decisions(output)
        mutate_decisions(events)
        data = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events).encode()
        (output / "decisions.jsonl").write_bytes(data)
    result = json.loads((output / "summary.json").read_text())
    result["streams"]["decisions"]["sha256"] = hashlib.sha256((output / "decisions.jsonl").read_bytes()).hexdigest()
    if mutate_summary is not None:
        mutate_summary(result["summary"])
    for name in ("summary.json", "index.json"):
        (output / name).write_text(json.dumps(result))


def strip_served_by(events):
    for event in events:
        event.pop("served_by", None)


def test_every_decision_served_by_backup_is_recorded_and_counted(tmp_path, monkeypatch):
    path = with_backup(tmp_path, monkeypatch)
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport_failing(lambda n: True))
    output = tmp_path / "run/operation"
    served = llm_decisions(output)
    assert len(served) == 4
    assert all(event["served_by"] == {"profile": 1, "provider": "anthropic", "model": "backup-model"}
               for event in served)
    # The configured primary stays under provenance, and the audit event does not carry served_by.
    assert all(event["provenance"].get("model") != "backup-model" for event in served)
    assert all("served_by" not in json.loads(line) for line in (output / "audit.jsonl").read_text().splitlines())
    summary = summary_of(output)
    reservoir_id = served[0]["reservoir_id"]
    assert summary["serving_profiles"] == {reservoir_id: {"1": 4}}
    assert summary["fallback_served_decisions"] == 4
    assert summary["fallback_used"] is True
    verified = verify_run(output)
    assert verified["status"] == "PASS"
    assert verified["fallback_served_decisions"] == 4 and verified["fallback_used"] is True


def test_no_failure_records_primary_everywhere(tmp_path, monkeypatch):
    path = with_backup(tmp_path, monkeypatch)
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport_failing(lambda n: False))
    output = tmp_path / "run/operation"
    served = llm_decisions(output)
    assert len(served) == 4
    assert all(event["served_by"] == {"profile": 0, "provider": "openai", "model": "fixture-model"}
               for event in served)
    summary = summary_of(output)
    assert summary["serving_profiles"] == {served[0]["reservoir_id"]: {"0": 4}}
    assert summary["fallback_served_decisions"] == 0
    assert summary["fallback_used"] is False
    assert verify_run(output)["fallback_used"] is False


def test_mixed_run_counts_each_profile(tmp_path, monkeypatch):
    path = with_backup(tmp_path, monkeypatch)
    run_coupled(load_coupled_settings(path), allow_network=True,
                transport=transport_failing(lambda n: n in (2, 3)))
    output = tmp_path / "run/operation"
    assert [event["served_by"]["profile"] for event in llm_decisions(output)] == [0, 1, 1, 0]
    summary = summary_of(output)
    assert list(summary["serving_profiles"].values()) == [{"0": 2, "1": 2}]
    assert summary["fallback_served_decisions"] == 2 and summary["fallback_used"] is True
    assert verify_run(output)["fallback_served_decisions"] == 2


def test_changed_served_by_or_summary_count_fails_verification(tmp_path, monkeypatch):
    path = with_backup(tmp_path, monkeypatch)
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport_failing(lambda n: True))
    output = tmp_path / "run/operation"
    original = {name: (output / name).read_bytes() for name in ("decisions.jsonl", "summary.json", "index.json")}

    def restore():
        for name, data in original.items():
            (output / name).write_bytes(data)

    def claim_primary(events):
        next(event for event in events if "served_by" in event)["served_by"] = {
            "profile": 0, "provider": "openai", "model": "fixture-model"}
    rewrite(output, mutate_decisions=claim_primary)
    with pytest.raises(ValueError, match="served_by does not match"):
        verify_run(output)
    restore()
    rewrite(output, mutate_decisions=strip_served_by)
    with pytest.raises(ValueError, match="served_by does not match"):
        verify_run(output)
    restore()
    rewrite(output, mutate_summary=lambda s: s.update(fallback_served_decisions=0, fallback_used=False))
    with pytest.raises(ValueError, match="serving-profile counts"):
        verify_run(output)
    restore()
    rewrite(output, mutate_summary=lambda s: [s.pop(key) for key in KEYS])
    with pytest.raises(ValueError, match="serving-profile counts"):
        verify_run(output)
    restore()
    # JSON values that compare equal to 1 in Python must still be rejected, with the same clear message.
    for bad in (1.0, True, "1"):
        rewrite(output, mutate_decisions=lambda events, bad=bad: next(
            event for event in events if "served_by" in event)["served_by"].update(profile=bad))
        with pytest.raises(ValueError, match="served_by does not match"):
            verify_run(output)
        restore()
    assert verify_run(output)["status"] == "PASS"


def test_served_by_is_read_from_the_successful_attempt_only():
    attempts = [{"success": False, "profile": 0, "provider": "openai", "model": "a"},
                {"success": True, "profile": 2, "provider": "gemini", "model": "c"}]
    expected = {"profile": 2, "provider": "gemini", "model": "c"}
    assert served_by_from_raw({"attempts": attempts}) == expected
    assert served_by_from_raw({"backend_trace": {"attempts": attempts}}) == expected
    assert served_by_from_raw({"attempts": attempts[:1]}) is None
    assert served_by_from_raw({"model_used": False}) is None
    assert served_by_from_raw({"attempts": [{"success": True, "provider": "x", "model": "y"}]}) is None
    assert served_by_from_raw(None) is None


def test_rule_based_run_has_no_served_by_and_no_new_summary_keys(tmp_path):
    path, _ = setup_case(tmp_path)
    run_coupled(load_coupled_settings(path))
    output = tmp_path / "run/operation"
    assert all("served_by" not in event for event in decisions(output))
    assert not set(KEYS) & set(summary_of(output))
    assert not set(KEYS) & set(verify_run(output, require_offline=True))


def test_saved_run_without_the_fields_still_verifies(tmp_path, monkeypatch):
    # A run written before this change has neither served_by nor the summary keys.
    path = with_backup(tmp_path, monkeypatch)
    run_coupled(load_coupled_settings(path), allow_network=True, transport=transport_failing(lambda n: True))
    output = tmp_path / "run/operation"
    rewrite(output, mutate_decisions=strip_served_by, mutate_summary=lambda s: [s.pop(key) for key in KEYS])
    verified = verify_run(output)
    assert verified["status"] == "PASS" and not set(KEYS) & set(verified)
    assert verified["observed_network_calls"] == 8


def interrupted_fallback_run(tmp_path, monkeypatch):
    path = with_backup(tmp_path, monkeypatch)
    checked = load_coupled_settings(path)
    attempts = []

    def interrupted(url, payload, headers, timeout):
        attempts.append(url)
        if len(attempts) == 6:
            raise RuntimeError("injected process stop")
        if url.endswith("/responses"):
            raise server_error(url)
        return reply("anthropic")
    with pytest.raises(RuntimeError, match="injected process stop"):
        run_coupled(checked, allow_network=True, transport=interrupted)
    return checked, tmp_path / "run/operation"


def test_kill_and_resume_keeps_fields_and_counts(tmp_path, monkeypatch):
    checked, source = interrupted_fallback_run(tmp_path, monkeypatch)
    resume_settings(load_settings(prepared_experiment(checked)), source, output=tmp_path / "recovered",
                    run_id="recovered", allow_network=True, transport=transport_failing(lambda n: True))
    output = tmp_path / "recovered"
    served = llm_decisions(output)
    # The earlier decisions are replayed from saved evidence, the later ones are new.
    assert [event["served_by"]["profile"] for event in served] == [1, 1, 1, 1]
    summary = summary_of(output)
    assert summary["serving_profiles"] == {served[0]["reservoir_id"]: {"1": 4}}
    assert summary["fallback_served_decisions"] == 4 and summary["fallback_used"] is True
    assert verify_run(output)["fallback_served_decisions"] == 4


def test_resume_of_a_run_written_before_the_change_still_works(tmp_path, monkeypatch):
    checked, source = interrupted_fallback_run(tmp_path, monkeypatch)
    rewrite(source, mutate_decisions=strip_served_by)
    resume_settings(load_settings(prepared_experiment(checked)), source, output=tmp_path / "recovered",
                    run_id="recovered", allow_network=True, transport=transport_failing(lambda n: True))
    output = tmp_path / "recovered"
    assert summary_of(output)["fallback_served_decisions"] == 4
    assert verify_run(output)["status"] == "PASS"
