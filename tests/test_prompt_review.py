"""The review keeps historical model input separate from proposed prompt edits."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

from scripts import build_prompt_review

from examples.fe_walter.extensions.seasonal_prompt_context import load_seasonal_prompt_context

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "docs/_static"
USER_HASHES = {
    "anik": (
        "3d742190a83304274f79f4c0484d6f7ecfc8c1e8f2f3ccfa8a65a0333a976ada",
        "9d69e2f9db221685de7ada2b12599b38eeca5caafa94a9063da7e293de7599fe",
        "1c5331730838d7310638544aedf85da7a064f2308b4cab4ec748853fa063b7b8",
    ),
    "hydroopsllm": (
        "b286d46599d8e9fe7bfb98a8c57f60118d543124c221ba0916146e8db11a702d",
        "c1853e719f63d73d2cfabcb1605417a465b25ac2fbf380cfa16acfd76d4b2e07",
        "9031aa37ce8f63594b7fb3516bce485e25399765ad3119007dbebd78d52e41ab",
    ),
}


def test_alternate_criteria_preview_records_its_actual_source(tmp_path, monkeypatch):
    """An external study file keeps its own source identity and byte hash."""
    actual_file = STATIC / "prompt-review-data.json"
    actual_bytes = actual_file.read_bytes()
    actual = json.loads(actual_bytes)
    criteria = tmp_path / "alternate_pool_criteria.json"
    criteria.write_bytes((ROOT / "examples/fe_walter/seasonal_pool_criteria.json").read_bytes() + b"\n")
    output = tmp_path / "request-review.json"
    monkeypatch.setattr(build_prompt_review, "build", lambda _: actual)
    monkeypatch.setattr(sys, "argv", [
        "build_prompt_review.py", "--evidence-root", str(tmp_path / "fixture"),
        "--output", str(output), "--criteria", str(criteria),
    ])

    build_prompt_review.main()

    preview = json.loads(output.with_name("seasonal-context-preview.json").read_text())
    assert preview["criteria_file"] == "external/alternate_pool_criteria.json"
    assert preview["criteria_sha256"] == hashlib.sha256(criteria.read_bytes()).hexdigest()
    assert str(tmp_path) not in preview["criteria_file"]
    assert preview["model_requests"] == 0
    assert json.loads(output.read_text()) == actual
    assert actual_file.read_bytes() == actual_bytes


def test_published_requests_preserve_independently_recorded_hashes():
    data = json.loads((STATIC / "prompt-review-data.json").read_text(encoding="utf-8"))
    assert data["kind"] == "historical_actual_requests"
    assert [item["date"] for item in data["days"]] == ["2016-10-12", "2016-10-13", "2016-10-14"]
    for index, day in enumerate(data["days"]):
        assert day["internal_record_only"]["sent_to_llm"] is False
        for key in ("system", "retrieved", "schema", "model_settings"):
            assert day["anik"][key] == day["hydroopsllm"][key]
        assert day["anik"]["user"] != day["hydroopsllm"]["user"]
        for engine in USER_HASHES:
            row = day[engine]
            assert hashlib.sha256(row["user"].encode()).hexdigest() == USER_HASHES[engine][index]
            assert row["payload"]["messages"] == [
                {"role": "system", "content": row["system"]},
                {"role": "user", "content": row["user"]},
            ]
            assert row["retrieved"] in row["user"]
            assert row["schema"] == row["payload"]["format"]
            assert "Study-defined seasonal pool context for" not in row["user"]
            assert json.loads(row["raw_reply"])  # Old replies remain valid, even where their dates are wrong.
            assert len(row["source"]["sha256"]) == 64


def test_proposed_context_is_separate_and_preserves_original_messages():
    actual = json.loads((STATIC / "prompt-review-data.json").read_text(encoding="utf-8"))
    proposed = json.loads((STATIC / "seasonal-context-preview.json").read_text(encoding="utf-8"))
    context = load_seasonal_prompt_context(ROOT / "examples/fe_walter/seasonal_pool_criteria.json")
    assert proposed["kind"] == "proposed_prompt_preview_not_sent_to_a_model"
    assert proposed["model_requests"] == 0
    assert proposed["criteria_sha256"] == context.sha256
    for old, new in zip(actual["days"], proposed["days"], strict=True):
        day = date.fromisoformat(old["date"])
        assert new["added_context"] == context.render(day)
        assert "summer" in new["added_context"]
        assert "no lower bound" in new["added_context"]
        assert "2016-10-15" in new["added_context"]
        for engine in USER_HASHES:
            assert new[engine + "_user_preview"] == old[engine]["user"] + "\n\n" + new["added_context"]
