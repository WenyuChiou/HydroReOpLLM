"""DKP-informed LLM reservoir release rule (the "DKP_LLM" method).

WHAT THIS FILE DOES
===================
Same release question as the other release modules -

    "Given the interval's mean inflow and current storage, what mean release
     should the reservoir make?"

- decided by an LLM, but at the FULL-knowledge tier of the NSF CDS&E
three-pager (RT2): the LLM is grounded in the reservoir's Decision Knowledge
Package (DKP), a structured extraction of the official water control manual
(one markdown file per reservoir, available at run time through its configured
path).

THE CONTROLLED COMPARISON
=========================
Both conditions receive the same baseline state and reservoir facts: the
same ReservoirBasicInfo fields rendered in the same shape (name, river,
purpose, capacity, max/min release, typical pool) and the same base state
block (date, inflow, storage, recent history, and physical pool elevation
when a documented conversion curve is configured).

The DKP condition additionally supplies document-derived operating knowledge
through retrieved DKP excerpts. It receives no separately injected seasonal
target, precomputed release recommendation, target-tracking controller output,
or above/below-target classification. The LLM must derive the applicable target
from the retrieved rules, compare the raw state values, and choose the release.

RETRIEVAL-AUGMENTED GENERATION (RAG), NOT COPY-PASTE
====================================================
The whole DKP is NOT pasted into the prompt. Instead:

    at startup           each decision interval
    ----------           ------------------------------------------------
    DKP .md file   --->  1. build a QUERY from the current raw state
      | split into           (see _make_query: real numbers, raw pool
      | sections              elevation, and direction of inflow change)
    TF-IDF index   --->  2. score every DKP section against the query
                         3. put the TOP-K sections into the prompt
                         4. the LLM applies those rules to decide

CORRECT CONCEPTUAL ARCHITECTURE
===============================
    today's state -> retrieve DKP text -> LLM reads the rules ->
    LLM interprets the rules -> LLM-selected release

The retriever's job stops at handing the LLM relevant excerpts. The driver
performs only state conversion and reservoir physics. A deterministic audit
observes the returned decision after the fact; it neither recommends nor
replaces a release. Final runs can stop rather than accepting an internally
contradictory or untraceable result.

WHY THIS MODULE DOES NOT SUBCLASS ZeroShotLLMPolicy
====================================================
An earlier version implemented DKPLLMPolicy as a subclass of
ZeroShotLLMPolicy, inheriting its skip-check, logging, sampling and
fallback machinery and overriding only the two prompt-building methods.
That made decision-relevant behavior used by DKP runs invisible when
reading or searching this file - a bug hunt had to already know to look in
the PARENT class. DKPLLMPolicy is therefore fully independent: every piece
of logic below is this class's own code. It shares with
zeroshot_llm_release.py only ReservoirBasicInfo (a plain data container) -
no decision logic. It exposes the same target_release /
record_reuse / record_outcome / finalize interface reservoir_model.py
expects, so the policies stay interchangeable at the call site without
either deriving from the other.

WHERE THE LLM-CONSULTATION CRITERION LIVES (not here)
======================================================
The inflow-change criterion that decides whether a given day needs an LLM
consultation lives in reservoir_model.py, as ONE constant shared by both
LLM conditions. It is run/cost control, not reservoir decision knowledge,
and keeping it in the driver means (a) it is visible for every method and
(b) DKP and zero-shot cannot silently drift apart on it. This class does
not decide whether to call the LLM; when target_release() is called it
calls the LLM, and reservoir_model.py calls record_reuse() instead on days
it judges a consultation unnecessary.
"""

import copy
import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Shared with zeroshot_llm_release.py: a plain data container of documented
# reservoir facts.
# No decision logic crosses this import - see module docstring.
from zeroshot_llm_release import (  # noqa: F401
    ReservoirBasicInfo,
    # shared, text-identical prompt blocks - formatting only, no decision logic
    cfs_to_af,
    cfs_to_cf,
    operation_target_lines,
    public_reservoir_lines,
    state_core_lines,
    volume_text,
    water_balance_lines,
    # shared, identical self-check fields and physics audit (both arms)
    NEUTRAL_DECISION_PROPERTIES,
    NEUTRAL_FIELD_NAMES,
    physics_audit,
    sha256_text,
    write_trace,
    backend_provenance,
)

# --- unit-conversion constants (this module's own copy, matching the
# convention reservoir_model.py already uses) --------------------------------
CFS_TO_CMS = 0.028316847      # cubic feet per second -> cubic meters per second
ACREFT_TO_M3 = 1233.4818      # acre-feet -> cubic meters


# DKP decisions carry auditable policy metadata in addition to the release.
# The backend accepts this policy-specific schema; zero-shot keeps its smaller
# release/reasoning schema, preserving the controlled comparison.
DKP_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        # neutral self-check fields FIRST, identical to the zero-shot schema
        **NEUTRAL_DECISION_PROPERTIES,
        "operating_mode": {
            "type": "string",
            "enum": [
                "pass_inflow",
                "store_toward_target",
                "draw_toward_target",
                "minimum_release",
                "flood_control",
                "post_flood_drawdown",
                "recreation_plan",
                "missing_information_fallback",
            ],
        },
        "rules_applied": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exact retrieved DKP section headings used",
        },
        "missing_inputs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Unavailable inputs that limit full WCM operation",
        },
        # reasoning, then release: the number comes LAST, after the self-checks,
        # the document fields and the reasoning. With the number first the
        # reasoning was written afterwards and could contradict it (2000-10:
        # JSON 500 cfs, reasoning concluding 100 cfs was correct).
        "reasoning": {
            "type": "string",
            "description": ("Brief rule citation and water-balance explanation: "
                            "the storage change the release will cause"),
        },
        "release_cfs": {
            "type": "number",
            "description": "Target mean release for the interval in cfs",
        },
    },
    "required": NEUTRAL_FIELD_NAMES + [
        "operating_mode",
        "rules_applied",
        "missing_inputs",
        "reasoning",
        "release_cfs",
    ],
    "additionalProperties": False,
}


# Model-boundary test condition: the exact baseline lines replaced or removed.
_BOUNDARY_REPLACE = {
    ("If required observations are unavailable, apply the DKP's",
     "missing-information fallback and state the limitation. Do not",
     "invent an unavailable downstream stage, observation, or rule."):
    ("This model represents the reservoir only: storage, inflow and release.",
     "Apply the storage, inflow, seasonal and release-limit rules.",
     "Do not invent an observation or rule."),
    ("- Missing downstream observations remain missing; use the",
     "  DKP fallback rather than reasoning as though they were observed."): (),
    ("- If the DKP does not provide a unique numeric release for the available",
     "  inputs, do not invent an official formula. Choose the most defensible",
     "  conservative action allowed by the retrieved rules, use",
     "  operating_mode=missing_information_fallback when appropriate, and state",
     "  exactly which observation or plan prevents full WCM application."):
    ("- If the DKP does not provide a unique numeric release for the available",
     "  inputs, do not invent an official formula. Choose the most defensible",
     "  action allowed by the retrieved rules and explain it in the reasoning."),
    ("  operating_mode, rules_applied, missing_inputs,",):
    ("  operating_mode, rules_applied,",),
    ("- Follow the DKP's rate-of-change and downstream-protection rules.",):
    ("- Follow the DKP's rate-of-change rules.",),
}


def _apply_model_boundary(lines: list) -> list:
    """Replace each baseline block exactly once; fail loudly if the baseline
    text ever changes, so the test condition can never silently drift."""
    out = list(lines)
    for old, new in _BOUNDARY_REPLACE.items():
        k = len(old)
        hits = [i for i in range(len(out) - k + 1) if tuple(out[i:i + k]) == old]
        if len(hits) != 1:
            raise RuntimeError(f"model-boundary text not found exactly once: {old[0]!r}")
        i = hits[0]
        out[i:i + k] = list(new)
    return out


CATEGORY_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def release_categories(min_cfs: float, max_cfs: float, n: int) -> list:
    """Release categories built ONLY from the manual's minimum and maximum
    release: n ranges spaced evenly on a logarithmic scale (equal-width ranges
    put every monthly release in the lowest one). Inner edges are rounded to
    whole cfs. Returns [(label, low_cfs, high_cfs, representative_cfs)], the
    representative value being the geometric midpoint (used only in
    'midpoint' mode)."""
    if not 1 <= n <= len(CATEGORY_LABELS):
        raise ValueError(f"number of release categories must be 1-{len(CATEGORY_LABELS)}")
    if not (0 < min_cfs < max_cfs):
        raise ValueError("release categories need 0 < minimum < maximum release")
    ratio = (max_cfs / min_cfs) ** (1.0 / n)
    edges = [float(min_cfs)] + [float(round(min_cfs * ratio ** k)) for k in range(1, n)] + [float(max_cfs)]
    return [(CATEGORY_LABELS[k], edges[k], edges[k + 1],
             float(round(math.sqrt(edges[k] * edges[k + 1])))) for k in range(n)]


