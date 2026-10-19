"""Extract three historical request pairs; never contact a provider or edit a run.

The external evidence directory is explicit. Only the selected records are copied
to the manual; full research journals remain outside the repository.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAYS = ("2016-10-12", "2016-10-13", "2016-10-14")
RAW_FILES = (
    "policy_16a8414fc8a2ea0912841a0431505832bd078fbc8ed9bbb02ddf308aa95394be.json",
    "policy_71af75b9d8fda4478adaf9699e87d22ea61a55d0ecf2886efc7e8a52a18c2c03.json",
    "policy_55f9005711847b6133cc259659c1d2effe5554a340bfa6e26ca5f0a7613f9f91.json",
)
RETRIEVAL_MARKER = "Retrieved DKP sections relevant to current conditions:"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_hash(text: str) -> str:
    return sha(text.encode("utf-8"))


def criteria_source_label(path: Path) -> str:
    """Use repository-relative labels; external inputs expose only a basename."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "external/" + resolved.name


def selected_request(payload, raw_reply, source, line=None):
    """Keep exact message strings and raw JSON reply, rather than reformatting them."""
    system, user = (m["content"] for m in payload["messages"])
    if RETRIEVAL_MARKER not in user:
        raise ValueError("Expected retrieved knowledge is absent")
    retrieved = user[user.index(RETRIEVAL_MARKER):]
    settings = {k: v for k, v in payload.items() if k not in {"messages", "format"}}
    return {
        "payload": payload, "raw_reply": raw_reply,
        "system": system, "user": user, "retrieved": retrieved,
        "schema": payload["format"], "model_settings": settings,
        "source": source, "source_line": line,
        "sha256": {k: text_hash(v) for k, v in {
            "system": system, "user": user, "retrieved": retrieved,
            "raw_reply": raw_reply}.items()},
    }


def build(evidence_root: Path) -> dict:
    journal = evidence_root / "original-llm_knowledge/decision_journal.jsonl"
    source_sha = sha(journal.read_bytes())
    native = {}
    for number, line in enumerate(journal.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        index = row.get("decision_index")
        if row.get("event") == "RETURNED" and index in (285, 286, 287):
            if index in native:
                raise ValueError(f"Duplicate returned decision {index}")
            native[index] = selected_request(row["payload"], row["raw_content"], {
                "path": "original-llm_knowledge/decision_journal.jsonl",
                "sha256": source_sha, "record_sha256": text_hash(line)}, number)
    days = []
    for index, (day, name) in enumerate(zip(DAYS, RAW_FILES), 285):
        path = evidence_root / "framework-llm_knowledge/operation/raw" / name
        trace = json.loads(path.read_text(encoding="utf-8"))["backend_trace"]
        framework = selected_request(
            trace["requests"][0]["payload"],
            trace["attempts"][0]["provider_reply"]["message"]["content"],
            {"path": path.relative_to(evidence_root).as_posix(), "sha256": sha(path.read_bytes())})
        original = native[index]
        for record in (original, framework):
            if not record["user"].startswith("Date: " + day):
                raise ValueError(f"Date mismatch for {day}")
        equal = {key: original[key] == framework[key]
                 for key in ("system", "user", "retrieved", "schema", "model_settings", "raw_reply")}
        if not all(equal[k] for k in ("system", "retrieved", "schema", "model_settings")):
            raise ValueError(f"Historical parity assertion changed on {day}")
        days.append({"date": day, "anik": original, "hydroopsllm": framework,
                     "equal": equal,
                     "user_differences": [
                         {"anik_lines": [a + 1, b], "anik": original["user"].splitlines()[a:b],
                          "hydroopsllm_lines": [c + 1, d], "hydroopsllm": framework["user"].splitlines()[c:d]}
                         for tag, a, b, c, d in difflib.SequenceMatcher(
                             a=original["user"].splitlines(), b=framework["user"].splitlines(),
                             autojunk=False).get_opcodes() if tag != "equal"],
                     "internal_record_only": {"framework_target_period": trace["input_variables"].get("target_period"),
                                              "sent_to_llm": False}})
    return {"schema_version": 1,
            "kind": "historical_actual_requests",
            "method": "LLM with additional operating knowledge",
            "evidence_root": "gemma4-comparison-2016",
            "notice": "Saved requests made before daily seasonal context was added. No new model request.",
            "client_settings": {"timeout_seconds": 120, "maximum_attempts": 2, "retry_delay_seconds": 2,
                                "note": "Client settings; these are not fields in the provider payload."},
            "days": days}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/_static/prompt-review-data.json")
    parser.add_argument("--criteria", type=Path,
                        help="Also write a separate proposed-context preview from this criteria file")
    args = parser.parse_args()
    data = build(args.evidence_root)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.criteria:
        from examples.fe_walter.extensions.seasonal_prompt_context import load_seasonal_prompt_context
        context = load_seasonal_prompt_context(args.criteria)
        preview = {
            "kind": "proposed_prompt_preview_not_sent_to_a_model",
            "criteria_file": criteria_source_label(args.criteria),
            "criteria_sha256": sha(args.criteria.read_bytes()),
            "days": [{"date": item["date"],
                      "added_context": context.render(date.fromisoformat(item["date"])),
                      "anik_user_preview": context.inject(item["anik"]["user"], date.fromisoformat(item["date"])),
                      "hydroopsllm_user_preview": context.inject(item["hydroopsllm"]["user"], date.fromisoformat(item["date"]))}
                     for item in data["days"]],
            "model_requests": 0,
        }
        args.output.with_name("seasonal-context-preview.json").write_text(
            json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha(args.output.read_bytes()),
                      "days": len(data["days"]), "model_requests": 0}))


if __name__ == "__main__":
    main()
