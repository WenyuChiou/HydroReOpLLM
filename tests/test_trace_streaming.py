"""Check long-log finalization memory, exact evidence hashes and read failures."""

import hashlib
import json
from pathlib import Path
import tracemalloc
from unittest.mock import patch

import pytest

from llm_reservoir_agent.trace import TraceJournal


def test_large_journal_finalizes_without_a_whole_log_memory_copy(tmp_path, record_property):
    journal = TraceJournal(tmp_path / "run", run_id="large-log")
    # Actual persisted events, rather than an artificial oversized summary.
    for i in range(16):
        journal.record_backend_event(
            "reservoir", f"diagnostic-{i}", timestep=0, timestamp="2020-01-01",
            details={"text": "x" * (1024 * 1024)},
        )
    path = journal.output / "backend_events.jsonl"
    assert path.stat().st_size > 16 * 1024 * 1024
    with path.open("rb") as stream:
        expected_hash = hashlib.file_digest(stream, "sha256").hexdigest()

    tracemalloc.start()
    try:
        result = journal.finalize()
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    record_property("finalization_peak_bytes", peak_bytes)
    record_property("journal_bytes", path.stat().st_size)
    assert peak_bytes < 6 * 1024 * 1024, peak_bytes
    saved = json.loads((journal.output / "summary.json").read_text())
    assert saved == result
    metadata = result["streams"]["backend_events"]
    assert metadata["sha256"] == expected_hash
    assert metadata["event_count"] == metadata["durable_event_count"] == 16
    assert metadata["incomplete_tail"] is False


def test_failed_journal_preserves_partial_tail_and_exact_hash(tmp_path):
    journal = TraceJournal(tmp_path / "run", run_id="partial-log")
    path = journal.output / "backend_events.jsonl"
    # Model a crash during one append, including a line crossing chunk boundaries.
    data = b'{"event":"' + b"x" * (2 * 1024 * 1024) + b'"}\n{"partial":'
    path.write_bytes(data)
    result = journal.fail("interrupted write")
    metadata = result["streams"]["backend_events"]
    assert result["status"] == "FAILED"
    assert metadata["sha256"] == hashlib.sha256(data).hexdigest()
    assert metadata["event_count"] == 1
    assert metadata["durable_event_count"] == 0
    assert metadata["incomplete_tail"] is True


def test_stream_read_failure_never_reports_a_completed_journal(tmp_path):
    journal = TraceJournal(tmp_path / "run", run_id="unreadable-log")
    real_open = Path.open

    def denied(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode")
        if path.name == "physics.jsonl" and mode == "rb":
            raise PermissionError("cannot read physical evidence")
        return real_open(path, *args, **kwargs)

    with patch.object(Path, "open", denied):
        with pytest.raises(PermissionError, match="physical evidence"):
            journal.finalize()
    assert not (journal.output / "summary.json").exists()
    with pytest.raises(RuntimeError, match="I/O failure"):
        journal.finalize()