def dkp_schema(include_missing_inputs: bool = True) -> dict:
    """The DKP answer format. With include_missing_inputs=False (the
    model-boundary test condition) the missing_inputs field and the
    missing_information_fallback operating mode are removed; everything
    else - including the field order - is unchanged."""
    if include_missing_inputs:
        return DKP_DECISION_SCHEMA
    s = copy.deepcopy(DKP_DECISION_SCHEMA)
    del s["properties"]["missing_inputs"]
    s["properties"]["operating_mode"]["enum"].remove("missing_information_fallback")
    s["required"].remove("missing_inputs")
    return s

# tokens = lowercase words/numbers. Digit-grouping commas are stripped FIRST
# (see _tokenize), so "148,210" indexes as the single token "148210" rather
# than as "148" and "210" - otherwise a DKP table row written with commas
# could never match a query number written without them, and the two short
# fragments would collide with unrelated table cells.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")
_DIGIT_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")


def _tokenize(text: str) -> list:
    """Lowercase a text and split it into simple word tokens.

    Applied to BOTH the DKP sections (at index time) and the retrieval
    query, so both sides normalize numbers the same way:

        DKP:   "148,210 acre-feet"  ->  "148210", "acre-feet"
        query: "148210 acre-feet"   ->  "148210", "acre-feet"

    Keeps things like "R-RELEASE" -> "r-release" and "el_rec_pool" intact.
    """
    return _TOKEN_RE.findall(_DIGIT_COMMA_RE.sub("", text.lower()))


# ===========================================================================
# SECTION 1 - RETRIEVAL OVER THE DKP MARKDOWN
# ===========================================================================

class DKPRetriever:
    """TF-IDF retrieval over the heading-delimited sections of a DKP file.

    TF-IDF in one sentence: a section scores high for a query word if the
    word appears OFTEN in that section (TF = term frequency) but RARELY in
    the other sections (IDF = inverse document frequency) - so distinctive
    rule vocabulary wins over ubiquitous filler words.
    """

    def __init__(self, dkp_path: Path, min_section_chars: int = 80):
        self.dkp_path = Path(dkp_path)
        text = self.dkp_path.read_text(encoding="utf-8")   # load the DKP .md
        self.sections = self._split_sections(text, min_section_chars)
        self.layout = "sections"                            # v1.3 / v1.4 layout
        if (not any(h == "Core Rule Priority and Release Constraints" for h, _ in self.sections)
                and any(h.startswith("§2.3 Decision Rules") for h, _ in self.sections)):
            self.sections = self._split_v12_rules(self.sections)
            self.layout = "v1.2-rules"
        self._index()                                       # build TF/IDF tables

    # ------------------------------------------------------------------
    @staticmethod
    def _split_v12_rules(sections: list) -> list:
        """DKP v1.2 keeps all decision rules in ONE section (§2.3), each rule
        starting with a bold "**R-NAME (...)**" line. Split it into one chunk per
        rule, so rules can be retrieved (or excluded) individually. The file is
        not changed; the text of every rule is kept exactly."""
        out = []
        for heading, body in sections:
            if not heading.startswith("§2.3 Decision Rules"):
                out.append((heading, body))
                continue
            lines = body.splitlines(); starts = [i for i, l in enumerate(lines) if l.strip().startswith("**R-")]
            if starts and starts[0] > 0 and "\n".join(lines[:starts[0]]).strip():
                out.append((heading, "\n".join(lines[:starts[0]]).strip()))
            for k, i in enumerate(starts):
                j = starts[k + 1] if k + 1 < len(starts) else len(lines)
                title = re.sub(r"\*\*", "", lines[i].strip()).strip()
                out.append((title, "\n".join(lines[i + 1:j]).strip()))
        return out

    @staticmethod
    def _split_sections(text: str, min_chars: int) -> list:
        """Split the markdown into (heading, body) sections.

        Every markdown heading line ('#', '##', ...) outside a fenced code
        block starts a new section.
        Sections with very short bodies are merged into the NEXT section so
        that a rule never gets separated from its surrounding context.
        """
        sections, heading, buf = [], "Preamble", []
        in_fence = False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                in_fence = not in_fence
                buf.append(line)
            elif not in_fence and re.match(r"^#{1,6}\s+", line):
                sections.append((heading, "\n".join(buf).strip()))
                heading, buf = line.strip("# ").strip(), []
            else:                                    # body line -> accumulate
                buf.append(line)
        sections.append((heading, "\n".join(buf).strip()))  # flush the last one

        # merge tiny sections forward (heading chains join with " / ")
        merged = []
        for heading, body in sections:
            if merged and len(merged[-1][1]) < min_chars:
                prev_h, prev_b = merged.pop()
                heading = f"{prev_h} / {heading}"
                body = f"{prev_b}\n{body}".strip()
            merged.append((heading, body))
        # drop sections that ended up empty
        return [(h, b) for h, b in merged if b]

    # ------------------------------------------------------------------
    def _index(self) -> None:
        """Precompute term frequencies (per section) and IDF weights (global).
        Done once at startup so each retrieval is just a dot product."""
        self._tf = []                      # one {token: count} dict per section
        df = {}                            # document frequency of each token
        for heading, body in self.sections:
            counts = {}
            for tok in _tokenize(heading + " " + body):
                counts[tok] = counts.get(tok, 0) + 1
            self._tf.append(counts)
            for tok in counts:             # count each token once per section
                df[tok] = df.get(tok, 0) + 1
        n = len(self.sections)
        # smoothed IDF: rare tokens get large weights, ubiquitous ones ~1
        self._idf = {tok: math.log((1 + n) / (1 + d)) + 1.0
                     for tok, d in df.items()}

    # ------------------------------------------------------------------
    def retrieve(self, query: str, k: int = 4) -> list:
        """Return the k most relevant sections as (heading, body) tuples.

        The query is DEDUPLICATED before scoring: each distinct token counts
        once, however many of the query's phrases happened to contain it.
        Otherwise common words ('release', 'pool', 'flood') would be
        weighted by how many phrases mention them - an accident of how the
        query text was assembled, not a statement about relevance.
        """
        q_tokens = list(dict.fromkeys(_tokenize(query)))   # order-preserving dedup
        scores = []
        for i, counts in enumerate(self._tf):
            # normalize by sqrt(section length) so long sections don't win
            # merely by containing more words
            length_norm = 1.0 / math.sqrt(1 + sum(counts.values()))
            score = sum(counts.get(t, 0) * self._idf.get(t, 0.0)
                        for t in q_tokens)
            scores.append((score * length_norm, i))
        top = sorted(scores, reverse=True)[:k]        # best k by score
        return [self.sections[i] for score, i in top if score > 0]


# ===========================================================================
# SECTION 2 - THE POLICY (fully independent - see module docstring)
# ===========================================================================

