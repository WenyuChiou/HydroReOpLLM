"""F.E. Walter WAGF prototype: replayable traces, safe output folders and the model version record.

Every run here uses the real run and resume code, the real F.E. Walter case (10 to 12 days),
an injected scripted transport and a fake local model reader. Nothing contacts a server.
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
from http.client import RemoteDisconnected
from urllib.error import HTTPError, URLError

import pytest
import yaml

WAGF_ROOT = os.environ.get("WAGF_ROOT")
pytestmark = pytest.mark.skipif(not WAGF_ROOT, reason="WAGF_ROOT is not set")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "fe_walter_wagf"
DIGEST_A, DIGEST_B = "a" * 64, "b" * 64
FAKE_KEY = "sk-test-FAKE-KEY-0123456789abcdef"
DAYS = 10
CUT = 6  # the interrupted run dies when day index 6 (2021-01-07) asks for its first answer


@pytest.fixture(scope="module")
def extension():
    from llm_reservoir_agent.extensions import load_extension
    module, _ = load_extension(EXAMPLE / "extension" / "__init__.py", base_path=EXAMPLE)
    return module


@pytest.fixture(scope="module")
def ident(extension):
    return importlib.import_module(extension.__name__ + ".identity")


class LocalModel:
    """Stands in for the Ollama server: the nth read returns the nth digest (the last one repeats)."""

    def __init__(self, *digests):
        self.digests, self.calls, self.version = list(digests or [DIGEST_A]), 0, "0.99.0"

    def __call__(self, model):
        digest = self.digests[min(self.calls, len(self.digests) - 1)]
        self.calls += 1
        return {"digest": digest, "family": "gemma", "parameter_size": "12B",
                "quantization_level": "Q4_K_M", "version": self.version}


@pytest.fixture
def local(ident, monkeypatch):
    fake = LocalModel()
    monkeypatch.setattr(ident, "read_local_model", fake)
    return fake


# ---------------------------------------------------------------- scripted model

DAY_EVENTS = {1: ["bad", "hold"],        # governance retry (blocked in the checked arms)
              2: ["429", "hold"],        # transient HTTP 429, then success
              3: ["garbage", "hold"]}    # unreadable reply, then a good one
# Errors that are retried, so they can sit inside a saved day, and errors that stop the run.
TEMPORARY_ERRORS = {"timeout": TimeoutError("scripted"), "reset": ConnectionResetError("scripted"),
                    "aborted": ConnectionAbortedError("scripted"), "broken": BrokenPipeError("scripted"),
                    "disconnected": RemoteDisconnected("scripted"), "url-timeout": URLError(TimeoutError("scripted"))}
STOPPING_ERRORS = {"ssl": ssl.SSLEOFError("scripted"), "ctrl-c": KeyboardInterrupt()}


class Script:
    """Answers by day, so two runs that ask the same questions get the same answers."""

    def __init__(self, *, fail_from_day=None, cloud=False, day_events=None, provider=None):
        self.fail_from_day, self.provider = fail_from_day, provider or ("openai" if cloud else "ollama")
        self.events = DAY_EVENTS if day_events is None else day_events
        self.calls, self.day, self.inflow, self.used = [], None, None, {}

    def _body(self, text, n):
        if self.provider == "openai":
            return {"id": f"resp-{FAKE_KEY}", "model": "gpt-test-a" if n < 3 else "gpt-test-b",
                    "status": "completed", "usage": {"input_tokens": 1, "output_tokens": 1},
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
        if self.provider == "anthropic":
            return {"id": "msg-1", "model": "claude-test", "stop_reason": "end_turn",
                    "usage": {"input_tokens": 1, "output_tokens": 1}, "content": [{"type": "text", "text": text}]}
        if self.provider == "gemini":
            return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}],
                    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1}}
        if self.provider == "openai_compatible":
            return {"id": "chat-1", "model": "local-test", "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                    "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}
        return {"model": "gemma4:12b", "message": {"role": "assistant", "content": text}, "done": True,
                "done_reason": "stop", "prompt_eval_count": 1, "eval_count": 1}

    def __call__(self, url, payload, headers, timeout):
        if "contents" in payload:
            user = payload["contents"][-1]["parts"][0]["text"]
        else:
            user = payload["messages"][-1]["content"] if "messages" in payload else payload["input"][-1]["content"]
        found = re.match(r"Date: \d{4}-\d\d-(\d\d)", user)
        if found:
            self.day = int(found.group(1)) - 1
            self.inflow = float(re.search(r"Today's inflow: ([\d,.]+) cfs", user).group(1).replace(",", ""))
        if self.fail_from_day is not None and self.day >= self.fail_from_day:
            self.calls.append((self.day, "interrupt"))
            raise ConnectionRefusedError("scripted interruption")
        todo = self.events.get(self.day, ["hold"])
        position = self.used.get(self.day, 0)
        self.used[self.day] = position + 1
        kind = todo[min(position, len(todo) - 1)]
        self.calls.append((self.day, kind))
        if kind == "cut":
            raise ConnectionRefusedError("scripted interruption in the middle of a day")
        if kind in TEMPORARY_ERRORS or kind in STOPPING_ERRORS:
            raise {**TEMPORARY_ERRORS, **STOPPING_ERRORS}[kind]
        if kind in ("429", "503"):
            raise HTTPError(url, int(kind), "Busy", {}, None)
        if kind == "garbage":
            return self._body("this is not json", len(self.calls))
        answer = {"reasoning": "scripted", "decision": "raise_pool", "release_cfs": 20.0} if kind == "bad" else {
            "reasoning": "scripted", "decision": "hold_pool", "release_cfs": self.inflow}
        return self._body(json.dumps(answer), len(self.calls))


# ---------------------------------------------------------------- configuration and runs

def write_config(folder: Path, name: str, *, arm="full", days=DAYS, provider="ollama", pin=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    agents = yaml.safe_load((EXAMPLE / f"agents.{arm}.yaml").read_text(encoding="utf-8"))
    params = agents["fe_operator"]["customization"]["parameters"]
    for key in ("system_prompt", "dkp"):
        params["reference"][key] = str((EXAMPLE / params["reference"][key]).resolve())
    params["wagf"] = {"arm": arm, "output": str(folder / f"{name}-wagf")}
    if pin is not None:
        params["wagf"]["expected_model_digest"] = pin
    (folder / f"{name}.agents.yaml").write_text(yaml.safe_dump(agents), encoding="utf-8")
    profile = {"ollama": {"provider": "ollama", "model": "gemma4:12b", "base_url": "http://localhost:11434"},
               "openai": {"provider": "openai", "model": "gpt-test", "base_url": "https://api.openai.com/v1",
                          "api_key_env": "WAGF_TEST_FAKE_KEY"},
               "anthropic": {"provider": "anthropic", "model": "claude-test", "base_url": "https://api.anthropic.com",
                             "api_key_env": "WAGF_TEST_FAKE_KEY", "max_tokens": 1000},
               "gemini": {"provider": "gemini", "model": "gemini-test", "api_key_env": "WAGF_TEST_FAKE_KEY",
                          "base_url": "https://generativelanguage.googleapis.com/v1beta"},
               "openai_compatible": {"provider": "openai_compatible", "model": "local-test",
                                     "base_url": "http://localhost:8000/v1"}}[provider]
    profile.update(timeout_seconds=5, max_attempts=3, retry_delay_seconds=0, retryable_http_statuses=[429, 503])
    (folder / f"{name}.models.yaml").write_text(yaml.safe_dump({"reservoir_model": profile}), encoding="utf-8")
    run = {"schema_version": "llm-reservoir-experiment.v2", "run_id": name,
           "case": str(ROOT / "examples/fe_walter/operation/case.json"), "output": str(folder / name),
           "start_date": "2021-01-01", "end_date": f"2021-01-{days:02d}", "max_calls": None,
           "agents": {"file": f"{name}.agents.yaml"},
           "auditors": {"file": str(ROOT / "examples/fe_walter/coupled/auditors.yaml")},
           "models": {"file": f"{name}.models.yaml"},
           "extensions": {"wagf_governed": str(EXAMPLE / "extension/__init__.py")}}
    path = folder / f"{name}.yaml"
    path.write_text(yaml.safe_dump(run), encoding="utf-8")
    return path


def start(config: Path, transport):
    from llm_reservoir_agent.workflow import load_settings, run_settings
    return run_settings(load_settings(config), allow_network=True, transport=transport)


def resume(config: Path, source: Path, transport, run_id="resumed"):
    from llm_reservoir_agent.recovery import resume_settings
    from llm_reservoir_agent.workflow import load_settings
    return resume_settings(load_settings(config), source, output=source.with_name(run_id), run_id=run_id,
                           allow_network=True, transport=transport)


def interrupted(folder: Path, name: str, arm: str):
    """Run until day CUT asks for an answer and the connection fails. Returns config and source folder."""
    config = write_config(folder, name, arm=arm)
    with pytest.raises(RuntimeError, match="model provider failed"):
        start(config, Script(fail_from_day=CUT))
    return config, folder / name


def tree_hashes(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def decision_lines(wagf_folder: Path) -> list[str]:
    return (wagf_folder / "decisions.jsonl").read_text(encoding="utf-8").splitlines()


def audit_outcomes(wagf_folder: Path) -> list[dict]:
    with (wagf_folder / "reservoir_operator_governance_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
        return [{k: v for k, v in row.items() if "time" not in k.lower()} for row in csv.DictReader(handle)]


def recovery_of(folder: Path) -> dict:
    return json.loads((folder / "summary.json").read_text(encoding="utf-8"))["summary"]["recovery"]


def physics(records) -> str:
    return json.dumps(records["FEWalter"], sort_keys=True)


# ---------------------------------------------------------------- 1, 2, 3, 4: resume

@pytest.mark.parametrize("arm", ["full", "none"])
def test_interrupted_then_resumed_run_equals_an_uninterrupted_run(extension, local, tmp_path, arm):
    whole_config = write_config(tmp_path, "whole", arm=arm)
    whole_records, _ = start(whole_config, Script())

    config, source = interrupted(tmp_path, "part", arm)
    resumed_records, _ = resume(config, source, Script(), run_id="part-resumed")

    assert physics(resumed_records) == physics(whole_records)
    assert [r["action"] for r in resumed_records["FEWalter"]] == [r["action"] for r in whole_records["FEWalter"]]
    whole_wagf, part_wagf = tmp_path / "whole-wagf", tmp_path / "part-wagf"
    assert len(decision_lines(part_wagf)) == DAYS
    # Same day-by-day decisions as the whole run, apart from the folder name that the file does not hold.
    assert decision_lines(part_wagf) == decision_lines(whole_wagf)
    assert audit_outcomes(part_wagf) == audit_outcomes(whole_wagf)
    if arm == "full":
        by_day = [json.loads(line) for line in decision_lines(part_wagf)]
        assert by_day[1]["governance_retries"] == 1  # the retry before the interruption really happened
        assert any("release_below_minimum" in row["failed_rules"] for row in audit_outcomes(part_wagf))
    # The earlier WAGF files are kept next to the new ones.
    assert (tmp_path / "part-wagf.previous-1" / "decisions.jsonl").is_file()


def corrupt_like_a_hard_kill(source: Path, wagf_folder: Path):
    """No summary, a half-written last journal line, and a request that was sent but never answered."""
    (source / "summary.json").unlink()
    with (source / "decisions.jsonl").open("ab") as handle:
        handle.write(b'{"run_id": "part", "reservoir_id": "FEW')
    ledger = source / "provider_attempts.jsonl"
    lines = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    last = max(item["attempt"] for item in lines)
    template = next(item for item in lines if item["status"] == "STARTED")
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({**template, "attempt": last + 1, "status": "STARTED"}) + "\n")
    (wagf_folder / "audit_summary.json").unlink(missing_ok=True)
    with (wagf_folder / "decisions.jsonl").open("ab") as handle:
        handle.write(b'{"date": "2021-01-0')


def test_a_hard_killed_run_still_resumes_correctly(extension, local, tmp_path):
    whole_records, _ = start(write_config(tmp_path, "whole"), Script())
    config, source = interrupted(tmp_path, "part", "full")
    corrupt_like_a_hard_kill(source, tmp_path / "part-wagf")
    script = Script()
    resumed_records, _ = resume(config, source, script, run_id="part-resumed")
    assert physics(resumed_records) == physics(whole_records)
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")
    # The unanswered reservation counts against the budget, the half line stays in the source.
    recovery = recovery_of(tmp_path / "part-resumed")
    assert recovery["incomplete_tail_bytes_retained_in_source"]["decisions"] > 0
    assert recovery["prior_network_calls"] > recovery["replayed_provider_replies"]
    # The unfinished WAGF folder was kept whole.
    kept = tmp_path / "part-wagf.previous-1"
    assert kept.is_dir() and (kept / "decisions.jsonl").read_bytes().endswith(b'{"date": "2021-01-0')


def test_saved_days_make_no_new_network_calls(extension, local, tmp_path):
    config, source = interrupted(tmp_path, "part", "full")
    script = Script()
    resume(config, source, script, run_id="part-resumed")
    assert recovery_of(tmp_path / "part-resumed")["replayed_provider_replies"] == 9
    # Days 0 to 5 came from the saved replies: the model is first asked about day 6.
    assert script.calls[0][0] == CUT
    assert {day for day, _ in script.calls} == set(range(CUT, DAYS))
    assert len(script.calls) == DAYS - CUT


def test_a_day_that_ended_in_the_safe_release_replays_exactly(extension, local, tmp_path):
    events = {**DAY_EVENTS, 4: ["bad"]}  # every answer on this day is blocked, so the safe release is used
    start(write_config(tmp_path, "whole"), Script(day_events=events))
    config = write_config(tmp_path, "part")
    with pytest.raises(RuntimeError, match="model provider failed"):
        start(config, Script(fail_from_day=CUT, day_events=events))
    script = Script(day_events=events)
    resume(config, tmp_path / "part", script, run_id="part-resumed")
    days = [json.loads(line) for line in decision_lines(tmp_path / "part-wagf")]
    assert days[4]["fallback"] is not None and script.calls[0][0] == CUT
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")


def test_a_crash_in_the_middle_of_a_day_asks_that_day_again(extension, local, tmp_path):
    answered = {**DAY_EVENTS, CUT: ["bad", "hold"]}
    start(write_config(tmp_path, "whole"), Script(day_events=answered))
    config = write_config(tmp_path, "part")
    with pytest.raises(RuntimeError, match="model provider failed"):
        start(config, Script(day_events={**DAY_EVENTS, CUT: ["bad", "cut"]}))
    script = Script(day_events=answered)
    resume(config, tmp_path / "part", script, run_id="part-resumed")
    assert script.calls[:2] == [(CUT, "bad"), (CUT, "hold")]
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")


@pytest.mark.parametrize("empty_folder", [False, True])
def test_a_resume_without_the_earlier_wagf_output_is_refused_before_any_request(extension, local, tmp_path, empty_folder):
    config, source = interrupted(tmp_path, "part", "full")
    shutil.rmtree(tmp_path / "part-wagf")
    if empty_folder:
        (tmp_path / "part-wagf").mkdir()
    local.digests, local.calls = [DIGEST_B], 0
    script = Script()
    with pytest.raises(RuntimeError, match="cannot resume"):
        resume(config, source, script, run_id="first-try")
    assert script.calls == []
    # The refused attempt's own files must not vouch for the next attempt.
    with pytest.raises(ValueError, match="no readable"):
        resume(config, source, script, run_id="second-try")
    assert script.calls == []


@pytest.mark.parametrize("provider", ["ollama", "openai", "anthropic", "gemini", "openai_compatible"])
def test_every_model_provider_resumes_to_the_same_result(extension, local, tmp_path, monkeypatch, provider):
    monkeypatch.setenv("WAGF_TEST_FAKE_KEY", FAKE_KEY)
    whole_records, _ = start(write_config(tmp_path, "whole", provider=provider), Script(provider=provider))
    config = write_config(tmp_path, "part", provider=provider)
    with pytest.raises(RuntimeError, match="model provider failed"):
        start(config, Script(provider=provider, fail_from_day=CUT))
    script = Script(provider=provider)
    resumed_records, _ = resume(config, tmp_path / "part", script, run_id="part-resumed")
    assert script.calls[0][0] == CUT
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")
    assert physics(resumed_records) == physics(whole_records)


@pytest.mark.parametrize("kind", [*TEMPORARY_ERRORS, "503"])
def test_a_temporary_error_inside_a_saved_day_replays_exactly(extension, local, tmp_path, kind):
    events = {**DAY_EVENTS, 4: [kind, "hold"]}
    start(write_config(tmp_path, "whole"), Script(day_events=events))
    config = write_config(tmp_path, "part")
    with pytest.raises(RuntimeError, match="model provider failed"):
        start(config, Script(fail_from_day=CUT, day_events=events))
    script = Script(day_events=events)
    resume(config, tmp_path / "part", script, run_id="part-resumed")
    assert script.calls[0][0] == CUT
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")


@pytest.mark.parametrize("kind, stopped_by", [("ssl", RuntimeError), ("ctrl-c", KeyboardInterrupt)])
def test_a_run_stopped_by_an_error_or_ctrl_c_can_be_resumed(extension, local, tmp_path, kind, stopped_by):
    start(write_config(tmp_path, "whole"), Script())
    config = write_config(tmp_path, "part")
    with pytest.raises(stopped_by):
        start(config, Script(day_events={**DAY_EVENTS, CUT: [kind]}))
    script = Script()
    resume(config, tmp_path / "part", script, run_id="part-resumed")
    assert script.calls[0][0] == CUT
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")


@pytest.mark.parametrize("stream", ["decisions", "physics", "audit", "backend_events", "provider_attempts"])
def test_a_line_cut_off_by_the_crash_does_not_stop_the_resume(extension, local, tmp_path, stream):
    start(write_config(tmp_path, "whole"), Script())
    config, source = interrupted(tmp_path, "part", "full")
    (source / "summary.json").unlink(missing_ok=True)  # a killed process never writes its summary
    with (source / f"{stream}.jsonl").open("ab") as handle:
        handle.write(b'{"run_id": "part", "timest')
    script = Script()
    resume(config, source, script, run_id="part-resumed")
    assert script.calls[0][0] == CUT
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")


def test_a_run_that_failed_only_at_the_last_version_check_resumes_without_a_new_request(extension, ident, tmp_path,
                                                                                         monkeypatch):
    reads = []

    def reader(model):
        reads.append(model["model"])
        if len(reads) == 2:
            raise OSError("server restarting")
        return {"digest": DIGEST_A, "family": "gemma", "parameter_size": "12B",
                "quantization_level": "Q4_K_M", "version": "0.99.0"}

    monkeypatch.setattr(ident, "read_local_model", reader)
    config = write_config(tmp_path, "part", days=4)
    with pytest.raises(RuntimeError, match="could not confirm the version"):
        start(config, Script(day_events={}))
    script = Script(day_events={})
    resume(config, tmp_path / "part", script, run_id="part-resumed")
    assert script.calls == []
    assert len(decision_lines(tmp_path / "part-wagf")) == 4
    assert json.loads((tmp_path / "part-resumed" / "summary.json").read_text(encoding="utf-8"))["status"] == "COMPLETED"


def test_an_ollama_upgrade_does_not_block_a_resume_and_is_recorded(extension, local, tmp_path):
    start(write_config(tmp_path, "whole"), Script())
    config, source = interrupted(tmp_path, "part", "full")
    local.version = "1.0.0"
    script = Script()
    resume(config, source, script, run_id="part-resumed")
    assert decision_lines(tmp_path / "part-wagf") == decision_lines(tmp_path / "whole-wagf")
    saved = json.loads((tmp_path / "part-wagf" / "run_identity.json").read_text(encoding="utf-8"))["model"]
    assert (saved["version"], saved["server_versions_seen"]) == ("1.0.0", ["0.99.0", "1.0.0"])


def test_a_fresh_run_that_runs_out_of_request_budget_is_not_called_a_resume(extension, local, tmp_path):
    config = write_config(tmp_path, "budget")
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["max_calls"] = DAYS  # the extra answers on days 1 to 3 use the budget up before the last day
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(RuntimeError) as caught:
        start(config, Script())
    assert "cannot resume" not in str(caught.value)
    assert (tmp_path / "budget-wagf" / "run_identity.json").is_file()
    assert not (tmp_path / "budget-wagf" / "run_identity.refused.json").exists()
    assert 0 < len(decision_lines(tmp_path / "budget-wagf")) < DAYS


def test_the_interrupted_source_run_is_not_changed(extension, local, tmp_path):
    config, source = interrupted(tmp_path, "part", "full")
    before = tree_hashes(source)
    wagf_before = tree_hashes(tmp_path / "part-wagf")
    resume(config, source, Script(), run_id="part-resumed")
    assert tree_hashes(source) == before
    # The earlier WAGF output moved intact, so nothing the first run wrote is lost.
    assert tree_hashes(tmp_path / "part-wagf.previous-1") == wagf_before


# ---------------------------------------------------------------- replayable trace shape (A)

def test_saved_trace_lists_every_attempt_in_order(extension, local, tmp_path):
    config = write_config(tmp_path, "whole")
    start(config, Script())
    traces = {}
    for path in sorted((tmp_path / "whole" / "raw").glob("policy_*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))["backend_trace"]
        traces[trace["governance"]["date"]] = trace
    retry, rate_limited, unreadable = traces["2021-01-02"], traces["2021-01-03"], traces["2021-01-04"]
    assert retry["model_used"] is True and retry["system"] and retry["governance"]["governance_retries"] == 1
    assert len(retry["model_calls"]) == 2 and set(retry["model_calls"][0]) == {"prompt", "reply"}
    assert len(retry["requests"]) == 2 and len(retry["attempts"]) == 2
    assert [a["request_sha256"] for a in retry["attempts"]] == [r["request_sha256"] for r in retry["requests"]]
    assert {"request_sha256", "url", "payload", "provider"} == set(retry["requests"][0])
    assert retry["requests"][0]["url"].endswith("/api/chat") and retry["requests"][0]["provider"] == "ollama"
    # One request sent twice: the 429 first, then the success.
    assert len(rate_limited["requests"]) == 1
    first, second = rate_limited["attempts"]
    assert first["request_sha256"] == second["request_sha256"]
    assert (first["error_class"], first["http_status"], first["provider_reply"]) == ("HTTPError", 429, None)
    assert second["error_class"] is None and second["provider_reply"]["message"]["content"]
    assert rate_limited["governance"]["model_calls"] == 1
    # An unreadable reply is kept as a reply plus its parse error, then the good one follows.
    bad, good = unreadable["attempts"]
    assert bad["provider_reply"] is not None and bad["error_class"] == "JSONDecodeError"
    assert good["error_class"] is None
    assert json.dumps(traces).count("api_key") == 0


# ---------------------------------------------------------------- 5: changed identity refuses to resume

def test_a_changed_digest_refuses_to_resume_and_keeps_earlier_output(extension, local, tmp_path):
    config, source = interrupted(tmp_path, "part", "full")
    wagf_before, source_before = tree_hashes(tmp_path / "part-wagf"), tree_hashes(source)
    local.digests, local.calls = [DIGEST_B], 0
    script = Script()
    with pytest.raises(ValueError, match=r"model\.digest"):
        resume(config, source, script)
    assert script.calls == []
    assert tree_hashes(tmp_path / "part-wagf") == wagf_before and tree_hashes(source) == source_before
    assert not (tmp_path / "part-wagf.previous-1").exists()


def test_a_changed_wagf_hash_refuses_to_resume_and_keeps_earlier_output(extension, ident, local, tmp_path,
                                                                        monkeypatch):
    config, source = interrupted(tmp_path, "part", "full")
    wagf_before = tree_hashes(tmp_path / "part-wagf")
    real = ident.wagf_code_identity
    monkeypatch.setattr(ident, "wagf_code_identity", lambda: {**real(), "broker_sha256": "0" * 64})
    script = Script()
    with pytest.raises(ValueError, match=r"wagf\.broker_sha256"):
        resume(config, source, script)
    assert script.calls == [] and tree_hashes(tmp_path / "part-wagf") == wagf_before
    assert not (tmp_path / "part-wagf.previous-1").exists()


def test_a_git_commit_change_alone_does_not_block_a_resume(extension, ident, local, tmp_path, monkeypatch):
    config, source = interrupted(tmp_path, "part", "full")
    real = ident.wagf_code_identity
    monkeypatch.setattr(ident, "wagf_code_identity", lambda: {**real(), "git_commit": "f" * 40, "git_dirty": True})
    resume(config, source, Script())


# ---------------------------------------------------------------- 6: model version rules

def test_a_digest_change_during_the_run_fails_the_run(extension, local, tmp_path):
    local.digests = [DIGEST_A, DIGEST_B]
    config = write_config(tmp_path, "whole", days=3)
    with pytest.raises(RuntimeError, match="changed during the run"):
        start(config, Script())
    wagf = tmp_path / "whole-wagf"
    saved = json.loads((wagf / "run_identity.json").read_text(encoding="utf-8"))
    assert saved["model"]["digest"] == DIGEST_A and saved["model"]["digest_at_end"] == DIGEST_B
    assert saved["model"]["model_changed_during_run"] is True
    assert (wagf / "audit_summary.json").is_file() and len(decision_lines(wagf)) == 3


def test_a_stable_digest_is_checked_again_at_the_end(extension, local, tmp_path):
    start(write_config(tmp_path, "whole", days=3), Script())
    saved = json.loads((tmp_path / "whole-wagf" / "run_identity.json").read_text(encoding="utf-8"))
    assert saved["model"]["digest_at_end"] == DIGEST_A and "model_changed_during_run" not in saved["model"]
    assert local.calls == 2


def test_a_missing_digest_stops_before_the_first_request(extension, local, tmp_path):
    local.digests = [None]
    script = Script()
    with pytest.raises(RuntimeError, match="digest"):
        start(write_config(tmp_path, "whole", days=3), script)
    assert script.calls == [] and not (tmp_path / "whole-wagf").exists()


def test_an_unreachable_model_server_stops_before_the_first_request(extension, ident, tmp_path, monkeypatch):
    def down(model):
        raise OSError("connection refused")
    monkeypatch.setattr(ident, "read_local_model", down)
    script = Script()
    with pytest.raises(RuntimeError, match="cannot read the version"):
        start(write_config(tmp_path, "whole", days=3), script)
    assert script.calls == []


def test_a_pin_mismatch_stops_before_the_first_request(extension, local, tmp_path):
    script = Script()
    with pytest.raises(RuntimeError, match="expected_model_digest"):
        start(write_config(tmp_path, "whole", days=3, pin="sha256:" + DIGEST_B), script)
    assert script.calls == [] and not (tmp_path / "whole-wagf").exists()


def test_a_matching_pin_is_accepted_with_or_without_the_prefix(extension, local, tmp_path):
    for name, pin in (("with", "sha256:" + DIGEST_A.upper()), ("without", DIGEST_A)):
        start(write_config(tmp_path, name, days=2, pin=pin), Script())
        saved = json.loads((tmp_path / f"{name}-wagf" / "run_identity.json").read_text(encoding="utf-8"))
        assert saved["model"]["digest"] == DIGEST_A


def test_a_pin_on_a_cloud_model_is_rejected(extension, tmp_path):
    from llm_reservoir_agent.workflow import load_settings
    config = write_config(tmp_path, "cloud", days=2, provider="openai", pin=DIGEST_A)
    with pytest.raises(ValueError, match="local model"):
        load_settings(config)


def test_a_badly_formed_pin_is_rejected(extension, tmp_path):
    from llm_reservoir_agent.workflow import load_settings
    with pytest.raises(ValueError, match="64-digit"):
        load_settings(write_config(tmp_path, "bad", days=2, pin="sha256:1234"))


def test_the_identity_file_and_describe_hold_the_same_record(extension, local, tmp_path):
    start(write_config(tmp_path, "whole", days=2), Script())
    saved = json.loads((tmp_path / "whole-wagf" / "run_identity.json").read_text(encoding="utf-8"))
    experiment = json.loads((tmp_path / "whole" / "experiment.json").read_text(encoding="utf-8"))
    described = json.dumps(experiment)
    assert DIGEST_A in described and saved["model"]["captured_at"] in described
    assert saved["arm"] == "full" and saved["wagf_seed"] == 42
    assert set(saved["wagf"]) == {"git_commit", "git_dirty", "broker_sha256"}
    assert len(saved["wagf"]["broker_sha256"]) == 64
    assert set(saved["config"]) == {"agent_types_sha256", "skill_registry_sha256"}
    assert saved["model"]["provider"] == "ollama" and saved["model"]["name"] == "gemma4:12b"
    assert {"family", "parameter_size", "quantization_level", "version"} <= set(saved["model"])


# ---------------------------------------------------------------- 7: repeated starts

def test_repeated_starts_keep_every_earlier_file(extension, local, tmp_path):
    config = write_config(tmp_path, "again", days=2)
    wagf = tmp_path / "again-wagf"
    seen = []
    for number in (1, 2, 3):
        shutil.rmtree(tmp_path / "again", ignore_errors=True)  # a new HydroCNHS run each time
        start(config, Script())
        seen.append(tree_hashes(wagf))
        assert (wagf / "run_identity.json").is_file()
        for earlier in range(1, number):
            assert tree_hashes(tmp_path / f"again-wagf.previous-{earlier}") == seen[earlier - 1]
    assert not (tmp_path / "again-wagf.previous-3").exists()
    assert (tmp_path / "again-wagf.previous-2" / "decisions.jsonl").is_file()


def test_a_start_does_not_truncate_the_decision_log(extension, local, tmp_path):
    config = write_config(tmp_path, "again", days=2)
    start(config, Script())
    lines = decision_lines(tmp_path / "again-wagf")
    shutil.rmtree(tmp_path / "again")
    from llm_reservoir_agent.workflow import load_settings
    from llm_reservoir_agent.workflow import run_settings
    # Constructing the backend again must not empty the earlier file before the move.
    kept = tmp_path / "again-wagf.previous-1"
    run_settings(load_settings(config), allow_network=True, transport=Script())
    assert decision_lines(kept) == lines


def test_a_different_identity_leaves_earlier_files_alone_and_names_the_fields(extension, local, tmp_path):
    config = write_config(tmp_path, "again", days=2)
    start(config, Script())
    wagf = tmp_path / "again-wagf"
    before = tree_hashes(wagf)
    shutil.rmtree(tmp_path / "again")
    local.digests, local.calls = [DIGEST_B], 0
    script = Script()
    with pytest.raises(ValueError) as caught:
        start(config, script)
    assert "model.digest" in str(caught.value) and "new output folder" in str(caught.value)
    assert script.calls == [] and tree_hashes(wagf) == before
    assert not (tmp_path / "again-wagf.previous-1").exists()


def test_a_folder_without_an_identity_file_is_not_overwritten(extension, local, tmp_path):
    config = write_config(tmp_path, "again", days=2)
    wagf = tmp_path / "again-wagf"
    wagf.mkdir()
    (wagf / "notes.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(ValueError, match="run_identity.json"):
        start(config, Script())
    assert (wagf / "notes.txt").read_text(encoding="utf-8") == "keep me"


# ---------------------------------------------------------------- 8: secrets, cloud models

def test_a_fake_api_key_is_in_no_saved_file(extension, tmp_path, monkeypatch):
    monkeypatch.setenv("WAGF_TEST_FAKE_KEY", FAKE_KEY)
    config = write_config(tmp_path, "cloud", days=4, provider="openai")
    sent = []

    class Echo(Script):
        def __call__(self, url, payload, headers, timeout):
            sent.append(dict(headers))
            return super().__call__(url, payload, headers, timeout)

    start(config, Echo(cloud=True))
    assert any(FAKE_KEY in value for headers in sent for value in headers.values())  # the key really was used
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files
    for path in files:
        assert FAKE_KEY.encode() not in path.read_bytes(), path


def test_a_cloud_model_records_observed_names_not_a_digest(extension, tmp_path, monkeypatch):
    monkeypatch.setenv("WAGF_TEST_FAKE_KEY", FAKE_KEY)
    config = write_config(tmp_path, "cloud", days=4, provider="openai")
    start(config, Script(cloud=True))
    saved = json.loads((tmp_path / "cloud-wagf" / "run_identity.json").read_text(encoding="utf-8"))
    assert set(saved["observed_provider_models"]) == {"gpt-test-a", "gpt-test-b"}
    assert all(count >= 1 for count in saved["observed_provider_models"].values())
    assert "digest" not in saved["model"] and "digest_at_end" not in saved["model"]
    assert saved["model"]["provider"] == "openai" and saved["model"]["name"] == "gpt-test"


def test_cloud_identity_comparison_ignores_observed_models_and_capture_time(ident):
    old = {"arm": "full", "model": {"provider": "openai", "name": "m", "captured_at": "x"},
           "observed_provider_models": {"a": 1}}
    new = {"arm": "full", "model": {"provider": "openai", "name": "m", "captured_at": "y"},
           "observed_provider_models": {"a": 2, "b": 1}}
    assert ident.differences(old, new) == []
    assert ident.differences(old, {**new, "arm": "none"}) == ["arm"]


# ---------------------------------------------------------------- the real local reader

def test_the_local_reader_falls_back_to_the_tag_list_for_the_digest(ident):
    asked = []

    class Reply:
        def __init__(self, value):
            self.value = value

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(self.value).encode()

    def opener(request, timeout):
        asked.append((request.full_url, request.get_method(), timeout))
        path = request.full_url.rsplit("/api/", 1)[1]
        return Reply({"show": {"details": {"family": "gemma", "parameter_size": "12B",
                                           "quantization_level": "Q4_K_M"}},
                      "tags": {"models": [{"name": "other:1", "digest": "1" * 64},
                                          {"name": "gemma4:12b", "digest": DIGEST_A}]},
                      "version": {"version": "0.99.0"}}[path])

    info = ident.read_local_model({"base_url": "http://localhost:11434/", "model": "gemma4:12b"}, opener=opener)
    assert info == {"digest": DIGEST_A, "family": "gemma", "parameter_size": "12B",
                    "quantization_level": "Q4_K_M", "version": "0.99.0"}
    assert [u for u, _, _ in asked] == ["http://localhost:11434/api/show", "http://localhost:11434/api/tags",
                                        "http://localhost:11434/api/version"]
    assert {t for _, _, t in asked} == {10}


def test_an_unreadable_digest_after_the_last_day_fails_the_run(extension, ident, tmp_path, monkeypatch):
    reads = []

    def reader(model):
        reads.append(model["model"])
        if len(reads) > 1:
            raise OSError("server restarting")
        return {"digest": DIGEST_A, "family": "gemma", "parameter_size": "12B",
                "quantization_level": "Q4_K_M", "version": "0.99.0"}

    monkeypatch.setattr(ident, "read_local_model", reader)
    with pytest.raises(RuntimeError, match="could not confirm the version"):
        start(write_config(tmp_path, "whole", days=2), Script(day_events={}))
    saved = json.loads((tmp_path / "whole-wagf" / "run_identity.json").read_text(encoding="utf-8"))["model"]
    assert saved["digest_at_end"] is None and "server restarting" in saved["digest_at_end_error"]
    assert len(decision_lines(tmp_path / "whole-wagf")) == 2


def test_a_left_over_temporary_identity_file_does_not_block_a_start(extension, local, tmp_path):
    (tmp_path / "whole-wagf").mkdir()
    (tmp_path / "whole-wagf" / "run_identity.json.tmp").write_text("{", encoding="utf-8")
    start(write_config(tmp_path, "whole", days=2), Script(day_events={}))
    assert len(decision_lines(tmp_path / "whole-wagf")) == 2


def test_the_wagf_code_hash_also_covers_yaml_files(ident, tmp_path):
    (tmp_path / "broker").mkdir()
    rules = tmp_path / "broker" / "profile.yaml"
    rules.write_text("limit: 1\n", encoding="utf-8")
    before = ident.broker_sha256(tmp_path)
    rules.write_text("limit: 2\n", encoding="utf-8")
    assert ident.broker_sha256(tmp_path) != before


def test_the_local_reader_finds_a_model_named_without_a_tag(ident):
    import io

    def opener(request, timeout):
        path = request.full_url.rsplit("/api/", 1)[1]
        value = {"show": {"details": {}},
                 "tags": {"models": [{"name": "gemma4:12b", "digest": "1" * 64},
                                     {"name": "gemma4:latest", "digest": DIGEST_A}]},
                 "version": {"version": "0.99.0"}}[path]
        return io.BytesIO(json.dumps(value).encode())

    info = ident.read_local_model({"base_url": "http://localhost:11434", "model": "gemma4"}, opener=opener)
    assert info["digest"] == DIGEST_A
