"""Zero-shot LLM reservoir release rule (the "Zero-shot_LLM" method).

WHAT THIS FILE DOES
===================
This module answers the same release question as benchmark_release.py -

    "Given the interval's mean inflow and current storage, what mean release
     should the reservoir make?"

- but instead of published equations, an LLM makes the call. In the
ZERO-SHOT condition (the lowest knowledge tier of the NSF CDS&E three-pager,
RT2) the LLM receives only BASIC reservoir facts: general purpose, storage
capacity, release capacity, minimum release. No operating manual, no DKP,
no historical release data.

HOW A DAILY DECISION HAPPENS
============================
    reservoir_model.py decides whether today needs an LLM consultation
    (the inflow-change criterion lives THERE, not here - see below), then
    calls either policy.record_reuse(...) or policy.target_release(...)
        |
        | 1. PROMPT   - system prompt (fixed reservoir facts + instructions)
        |             + state prompt (today's numbers + recent history)
        v
        | 2. LLM CALL - backend.decide() returns {"release_cfs", "reasoning"}
        |    (on any failure: fall back to the last release decision)
        v
        | 3. SAFETY   - clip the answer into [min_release, max_release]
        v
        | 4. RECORD   - one line in the decision log; occasionally keep the
        |    full prompt/response pair for the samples file
        v
      return release (in m^3/s) to the water balance

WHERE THE LLM-CONSULTATION CRITERION LIVES (moved out of this file)
===================================================================
Earlier versions of this module owned a `_can_reuse()` check and an
`inflow_change_threshold` field: if today's inflow differed from
yesterday's by no more than 10%, the policy silently reused yesterday's
release without consulting the LLM. That has been REMOVED from here and
moved into reservoir_model.py, for two reasons:

  1. It is not policy-specific decision knowledge. It is a run-control /
     cost-control decision about how often the simulation consults an LLM,
     so it belongs in the main simulation driver where it is visible for
     every method, rather than inside one policy class (where the DKP
     method inherited it invisibly - the bug that started this cleanup).
  2. Both LLM conditions must use the SAME criterion. With one shared
     constant in reservoir_model.py, the zero-shot and DKP conditions
     cannot drift apart unless that is deliberately introduced as an
     experimental factor.

This class therefore no longer decides WHETHER to consult the LLM. When
target_release() is called, it calls the LLM. reservoir_model.py calls
record_reuse() instead on days it judges a consultation unnecessary, so
those days still appear in this policy's log and counters.

COST / LOG CONTROLS (tunable dataclass fields)
==============================================
  * reasoning_log_fraction (0.30): only ~30% of successful LLM decisions
    get their reasoning written to the log (failures are always logged).
  * n_prompt_samples (5): five randomly chosen LLM calls are saved IN FULL
    (actual prompt + actual response) to a *_prompt_samples.txt file,
    using reservoir sampling so every call has an equal chance.

TWO INTERCHANGEABLE LLM BACKENDS
================================
  * AnthropicBackend - Claude via the Anthropic API (default claude-sonnet-5)
  * OllamaBackend    - a local model served by Ollama (default gemma4:12b)
Both expose one method: decide(system, prompt) -> {"release_cfs", "reasoning"}.
"""

import hashlib
import json
import math
import random
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# --- unit-conversion constants ---------------------------------------------
CFS_TO_CMS = 0.028316847      # cubic feet per second -> cubic meters per second
ACREFT_TO_M3 = 1233.4818      # acre-feet -> cubic meters

# --- the JSON shape every LLM answer must follow ----------------------------
# (enforced server-side by Anthropic structured outputs / Ollama "format")
# NEUTRAL SELF-CHECK FIELDS - shared VERBATIM by both LLM conditions.
# They come FIRST in the schema, before release_cfs. The model writes JSON in
# schema order, so it must commit to (1) which target applies, (2) where the
# pool stands relative to it, (3) which way it intends storage to move and
# (4) how its release will compare with inflow - all BEFORE it writes the
# number. The LLM populates every field; Python only audits the answers.
# Both conditions can answer them from their own prompt: the operation target
# sentence, the beginning water level and the inflow are given to both.
NEUTRAL_DECISION_PROPERTIES = {
    "applicable_target_ft": {
        "type": "number",
        "description": ("Operation-target water level (ft NGVD29) that applies "
                        "to this interval, read from the operation target"),
    },
    "pool_position": {
        "type": "string",
        "enum": ["below_target", "at_target", "above_target"],
        "description": "Beginning water level compared with applicable_target_ft",
    },
    "intended_storage_direction": {
        "type": "string",
        "enum": ["increase", "hold", "decrease"],
        "description": "How you intend storage to change over this interval",
    },
    "release_relation_to_inflow": {
        "type": "string",
        "enum": ["below_inflow", "equal_to_inflow", "above_inflow"],
        "description": "How your release will compare with this interval's inflow",
    },
}
NEUTRAL_FIELD_NAMES = list(NEUTRAL_DECISION_PROPERTIES)

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        **NEUTRAL_DECISION_PROPERTIES,
        # reasoning comes BEFORE release_cfs. The model writes JSON in schema
        # order, so this makes it reason first and then commit to a number.
        # With the number first, the reasoning was written afterwards and could
        # argue for a different value (DKP, 2000-10: JSON 500 cfs, reasoning
        # concluding that 100 cfs was correct).
        "reasoning": {
            "type": "string",
            "description": ("One or two sentences: the storage change your release "
                            "will cause, and why it moves toward the target"),
        },
        "release_cfs": {
            "type": "number",
            "description": "Target mean release for the interval in cubic feet per second",
        },
    },
    "required": NEUTRAL_FIELD_NAMES + ["reasoning", "release_cfs"],
    "additionalProperties": False,
}