@dataclass
class DKPLLMPolicy:
    """Daily release decisions made by an LLM grounded in the reservoir's DKP
    through retrieval-augmented generation."""

    # marks this policy as LLM-backed, so reservoir_model.py knows to apply
    # its LLM-consultation criterion (see that file's simulate())
    uses_llm = True

    # --- required configuration ---------------------------------------
    info: ReservoirBasicInfo      # the SAME basic facts the zero-shot condition gets
    backend: object               # anything exposing .decide(system, prompt)
    dkp_path: Path = None         # the reservoir's DKP markdown file (required)
    # --- optional configuration ----------------------------------------
    top_k: int = 5                # essential rules plus applicable event sections
    history_days: int = 2         # previous simulated decisions shown in prompt
    log_path: Path = None         # plain-text decision log (1 line per day)
    trace_path: Path = None       # complete per-call trace (JSONL): prompt, excerpts, raw reply
    sample_path: Path = None      # text file for sampled prompt/response pairs
    reasoning_log_fraction: float = 1.0    # validation runs retain every explanation
    n_prompt_samples: int = 5     # full prompt/response pairs kept per run
    n_failure_samples: int = 5    # full prompts kept for FAILED calls (see
    #                               _record_failure_sample: failures are kept
    #                               in full, not sampled, because a run where
    #                               every call fails must still show a prompt)
    seed: int = 42                # RNG seed -> reproducible sampling
    audit_action: str = "warn"    # "warn" | "record" | "stop"
    #   warn   - classify and log, continue the run
    #   record - identical to warn, but the run is explicitly marked a
    #            DIAGNOSTIC trajectory: FAIL decisions entered the storage
    #            record, so the output must not be reported as a result
    #   stop   - abort before an invalid decision alters storage
    # Classification is ALWAYS FAIL; only the ACTION differs. Use "stop"
    # for any run whose output is reported; use "record" only to document
    # a failure mode across a full season.
    target_tolerance_ft: float = 0.5
    # True (default, = the 2026-10-03 baseline). False = the model-boundary
    # test condition: no missing_inputs field, no missing-information fallback
    # mode, no always-retrieved fallback section, and the missing-information
    # instructions replaced by one neutral statement of the model's scope.
    include_missing_inputs: bool = True
    # 0 (default) = numerical mode: the LLM gives release_cfs from 0 upward.
    # N > 0 = category mode: N release ranges built from the manual's minimum
    # and maximum release (log-spaced). The LLM picks a category; with
    # category_value "llm" it also gives release_cfs inside that range (Python
    # only checks it), with "midpoint" Python applies the range's geometric
    # midpoint. DKP only - zero-shot has no manual release limits.
    release_categories: int = 0
    category_value: str = "llm"
    max_audit_revisions: int = 0  # 0 = single-pass (the controlled condition).
    #   >0 makes the run a SEPARATE, labelled DKP self-correction experiment:
    #   zero-shot has no equivalent revision step, so a run with revisions is
    #   not a like-for-like comparison with zero-shot.

    def __post_init__(self):
        """Initialize the run-time state (nothing here talks to the LLM)."""
        if self.dkp_path is None:
            raise ValueError("DKPLLMPolicy requires dkp_path (the reservoir's DKP file)")
        if self.audit_action not in ("warn", "record", "stop"):
            raise ValueError("audit_action must be 'warn', 'record' or 'stop'")
        self._retriever = DKPRetriever(self.dkp_path)
        self._schema = dkp_schema(self.include_missing_inputs)
        self._categories = []
        if self.release_categories:
            if self.category_value not in ("llm", "midpoint"):
                raise ValueError("category_value must be 'llm' or 'midpoint'")
            self._categories = release_categories(self.info.min_release_cfs,
                                                  self.info.max_release_cfs,
                                                  self.release_categories)
            base = self._schema
            props, req = {}, []
            for key, val in base["properties"].items():
                if key == "release_cfs":
                    props["release_category"] = {
                        "type": "string", "enum": [c[0] for c in self._categories],
                        "description": "Release category chosen from the listed ranges"}
                    if self.category_value == "llm":
                        props["release_cfs"] = copy.deepcopy(val)
                    continue
                props[key] = copy.deepcopy(val)
            for key in base["required"]:
                if key == "release_cfs":
                    req.append("release_category")
                    if self.category_value == "llm":
                        req.append("release_cfs")
                    continue
                req.append(key)
            self._schema = dict(copy.deepcopy(base), properties=props, required=req)
        self._history = []              # prior simulated release decisions
        # two DISTINCT notions of "last release", kept separate so the
        # persistence fallback is unambiguous (same convention as the
        # zero-shot policy):
        #   _last_decision_release_cms    what this policy last ASKED for
        #                                 (post safety-clip, pre water balance)
        #   _last_implemented_release_cms actual total outflow after physical
        #                                 availability and spill (bookkeeping;
        #                                 never shown as a prior decision)
        # The fallback repeats the policy's prior intent. Prompt history shows
        # prior simulated DECISIONS, not spill-inclusive outflow or observations.
        self._last_decision_release_cms = None
        self._last_implemented_release_cms = None
        self._system_prompt = self._build_system_prompt()  # fixed for the run
        self._system_prompt_sha256 = sha256_text(self._system_prompt)
        self._last_retrieved_excerpts = []
        self.provenance = backend_provenance(self.backend)
        write_trace(self.trace_path, {"type": "system_prompt", "arm": "dkp",
                                      "sha256": self._system_prompt_sha256,
                                      "text": self._system_prompt,
                                      "provenance": self.provenance,
                                      "show_availability_line": self.info.show_availability_line})
        self._rng = random.Random(self.seed)   # private RNG -> reproducible
        # counters, kept separate (one day is exactly one of: reuse,
        # LLM success, LLM failure/fallback)
        self.days_decided = 0           # total days decided
        self.reuse_days = 0             # days the driver reused a prior decision
        self.llm_attempts = 0           # days an LLM call was attempted
        self.llm_successes = 0          # attempts that returned a usable decision
        self.llm_failures = 0           # attempts that raised (timeout, bad JSON, ...)
        self._prompt_samples = []       # reservoir sample of SUCCESSFUL exchanges
        self._failure_samples = []      # first n_failure_samples FAILED calls, in full
        # True when the most recent LLM attempt failed and the release
        # returned was a fallback rather than a model decision.
        # reservoir_model.py reads this to force a retry the next day
        # instead of letting the reuse criterion propagate a failure.
        self.last_decision_failed = False
        self.total_wall_seconds = 0.0
        self.total_prompt_tokens = 0
        self.total_response_tokens = 0
        self.total_backend_attempts = 0 # raw HTTP/model attempts, including retries
        self.total_backend_retries = 0
        self.audit_passes = 0
        self.audit_warnings = 0
        self.audit_failures = 0
        self.physics_audit_failure_count = 0   # shared metric, comparable with zero-shot
        self.hard_physics_failures = 0      # attributed physically-impossible requests
        self.policy_failures = 0            # consistency / target-tracking failures
        self.unattributed_hard_physics = 0  # impossible requests without the info to know
        self.audit_revision_attempts = 0
        self.audit_revision_errors = 0   # revision calls that errored (candidate kept)
        self.audit_revision_successes = 0
        # first failing step, so a diagnostic run can report where the
        # trajectory stopped being a valid research result
        self.first_audit_failure = None
        self._last_retrieved_headings = []

    @property
    def llm_calls(self) -> int:
        """Successful LLM consultations (alias for run summaries)."""
        return self.llm_successes

    # ------------------------------------------------------------------
    # 2a. PROMPT CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        """The FIXED part of every prompt: the same baseline reservoir facts
        the zero-shot condition receives, plus how to use the retrieved DKP
        excerpts. Built once; identical every call (so API-side prompt
        caching works).

        Deliberately tells the LLM to apply whatever operating zones,
        decision rules, release constraints, rating tables and seasonal
        guidance turn up in the RETRIEVED TEXT. The code never encodes a
        specific rule (no "if month == 12: ..."); it only chooses which
        excerpts to retrieve, then leaves interpretation to the LLM.
        """
        info = self.info
        interval_noun = "day" if info.decision_interval == "daily" else "month"
        lines = [
            f"You are the water control manager operating {info.name}"
            + (f" on the {info.river}" if info.river else "") + ",",
            f"making one release decision per {interval_noun}.",
            "",
        ]
        if info.public_profile:
            # --- IDENTICAL baseline to the zero-shot condition (shared code) ---
            lines += public_reservoir_lines(info)
            lines += operation_target_lines(info)
            # --- what this tier ADDS: constants from the water control manual ---
            lines += [
                "",
                "From the reservoir's water control manual:",
                f"- Storage at spillway crest (el. 1450.0 ft): "
                f"{info.capacity_af:,.0f} acre-feet",
                f"- Maximum allowable release: {info.max_release_cfs:,.0f} cfs",
                f"- Minimum required release: {info.min_release_cfs:,.0f} cfs",
            ]
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
            # --- the one thing this condition adds: document grounding ---
            "Your operating knowledge comes from the reservoir's Decision",
            "Knowledge Package (DKP), extracted from the project's official",
            f"water control manual. Each {interval_noun}, the sections of the DKP most",
            "relevant to the current conditions are retrieved and provided to",
            "you together with the system state. Base your decision on those",
            "retrieved DKP excerpts: apply their operating zones, decision",
            "rules, release constraints, rating tables, and seasonal guidance.",
            "If required observations are unavailable, apply the DKP's",
            "missing-information fallback and state the limitation. Do not",
            "invent an unavailable downstream stage, observation, or rule.",
            "",
            "How to apply the DKP in this simulation:",
            "- Storage-to-elevation conversion is physical preprocessing and the current",
            "  pool elevation may be supplied. Apply the shared operation target stated",
            "  in the reservoir information; do not derive a different target from the DKP.",
            "- Compare the current pool with that target yourself; no precomputed",
            "  above-target or below-target interpretation is supplied.",
            "- Gate-position rate limits are not discharge-rate limits. Do not convert",
            "  them to cfs per hour without the required gate-rating information.",
            "- Missing downstream observations remain missing; use the",
            "  DKP fallback rather than reasoning as though they were observed.",
            "- Exhibit D's numerical recreation calendar is explicitly specific to 2014.",
            "  In every other year, apply only the structural recreation constraints",
            "  stated by the DKP and identify the annual calendar as unavailable; do not",
            "  transfer the 2014 weekday, weekend, event-date, or numeric release schedule.",
            "- No recommended release, target-tracking controller output, or precomputed",
            "  above/below-target label is supplied. Select the release independently",
            "  from the retrieved DKP rules and the raw state values.",
            "- If the DKP does not provide a unique numeric release for the available",
            "  inputs, do not invent an official formula. Choose the most defensible",
            "  conservative action allowed by the retrieved rules, use",
            "  operating_mode=missing_information_fallback when appropriate, and state",
            "  exactly which observation or plan prevents full WCM application.",
            "- No external reduced-domain release rule is supplied in this run.",
            "- Use store_toward_target or draw_toward_target only when the selected",
            "  release actually changes storage in that direction. Use pass_inflow only",
            "  when the selected release is approximately equal to inflow.",
            "- During seasonal refill, report store_toward_target; during seasonal",
            "  drawdown, report draw_toward_target. Reserve recreation_plan for an",
            "  applicable dated recreation-release instruction whose calendar is known.",
            "",
            # This is neutral physics, not reservoir operating knowledge. Keep
            # this block text-identical in the zero-shot and DKP prompts.
            *water_balance_lines(),
            "",
            "Reduced-model hard constraints on your answer:",
            f"- Release between {info.min_release_cfs:,.0f} and "
            f"{info.max_release_cfs:,.0f} cfs.",
            ("- Do not plan to release more water than is available "
             "(see item 6 above for this interval's exact ceiling, when shown)."
             if info.show_availability_line else
             "- Do not plan to release more water than is available (storage + inflow)."),
            "- Follow the DKP's rate-of-change and downstream-protection rules.",
            "- The 50-10,000 cfs bounds cannot represent the WCM's declared-drought",
            "  43-cfs exception or its conditional post-flood >10,000-cfs exception;",
            "  identify those conditions as outside the reduced-model scope.",
            "",
            "Before answering, check that the proposed release changes storage in the",
            "direction claimed by the reasoning. Respond only with JSON, with the",
            "fields in this order:",
            "  applicable_target_ft (the operation-target water level for this interval),",
            "  pool_position (below_target | at_target | above_target),",
            "  intended_storage_direction (increase | hold | decrease),",
            "  release_relation_to_inflow (below_inflow | equal_to_inflow | above_inflow),",
            "  operating_mode, rules_applied, missing_inputs,",
            "  reasoning, release_cfs (number).",
            "Decide the first four, then write the reasoning, then choose release_cfs.",
            "Make release_cfs consistent with the four fields and with your reasoning.",
            "In rules_applied, copy the exact heading of every retrieved DKP section",
            "used; do not invent rule identifiers.",
        ]
        if not self.include_missing_inputs:
            lines = _apply_model_boundary(lines)
        if self._categories:
            lines = self._apply_category_prompt(lines)
        return "\n".join(lines)

    def _apply_category_prompt(self, lines: list) -> list:
        """Category mode: list the ranges and ask for a category. Exact,
        fail-loudly replacements of the baseline wording."""
        llm = self.category_value == "llm"
        info = self.info
        table = [f"Release categories (the water control manual's release limits, "
                 f"{info.min_release_cfs:,.0f} to {info.max_release_cfs:,.0f} cfs, divided into "
                 f"{len(self._categories)} ranges spaced evenly on a logarithmic scale):"]
        for lab, lo, hi, mid in self._categories:
            table.append(f"  {lab}: {lo:,.0f} to {hi:,.0f} cfs" + ("" if llm else f" (applied as {mid:,.0f} cfs)"))
        table.append("Select the category whose range contains the release you choose; "
                     "release_cfs must lie inside it." if llm else
                     "Select one category; the release applied is the value shown for that category.")
        table.append("")
        swaps = {
            "  reasoning, release_cfs (number).":
                ("  reasoning, release_category (one letter), release_cfs (number inside that category)."
                 if llm else "  reasoning, release_category (one letter)."),
            "Decide the first four, then write the reasoning, then choose release_cfs.":
                ("Decide the first four, then write the reasoning, then choose the release category, "
                 "then release_cfs inside it." if llm else
                 "Decide the first four, then write the reasoning, then choose the release category."),
            "Make release_cfs consistent with the four fields and with your reasoning.":
                ("Make the category and release_cfs consistent with the four fields and with your reasoning."
                 if llm else "Make the category consistent with the four fields and with your reasoning."),
        }
        out = list(lines)
        for old, new in swaps.items():
            if out.count(old) != 1:
                raise RuntimeError(f"category text not found exactly once: {old!r}")
            out[out.index(old)] = new
        anchor = "Before answering, check that the proposed release changes storage in the"
        if out.count(anchor) != 1:
            raise RuntimeError("category table anchor not found exactly once")
        i = out.index(anchor)
        return out[:i] + table + out[i:]

    def _cites_retrieved_rule(self, rule) -> bool:
        """True when a cited rule is one that was retrieved this step: its full
        heading, or the rule's own name - e.g. "R-RELEASE" for "R-RELEASE (composite
        ...)", or "R-MINFC" for "R-MINNORM, R-MINFC, R-MINDROUGHT (...)". A rule that
        was NOT retrieved, or an invented one, still fails."""
        cited = str(rule).strip()
        for heading in self._last_retrieved_headings:
            if cited == heading:
                return True
            names = [n.strip() for n in heading.split(" (")[0].split(",")]
            if cited in names or cited == heading.split(" (")[0].strip():
                return True
        return False

    def _apply_category(self, decision: dict) -> dict:
        """Midpoint mode: turn the chosen category into the release Python
        applies. LLM mode: nothing here (the audit checks the range)."""
        if self._categories and self.category_value == "midpoint":
            cat = decision.get("release_category")
            match = [c for c in self._categories if c[0] == cat]
            if not match:
                raise ValueError(f"invalid release_category: {cat!r}")
            decision = dict(decision, release_cfs=match[0][3])
        return decision

    def _retrieve_operational_sections(self, date: pd.Timestamp, query: str,
                                        runtime_state: dict) -> list:
        """Return essential normal-operation rules plus relevant event text.

        Pure top-k retrieval previously spent slots on interface prose while
        omitting essential operating or fallback sections. This router guarantees
        the core rule sections needed for every reduced-domain decision, then
        uses TF-IDF for applicable event sections. The structural recreation
        rules are eligible every April-October; their numerical 2014 calendar
        remains year-specific. This method routes document text; it does not
        choose a release.
        """
        if getattr(self._retriever, "layout", "sections") == "v1.2-rules":
            return self._retrieve_v12_rules(date, runtime_state)
        required_names = (
            "Core Rule Priority and Release Constraints",
            "Normal Operation and Minimum Release Decision",
            "Missing Information and Conservative Fallback",
        )
        if not self.include_missing_inputs:
            required_names = required_names[:2]   # model-boundary test condition
        selected = []
        selected_headings = set()
        for wanted in required_names:
            for heading, body in self._retriever.sections:
                if heading == wanted:
                    selected.append((heading, body))
                    selected_headings.add(heading)
                    break

        ranked = self._retriever.retrieve(
            query, k=len(self._retriever.sections)
        )
        flood_storage = float(runtime_state.get("flood_storage_percent") or 0.0)
        pool_ft = runtime_state.get("pool_elevation_ft")
        start_target_ft = runtime_state.get("seasonal_target_start_ft")
        flood_event = (
            pool_ft is not None
            and start_target_ft is not None
            and float(pool_ft) > float(start_target_ft) + self.target_tolerance_ft
        )
        stages_trend = str(runtime_state.get("stages_trend") or "").lower()
        dynamic_allowed = {
            "Flood Plans B and C - Inflow Rising Above Target",   # DKP v1.3 heading
            "Flood Plan B - Pool Above Target",                   # DKP v1.4 heading
            "Post-Flood Drawdown and Downstream Protection",
            "Recreation Operation",
        }
        for heading, body in ranked:
            if len(selected) >= self.top_k:
                break
            if heading in selected_headings or heading == "Required Runtime Inputs and LLM Output":
                continue
            if heading not in dynamic_allowed:
                continue
            if (heading == "Recreation Operation"
                    and (date.month not in range(4, 11) or flood_event)):
                continue
            if heading in (
                "Flood Plans B and C - Inflow Rising Above Target",
                "Flood Plan B - Pool Above Target",
                "Post-Flood Drawdown and Downstream Protection",
            ) and (flood_storage <= 0.0 or not flood_event):
                continue
            if (heading == "Post-Flood Drawdown and Downstream Protection"
                    and stages_trend != "falling_after_peak"):
                continue
            if (heading == "Flood Plans B and C - Inflow Rising Above Target"
                    and stages_trend == "falling_after_peak"):
                continue
            selected.append((heading, body))
            selected_headings.add(heading)

        self._last_retrieved_headings = [heading for heading, _ in selected]
        self._last_retrieved_excerpts = list(selected)   # exact text, for the trace
        return selected

    # DKP v1.2 rules mapped to the v1.3 router: the core rules every month, and
    # the plan / recreation rules under exactly the v1.3 conditions.
    V12_CORE = ("R-RELEASE", "R-MINNORM", "R-ATSITE", "R-ZONE")
    V12_EXCLUDED = ("Fallback Policy", "R-DOWNSTREAM",
                    "§2.4.4 Downstream Station Ratings", "§2.4.6 Time of Travel Schedule")

    def _retrieve_v12_rules(self, date: pd.Timestamp, runtime_state: dict) -> list:
        """Routing for DKP v1.2 (rule-level). Never returns the downstream
        control-point rule, the fallback policy or the downstream reference
        tables. Returns rule text exactly as written in the DKP file."""
        secs = self._retriever.sections
        def find(prefix):
            for h, b in secs:
                if h.startswith(prefix) and not h.startswith(self.V12_EXCLUDED):
                    return (h, b)
            return None
        core = list(self.V12_CORE)
        selected = [x for x in (find(p) for p in core) if x]
        if self.include_missing_inputs:                 # baseline-style condition only
            fb = [(h, b) for h, b in secs if h == "Fallback Policy"]
            selected += fb
        flood_storage = float(runtime_state.get("flood_storage_percent") or 0.0)
        pool_ft = runtime_state.get("pool_elevation_ft")
        start_target_ft = runtime_state.get("seasonal_target_start_ft")
        flood_event = (pool_ft is not None and start_target_ft is not None
                       and float(pool_ft) > float(start_target_ft) + self.target_tolerance_ft)
        if flood_storage > 0.0 and flood_event:          # = v1.3 "Flood Plans" condition
            x = find("R-PLAN")
            if x: selected.append(x)
        if date.month in range(4, 11) and not flood_event:   # = v1.3 "Recreation" condition
            x = find("R-RECREATION")
            if x: selected.append(x)
        self._last_retrieved_headings = [h for h, _ in selected]
        self._last_retrieved_excerpts = list(selected)
        return selected

    def _build_state_prompt(self, date: pd.Timestamp, inflow_cfs: float,
                            storage_af: float,
                            runtime_state: dict = None) -> str:
        """The VARIABLE part of the prompt: today's numbers, recent history
        (identical in shape to the zero-shot condition's state block), then
        the DKP sections retrieved for today's conditions."""
        runtime_state = runtime_state or {}
        # items 1-6: text-identical to the zero-shot condition (shared code) -
        # includes the water-availability ceiling (item 6) when storage is on
        lines = state_core_lines(self.info, date, inflow_cfs, storage_af,
                                 runtime_state, self._history)
        # item 7: the WCM release limits restated as volumes for THIS interval.
        # The limits are instantaneous rates; the model decides once per
        # interval, so the same limits are also given in the unit of the
        # water-balance equation. Computed from the actual day count.
        days = int(runtime_state.get("step_days") or 1)
        # numbered directly after the shared block: 5 if storage is off; with
        # storage on, 7 when the shared item 6 (availability) is shown, 6 when
        # the anchoring-test condition hides it
        item = ((7 if self.info.show_availability_line else 6)
                if self.info.prompt_storage else 5)
        lines.append(
            f"{item}. Release limits for this interval (water control manual): "
            f"{self.info.min_release_cfs:,.0f}-{self.info.max_release_cfs:,.0f} cfs "
            f"(= {cfs_to_cf(self.info.min_release_cfs, days):,.0f}-"
            f"{cfs_to_cf(self.info.max_release_cfs, days):,.0f} cubic feet "
            f"over {days} days)"
        )
        # retrieve the DKP sections most relevant to TODAY's conditions
        query = self._make_query(
            date, inflow_cfs, storage_af, runtime_state=runtime_state
        )
        excerpts = self._retrieve_operational_sections(
            date, query, runtime_state
        )
        lines.append("")
        lines.append("Retrieved DKP sections relevant to current conditions:")
        for i, (heading, body) in enumerate(excerpts, 1):
            lines.append(f"\n--- DKP excerpt {i}: {heading} ---")
            lines.append(body)
        lines.append("")
        lines.append(
            f"The simulated year is {date.year}. Check the year of every dated DKP "
            "instruction before applying it."
        )
        lines.append("Apply these DKP rules to decide the mean release for this interval (cfs).")
        return "\n".join(lines)

    def _make_query(self, date: pd.Timestamp, inflow_cfs: float,
                    storage_af: float,
                    runtime_state: dict = None) -> str:
        """Compose the retrieval query from the current system state.

        The query varies with raw state so retrieval can surface the relevant
        section. It contains numbers and trend descriptions, but never a
        precomputed ``above target`` or ``below target`` label:

        (a) always-on operational vocabulary, so the decision-rule and
            constraint sections stay candidates every day;
        (b) today's actual numbers as search tokens (storage in af, inflow
            in cfs, percent of capacity). Written WITHOUT thousands
            separators: the tokenizer splits on commas, so "148,210" would
            become the tokens "148" and "210" - two short numbers likely to
            collide with unrelated table cells - whereas "148210" stays one
            distinctive token that can match a real table row;
        (c) deterministic pool elevation when the driver supplies it. The
            shared seasonal target is already present in the system prompt
            and need not be repeated in the retrieval query;
        (d) DIRECTION of inflow change against yesterday and against the
            recent mean, again stated bare ("inflow rising", "inflow above
            recent mean") rather than labelled. A 1 cfs rise on a 500 cfs
            day is genuinely "rising"; whether it is a storm event is for
            the retrieved document text to establish, not for this query
            to assert by attaching "storm event peak" to any positive
            difference.

        Duplicate tokens across these phrases are harmless: retrieve()
        deduplicates before scoring.
        """
        info = self.info
        runtime_state = runtime_state or {}
        terms = [
            # (a) always-on operational vocabulary
            "release decision rule minimum release maximum release",
            "rate of change operating zone pool elevation storage guide curve",
            f"{date:%B} seasonal",                 # month name, e.g. "October"
        ]

        # (b) today's real numbers as tokens. NO thousands separators here:
        # the tokenizer splits on commas, so "148,210" would become "148"
        # and "210". Commas are still used in the PROMPT text itself, which
        # humans and the LLM read; this string is only ever fed to the
        # retriever.
        pct_full = 100.0 * storage_af / info.capacity_af if info.capacity_af else 0.0
        terms.append(f"storage {storage_af:.0f} acre-feet "
                     f"inflow {inflow_cfs:.0f} cfs "
                     f"{pct_full:.0f} percent of capacity")

        # (c) raw physical conversion only. The shared seasonal target is
        # supplied identically to both LLM conditions in the system prompt;
        # it is deliberately not repeated as a retrieval-query label.
        if runtime_state.get("pool_elevation_ft") is not None:
            terms.append(
                f"pool elevation {runtime_state['pool_elevation_ft']:.2f} ft"
            )
        # Storage has reached the capacity this model uses. NOTE: capacity_af
        # is the MODELED capacity and its documented basis differs between
        # reservoirs (spillway crest for Prompton/F.E. Walter, top of dam
        # for Wallenpaupack), so this deliberately does not name it
        # "spillway crest" or attach flood/surcharge vocabulary. If a true
        # spillway-crest storage is needed as its own concept, it should be
        # added to ReservoirConfig as a separate documented field.
        if info.capacity_af and storage_af >= info.capacity_af:
            terms.append("at maximum modeled storage capacity")

        # (d) DIRECTION of inflow change - direction only, no label. A rise
        # is reported as a rise whether it is 1 cfs or 10,000; deciding
        # whether it constitutes a storm event is the document's job.
        if self._history:
            yesterday = self._history[-1]["inflow_cfs"]
            recent = sum(h["inflow_cfs"] for h in self._history) / len(self._history)
            if inflow_cfs > yesterday:
                terms.append("inflow rising")
            elif inflow_cfs < yesterday:
                terms.append("inflow falling")
            if inflow_cfs > recent:
                terms.append("inflow above recent mean")
            elif inflow_cfs < recent:
                terms.append("inflow below recent mean")

        return " ".join(terms)

    # ------------------------------------------------------------------
    # 2b. THE DAILY DECISION
    # ------------------------------------------------------------------

    def _audit_decision(self, date: pd.Timestamp, decision: dict,
                        requested_release_cfs: float, release_cfs: float,
                        inflow_cfs: float,
                        storage_af: float, runtime_state: dict) -> dict:
        """Deterministically test direction, traceability, and water balance.

        The audit never invents an official rule and never silently replaces
        the LLM release.  It exposes contradictions (for example, claiming
        refill while passing all inflow) and can stop final runs before an
        invalid trajectory is written as a research result.
        """
        runtime_state = runtime_state or {}
        failures, warnings = [], []
        mode = str(decision.get("operating_mode", ""))
        rules = decision.get("rules_applied")
        missing = decision.get("missing_inputs")
        reasoning = str(decision.get("reasoning", ""))

        if not mode:
            failures.append("missing operating_mode")
        if self._categories and self.category_value == "llm":
            cat = decision.get("release_category")
            match = [c for c in self._categories if c[0] == cat]
            if not match:
                failures.append(f"release_category {cat!r} is not one of the listed categories")
            elif not (match[0][1] - 0.5 <= requested_release_cfs <= match[0][2] + 0.5):
                failures.append(
                    f"release_cfs {requested_release_cfs:,.1f} lies outside the chosen category "
                    f"{cat} ({match[0][1]:,.0f}-{match[0][2]:,.0f} cfs)")
        if not isinstance(rules, list) or not rules:
            failures.append("rules_applied must contain at least one DKP section heading")
        elif any(not self._cites_retrieved_rule(rule) for rule in rules):
            failures.append(
                "every rules_applied entry must be an exact retrieved DKP section heading"
            )
        if self.include_missing_inputs and not isinstance(missing, list):
            failures.append("missing_inputs must be a JSON list")
        if (requested_release_cfs < self.info.min_release_cfs
                or requested_release_cfs > self.info.max_release_cfs):
            failures.append(
                "LLM release violated configured bounds and required clipping"
            )
        physically_available_cfs = runtime_state.get(
            "physically_available_release_cfs"
        )
        # The physical-availability check moved into the SHARED physics_audit
        # (zeroshot_llm_release.py), so both arms apply it identically. Before,
        # only this arm had it, and zero-shot could request an impossible
        # release without being flagged.

        step_days = int(runtime_state.get("step_days") or 1)
        storage_change_af = (
            (inflow_cfs - release_cfs) * CFS_TO_CMS
            * step_days * 86400.0 / ACREFT_TO_M3
        )
        projected_end_storage_af = storage_af + storage_change_af
        target_storage_af = runtime_state.get("seasonal_target_storage_af")
        pool_ft = runtime_state.get("pool_elevation_ft")
        target_ft = runtime_state.get("seasonal_target_ft")
        target_error_start_af = None
        target_error_end_af = None
        if target_storage_af is not None:
            target_error_start_af = abs(target_storage_af - storage_af)
            target_error_end_af = abs(
                target_storage_af - projected_end_storage_af
            )

        # The audit may judge the LLM ONLY on information the LLM received.
        # Without prompt storage the model sees water levels, not volumes, so
        # it cannot size a release against a storage deficit - it can only
        # choose a direction. Direction is therefore always audited (the LLM
        # has both elevations and knows R versus I); MAGNITUDE (does the
        # release reduce the target-storage error?) is audited only when
        # storage was in the prompt. target_error_* is still computed and
        # logged for post-run analysis - logging is not judging.
        judge_magnitude = bool(self.info.prompt_storage)

        # Audit what the LLM CLAIMED to do; do not impose a hidden target
        # controller or require a particular release merely because the pool
        # differs from the seasonal target. The WCM does not provide a
        # universal numerical refill formula for every reduced-domain state.
        if mode == "store_toward_target":
            if release_cfs >= inflow_cfs - 0.1:
                failures.append(
                    "store_toward_target mode does not retain inflow"
                )
            if (judge_magnitude and target_error_start_af is not None
                    and target_error_end_af >= target_error_start_af - 0.5):
                failures.append(
                    "store_toward_target mode does not reduce target error"
                )
            if (pool_ft is not None and target_ft is not None
                    and pool_ft > target_ft + self.target_tolerance_ft):
                warnings.append(
                    "store_toward_target mode selected while pool is above target"
                )
        elif mode in ("draw_toward_target", "post_flood_drawdown"):
            if release_cfs <= inflow_cfs + 0.1:
                failures.append(
                    f"{mode} mode does not release more than inflow"
                )
            if (judge_magnitude and target_error_start_af is not None
                    and target_error_end_af >= target_error_start_af - 0.5):
                failures.append(
                    f"{mode} mode does not reduce target error"
                )
            if (pool_ft is not None and target_ft is not None
                    and pool_ft < target_ft - self.target_tolerance_ft):
                warnings.append(
                    f"{mode} mode selected while pool is below target"
                )
        elif mode == "pass_inflow":
            # Rounding-only tolerance (see _flow_relation in the zero-shot
            # module for the same fix and the reasoning): a percentage-of-
            # inflow band let a real, intended release-vs-inflow gap be
            # waved through as "pass_inflow" whenever inflow was large.
            pass_tolerance = max(1.0, 1e-9 * max(abs(inflow_cfs), 1.0))
            if abs(release_cfs - inflow_cfs) > pass_tolerance:
                failures.append(
                    "pass_inflow mode release is not approximately equal to inflow"
                )
            # Table 7-1/R-RELEASE directs Plan-A storage when the pool is
            # materially below target and inflow exceeds the applicable minimum.
            # Passing inflow cannot accomplish that direction. The durable
            # 1365-1370 ft May-10-to-Jun-30 recreation hold is the documented
            # exception. This is an after-the-fact consistency test only: it
            # never calculates or substitutes a release.
            recreation_hold = (
                pool_ft is not None
                and 1365.0 - self.target_tolerance_ft <= pool_ft <= 1370.0
                and (date.month == 6 or (date.month == 5 and date.day >= 10))
            )
            if (pool_ft is not None and target_ft is not None
                    and pool_ft < target_ft - self.target_tolerance_ft
                    and inflow_cfs > self.info.min_release_cfs + pass_tolerance
                    and not recreation_hold):
                failures.append(
                    "below-target pass_inflow cannot raise storage toward the target"
                )

        # This identifier belonged to the removed hybrid controller. Its
        # appearance now means the model invented or retained a prohibited
        # non-DKP decision source.
        trace = " ".join(str(item) for item in (rules or [])) + " " + reasoning
        missing_text = " ".join(str(item) for item in (missing or []))
        applicability_trace = trace + " " + missing_text
        if re.search(r"RESEARCH-TARGET-TRACKING|target[-_ ]tracking release", trace,
                     re.IGNORECASE):
            failures.append("prohibited target-tracking controller cited")

        if date.year != 2014 and 4 <= date.month <= 10:
            # Mentioning the 2014 schedule to disclaim it is valid. Fail only
            # when the response appears to apply its distinctive calendar or
            # numerical limits without explicitly saying they are unavailable
            # or inapplicable in the simulated year.
            # Narrowed (register AU-02): a bare round number such as "1,000
            # cfs" in a winter month is an ordinary release, not calendar use.
            # The check now requires BOTH a recreation-calendar context word
            # and a distinctive 2014 value, and only runs April-October, the
            # months a recreation calendar could govern at all.
            calendar_context = re.search(
                r"(?:recreation|whitewater|boating|calendar|schedul|"
                r"weekend|weekday|holiday|memorial|labor\s+day|event\s+date)",
                trace,
                re.IGNORECASE,
            )
            applies_2014_calendar = calendar_context and re.search(
                r"(?:weekday|weekend|May\s+(?:9|10)|"
                r"(?:225|250|750|1,?000)\s*cfs)",
                trace,
                re.IGNORECASE,
            )
            disclaims_2014_calendar = re.search(
                r"(?:not\s+applicable|not\s+appl(?:y|ied)|not\s+used|"
                r"year[- ]specific|2014\s+specific|calendar\s+(?:is\s+)?"
                r"(?:unknown|unavailable|missing)|outside\s+2014)",
                applicability_trace,
                re.IGNORECASE,
            )
            if applies_2014_calendar and not disclaims_2014_calendar:
                failures.append("2014-only recreation calendar applied outside 2014")

            if mode == "recreation_plan":
                if not re.search(
                    r"(?:annual|year[- ]specific|2014).*(?:calendar|schedule)|"
                    r"(?:calendar|schedule).*(?:unknown|unavailable|missing)",
                    missing_text if self.include_missing_inputs else applicability_trace,
                    re.IGNORECASE,
                ):
                    warnings.append(
                        "recreation_plan outside 2014 does not disclose the missing "
                        "annual recreation calendar"
                    )

        expected_missing = runtime_state.get("runtime_missing_inputs") or []
        if (self.include_missing_inputs and expected_missing
                and isinstance(missing, list) and not missing):
            warnings.append("known unavailable runtime inputs were not disclosed")

        # shared physics audit - IDENTICAL code to the zero-shot arm. Reported
        # separately so the two arms can be compared on the same metric.
        physics_res = physics_audit(
            decision, inflow_cfs=inflow_cfs, release_cfs=release_cfs,
            pool_ft=pool_ft, target_ft=target_ft,
            min_release_cfs=self.info.min_release_cfs,
            max_release_cfs=self.info.max_release_cfs,
            prompt_storage=self.info.prompt_storage,
            target_error_start_af=target_error_start_af,
            target_error_end_af=target_error_end_af,
            target_tolerance_ft=self.target_tolerance_ft,
            requested_release_cfs=requested_release_cfs,
            physically_available_cfs=physically_available_cfs,
        )
        physics_hard = physics_res["hard_physics"]
        physics_hard_unattr = physics_res["hard_physics_unattributed"]
        physics_policy = physics_res["policy"]
        physics_warnings = physics_res["warnings"]
        physics_failures = physics_hard + physics_policy   # attributed to the model
        dkp_rule_failures = list(failures)
        failures = physics_failures + [f for f in failures if f not in physics_failures]
        warnings = physics_warnings + warnings

        status = ("FAIL" if failures
                  else "WARN" if (warnings or physics_hard_unattr) else "PASS")
        return {
            "physics_audit_status": ("FAIL" if physics_failures
                                     else "WARN" if (physics_warnings
                                                     or physics_hard_unattr)
                                     else "PASS"),
            "physics_audit_failures": physics_failures,
            "hard_physics_failures": physics_hard,
            "hard_physics_unattributed": physics_hard_unattr,
            "policy_failures": physics_policy,
            "request_physically_feasible": not (physics_hard or physics_hard_unattr),
            "dkp_rule_failures": dkp_rule_failures,
            "audit_status": status,
            "audit_failures": failures,
            "audit_warnings": warnings,
            "storage_change_af": storage_change_af,
            "projected_end_storage_af": projected_end_storage_af,
            "target_error_start_af": target_error_start_af,
            "target_error_end_af": target_error_end_af,
        }

    def _build_audit_revision_prompt(self, original_prompt: str,
                                     decision: dict, audit: dict,
                                     revision_number: int) -> str:
        """Ask the LLM to repair its own internally inconsistent candidate.

        The audit supplies only the failed consistency statements. It never
        calculates, recommends, or substitutes a release; the revised release
        remains an LLM decision grounded in the same state and DKP excerpts.
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
            + "\nRe-read the same state and retrieved DKP excerpts, apply the physical "
              "water balance, and revise your own decision so every listed "
              "contradiction is resolved. The audit has not supplied a release "
              "value. Return only a complete replacement JSON object in the "
              "required schema."
        )

    def target_release(self, date: pd.Timestamp, inflow_now: float,
                       storage_start_m3: float,
                       runtime_state: dict = None) -> float:
        """Return the release decision (m^3/s) for one interval using the LLM.

        Called by reservoir_model.py only on days it has decided an LLM
        consultation is warranted; this method itself never skips the call.
        """
        inflow_cfs = inflow_now / CFS_TO_CMS
        storage_af = storage_start_m3 / ACREFT_TO_M3
        self.days_decided += 1

        # --- STEP 1: build today's prompt (state + retrieved DKP excerpts)
        prompt = self._build_state_prompt(
            date, inflow_cfs, storage_af, runtime_state=runtime_state
        )

        # --- STEP 2: ask the LLM (with a safe fallback on ANY failure)
        self.llm_attempts += 1
        call_stats_records = []
        active_prompt = prompt
        try:
            decision = self.backend.decide(
                self._system_prompt, prompt, schema=self._schema
            )
            decision = self._apply_category(decision)
            requested_release_cfs = float(decision["release_cfs"])
            if not math.isfinite(requested_release_cfs):
                raise ValueError(f"non-finite release_cfs: {decision['release_cfs']!r}")
            release_cfs = requested_release_cfs
            reasoning = str(decision.get("reasoning", ""))
            fallback = False
            self.llm_successes += 1
        except Exception as exc:   # network error, refusal, bad JSON, timeout...
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

        # --- STEP 3: safety clip (bounds enforced in code regardless of the LLM)
        release_cfs = float(min(max(release_cfs, self.info.min_release_cfs),
                                self.info.max_release_cfs))
        release_cms = release_cfs * CFS_TO_CMS
        self._last_decision_release_cms = release_cms

        audit = None
        audit_revision_count = 0
        audit_revision_failures = []
        audit_revision_error = None
        if not fallback:
            audit = self._audit_decision(
                date, decision, requested_release_cfs, release_cfs,
                inflow_cfs, storage_af,
                runtime_state or {},
            )
            while (audit["audit_status"] == "FAIL"
                   and audit_revision_count < self.max_audit_revisions):
                audit_revision_failures.append(list(audit["audit_failures"]))
                audit_revision_count += 1
                self.audit_revision_attempts += 1
                active_prompt = self._build_audit_revision_prompt(
                    prompt, decision, audit, audit_revision_count
                )
                # the latest candidate the LLM actually produced, and its audit;
                # restored if this revision call errors (see except below)
                prior = (decision, requested_release_cfs, release_cfs,
                         reasoning, audit)
                try:
                    decision = self.backend.decide(
                        self._system_prompt,
                        active_prompt,
                        schema=self._schema,
                    )
                    decision = self._apply_category(decision)
                    requested_release_cfs = float(decision["release_cfs"])
                    if not math.isfinite(requested_release_cfs):
                        raise ValueError(f"non-finite release_cfs: {decision['release_cfs']!r}")
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
                        "type": "revision", "arm": "dkp", "date": f"{date:%Y-%m-%d}",
                        "revision_number": audit_revision_count,
                        "prompt": active_prompt,
                        "prompt_sha256": sha256_text(active_prompt),
                        "raw_response": getattr(self.backend, "last_raw_content", None),
                        "parsed": decision,
                        "requested_release_cfs": requested_release_cfs,
                        "audit_status": audit["audit_status"],
                        "audit_failures": audit["audit_failures"]})
                except Exception as exc:
                    # A failed REVISION call must not erase the decision the LLM
                    # already made. Previously this path discarded the candidate,
                    # substituted last month's release (a Python-supplied value
                    # never audited against this state), set audit=None - which
                    # dropped the FAIL from the counters and bypassed the
                    # audit-stop gate - and decremented a success that had
                    # genuinely occurred. Now: restore the latest LLM candidate
                    # AND its FAIL audit, record the error, and let the normal
                    # path count it and apply --dkp-audit-action. The release
                    # stays LLM-authored; Python still never supplies one.
                    revision_stats = getattr(self.backend, "last_call_stats", None)
                    if revision_stats:
                        call_stats_records.append(dict(revision_stats))
                    write_trace(self.trace_path, {
                        "type": "revision", "arm": "dkp", "date": f"{date:%Y-%m-%d}",
                        "revision_number": audit_revision_count,
                        "prompt": active_prompt,
                        "prompt_sha256": sha256_text(active_prompt),
                        "error": f"{type(exc).__name__}: {exc}"})
                    (decision, requested_release_cfs, release_cfs,
                     reasoning, audit) = prior
                    audit_revision_error = f"{type(exc).__name__}: {exc}"
                    self.audit_revision_errors += 1
                    break

            if (audit is not None and audit["audit_status"] != "FAIL"
                    and audit_revision_count):
                self.audit_revision_successes += 1

            release_cms = release_cfs * CFS_TO_CMS
            self._last_decision_release_cms = release_cms

        if audit is not None:
            if audit.get("hard_physics_unattributed"):
                self.unattributed_hard_physics += 1
            if audit["audit_status"] == "PASS":
                self.audit_passes += 1
            elif audit["audit_status"] == "WARN":
                self.audit_warnings += 1
            else:
                self.audit_failures += 1
                if audit.get("physics_audit_failures"):
                    self.physics_audit_failure_count += 1
                if audit.get("hard_physics_failures"):
                    self.hard_physics_failures += 1
                if audit.get("policy_failures"):
                    self.policy_failures += 1
                if self.first_audit_failure is None:
                    self.first_audit_failure = {
                        "date": f"{date:%Y-%m-%d}",
                        "failures": list(audit["audit_failures"]),
                    }

        # --- STEP 4: record
        # tell the driver whether this day's number came from the model or
        # from the fallback path (see reservoir_model.simulate STEP 0)
        self.last_decision_failed = fallback

        call_stats = None
        if call_stats_records:
            call_stats = dict(call_stats_records[-1])
            call_stats["wall_seconds"] = sum(
                float(item.get("wall_seconds") or 0.0)
                for item in call_stats_records
            )
            call_stats["prompt_tokens"] = sum(
                int(item.get("prompt_tokens") or 0)
                for item in call_stats_records
            )
            call_stats["response_tokens"] = sum(
                int(item.get("response_tokens") or 0)
                for item in call_stats_records
            )
            call_stats["backend_attempts"] = sum(
                int(item.get("backend_attempts") or 1)
                for item in call_stats_records
            )
            call_stats["retry_errors"] = [
                error
                for item in call_stats_records
                for error in (item.get("retry_errors") or [])
            ]
        if call_stats:
            backend_attempts = int(call_stats.get("backend_attempts") or 1)
            self.total_backend_attempts += backend_attempts
            self.total_backend_retries += max(backend_attempts - 1, 0)
        if fallback:
            # ALWAYS keep failed prompts (up to n_failure_samples), never
            # sample them: a run of 100 attempts and 100 failures must still
            # produce the actual prompt that failed, which is exactly what
            # is needed to diagnose it.
            self._record_failure_sample(date, active_prompt, reasoning, release_cfs)
        else:
            self._sample_prompt(date, active_prompt, decision)
            if call_stats:
                self.total_wall_seconds += call_stats.get("wall_seconds") or 0.0
                self.total_prompt_tokens += call_stats.get("prompt_tokens") or 0
                self.total_response_tokens += call_stats.get("response_tokens") or 0

        record = {
            "date": f"{date:%Y-%m-%d}",
            "outcome": "fallback" if fallback else "llm",
            "llm_attempted": True,
            "llm_succeeded": not fallback,
            "llm": self.backend.name,
            "inflow_cfs": round(inflow_cfs, 1),
            "storage_start_af": round(storage_af, 1),
            "decision_release_cfs": round(release_cfs, 1),
        }
        if decision:
            record["llm_release_cfs_raw"] = round(requested_release_cfs, 1)
            for field in NEUTRAL_FIELD_NAMES:
                record[field] = decision.get(field)
            record["operating_mode"] = decision.get("operating_mode", "")
            record["rules_applied"] = decision.get("rules_applied", [])
            record["missing_inputs"] = decision.get("missing_inputs", [])
            if self._categories:
                record["release_category"] = decision.get("release_category")
        record["retrieved_sections"] = self._last_retrieved_headings
        if audit:
            record["audit_status"] = audit["audit_status"]
            record["physics_audit_status"] = audit.get("physics_audit_status")
            record["physics_audit_failures"] = audit.get("physics_audit_failures")
            record["hard_physics_failures"] = audit.get("hard_physics_failures")
            record["hard_physics_unattributed"] = audit.get("hard_physics_unattributed")
            record["policy_failures"] = audit.get("policy_failures")
            record["request_physically_feasible"] = audit.get("request_physically_feasible")
            record["dkp_rule_failures"] = audit.get("dkp_rule_failures")
            record["audit_failures"] = audit["audit_failures"]
            record["audit_warnings"] = audit["audit_warnings"]
            record["storage_change_af"] = round(audit["storage_change_af"], 1)
            record["projected_end_storage_af"] = round(
                audit["projected_end_storage_af"], 1
            )
            if audit["target_error_start_af"] is not None:
                record["target_error_start_af"] = round(
                    audit["target_error_start_af"], 1
                )
                record["target_error_end_af"] = round(
                    audit["target_error_end_af"], 1
                )
        record["audit_revision_count"] = audit_revision_count
        if audit_revision_failures:
            record["audit_revision_failures"] = audit_revision_failures
        if audit_revision_error:
            record["audit_revision_error"] = audit_revision_error
        if runtime_state:
            if runtime_state.get("pool_elevation_ft") is not None:
                record["pool_elevation_start_ft"] = round(
                    runtime_state["pool_elevation_ft"], 2)
            for key in (
                "seasonal_target_start_ft",
                "seasonal_target_mean_ft",
                "seasonal_target_ft",
                "seasonal_target_storage_af",
                "physically_available_release_cfs",
                "flood_storage_percent",
            ):
                if runtime_state.get(key) is not None:
                    record[key] = round(runtime_state[key], 2)
        if call_stats:
            record["wall_seconds"] = round(call_stats.get("wall_seconds") or 0.0, 2)
            if call_stats.get("prompt_tokens") is not None:
                record["prompt_tokens"] = call_stats["prompt_tokens"]
            if call_stats.get("response_tokens") is not None:
                record["response_tokens"] = call_stats["response_tokens"]
            for key in ("done_reason", "content_chars", "thinking_chars",
                        "backend_attempts", "retry_errors"):
                if call_stats.get(key) is not None:
                    record[key] = call_stats[key]
        # DKP validation defaults to 100% reasoning retention.
        if fallback or self._rng.random() < self.reasoning_log_fraction:
            record["reasoning"] = reasoning
        self._log(record)
        write_trace(self.trace_path, {
            "type": "call", "arm": "dkp", "date": f"{date:%Y-%m-%d}",
            "system_prompt_sha256": self._system_prompt_sha256,
            "prompt": prompt, "prompt_sha256": sha256_text(prompt),
            "retrieved": [{"heading": h, "sha256": sha256_text(b), "chars": len(b)}
                          for h, b in self._last_retrieved_excerpts],
            "raw_response": None if fallback else getattr(self.backend, "last_raw_content", None),
            "parsed": decision, "requested_release_cfs": requested_release_cfs,
            "decision_release_cfs": release_cfs, "outcome": "fallback" if fallback else "llm",
            "audit_status": record.get("audit_status"), "audit_failures": record.get("audit_failures"),
            "hard_physics_failures": record.get("hard_physics_failures"),
            "hard_physics_unattributed": record.get("hard_physics_unattributed"),
            "policy_failures": record.get("policy_failures"),
            "dkp_rule_failures": record.get("dkp_rule_failures"),
            "selection_inputs": ({k: (runtime_state or {}).get(k) for k in
                                  ("pool_elevation_ft", "seasonal_target_ft",
                                   "seasonal_target_storage_af",
                                   "physically_available_release_cfs",
                                   "stages_trend", "inflow_trend", "step_days")}
                                 if runtime_state else None),
            "audit_revision_count": record.get("audit_revision_count"), "reasoning": reasoning})
        if (audit and self.audit_action == "stop"
                and (audit["audit_status"] == "FAIL"
                     or audit.get("hard_physics_unattributed"))):
            raise RuntimeError(
                f"DKP rule audit failed on {date:%Y-%m-%d}: "
                + "; ".join(list(audit["audit_failures"])
                            + list(audit.get("hard_physics_unattributed") or []))
            )
        return release_cms

    def record_reuse(self, date: pd.Timestamp, inflow_now: float,
                     storage_start_m3: float, decision_release_cms: float,
                     runtime_state: dict = None) -> None:
        """Log a day on which reservoir_model.py reused the prior release
        decision instead of consulting the LLM.

        The reuse DECISION is made in reservoir_model.py (that is where the
        inflow-change criterion lives); this only records it, so the log
        keeps one line per simulated day and the counters add up:
        days_decided = reuse_days + llm_attempts.
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
        if runtime_state:
            if runtime_state.get("pool_elevation_ft") is not None:
                record["pool_elevation_start_ft"] = round(
                    runtime_state["pool_elevation_ft"], 2)
            for key in ("seasonal_target_ft",
                        "flood_storage_percent"):
                if runtime_state.get(key) is not None:
                    record[key] = round(runtime_state[key], 2)
        self._log(record)

    # ------------------------------------------------------------------
    # 2c. BOOKKEEPING (history, sampling, logging, final outputs)
    # ------------------------------------------------------------------

    def record_outcome(self, date: pd.Timestamp, decision_release_cms: float,
                       storage_end_m3: float, inflow_cms: float,
                       implemented_release_cms: float = None) -> None:
        """Record the prior simulated decision after the water-balance step.

        The next prompt receives ``decision_release_cms``. The actual total
        outflow is retained only for bookkeeping because it may contain
        availability clipping or uncontrolled spill, neither of which is an
        LLM decision.
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
        """Keep a uniform random sample of n_prompt_samples LLM exchanges via
        reservoir sampling (the total call count isn't known in advance
        because the consultation criterion makes it data-dependent)."""
        pair = {
            "date": f"{date:%Y-%m-%d}",
            "prompt": prompt,
            "llm_response": decision,
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
            if key in ("date", "reasoning"):
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
        dkp_resolved = Path(self.dkp_path).resolve()
        dkp_sha256 = hashlib.sha256(dkp_resolved.read_bytes()).hexdigest()
        lines = [
            f"LLM decision engine: {self.backend.name}",
            f"Provenance: Ollama {self.provenance.get('ollama_version')} | model digest "
            f"{self.provenance.get('model_digest')} | availability line shown: "
            f"{self.info.show_availability_line}",
            f"DKP file: {dkp_resolved} "
            f"({len(self._retriever.sections)} sections indexed, "
            f"top_k={self.top_k})",
            f"DKP SHA256: {dkp_sha256}",
            f"Days decided: {self.days_decided} "
            f"(LLM attempts {self.llm_attempts}: {self.llm_successes} succeeded, "
            f"{self.llm_failures} failed; {self.reuse_days} reuse steps)",
            f"Rule audit: {self.audit_passes} PASS, {self.audit_warnings} WARN, "
            f"{self.audit_failures} FAIL (action={self.audit_action})",
            ("DIAGNOSTIC TRAJECTORY - NOT A VALID RESEARCH RESULT: "
             f"first FAIL {self.first_audit_failure['date']} "
             f"({'; '.join(self.first_audit_failure['failures'])})"
             if self.audit_failures and self.audit_action != "stop"
             else ""),
            f"Sampled {len(self._prompt_samples)} of {self.llm_successes} "
            f"successful LLM calls",
            "",
            bar,
            "SYSTEM PROMPT (identical for every call)",
            bar,
            self._system_prompt,
        ]
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
                f"operating_mode: {response.get('operating_mode', '')}",
                f"rules_applied: {response.get('rules_applied', [])}",
                f"missing_inputs: {response.get('missing_inputs', [])}",
                f"release_category: {response.get('release_category', '-')}",
                f"reasoning: {response.get('reasoning', '')}",
            ]
        with open(self.sample_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
