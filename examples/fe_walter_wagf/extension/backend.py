"""F.E. Walter daily policy whose answers pass through WAGF before HydroCNHS sees them."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from broker import AuditConfig, GenericAuditWriter, SkillRegistry
from broker.components.governance.validator_registry import ValidatorRegistry
from broker.core.skill_broker_engine import SkillBrokerEngine
from broker.interfaces.skill_types import SkillOutcome
from broker.utils.agent_config import AgentTypeConfig
from broker.utils.model_adapter import get_adapter
from broker.validators.agent import AgentValidator

from llm_reservoir_agent.audit import json_snapshot

from . import identity as run_identity
from .checks import PHYSICAL_CHECKS, decision_env, fallback_release_cfs

AGENT_TYPE = "reservoir_operator"
DOMAIN = "fe_walter"
ARMS = ("none", "physical", "full")
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
AGENT_TYPES_FILE = CONFIG_DIR / "agent_types.yaml"
SKILL_REGISTRY_FILE = CONFIG_DIR / "skill_registry.yaml"
SEED = 42

# The paper prompt ends by asking for its own answer fields; only that ending is replaced.
NATIVE_ANSWER_MARKER = "Before answering, check that the proposed release changes storage"
GOVERNED_ANSWER = ("Before answering, check that the proposed release changes storage in the "
                   "direction you choose. Respond only with JSON, with the fields requested in "
                   "the ANSWER section of the message.")
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "decision": {"type": "string", "enum": ["lower_pool", "hold_pool", "raise_pool"]},
        "release_cfs": {"type": "number"},
    },
    "required": ["reasoning", "decision", "release_cfs"],
    "additionalProperties": False,
}

ValidatorRegistry.register(DOMAIN, "physical", list(PHYSICAL_CHECKS))


def governed_system_prompt(native_prompt: str) -> str:
    head, marker, _ = native_prompt.partition(NATIVE_ANSWER_MARKER)
    if not marker:
        raise ValueError("system prompt no longer contains the expected answer section")
    return head + GOVERNED_ANSWER + "\n"


class _PromptBuilder:
    """Hand WAGF the prompt for the current day."""
    memory_engine = None

    def __init__(self, template: str):
        self.template, self.native_prompt = template, ""
        self.prompt_templates = {AGENT_TYPE: template}

    def build(self, agent_id: str, **kwargs: Any) -> dict:
        return {"agent_id": agent_id, "agent_type": AGENT_TYPE, "step_id": kwargs.get("step_id"),
                "state": {}, "personal": {}}

    def format_prompt(self, context: Mapping[str, Any]) -> str:
        return (self.template.replace("{native_prompt}", self.native_prompt)
                .replace("{options_text}", context["personal"]["options_text"]))


def build_engine(arm: str, output: Path, model_name: str) -> tuple[SkillBrokerEngine, _PromptBuilder, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown governance arm {arm!r}")
    # WAGF reads the active rule set from this variable; one process runs one arm.
    os.environ["GOVERNANCE_PROFILE"] = arm
    config = AgentTypeConfig.load(str(AGENT_TYPES_FILE))
    registry = SkillRegistry()
    registry.register_from_yaml(str(SKILL_REGISTRY_FILE))
    adapter = get_adapter(model_name, config_path=str(AGENT_TYPES_FILE))
    adapter.agent_type = AGENT_TYPE
    adapter.config_path = str(AGENT_TYPES_FILE)
    adapter.valid_skills = set(registry.skills)
    adapter.alias_map = {**config.get_action_alias_map(AGENT_TYPE), **{s: s for s in registry.skills}}
    builder = _PromptBuilder(config.get(AGENT_TYPE)["prompt_template"])
    output.mkdir(parents=True, exist_ok=True)
    audit = GenericAuditWriter(AuditConfig(output_dir=str(output), experiment_name=arm))
    engine = SkillBrokerEngine(
        skill_registry=registry, model_adapter=adapter,
        validators=[] if arm == "none" else [AgentValidator(config_path=str(AGENT_TYPES_FILE))],
        simulation_engine=None, context_builder=builder, config=config, audit_writer=audit,
        max_retries=config.get_governance_retries(),
        domain_physical_dispatch=None if arm == "none" else DOMAIN,
    )
    return engine, builder, audit


def _request_sha256(url: str, payload: Any) -> str:
    """Same request hash the paper's chat transport puts on every attempt."""
    return hashlib.sha256(json.dumps({"url": url, "payload": payload}, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class _RecordingTransport:
    """Pass every call through and remember its URL and payload (never the headers)."""

    def __init__(self, transport: Any):
        self._transport = transport
        self.requests: dict[str, dict] = {}
        self.replayed_a_saved_reply = False

    @property
    def network_calls(self):
        # Raises AttributeError for a plain function, which is how the caller tells "not counted".
        return self._transport.network_calls

    def __call__(self, url, payload, headers, timeout):
        self.requests.setdefault(_request_sha256(url, payload),
                                 {"url": url, "payload": copy.deepcopy(json_snapshot(payload))})
        before = getattr(self._transport, "network_calls", None)
        reply = self._transport(url, payload, headers, timeout)
        # A resume answers saved days without counting a network call.
        if before is not None and getattr(self._transport, "network_calls", None) == before:
            self.replayed_a_saved_reply = True
        return reply


class GovernedBackend:
    """Ask the model, let WAGF check the answer, and return one release to the simulator."""

    def __init__(self, settings: Mapping[str, Any], physical: Mapping[str, Any], *, runtime_root: Any,
                 model: Mapping[str, Any], transport: Any, native: Any, reference: Any,
                 agent_id: str = "fe_operator", local_model_reader: Any = None):
        wagf, spec = settings["wagf"], settings["reference"]
        self.arm, self.agent_id, self._days = wagf["arm"], agent_id, wagf["days"]
        self.policy_id = "wagf_governed_" + self.arm
        self._cfs_to_cms, self._acreft_to_m3 = native.CFS_TO_CMS, native.ACREFT_TO_M3
        self._profile = native.load_case_profile(runtime_root, spec.get("profile_file"))
        system, _, _ = native.read_system_prompt(self._profile, spec["method"], spec)
        self._system = governed_system_prompt(system)
        self._formatter = native.NativePromptFormatter(self._profile, spec, Path(spec["dkp"]), None)
        self._recorder = _RecordingTransport(transport)
        self._chat = reference._ReferenceChatTransport(model, self._recorder, validation_stage="policy")
        self._model = dict(model)
        output = Path(wagf["output"])
        # Everything that can refuse a run happens before the first model request and before any
        # earlier output is touched. The reader is looked up now so tests can replace it.
        self._reader = local_model_reader or run_identity.read_local_model
        self._identity = run_identity.build_identity(
            self.arm, SEED, model, agent_types=AGENT_TYPES_FILE, skill_registry=SKILL_REGISTRY_FILE,
            reader=self._reader, expected_digest=wagf.get("expected_model_digest"))
        earlier = run_identity.prepare_output(output, self._identity)
        self._earlier_identity_compared = earlier is not None
        run_identity.note_server_versions(earlier, self._identity)
        output.mkdir(parents=True, exist_ok=True)
        self._identity_path = output / run_identity.IDENTITY_FILE
        run_identity.write_json_atomic(self._identity_path, self._identity)
        # describe() is compared on every step and must not change, so it keeps the identity as it
        # was at the start; the file in the output folder also records what is learned later.
        self._identity_at_start = json_snapshot(self._identity)
        self._engine, self._builder, self._audit = build_engine(self.arm, output, model["model"])
        self._log_path = output / "decisions.jsonl"
        self._log_path.touch()
        self._pending, self._latest_trace, self._provider_failure = None, None, None
        self._model_calls, self._provider_attempts, self._day_requests = [], [], {}

    @property
    def state_owner(self):
        return self

    @property
    def network_calls(self):
        return self._chat.network_calls

    @property
    def latest_audit(self):
        return None

    @property
    def latest_trace(self):
        return json_snapshot(self._latest_trace)

    def _harvest(self, before: Any) -> None:
        """Keep every provider attempt of the call that just ended, with the request it used."""
        trace = self._chat.latest_trace
        if trace is None or trace is before:
            return
        for attempt in trace.get("attempts", []):
            sha = attempt["request_sha256"]
            request = self._recorder.requests.get(sha)
            if request is None:
                raise RuntimeError("a provider attempt has no recorded request; the run could not be resumed")
            self._day_requests.setdefault(sha, {"request_sha256": sha, "url": request["url"],
                                                "payload": request["payload"], "provider": self._model["provider"]})
            saved = {"request_sha256": sha, "provider_reply": attempt.get("provider_reply"),
                     "error_class": attempt.get("error_class")}
            for key in ("http_status", "url_error_retryable"):
                if attempt.get(key) is not None:
                    saved[key] = attempt[key]
            self._provider_attempts.append(json_snapshot(saved))
            self._note_provider_model(attempt.get("provider_reply"))

    def _note_provider_model(self, reply: Any) -> None:
        """Count the model name a cloud provider reports; save the file when a new name appears."""
        if "observed_provider_models" not in self._identity or not isinstance(reply, dict):
            return
        name = reply.get("model")
        if not isinstance(name, str) or not name:
            return
        seen = self._identity["observed_provider_models"]
        new = name not in seen
        seen[name] = seen.get(name, 0) + 1
        if new:
            run_identity.write_json_atomic(self._identity_path, self._identity)

    def _invoke(self, prompt: str) -> str:
        """One model call. A dead connection stops the run; an unreadable reply is a format failure."""
        before = self._chat.latest_trace
        try:
            text = json.dumps(self._chat.decide(self._system, prompt, RESPONSE_SCHEMA), ensure_ascii=False)
        except RuntimeError as exc:
            self._harvest(before)
            # A call that failed before it started leaves the previous call's trace in place.
            trace = self._chat.latest_trace
            attempt = {} if trace is None or trace is before else trace.get("latest_attempt") or {}
            if attempt.get("provider_reply") is None:
                self._provider_failure = exc
                raise
            # Empty text, so WAGF's parser cannot guess a number from a cut-off reply.
            self._provider_failure = None
            self._model_calls.append({"prompt": prompt, "reply": "", "error": attempt.get("error_class")})
            return ""
        self._harvest(before)
        self._provider_failure = None
        self._model_calls.append({"prompt": prompt, "reply": text})
        return text

    def _chosen_release(self, result: Any, env: Mapping[str, Any]) -> tuple[float, str | None]:
        """Return (release in cfs, why the safe release was used instead of the model's)."""
        if result.outcome not in (SkillOutcome.APPROVED, SkillOutcome.RETRY_SUCCESS):
            return fallback_release_cfs(env), str(getattr(result.outcome, "value", result.outcome))
        value = (result.approved_skill.parameters or {}).get("release_cfs")
        if value is None or not math.isfinite(float(value)):
            return fallback_release_cfs(env), "no_usable_release"
        # Only the unchecked arm can reach this with a negative number.
        return max(float(value), 0.0), None

    def decide(self, observation: Mapping[str, Any]) -> dict:
        if self._pending is not None:
            raise RuntimeError("the previous decision must be committed before deciding again")
        _, _, _, runtime = self._formatter.runtime(observation)
        self._builder.native_prompt = self._formatter(SimpleNamespace(observation=observation)).value
        env = decision_env(observation, runtime, self._cfs_to_cms)
        self._model_calls, self._provider_attempts, self._day_requests = [], [], {}
        self._provider_failure = None
        try:
            result = self._engine.process_step(
                agent_id=self.agent_id, step_id=observation["timestep"] + 1, run_id=self.policy_id, seed=SEED,
                llm_invoke=self._invoke, agent_type=AGENT_TYPE, env_context=dict(env))
        except Exception:
            if self._provider_failure is None:
                raise
            result = None
        self._refuse_an_unverifiable_resume()
        approved = result is not None and result.outcome in (SkillOutcome.APPROVED, SkillOutcome.RETRY_SUCCESS)
        if self._provider_failure is not None and not approved:
            self._audit.finalize()
            raise RuntimeError(f"model provider failed on {env['date']}") from self._provider_failure
        release_cfs, fallback = self._chosen_release(result, env)
        proposal, skill = result.skill_proposal, result.approved_skill
        self._pending = {
            "date": env["date"], "timestep": observation["timestep"], "arm": self.arm,
            "season": env["season"], "pool_start_ft": env["pool_elevation_ft"], "inflow_cfs": env["inflow_cfs"],
            "outcome": str(getattr(result.outcome, "value", result.outcome)),
            "proposed_skill": getattr(proposal, "skill_name", None),
            "final_skill": getattr(skill, "skill_name", None),
            "governance_retries": result.retry_count, "format_retries": result.format_retries,
            "model_calls": len(self._model_calls),
            # Rules blocking the last answer only; the audit CSV's failed_rules lists every attempt.
            "final_blocked_rules": sorted(getattr(result, "blocking_rule_ids", []) or []),
            "proposed_release_cfs": (getattr(proposal, "parameters", None) or {}).get("release_cfs"),
            "fallback": fallback, "requested_release_cfs": release_cfs,
        }
        self._latest_trace = {"model_used": True, "system": self._system,
                              "requests": list(self._day_requests.values()),
                              "attempts": self._provider_attempts, "model_calls": self._model_calls,
                              "governance": self._pending}
        return {"schema_version": "reservoir-action.v1", "release_cms": release_cfs * self._cfs_to_cms}

    def _refuse_an_unverifiable_resume(self) -> None:
        """Saved days come first in a resume, so this stops before any new model request is sent."""
        if self._earlier_identity_compared or not self._recorder.replayed_a_saved_reply:
            return
        # Keep the refusal in force: this folder's identity must not vouch for a later attempt.
        os.replace(self._identity_path, self._identity_path.with_name("run_identity.refused.json"))
        self._audit.finalize()
        raise RuntimeError("cannot resume: the earlier WAGF output folder is missing or empty, so the model and "
                           "WAGF versions of the saved days cannot be compared. Restore that folder, or start "
                           "a new run with a new wagf.output.")

    def record_transition(self, record: Mapping[str, Any]) -> None:
        if self._pending is None or record["observation"]["timestep"] != self._pending["timestep"]:
            raise RuntimeError("transition does not match the pending decision")
        self._formatter.commit(record)
        transition = record["transition"]
        storage_af = transition["storage_end_m3"] / self._acreft_to_m3
        line = {**self._pending,
                "controlled_release_cfs": transition["controlled_release_cms"] / self._cfs_to_cms,
                "spill_cfs": transition["spill_cms"] / self._cfs_to_cms,
                "pool_end_ft": self._profile.storage_to_elevation(storage_af)}
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        last_day = record["observation"]["timestep"] + 1 == self._days
        self._pending = None
        if last_day:
            self._finish_run()

    def _finish_run(self) -> None:
        """Re-check the local model after the last day, then close the audit."""
        record = self._identity["model"]
        problem = None
        if run_identity.is_local(record["provider"]):
            try:
                end = run_identity.read_current_digest(self._model, self._reader)
            except Exception as exc:
                end = None
                record["digest_at_end_error"] = f"{type(exc).__name__}: {exc}"
            record["digest_at_end"] = end
            if end is None:
                problem = (f"could not confirm the version of local model {record['name']!r} after the last day: "
                           f"{record.get('digest_at_end_error', 'the server reported no digest')}")
            elif end != record["digest"]:
                record["model_changed_during_run"] = True
                problem = (f"local model {record['name']!r} changed during the run "
                           f"({record['digest']} at start, {end} at end)")
        run_identity.write_json_atomic(self._identity_path, self._identity)
        self._audit.finalize()
        if problem:
            raise RuntimeError(problem)

    def describe(self) -> dict:
        model = {**json_snapshot(self._model), "base_url": run_identity.safe_url(self._model["base_url"])}
        return {"backend": "wagf_governed", "arm": self.arm, "model": model,
                "model_used": True, "wagf_seed": SEED, "run_identity": json_snapshot(self._identity_at_start)}