def sha256_text(text) -> str:
    """SHA256 of a text, so each prompt and excerpt can be identified exactly."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def write_trace(path, record: dict) -> None:
    """Append one JSON line to a trace file. Shared by both arms, so their
    traces have the same structure. A no-op when tracing is off."""
    if path is None:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _flow_relation(release_cfs: float, inflow_cfs: float) -> tuple:
    """(relation, storage direction) implied by release versus inflow.

    The tolerance is rounding-only, not a similarity band. A wider tolerance
    (previously 1% of inflow) incorrectly classified real, intended storage
    changes as "hold" whenever the release was close to inflow relative to
    a large flow - exactly the case the target-tracking audit most needs to
    judge correctly.
    """
    tol = max(1.0, 1e-9 * max(abs(inflow_cfs), 1.0))
    if release_cfs < inflow_cfs - tol:
        return "below_inflow", "increase", tol
    if release_cfs > inflow_cfs + tol:
        return "above_inflow", "decrease", tol
    return "equal_to_inflow", "hold", tol


def physics_audit(decision: dict, *, inflow_cfs: float, release_cfs: float,
                  pool_ft: float, target_ft: float,
                  min_release_cfs: float, max_release_cfs: float,
                  prompt_storage: bool,
                  target_error_start_af: float = None,
                  target_error_end_af: float = None,
                  target_tolerance_ft: float = 0.5,
                  requested_release_cfs: float = None,
                  physically_available_cfs: float = None,
                  target_known: bool = True) -> tuple:
    """Neutral post-decision physics audit, applied IDENTICALLY to both arms.

    It judges the LLM only on information both prompts contain - the shared
    operation target, the beginning water level, inflow and the model's own
    release - and it NEVER suggests or replaces a release. Returns
    a dict of four lists:
      hard_physics              physically infeasible requests, attributed to
                                the model (it had the information to know)
      hard_physics_unattributed the same infeasibility when the prompt lacked
                                the information (storage off): it still makes
                                the month physically invalid for a formal
                                trajectory, but is not the model's error
      policy                    self-consistency and target-tracking failures
                                (poor operation, not physical impossibility)
      warnings                  notes that fail nothing

    Checks the model's own statements against the water balance, then
    whether the chosen direction moves toward the target it was given:
      below target -> storage must increase (release below inflow), unless
                      inflow does not exceed the minimum release
      above target -> storage must decrease (release above inflow), unless
                      inflow already exceeds the maximum release
    Magnitude (does the release REDUCE the target-storage error) is judged
    only when storage was in the prompt, because otherwise the model had no
    volume to size against.
    """
    hard, hard_unattr, policy, warnings = [], [], [], []
    # HARD PHYSICS - identical for both arms.
    # (a) The raw request must lie inside the configured release bounds. Both
    #     system prompts state these bounds, so a violation is attributed.
    if requested_release_cfs is not None and (
            requested_release_cfs < min_release_cfs - 0.1
            or requested_release_cfs > max_release_cfs + 0.1):
        hard.append(f"requested release {requested_release_cfs:,.1f} cfs outside "
                    f"configured bounds [{min_release_cfs:,.0f}, "
                    f"{max_release_cfs:,.0f}] cfs")
    # (b) A requested release larger than the water that exists (inflow +
    #     storage above the inactive pool) cannot be delivered; Python clips it
    #     either way, so the month is physically invalid as requested. It is
    #     ATTRIBUTED to the model only when storage was in the prompt, because
    #     without volumes the model could not know the limit - but it is a hard
    #     physics event for the trajectory in both cases.
    if (requested_release_cfs is not None and physically_available_cfs is not None
            and requested_release_cfs > physically_available_cfs + 0.1):
        msg = (f"requested release {requested_release_cfs:,.1f} cfs exceeds physically "
               f"available {physically_available_cfs:,.1f} cfs")
        if prompt_storage:
            hard.append(msg)
        else:
            hard_unattr.append(msg + " (not attributed: storage not in prompt)")
    def _result():
        return {"hard_physics": hard, "hard_physics_unattributed": hard_unattr,
                "policy": policy, "warnings": warnings}
    relation, direction, tol = _flow_relation(release_cfs, inflow_cfs)
    if pool_ft is None or target_ft is None:
        warnings.append("physics audit skipped: pool or target unavailable")
        return _result()
    if not target_known:
        # The official target was NOT in the prompt (zero-shot Wikipedia-only):
        # judge the model against the target it states itself, and record any
        # difference from the official target as information, not a failure.
        try:
            own = float(decision.get("applicable_target_ft"))
        except (TypeError, ValueError):
            policy.append("applicable_target_ft missing or not numeric")
            return _result()
        if abs(own - target_ft) > target_tolerance_ft:
            warnings.append(f"model's own target {own:.1f} ft differs from the official "
                            f"target {target_ft:.1f} ft (not judged: target not in prompt)")
        target_ft = own
        decision = dict(decision, applicable_target_ft=own)
        # target_error_*_af were measured by the caller to this same own target
    if pool_ft < target_ft - target_tolerance_ft:
        position = "below_target"
    elif pool_ft > target_ft + target_tolerance_ft:
        position = "above_target"
    else:
        position = "at_target"

    stated_target = decision.get("applicable_target_ft")
    try:
        stated_target = float(stated_target)
    except (TypeError, ValueError):
        policy.append("applicable_target_ft missing or not numeric")
        stated_target = None
    if stated_target is not None and abs(stated_target - target_ft) > target_tolerance_ft:
        policy.append(f"stated applicable_target_ft {stated_target:.1f} differs "
                        f"from the operation target {target_ft:.1f} for this date")
    if decision.get("pool_position") != position:
        policy.append(f"pool_position '{decision.get('pool_position')}' contradicts "
                        f"the water level ({pool_ft:.2f} ft vs target {target_ft:.1f} ft)")
    if decision.get("release_relation_to_inflow") != relation:
        policy.append(f"release_relation_to_inflow "
                        f"'{decision.get('release_relation_to_inflow')}' contradicts "
                        f"release {release_cfs:,.1f} vs inflow {inflow_cfs:,.1f} cfs")
    if decision.get("intended_storage_direction") != direction:
        policy.append(f"intended_storage_direction "
                        f"'{decision.get('intended_storage_direction')}' contradicts "
                        f"the water balance (storage will {direction})")

    if (position == "below_target" and inflow_cfs > min_release_cfs + tol
            and direction != "increase"):
        policy.append("pool below target but release does not retain inflow, "
                        "so storage cannot move toward the target")
    if (position == "above_target" and inflow_cfs < max_release_cfs - tol
            and direction != "decrease"):
        policy.append("pool above target but release does not draw storage down")

    if (prompt_storage and position != "at_target"
            and target_error_start_af is not None and target_error_end_af is not None
            and target_error_end_af >= target_error_start_af - 0.5):
        policy.append("release does not reduce the target-storage error")
    return _result()


# ===========================================================================
# SECTION 1 - LLM BACKENDS (how we talk to a model; nothing about reservoirs)
# ===========================================================================

class AnthropicBackend:
    """Claude as the decision engine, via the Anthropic API."""

    def __init__(self, model: str = "claude-sonnet-5", max_tokens: int = 1024):
        # imported here (not at module top) so that Ollama-only users do not
        # need the anthropic package installed at all
        import anthropic
        self.client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
        self.model = model
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        """Shown in logs so a run records which engine produced it."""
        return self.model

    def decide(self, system: str, prompt: str, schema: dict = None) -> dict:
        """One decision: send the prompts, get validated JSON back.

        Raises on any failure - the caller decides what the fallback is.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            # thinking off: each call is one small structured decision, so
            # extra reasoning tokens add latency/cost across ~730 daily calls
            thinking={"type": "disabled"},
            # cache_control: the system prompt is identical every call, so
            # the API caches it (~90% cheaper). Essential for the long DKP
            # prompts; harmless for short ones (they silently don't cache).
            system=[{"type": "text", "text": system,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
            # structured outputs: the API guarantees the reply is valid JSON
            # matching DECISION_SCHEMA - no fragile text parsing needed
            output_config={"format": {"type": "json_schema",
                                      "schema": schema or DECISION_SCHEMA}},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model refused the request")
        # the reply's first text block holds the JSON string
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


class GroqBackend:
    """Groq-hosted open model as the decision engine (free tier friendly).

    Added (Anik, Jul 2026) so full multi-year runs can use Llama 3.3 70B on
    the Groq free tier (100k tokens/day) instead of a paid API. Mirrors the
    AnthropicBackend interface: decide(system, prompt) -> validated dict.
    Reads GROQ_API_KEY from the environment.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile",
                 max_tokens: int = 300):
        # imported here so non-Groq users don't need the groq package
        from groq import Groq
        self.client = Groq()                 # reads GROQ_API_KEY from env
        self.model = model
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        return self.model

    def decide(self, system: str, prompt: str, schema: dict = None) -> dict:
        """One decision: send the prompts, get validated JSON back.
        Raises on any failure - the caller decides what the fallback is."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            max_tokens=self.max_tokens,
            # JSON mode: Groq constrains the reply to be a valid JSON object
            # (the system prompt already demands the release/reasoning keys)
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
        data = json.loads(text)
        if "release_cfs" not in data:
            raise ValueError(f"missing release_cfs in reply: {text[:120]}")
        return data


# Request settings sent with every Ollama call (unchanged values). Kept in one
# place so the provenance record reports exactly what the payload uses.
OLLAMA_REQUEST_OPTIONS = {"temperature": 0, "num_ctx": 16384, "num_predict": 2048}


def backend_provenance(backend) -> dict:
    """Software provenance of the decision engine, for logs only - it never
    enters a prompt or affects a decision. Never raises."""
    fn = getattr(backend, "provenance", None)
    try:
        return fn() if callable(fn) else {"backend": getattr(backend, "name", None)}
    except Exception as exc:                       # pragma: no cover
        return {"backend": getattr(backend, "name", None),
                "error": f"{type(exc).__name__}: {exc}"}


class OllamaBackend:
    """A local model served by Ollama as the decision engine (stdlib only)."""

    def __init__(self, model: str = "gemma4:12b",
                 base_url: str = "http://localhost:11434",
                 timeout: float = 120.0, max_attempts: int = 2,
                 retry_delay_seconds: float = 2.0,
                 temperature=0, seed: int = None):
        # temperature: a number, or None = send NO temperature, so Ollama uses
        # the model's own default (gemma4's Modelfile value, else Ollama's
        # built-in default). seed: optional; makes a run at temperature > 0
        # repeatable on the same setup (one seed per Monte Carlo replicate).
        self.temperature = temperature
        self.seed = seed
        opts = {}
        if temperature is not None:
            opts["temperature"] = temperature
        opts["num_ctx"] = OLLAMA_REQUEST_OPTIONS["num_ctx"]
        opts["num_predict"] = OLLAMA_REQUEST_OPTIONS["num_predict"]
        if seed is not None:
            opts["seed"] = int(seed)
        self.request_options = opts            # exactly what every request sends
        self.model = model
        self.base_url = base_url.rstrip("/")   # normalize trailing slash
        self.timeout = timeout                 # local models can be slow
        self.max_attempts = max(1, int(max_attempts))
        self.retry_delay_seconds = max(0.0, float(retry_delay_seconds))

    @property
    def name(self) -> str:
        return self.model

    def provenance(self) -> dict:
        """Ollama version and the exact model build (digest), queried once.

        Recorded so that runs compared against each other can be shown to
        have used the same software and model file - at temperature 0 a
        different build can change answers from identical prompts. Failures
        are recorded, never raised; nothing here affects a decision.
        """
        if getattr(self, "_provenance", None) is not None:
            return self._provenance
        info = {"backend": "ollama", "model": self.model, "base_url": self.base_url,
                "request_options": dict(self.request_options),
                "temperature_setting": ("model default (not sent)" if self.temperature is None
                                        else self.temperature),
                "seed": self.seed,
                "think": False, "stream": False, "keep_alive": "30m"}
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/version", timeout=10) as r:
                info["ollama_version"] = json.loads(r.read().decode("utf-8")).get("version")
        except Exception as exc:
            info["ollama_version"] = None
            info["ollama_version_error"] = f"{type(exc).__name__}: {exc}"
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=10) as r:
                models = json.loads(r.read().decode("utf-8")).get("models", [])
            m = next((x for x in models
                      if self.model in (x.get("name"), x.get("model"))), None)
            info["model_digest"] = m.get("digest") if m else None
            if m:
                info["model_size_bytes"] = m.get("size")
                info["model_modified_at"] = m.get("modified_at")
                info["model_details"] = m.get("details")
            else:
                info["model_digest_error"] = "model not listed by /api/tags"
        except Exception as exc:
            info["model_digest"] = None
            info["model_digest_error"] = f"{type(exc).__name__}: {exc}"
        # the model's own default sampling parameters (from its Modelfile), so a
        # run at "default temperature" records which temperature that was
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/show",
                data=json.dumps({"model": self.model}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                params = json.loads(r.read().decode("utf-8")).get("parameters") or ""
            info["model_default_parameters"] = params
            m = re.search(r"^\s*temperature\s+([0-9.]+)", params, re.MULTILINE)
            info["model_default_temperature"] = float(m.group(1)) if m else None
        except Exception as exc:
            info["model_default_parameters"] = None
            info["model_default_temperature"] = None
            info["model_default_parameters_error"] = f"{type(exc).__name__}: {exc}"
        if self.temperature is None:
            info["effective_temperature"] = (
                info["model_default_temperature"]
                if info["model_default_temperature"] is not None
                else "Ollama built-in default (the model sets none)")
        else:
            info["effective_temperature"] = self.temperature
        self._provenance = info
        return info

    def decide(self, system: str, prompt: str, schema: dict = None) -> dict:
        """One decision via Ollama, with one transparent transient retry.

        The exact same prompt, schema, and temperature are used for the retry;
        reservoir state is not advanced between attempts. If every attempt
        fails, the policy/main driver decides whether to stop or fall back.

        Also records this call's timing and token counts on
        self.last_call_stats (wall_seconds, ollama_total_seconds,
        prompt_tokens, response_tokens) - Ollama reports these directly in
        its response, alongside the decision itself. AnthropicBackend/
        GroqBackend don't set this attribute, so callers should use
        getattr(backend, "last_call_stats", None) rather than assume it
        exists.
        """
        retry_errors = []
        total_wall_seconds = 0.0
        total_prompt_tokens = 0
        total_response_tokens = 0
        total_ollama_seconds = 0.0

        for attempt in range(1, self.max_attempts + 1):
            # Clear the previous attempt's diagnostics so a transport timeout
            # cannot inherit data from an earlier response.
            self.last_call_stats = None
            attempt_start = time.perf_counter()
            try:
                decision = self._decide_once(system, prompt, schema=schema)
                stats = dict(self.last_call_stats or {})
                attempt_wall = stats.get("wall_seconds")
                total_wall_seconds += (attempt_wall if attempt_wall is not None
                                       else time.perf_counter() - attempt_start)
                total_prompt_tokens += stats.get("prompt_tokens") or 0
                total_response_tokens += stats.get("response_tokens") or 0
                total_ollama_seconds += stats.get("ollama_total_seconds") or 0.0
                stats.update({
                    "wall_seconds": total_wall_seconds,
                    "ollama_total_seconds": total_ollama_seconds,
                    "prompt_tokens": total_prompt_tokens,
                    "response_tokens": total_response_tokens,
                    "backend_attempts": attempt,
                    "retry_errors": list(retry_errors),
                })
                self.last_call_stats = stats
                return decision
            except Exception as exc:
                stats = dict(self.last_call_stats or {})
                attempt_wall = stats.get("wall_seconds")
                total_wall_seconds += (attempt_wall if attempt_wall is not None
                                       else time.perf_counter() - attempt_start)
                total_prompt_tokens += stats.get("prompt_tokens") or 0
                total_response_tokens += stats.get("response_tokens") or 0
                total_ollama_seconds += stats.get("ollama_total_seconds") or 0.0
                retry_errors.append(f"{type(exc).__name__}: {exc}")
                if attempt >= self.max_attempts:
                    stats.update({
                        "wall_seconds": total_wall_seconds,
                        "ollama_total_seconds": total_ollama_seconds,
                        "prompt_tokens": total_prompt_tokens,
                        "response_tokens": total_response_tokens,
                        "backend_attempts": attempt,
                        "retry_errors": list(retry_errors),
                    })
                    self.last_call_stats = stats
                    raise
                print(
                    f"  Ollama attempt {attempt}/{self.max_attempts} failed "
                    f"({type(exc).__name__}); retrying the same decision...",
                    flush=True,
                )
                time.sleep(self.retry_delay_seconds)

        raise RuntimeError("unreachable Ollama retry state")

    def _decide_once(self, system: str, prompt: str,
                     schema: dict = None) -> dict:
        """Send one raw /api/chat request and parse its structured response."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,                   # wait for the complete answer
            "format": schema or DECISION_SCHEMA,  # policy-specific JSON schema
            # For thinking-capable Ollama models, reasoning is otherwise placed
            # in message.thinking and can consume the generation allowance before
            # message.content receives the required JSON object.
            "think": False,
            # Preserve the established 16k context so every retrieved DKP
            # excerpt fits with ample margin. The response itself is capped at
            # 2k tokens: valid decisions are much shorter, but earlier Gemma
            # responses occasionally used about 1,600 generated tokens. The
            # former 8k allowance could let malformed output run for minutes.
            "options": dict(self.request_options),  # temperature 0 by default = baseline
            "keep_alive": "30m",               # avoid reloading between months
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        wall_start = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        wall_seconds = time.perf_counter() - wall_start

        # Ollama returns these alongside message.content - total_duration
        # etc. are nanoseconds, so convert to seconds. Missing fields
        # (e.g. an older Ollama version) default to None rather than error.
        total_duration_ns = data.get("total_duration")
        message = data.get("message") or {}
        content = message.get("content") or ""
        thinking = message.get("thinking") or ""
        self.last_raw_content = content        # exact reply text, kept for the trace
        self.last_call_stats = {
            "wall_seconds": wall_seconds,
            "ollama_total_seconds": (
                total_duration_ns / 1e9 if total_duration_ns is not None else None
            ),
            "prompt_tokens": data.get("prompt_eval_count"),
            "response_tokens": data.get("eval_count"),
            "done_reason": data.get("done_reason"),
            "content_chars": len(content),
            "thinking_chars": len(thinking),
        }

        if not content.strip():
            raise ValueError(
                "Ollama returned empty message.content "
                f"(done_reason={data.get('done_reason')!r}, "
                f"eval_count={data.get('eval_count')!r}, "
                f"thinking_chars={len(thinking)})"
            )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Ollama returned invalid JSON in message.content: "
                f"{content[:200]!r}"
            ) from exc


# ===========================================================================
# SECTION 2 - RESERVOIR BASIC INFORMATION
# ===========================================================================

@dataclass
class ReservoirBasicInfo:
    """The reservoir facts available in the zero-shot condition.

    The DKP condition is given this SAME set of facts (see
    dkp_llm_release.py) and then, additionally, retrieved DKP excerpts -
    so document grounding is the only difference between the two
    conditions, not the baseline information.
    """

    name: str                     # e.g. "Prompton Reservoir"
    purpose: str                  # e.g. "flood control"
    capacity_af: float            # total storage capacity (acre-feet)
    max_release_cfs: float        # outlet / non-damaging release capacity
    min_release_cfs: float        # minimum (environmental) release
    river: str = ""               # river and location, if known
    normal_pool_af: float = None  # typical non-flood pool, if known (also
    #                                used as the fallback/annual-average
    #                                value when monthly_target_af is set)
    monthly_target_af: dict = None  # {1..12: acre-feet} first-of-month
    #                                target storage, for reservoirs run
    #                                against a seasonal elevation-target
    #                                schedule (e.g. Wallenpaupack) rather
    #                                than one steady conservation pool.
    #                                None for every other reservoir - see
    #                                resolve_normal_pool_af() below.
    operation_target_description: str = ""  # shared target supplied equally
    #                                         to zero-shot and DKP prompts
    decision_interval: str = "daily"  # daily or monthly; prompt wording only
    # --- zero-shot knowledge tier -------------------------------------
    public_profile: tuple = ()        # Wikipedia-level facts, one per string
    public_capacity_af: float = None  # capacity as publicly reported
    # --- shared operation target restated as storage --------------------
    target_storage_equivalents: dict = None  # {target_elevation_ft: storage_af}
    # --- prompt condition ----------------------------------------------
    # False (default): the prompt carries Prof. Yang's specified inputs only -
    #   inflow, beginning water level, previous simulated releases - plus the
    #   interval length. No storage figure of any kind reaches the LLM.
    # True: a SEPARATE condition that additionally supplies beginning storage
    #   and the operation target in storage terms, to BOTH LLM arms. Pending
    #   Prof. Yang's approval; results must be labelled with the condition.
    prompt_storage: bool = False
    # True (default, = the 2026-10-03 baseline): when storage is in the prompt,
    #   item 6 states the physically available release (inflow + usable
    #   storage) as a number, and the constraint bullet refers to it.
    # False: a SEPARATE test condition for the anchoring hypothesis - item 6 and
    #   every reference to it are removed from BOTH arms' prompts. Python's
    #   physical limit, clipping, audit and water balance are unchanged.
    show_availability_line: bool = True
    # Zero-shot knowledge version. True (default) = the 1300/1370 ft operation
    # target is in the zero-shot prompt. False = "Wikipedia-only": the target
    # sentence and its storage equivalents are removed (public sources give no
    # target levels); the audit then judges the model against the target IT
    # states, not the official one. Applies to the zero-shot arm only.
    show_operation_target: bool = True


# ===========================================================================
# SHARED PROMPT TEXT (imported by dkp_llm_release.py)
# ===========================================================================
# Every block below is used VERBATIM by both LLM conditions, so the baseline
# the two models receive cannot drift apart. The DKP condition adds its
# document-derived content AFTER these blocks; it never edits them.

AF_PER_CFS_DAY = 1.98347   # 1 cfs sustained for 1 day = 1.98347 acre-feet
SECONDS_PER_DAY_PROMPT = 86_400
CF_PER_ACREFT_PROMPT = 43_560.0


def cfs_to_af(cfs: float, days: float) -> float:
    """Volume (acre-feet) of a mean flow sustained over an interval."""
    return float(cfs) * float(days) * AF_PER_CFS_DAY


def cfs_to_cf(cfs: float, days: float) -> float:
    """Volume (cubic feet) of a mean flow sustained over an interval:
    cfs x 86,400 s/day x days. This is the water-balance unit."""
    return float(cfs) * SECONDS_PER_DAY_PROMPT * float(days)


def volume_text(cfs: float, days: float) -> str:
    """'<ft3> cubic feet (= <af> acre-feet) over <n> days' - cubic feet is the
    working unit Prof. Yang specified; acre-feet is kept for readability."""
    return (f"{cfs_to_cf(cfs, days):,.0f} cubic feet "
            f"(= {cfs_to_af(cfs, days):,.0f} acre-feet) over {int(days)} days")


def water_balance_lines() -> list:
    """Neutral physics shared VERBATIM by both LLM conditions. It explains how
    inflow and release change storage; it does not prescribe a release."""
    return [
        "Physical water balance (not an operating rule):",
        "- storage_change_cubic_feet = (inflow_cfs - release_cfs) * 86,400 * interval_days.",
        "- A release below inflow increases storage; a release equal to inflow",
        "  leaves storage approximately unchanged; a release above inflow decreases",
        "  storage. Passing inflow cannot refill a reservoir below its target.",
    ]


def _interval_days(date_text: str, decision_interval: str) -> int:
    """Length of the interval that began on date_text."""
    if decision_interval != "monthly":
        return 1
    return int(pd.Timestamp(date_text).days_in_month)


def public_reservoir_lines(info: "ReservoirBasicInfo") -> list:
    """Public (Wikipedia-level) reservoir facts - the zero-shot tier."""
    lines = [
        "Reservoir information (public sources):",
        f"- Name: {info.name}" + (f" on the {info.river}" if info.river else ""),
    ]
    lines += [f"- {fact}" for fact in info.public_profile]
    if info.public_capacity_af:
        lines.append(f"- Total capacity (publicly reported): "
                     f"{info.public_capacity_af:,.0f} acre-feet")
    return lines


def operation_target_lines(info: "ReservoirBasicInfo") -> list:
    """The shared operation target, in water-level and storage terms.

    Both target elevations are restated as storage using the rating curve
    that the simulation applies to all three methods. Python does not pick
    which target applies on a given date - the LLM does, from the sentence.
    """
    lines = []
    if info.operation_target_description:
        lines.append(f"- Operation target: {info.operation_target_description}")
    # storage information appears ONLY in the prompt-storage condition
    if info.prompt_storage and info.target_storage_equivalents:
        parts = "; ".join(
            f"{elev:.1f} ft = {stor * CF_PER_ACREFT_PROMPT:,.0f} cubic feet "
            f"(= {stor:,.0f} acre-feet)"
            for elev, stor in sorted(info.target_storage_equivalents.items())
        )
        lines.append(f"- Operation target in storage terms (from the rating "
                     f"curve): {parts}")
    return lines


def state_core_lines(info: "ReservoirBasicInfo", date: pd.Timestamp,
                     inflow_cfs: float, storage_af: float,
                     runtime_state: dict, history: list) -> list:
    """Numbered state block shared by both LLM conditions.

    Items 1-3 are the inputs specified by Prof. Yang, in his order of
    necessity; item 4 is the interval length; item 5 is beginning storage;
    item 6 is the physically available release ceiling (storage-dependent,
    so it only appears when storage is in the prompt). Every flow is also
    stated as a volume over its own interval, so the water-balance equation
    can be applied in one consistent unit.

    Item 1's inflow is the REALIZED mean for THIS interval - the actual
    average of the days that make up the current month, exactly as they
    occurred. It is not a forecast, and it is not the prior interval's
    value: the experiment design gives the model perfect knowledge of the
    current interval's inflow (confirmed with Prof. Yang - the retrospective
    simulation reflects what happened, not what could have been predicted in
    advance). A month's own mean can differ substantially from the month
    before or after it; that is expected, not a labelling error.
    """
    runtime_state = runtime_state or {}
    days = int(runtime_state.get("step_days") or 1)
    inflow_label = ("Today's inflow" if info.decision_interval == "daily"
                    else "Mean inflow for this month")
    lines = [
        f"Date: {date:%Y-%m-%d} ({date:%B}, day {date.dayofyear} of the year)",
        f"1. {inflow_label}: {inflow_cfs:,.1f} cfs "
        f"(= {volume_text(inflow_cfs, days)})",
    ]
    if runtime_state.get("pool_elevation_ft") is not None:
        lines.append(f"2. Water level at beginning of interval: "
                     f"{runtime_state['pool_elevation_ft']:.2f} ft NGVD29")
    else:
        lines.append("2. Water level at beginning of interval: unavailable")
    lines.append("3. Previous simulated release decisions (and what was actually released):")
    if history:
        for h in history:
            h_days = _interval_days(h["date"], info.decision_interval)
            dec = h["decision_release_cfs"]
            imp = h.get("implemented_release_cfs", dec)
            line = (f"   {h['date']}: decided {dec:,.1f} cfs; actually released "
                    f"{imp:,.1f} cfs (= {volume_text(imp, h_days)})")
            if imp < dec - 0.5:
                line += " - limited by the water available"
            elif imp > dec + 0.5:
                line += " - includes uncontrolled spill"
            lines.append(line)
    else:
        lines.append("   None (first simulated step).")
    lines.append(f"4. Number of days in this decision interval: {days}")
    if info.prompt_storage:
        lines.append(
            f"5. Storage at beginning of interval: "
            f"{storage_af * CF_PER_ACREFT_PROMPT:,.0f} cubic feet "
            f"(= {storage_af:,.0f} acre-feet)"
        )
        # Item 6 - the TRUE release ceiling for this interval. This is NOT
        # storage alone: a reservoir can correctly release far more than its
        # own storage when inflow is high (pass-through), and far less than
        # its storage when the target calls for holding water back. The
        # ceiling is storage above the inactive pool PLUS this interval's
        # inflow, exactly the quantity reservoir_model.py's water balance
        # enforces - stating it here lets the model see the same number the
        # audit will judge it against, rather than reconstruct it from items
        # 1 and 5 on its own (a step past decisions have often gotten wrong).
        available_cfs = runtime_state.get("physically_available_release_cfs")
        if available_cfs is not None and info.show_availability_line:
            lines.append(
                f"6. Maximum release given the water available this interval: "
                f"{available_cfs:,.1f} cfs (= this interval's inflow plus "
                f"storage above the inactive pool, spread over {days} days). "
                f"This is a hard ceiling, not a target: requesting more will "
                f"be reduced by the water balance regardless of the reason."
            )
    return lines


def resolve_normal_pool_af(info: ReservoirBasicInfo, date: pd.Timestamp) -> float:
    """Return the 'normal pool' storage (acre-feet) that applies on this
    specific date.

    Most reservoirs in this project hold one steady conservation pool all
    year (info.normal_pool_af) - for those, this just returns that value
    unchanged. A few, chiefly Wallenpaupack, are instead run against a
    MONTHLY schedule of target elevations (info.monthly_target_af). When
    that's set, this linearly interpolates between the current and next
    month's first-of-month target based on day-of-month, so the target a
    policy compares against moves smoothly across the year instead of
    jumping on the 1st - consistent with the license's own description of
    a gradually-managed guide curve ("generation... scheduled to gradually
    reduce the water surface elevation in the late summer and fall").

    NOTE: every value this returns comes from the reservoir's own
    documentation (WCM / FERC license / DRBC Water Code tables, via
    ReservoirConfig in reservoir_model.py). This function interpolates
    between documented values; it does not invent operating levels.
    """
    if not info.monthly_target_af:
        return info.normal_pool_af

    this_month = date.month
    next_month = 1 if this_month == 12 else this_month + 1
    start_val = info.monthly_target_af[this_month]
    end_val = info.monthly_target_af[next_month]
    frac = (date.day - 1) / date.days_in_month
    return start_val + frac * (end_val - start_val)


# ===========================================================================
# SECTION 3 - THE POLICY
# ===========================================================================

@dataclass
class ZeroShotLLMPolicy:
    """Daily release decisions made by an LLM from basic information only."""

    # marks this policy as LLM-backed, so reservoir_model.py knows to apply
    # its LLM-consultation criterion (see that file's simulate())
    uses_llm = True

    # --- required configuration ---------------------------------------
    info: ReservoirBasicInfo      # the basic facts fed to the LLM
    backend: object               # AnthropicBackend, GroqBackend or OllamaBackend
    # --- optional configuration (defaults follow the experiment design) -
    history_days: int = 2         # previous simulated decisions shown in prompt
    log_path: Path = None         # plain-text decision log (1 line per day)
    trace_path: Path = None       # complete per-call trace (JSONL): prompt, raw reply, audit
    sample_path: Path = None      # text file for sampled prompt/response pairs
    reasoning_log_fraction: float = 1.0    # keep every explanation (matches DKP)
    n_prompt_samples: int = 5     # full prompt/response pairs kept per run
    n_failure_samples: int = 5    # full prompts kept for FAILED calls (see
    #                               _record_failure_sample: failures are kept
    #                               in full, not sampled, because a run where
    #                               every call fails must still show a prompt)
    seed: int = 42                # RNG seed -> reproducible sampling
    # --- shared physics audit (identical checks to the DKP arm) --------
    audit_action: str = "warn"    # "warn" | "record" | "stop" - never corrects
    target_tolerance_ft: float = 0.5
    # --- symmetric self-correction (identical mechanism to the DKP arm) -
    max_audit_revisions: int = 0  # 0 = single-pass (the controlled condition).
    #   >0 asks the SAME model to re-answer after a failed audit, up to this
    #   many times; if still FAIL, the last candidate is accepted and the
    #   month is flagged - the run is never stopped by this loop itself.
    #   Any value > 0 is a separate, labelled self-correction experiment.

    def __post_init__(self):
        """Initialize the run-time state (nothing here talks to the LLM)."""
        self._history = []              # prior simulated release decisions
        # --- two DISTINCT notions of "last release" (kept separate so the
        # persistence fallback is unambiguous):
        #   _last_decision_release_cms    what this policy last ASKED for,
        #                                 after the safety clip but before
        #                                 the water balance touched it
        #   _last_implemented_release_cms actual total outflow after physical
        #                                 availability and spill (bookkeeping;
        #                                 never shown as a prior decision)
        # The fallback uses the prior DECISION, because it is this policy's own
        # prior intent. In accordance with the experiment specification, the
        # prompt history contains prior simulated DECISIONS, not spill-inclusive
        # outflow and not observations.
        self._last_decision_release_cms = None
        self._last_implemented_release_cms = None
        self._system_prompt = self._build_system_prompt()  # fixed for the run
        self._schema_kw = {}            # default: backend's own schema (= baseline request)
        if not self.info.show_operation_target:
            import copy as _copy, inspect as _inspect
            wiki = _copy.deepcopy(DECISION_SCHEMA)
            wiki["properties"]["applicable_target_ft"]["description"] = (
                "Water level (ft NGVD29) you are aiming for in this interval")
            if "schema" in _inspect.signature(self.backend.decide).parameters:
                self._schema_kw = {"schema": wiki}
        self._system_prompt_sha256 = sha256_text(self._system_prompt)
        self.provenance = backend_provenance(self.backend)
        write_trace(self.trace_path, {"type": "system_prompt", "arm": "zeroshot",
                                      "sha256": self._system_prompt_sha256,
                                      "text": self._system_prompt,
                                      "provenance": self.provenance,
                                      "show_availability_line": self.info.show_availability_line})
        self._rng = random.Random(self.seed)   # private RNG -> reproducible
        # --- counters, kept separate (one day is exactly one of: reuse,
        # LLM success, LLM failure/fallback)
        self.days_decided = 0           # total days decided
        self.reuse_days = 0             # days the driver reused a prior decision
        self.llm_attempts = 0           # days an LLM call was attempted
        self.llm_successes = 0          # attempts that returned a usable decision
        self.llm_failures = 0           # attempts that raised (timeout, bad JSON, ...)
        if self.audit_action not in ("warn", "record", "stop"):
            raise ValueError("audit_action must be 'warn', 'record' or 'stop'")
        self.audit_passes = 0
        self.audit_warnings = 0
        self.audit_failures = 0
        self.hard_physics_failures = 0      # attributed physically-impossible requests
        self.policy_failures = 0            # consistency / target-tracking failures
        self.unattributed_hard_physics = 0  # impossible requests without the info to know
        self.first_audit_failure = None
        self.audit_revision_attempts = 0    # revision calls actually made
        self.audit_revision_errors = 0      # revision calls that errored (candidate kept)
        self.audit_revision_successes = 0   # months that reached PASS/WARN after >=1 revision
        self._prompt_samples = []       # reservoir sample of SUCCESSFUL exchanges
        self._failure_samples = []      # first n_failure_samples FAILED calls, in full
        # True when the most recent LLM attempt failed and the release
        # returned was a fallback rather than a model decision.
        # reservoir_model.py reads this to force a retry the next day
        # instead of letting the reuse criterion propagate a failure.
        self.last_decision_failed = False
        self.total_wall_seconds = 0.0   # summed real call time (successes only)
        self.total_prompt_tokens = 0    # summed, when the backend reports it (Ollama only)
        self.total_response_tokens = 0  # summed, when the backend reports it (Ollama only)
        self.total_backend_attempts = 0 # raw HTTP/model attempts, including retries
        self.total_backend_retries = 0

    @property
    def llm_calls(self) -> int:
        """Successful LLM consultations (kept as an alias for readability in
        run summaries; llm_attempts/llm_failures give the fuller picture)."""
        return self.llm_successes

    # ------------------------------------------------------------------
    # 3a. PROMPT CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """The FIXED part of every prompt: who you are, what you know,
        what the rules of the game are. Built once; identical every call
        (which is what makes API-side prompt caching work)."""
        info = self.info
        interval_noun = "day" if info.decision_interval == "daily" else "month"
        public_tier = bool(info.public_profile)
        lines = [
            f"You are the operator of a reservoir, making one release decision per "
            f"{interval_noun}.",
            "",
        ]
        if public_tier:
            # ZERO-SHOT TIER = public, Wikipedia-level knowledge only. The
            # WCM release limits and crest-level capacity are deliberately
            # absent; they are document knowledge and belong to the DKP tier.
            lines += public_reservoir_lines(info)
            if info.show_operation_target:
                lines += operation_target_lines(info)
        else:
            # legacy facts, for reservoirs without a public profile yet
            lines += [
                "Reservoir information:",
                f"- Name: {info.name}" + (f" on the {info.river}" if info.river else ""),
                f"- Primary purpose: {info.purpose}",
                f"- Total storage capacity: {info.capacity_af:,.0f} acre-feet",
                f"- Maximum allowable release: {info.max_release_cfs:,.0f} cfs",
                f"- Minimum required release: {info.min_release_cfs:,.0f} cfs",
            ]
            if info.operation_target_description:
                lines += operation_target_lines(info)
            elif info.normal_pool_af is not None:
                lines.append(f"- Typical (non-flood) pool storage: "
                             f"{info.normal_pool_af:,.0f} acre-feet")
        lines += [
            "",
            f"Each {interval_noun} you will receive the current date, mean inflow,",
            "water level at the beginning of the interval, and the previous one or two",
            "simulated release decisions"
            + (", and storage at the beginning of the interval." if info.prompt_storage
               else "."),
            "Flows are also stated as volumes in cubic feet over their interval, the",
            "unit of the water balance. Decide the interval's mean release",
            "in cfs, consistent with the reservoir's purpose. You have no operating",
            "manual; use general reservoir-operation principles.",
            "",
            # This is neutral physics, not reservoir operating knowledge. Keep
            # this block text-identical in the zero-shot and DKP prompts.
            *water_balance_lines(),
            "",
            "Constraints you must respect:",
        ]
        if not public_tier:
            lines.append(f"- Release between {info.min_release_cfs:,.0f} and "
                         f"{info.max_release_cfs:,.0f} cfs.")
        lines += [
            ("- Do not plan to release more water than is available "
             "(see item 6 above for this interval's exact ceiling, when shown)."
             if info.show_availability_line else
             "- Do not plan to release more water than is available (storage + inflow)."),
            "- Avoid letting storage exceed capacity (uncontrolled spill).",
            "- Avoid abrupt interval-to-interval release changes unless conditions require them.",
            "",
            "Respond only with JSON, with the fields in this order:",
            ("  applicable_target_ft (the operation-target water level for this interval),"
             if info.show_operation_target else
             "  applicable_target_ft (the water level you are aiming for this interval),"),
            "  pool_position (below_target | at_target | above_target),",
            "  intended_storage_direction (increase | hold | decrease),",
            "  release_relation_to_inflow (below_inflow | equal_to_inflow | above_inflow),",
            "  reasoning (1-2 sentences), release_cfs (number).",
            "Decide the first four, then write the reasoning, then choose release_cfs.",
            "Make release_cfs consistent with the four fields and with your reasoning.",
        ]
        return "\n".join(lines)

    def _build_state_prompt(self, date: pd.Timestamp, inflow_cfs: float,
                            storage_af: float,
                            runtime_state: dict = None) -> str:
        """The VARIABLE part of the prompt: today's numbers plus a small
        table of the recent days, so the LLM can see the trend."""
        lines = state_core_lines(self.info, date, inflow_cfs, storage_af,
                                 runtime_state, self._history)
        lines.append("")
        lines.append("Decide the mean release for this interval (cfs).")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 3b. THE DAILY DECISION
    # ------------------------------------------------------------------

    def _audit_decision(self, date: pd.Timestamp, decision: dict,
                        requested_release_cfs: float, release_cfs: float,
                        inflow_cfs: float, storage_af: float,
                        runtime_state: dict) -> dict:
        """Run the shared physics audit and package it into one categorized
        dict, so both the initial call and every self-correction revision can
        be judged the same way, and the DKP arm's revision loop can be
        mirrored exactly.
        """
        rs = runtime_state or {}
        days = int(rs.get("step_days") or 1)
        storage_change_af = (inflow_cfs - release_cfs) * days * 1.98347
        target_storage_af = rs.get("seasonal_target_storage_af")
        if not self.info.show_operation_target:
            # Wikipedia-only: the gap is measured to the level the MODEL says it
            # is aiming for (same rating curve as the simulation), so the
            # "reduces the gap" check applies exactly as in the target version.
            conv = rs.get("storage_af_for_elevation")
            try:
                target_storage_af = conv(float(decision.get("applicable_target_ft")))
            except (TypeError, ValueError):
                target_storage_af = None
        err0 = err1 = None
        if target_storage_af is not None:
            err0 = abs(target_storage_af - storage_af)
            err1 = abs(target_storage_af - (storage_af + storage_change_af))
        res = physics_audit(
            decision, inflow_cfs=inflow_cfs, release_cfs=release_cfs,
            pool_ft=rs.get("pool_elevation_ft"),
            target_ft=rs.get("seasonal_target_ft"),
            min_release_cfs=self.info.min_release_cfs,
            max_release_cfs=self.info.max_release_cfs,
            prompt_storage=self.info.prompt_storage,
            target_error_start_af=err0, target_error_end_af=err1,
            target_tolerance_ft=self.target_tolerance_ft,
            requested_release_cfs=requested_release_cfs,
            physically_available_cfs=rs.get("physically_available_release_cfs"),
            target_known=self.info.show_operation_target,
        )
        hard = res["hard_physics"]; hard_unattr = res["hard_physics_unattributed"]
        policy_fails = res["policy"]; warnings = res["warnings"]
        failures = hard + policy_fails      # attributed to the model
        return {
            "audit_status": ("FAIL" if failures
                             else "WARN" if (warnings or hard_unattr) else "PASS"),
            "audit_failures": failures,
            "hard_physics_failures": hard,
            "hard_physics_unattributed": hard_unattr,
            "policy_failures": policy_fails,
            "audit_warnings": warnings,
            # False whenever the REQUEST was physically impossible, whoever is
            # to blame: formal trajectories should treat such months as invalid
            "request_physically_feasible": not (hard or hard_unattr),
            "target_error_start_af": None if err0 is None else round(err0, 1),
            "target_error_end_af": None if err1 is None else round(err1, 1),
        }

    def _build_audit_revision_prompt(self, original_prompt: str,
                                     decision: dict, audit: dict,
                                     revision_number: int) -> str:
        """Ask the LLM to repair its own internally inconsistent candidate.

        Mirrors the DKP arm's revision prompt exactly (same structure, same
        "no release value is being supplied" guarantee), except it points the
        model back at general reservoir-operation principles rather than at
        retrieved manual excerpts: zero-shot never receives a manual, and
        this step must not introduce one - that would break the knowledge-
        tier separation between the two arms.
        """
        failures = "\n".join(
            f"- {failure}" for failure in audit.get("audit_failures", [])
        )
        return (
            original_prompt
            + "\n\n--- REQUIRED SELF-CORRECTION "
            + f"{revision_number}/{self.max_audit_revisions} ---\n"
            + "Your previous candidate JSON was:\n"
            + json.dumps(decision, ensure_ascii=False, indent=2)
            + "\n\nThat candidate failed these deterministic consistency checks:\n"
            + failures
            + ("\nRe-read the same date, inflow, storage and operation target above, "
               if self.info.show_operation_target else
               "\nRe-read the same date, inflow and storage above, ")
            + "apply the physical water balance and general reservoir-operation "
              "principles, and revise your own decision so every listed "
              "contradiction is resolved. No release value is being supplied. "
              "Return only a complete replacement JSON object in the required schema."
        )

    def target_release(self, date: pd.Timestamp, inflow_now: float,
                       storage_start_m3: float,
                       runtime_state: dict = None) -> float:
        """Return the release decision (m^3/s) for one interval using the LLM.

        Called by reservoir_model.py only on days it has decided an LLM
        consultation is warranted; this method itself never skips the call.
        """
        # convert internal SI units to the operator-friendly US units used
        # in the prompt and the logs
        inflow_cfs = inflow_now / CFS_TO_CMS
        storage_af = storage_start_m3 / ACREFT_TO_M3
        self.days_decided += 1

        # --- STEP 1: build the prompt for today
        prompt = self._build_state_prompt(
            date, inflow_cfs, storage_af, runtime_state=runtime_state
        )

        # --- STEP 2: ask the LLM (with a safe fallback on ANY failure)
        self.llm_attempts += 1
        active_prompt = prompt                  # the prompt actually answered
        call_stats_records = []
        try:
            decision = self.backend.decide(self._system_prompt, prompt, **self._schema_kw)
            requested_release_cfs = float(decision["release_cfs"])
            if not math.isfinite(requested_release_cfs):
                # NaN or infinity must never reach the clip, where infinity
                # would silently become the maximum release
                raise ValueError(f"non-finite release_cfs: {decision['release_cfs']!r}")
            release_cfs = requested_release_cfs
            reasoning = str(decision.get("reasoning", ""))
            fallback = False
            self.llm_successes += 1
        except Exception as exc:   # network error, refusal, bad JSON, timeout...
            # persistence fallback: repeat the last release DECISION; on the
            # very first step there is no prior decision, so use the minimum
            decision = None
            requested_release_cfs = None
            release_cfs = (self._last_decision_release_cms / CFS_TO_CMS
                           if self._last_decision_release_cms is not None
                           else self.info.min_release_cfs)
            reasoning = f"fallback ({type(exc).__name__}: {exc})"
            fallback = True
            self.llm_failures += 1
        initial_stats = getattr(self.backend, "last_call_stats", None)
        if initial_stats:
            call_stats_records.append(dict(initial_stats))

        # --- STEP 3: safety clip. The stated bounds are enforced in code,
        # no matter what the LLM answered.
        release_cfs = float(min(max(release_cfs, self.info.min_release_cfs),
                                self.info.max_release_cfs))
        release_cms = release_cfs * CFS_TO_CMS
        self._last_decision_release_cms = release_cms  # remembered for next step

        # --- STEP 3b: SYMMETRIC SELF-CORRECTION - identical mechanism to the
        # DKP arm (register: "symmetric self-correction"). The audit is the
        # parser Prof. Yang described: it checks the model's own stated
        # target and consistency against the water balance, and never
        # supplies or suggests a release. On FAIL, the SAME model is handed
        # its own failed answer and asked to re-decide, up to
        # max_audit_revisions times. If it still fails after that many
        # attempts, the LAST candidate is accepted and the month is flagged -
        # this loop never stops the run by itself; only --zeroshot-audit-action
        # stop does, and only after the retries are exhausted.
        audit = None
        audit_revision_count = 0
        audit_revision_failures = []
        audit_revision_error = None
        if not fallback:
            audit = self._audit_decision(
                date, decision, requested_release_cfs, release_cfs,
                inflow_cfs, storage_af, runtime_state or {},
            )
            while (audit["audit_status"] == "FAIL"
                   and audit_revision_count < self.max_audit_revisions):
                audit_revision_failures.append(list(audit["audit_failures"]))
                audit_revision_count += 1
                self.audit_revision_attempts += 1
                active_prompt = self._build_audit_revision_prompt(
                    prompt, decision, audit, audit_revision_count
                )
                # the latest candidate the LLM actually produced, and its
                # audit; restored if this revision call errors (see except)
                prior = (decision, requested_release_cfs, release_cfs,
                         reasoning, audit)
                try:
                    decision = self.backend.decide(self._system_prompt, active_prompt,
                                                   **self._schema_kw)
                    requested_release_cfs = float(decision["release_cfs"])
                    if not math.isfinite(requested_release_cfs):
                        raise ValueError(
                            f"non-finite release_cfs: {decision['release_cfs']!r}"
                        )
                    release_cfs = float(min(
                        max(requested_release_cfs, self.info.min_release_cfs),
                        self.info.max_release_cfs,
                    ))
                    reasoning = str(decision.get("reasoning", ""))
                    revision_stats = getattr(self.backend, "last_call_stats", None)
                    if revision_stats:
                        call_stats_records.append(dict(revision_stats))
                    audit = self._audit_decision(
                        date, decision, requested_release_cfs, release_cfs,
                        inflow_cfs, storage_af, runtime_state or {},
                    )
                    write_trace(self.trace_path, {
                        "type": "revision", "arm": "zeroshot",
                        "date": f"{date:%Y-%m-%d}",
                        "revision_number": audit_revision_count,
                        "prompt": active_prompt,
                        "prompt_sha256": sha256_text(active_prompt),
                        "raw_response": getattr(self.backend, "last_raw_content", None),
                        "parsed": decision,
                        "requested_release_cfs": requested_release_cfs,
                        "audit_status": audit["audit_status"],
                        "audit_failures": audit["audit_failures"]})
                except Exception as exc:
                    write_trace(self.trace_path, {
                        "type": "revision", "arm": "zeroshot",
                        "date": f"{date:%Y-%m-%d}",
                        "revision_number": audit_revision_count,
                        "prompt": active_prompt,
                        "prompt_sha256": sha256_text(active_prompt),
                        "error": f"{type(exc).__name__}: {exc}"})
                    (decision, requested_release_cfs, release_cfs,
                     reasoning, audit) = prior
                    audit_revision_error = f"{type(exc).__name__}: {exc}"
                    self.audit_revision_errors += 1
                    break
            if audit["audit_status"] != "FAIL" and audit_revision_count:
                self.audit_revision_successes += 1
            release_cms = release_cfs * CFS_TO_CMS
            self._last_decision_release_cms = release_cms

        # --- STEP 4: record. Count the call, maybe sample it, write the log.
        # tell the driver whether this day's number came from the model or
        # from the fallback path (see reservoir_model.simulate STEP 0)
        self.last_decision_failed = fallback

        call_stats = call_stats_records[-1] if call_stats_records else None
        if call_stats:
            backend_attempts = int(call_stats.get("backend_attempts") or 1)
            self.total_backend_attempts += backend_attempts
            self.total_backend_retries += max(backend_attempts - 1, 0)
        if fallback:
            # ALWAYS keep failed prompts (up to n_failure_samples), never
            # sample them: a run of 100 attempts and 100 failures must still
            # produce the actual prompt that failed, which is exactly what
            # is needed to diagnose it.
            self._record_failure_sample(date, prompt, reasoning, release_cfs)
        else:
            self._sample_prompt(date, active_prompt, decision)
            for cs in call_stats_records:
                self.total_wall_seconds += cs.get("wall_seconds") or 0.0
                self.total_prompt_tokens += cs.get("prompt_tokens") or 0
                self.total_response_tokens += cs.get("response_tokens") or 0

        record = {
            "date": f"{date:%Y-%m-%d}",
            "outcome": "fallback" if fallback else "llm",
            "llm_attempted": True,
            "llm_succeeded": not fallback,
            "llm": self.backend.name,
            "inflow_cfs": round(inflow_cfs, 1),
            "storage_start_af": round(storage_af, 1),
            "llm_release_cfs_raw": (None if requested_release_cfs is None
                                    else round(requested_release_cfs, 1)),
            "decision_release_cfs": round(release_cfs, 1),
        }
        if runtime_state and runtime_state.get("pool_elevation_ft") is not None:
            record["pool_elevation_start_ft"] = round(
                runtime_state["pool_elevation_ft"], 2
            )
        # per-call timing/token counts, when the backend reports them
        # (Ollama does; AnthropicBackend/GroqBackend currently don't).
        # wall_seconds sums every attempt this step made (initial + revisions);
        # token/attempt fields are read from the LAST attempt only.
        if call_stats:
            record["wall_seconds"] = round(
                sum(cs.get("wall_seconds") or 0.0 for cs in call_stats_records), 2
            )
            if call_stats.get("prompt_tokens") is not None:
                record["prompt_tokens"] = call_stats["prompt_tokens"]
            if call_stats.get("response_tokens") is not None:
                record["response_tokens"] = call_stats["response_tokens"]
            for key in ("done_reason", "content_chars", "thinking_chars",
                        "backend_attempts", "retry_errors"):
                if call_stats.get(key) is not None:
                    record[key] = call_stats[key]

        # --- STEP 5: apply the (possibly revised) audit to the record. It
        # records or stops; it never suggests or replaces a release.
        audit_failed = False
        if audit is not None:
            for field in NEUTRAL_FIELD_NAMES:
                record[field] = decision.get(field)
            record["audit_status"] = audit["audit_status"]
            # three separate categories (register AU-01): hard physical
            # feasibility, operating/policy quality, and (DKP only, in the
            # other file) rule traceability
            record["hard_physics_failures"] = audit["hard_physics_failures"]
            record["hard_physics_unattributed"] = audit["hard_physics_unattributed"]
            record["policy_failures"] = audit["policy_failures"]
            record["audit_failures"] = audit["audit_failures"]
            record["audit_warnings"] = audit["audit_warnings"]
            # False whenever the REQUEST was physically impossible, whoever is
            # to blame: formal trajectories should treat such months as invalid
            record["request_physically_feasible"] = audit["request_physically_feasible"]
            record["target_error_start_af"] = audit["target_error_start_af"]
            record["target_error_end_af"] = audit["target_error_end_af"]
            record["audit_revision_count"] = audit_revision_count
            if audit_revision_failures:
                record["audit_revision_failures"] = audit_revision_failures
            if audit_revision_error:
                record["audit_revision_error"] = audit_revision_error
            if audit["audit_status"] == "FAIL":
                audit_failed = True
                self.audit_failures += 1
                if audit["hard_physics_failures"]:
                    self.hard_physics_failures += 1
                if audit["policy_failures"]:
                    self.policy_failures += 1
                if self.first_audit_failure is None:
                    self.first_audit_failure = {
                        "date": f"{date:%Y-%m-%d}",
                        "failures": list(audit["audit_failures"]),
                    }
            elif audit["audit_warnings"] or audit["hard_physics_unattributed"]:
                self.audit_warnings += 1
            else:
                self.audit_passes += 1
            if audit["hard_physics_unattributed"]:
                self.unattributed_hard_physics += 1

        # reasoning is logged for a random ~30% of successful calls; failure
        # reasons AND audit failures are ALWAYS logged, since they flag problems
        if (fallback or audit_failed
                or self._rng.random() < self.reasoning_log_fraction):
            record["reasoning"] = reasoning
        self._log(record)
        write_trace(self.trace_path, {
            "type": "call", "arm": "zeroshot", "date": f"{date:%Y-%m-%d}",
            "system_prompt_sha256": self._system_prompt_sha256,
            "prompt": prompt, "prompt_sha256": sha256_text(prompt),
            "raw_response": None if fallback else getattr(self.backend, "last_raw_content", None),
            "parsed": decision, "requested_release_cfs": requested_release_cfs,
            "decision_release_cfs": release_cfs, "outcome": "fallback" if fallback else "llm",
            "audit_status": record.get("audit_status"), "audit_failures": record.get("audit_failures"),
            "hard_physics_failures": record.get("hard_physics_failures"),
            "hard_physics_unattributed": record.get("hard_physics_unattributed"),
            "policy_failures": record.get("policy_failures"),
            "audit_revision_count": record.get("audit_revision_count"),
            "reasoning": reasoning})
        # stop on any hard-physics event, attributed or not, even AFTER
        # exhausting self-correction: an impossible request invalidates a
        # formal trajectory regardless of blame or how many retries were
        # tried. A policy-only FAIL that the model corrected on its own
        # (audit_status no longer FAIL) does NOT stop the run - that is the
        # whole point of the revision loop.
        if self.audit_action == "stop" and (
                audit_failed or record.get("hard_physics_unattributed")):
            raise RuntimeError(
                f"Zero-shot physics audit failed on {date:%Y-%m-%d} "
                f"after {audit_revision_count} revision(s): "
                + "; ".join((record.get("audit_failures") or [])
                            + (record.get("hard_physics_unattributed") or []))
            )
        return release_cms

    def record_reuse(self, date: pd.Timestamp, inflow_now: float,
                     storage_start_m3: float, decision_release_cms: float,
                     runtime_state: dict = None) -> None:
        """Log a day on which reservoir_model.py reused the prior release
        decision instead of consulting the LLM.

        The reuse DECISION is made in reservoir_model.py (that is where the
        inflow-change criterion lives); this method only records it, so the
        decision log still has one line per simulated day and the counters
        add up: days_decided = reuse_days + llm_attempts.
        """
        self.days_decided += 1
        self.reuse_days += 1
        self._last_decision_release_cms = decision_release_cms
        record = {
            "date": f"{date:%Y-%m-%d}",
            "outcome": "reuse",
            "llm_attempted": False,
            "inflow_cfs": round(inflow_now / CFS_TO_CMS, 1),
            "storage_start_af": round(storage_start_m3 / ACREFT_TO_M3, 1),
            "decision_release_cfs": round(decision_release_cms / CFS_TO_CMS, 1),
        }
        if runtime_state and runtime_state.get("pool_elevation_ft") is not None:
            record["pool_elevation_start_ft"] = round(
                runtime_state["pool_elevation_ft"], 2
            )
        self._log(record)

    # ------------------------------------------------------------------
    # 3c. BOOKKEEPING (history, sampling, logging, final outputs)
    # ------------------------------------------------------------------

    def record_outcome(self, date: pd.Timestamp, decision_release_cms: float,
                       storage_end_m3: float, inflow_cms: float,
                       implemented_release_cms: float = None) -> None:
        """Record the prior simulated decision after the water-balance step.

        The next prompt receives ``decision_release_cms`` exactly as requested
        by the experiment design. ``implemented_release_cms`` is retained only
        for bookkeeping because it may include availability clipping or
        uncontrolled spill, neither of which is an LLM decision.
        """
        if implemented_release_cms is None:
            implemented_release_cms = decision_release_cms
        self._last_implemented_release_cms = implemented_release_cms
        self._history.append({
            "date": f"{date:%Y-%m-%d}",
            "inflow_cfs": inflow_cms / CFS_TO_CMS,
            "decision_release_cfs": decision_release_cms / CFS_TO_CMS,
            "implemented_release_cfs": implemented_release_cms / CFS_TO_CMS,
            "storage_end_af": storage_end_m3 / ACREFT_TO_M3,
        })
        # keep only the most recent history_days entries
        if len(self._history) > self.history_days:
            self._history.pop(0)

    def _record_failure_sample(self, date, prompt: str, error: str,
                               fallback_release_cfs: float) -> None:
        """Keep the first n_failure_samples FAILED calls in full.

        Deliberately NOT reservoir-sampled. Successful calls are sampled
        because there are usually many and any one is representative;
        failures are the opposite - there may be only a handful, or there
        may be nothing BUT failures, and in either case the actual prompt
        that failed is the artifact needed to diagnose the problem. Keeping
        the first few means a run that fails immediately still writes a
        usable samples file.
        """
        if len(self._failure_samples) >= self.n_failure_samples:
            return
        self._failure_samples.append({
            "date": f"{date:%Y-%m-%d}",
            "prompt": prompt,                       # the EXACT text that failed
            "error": error,                         # exception type + message
            "fallback_release_cfs": fallback_release_cfs,
        })

    def _sample_prompt(self, date: pd.Timestamp, prompt: str, decision: dict) -> None:
        """Keep a uniform random sample of n_prompt_samples LLM exchanges.

        Uses RESERVOIR SAMPLING because the total number of LLM calls is not
        known in advance (the consultation criterion makes it data-dependent):
        keep the first n; afterwards, the i-th call replaces a kept one with
        probability n/i. Every call ends up equally likely to be kept.
        """
        pair = {
            "date": f"{date:%Y-%m-%d}",
            "prompt": prompt,               # the EXACT text sent to the LLM
            "llm_response": decision,       # the EXACT decision returned
        }
        if len(self._prompt_samples) < self.n_prompt_samples:
            self._prompt_samples.append(pair)
        else:
            j = self._rng.randint(0, self.llm_successes - 1)
            if j < self.n_prompt_samples:
                self._prompt_samples[j] = pair

    def _log(self, record: dict) -> None:
        """Append one readable text line per decision to the log file.

        Format:  date | key=value | key=value | ... | reasoning="..."
        """
        if self.log_path is None:
            return
        parts = [record["date"]]
        for key, value in record.items():
            if key in ("date", "reasoning"):    # date leads; reasoning trails
                continue
            parts.append(f"{key}={value}")
        if "reasoning" in record:
            parts.append(f'reasoning="{record["reasoning"]}"')
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(" | ".join(parts) + "\n")

    def finalize(self) -> None:
        """Write the sampled prompt/response pairs as readable text.
        reservoir_model.py calls this once, after the simulation ends."""
        # write the file if there is ANYTHING to show - including a run that
        # produced only failures, which is precisely when the samples file
        # matters most
        if self.sample_path is None or not (self._prompt_samples
                                            or self._failure_samples):
            return
        bar = "=" * 72
        # header + the system prompt (shared by every call) once at the top
        lines = [
            f"LLM decision engine: {self.backend.name}",
            f"Provenance: Ollama {self.provenance.get('ollama_version')} | model digest "
            f"{self.provenance.get('model_digest')} | availability line shown: "
            f"{self.info.show_availability_line}",
            f"Physics audit: {self.audit_passes} PASS, {self.audit_warnings} WARN, "
            f"{self.audit_failures} FAIL "
            f"(hard physics {self.hard_physics_failures}, "
            f"policy {self.policy_failures}, "
            f"unattributed-hard {self.unattributed_hard_physics}; "
            f"action={self.audit_action})",
            ("DIAGNOSTIC TRAJECTORY - NOT A VALID RESEARCH RESULT: first FAIL "
             f"{self.first_audit_failure['date']}"
             if self.audit_failures and self.audit_action != "stop" else ""),
            f"Days decided: {self.days_decided} "
            f"(LLM attempts {self.llm_attempts}: {self.llm_successes} succeeded, "
            f"{self.llm_failures} failed; {self.reuse_days} reuse steps)",
            f"Sampled {len(self._prompt_samples)} of {self.llm_successes} "
            f"successful LLM calls",
            "",
            bar,
            "SYSTEM PROMPT (identical for every call)",
            bar,
            self._system_prompt,
        ]
        # then each sampled exchange, in date order
        # --- FAILED calls first: they are the reason to open this file ---
        if self._failure_samples:
            lines += [
                "",
                bar,
                f"FAILED CALLS ({len(self._failure_samples)} of "
                f"{self.llm_failures} failures kept in full)",
                bar,
            ]
            for i, fail in enumerate(self._failure_samples, 1):
                lines += [
                    "",
                    f"--- FAILED CALL {i} - {fail['date']} ---",
                    f"error: {fail['error']}",
                    f"release used instead (fallback): "
                    f"{fail['fallback_release_cfs']:,.1f} cfs",
                    "",
                    "--- actual prompt sent to the LLM ---",
                    fail["prompt"],
                ]

        for i, pair in enumerate(sorted(self._prompt_samples,
                                        key=lambda p: p["date"]), 1):
            response = pair["llm_response"] or {}
            lines += [
                "",
                bar,
                f"SAMPLE {i} of {len(self._prompt_samples)} - {pair['date']}",
                bar,
                "--- actual prompt sent to the LLM ---",
                pair["prompt"],
                "",
                "--- actual LLM response ---",
                f"release_cfs: {response.get('release_cfs')}",
                f"reasoning: {response.get('reasoning', '')}",
            ]
        with open(self.sample_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
