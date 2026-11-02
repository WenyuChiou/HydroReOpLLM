"""Exercise metadata-only Windows rename retries without repeating decisions."""

import errno
import json
from unittest.mock import patch

import pytest

from llm_reservoir_agent.experiment import write_json


def locked():
    error = PermissionError("destination is temporarily locked")
    error.winerror = 32
    return error


def test_temporary_windows_lock_retries_the_same_fsynced_file(tmp_path):
    import os

    path = tmp_path / "progress.json"
    path.write_text('{"previous":true}\n')
    actual_replace = os.replace
    calls = []

    def replace(source, destination):
        calls.append((source, destination, source.read_bytes()))
        if len(calls) == 1:
            raise locked()
        actual_replace(source, destination)

    with patch("llm_reservoir_agent.experiment.os.replace", side_effect=replace):
        with patch("llm_reservoir_agent.experiment.time.sleep") as sleep:
            write_json(path, {"completed": 1})
    assert calls[0] == calls[1]
    sleep.assert_called_once_with(0.05)
    assert json.loads(path.read_text()) == {"completed": 1}
    assert not path.with_suffix(".json.tmp").exists()


def test_permanent_windows_lock_preserves_both_files_and_stops(tmp_path):
    path = tmp_path / "progress.json"
    previous = b'{"completed":0}\n'
    path.write_bytes(previous)
    with patch("llm_reservoir_agent.experiment.os.replace", side_effect=locked()) as replace:
        with patch("llm_reservoir_agent.experiment.time.sleep") as sleep:
            with pytest.raises(PermissionError):
                write_json(path, {"completed": 1})
    assert replace.call_count == 6
    assert sleep.call_count == 5
    assert path.read_bytes() == previous
    assert json.loads(path.with_suffix(".json.tmp").read_text()) == {"completed": 1}


def test_other_os_error_has_no_retry(tmp_path):
    path = tmp_path / "progress.json"
    with patch("llm_reservoir_agent.experiment.os.replace", side_effect=OSError(errno.EIO, "disk failure")) as replace:
        with patch("llm_reservoir_agent.experiment.time.sleep") as sleep:
            with pytest.raises(OSError, match="disk failure"):
                write_json(path, {"completed": 1})
    assert replace.call_count == 1
    sleep.assert_not_called()
    assert not path.exists()


def test_flush_failure_never_attempts_rename(tmp_path):
    path = tmp_path / "progress.json"
    with patch("llm_reservoir_agent.experiment.os.fsync", side_effect=OSError("flush failed")):
        with patch("llm_reservoir_agent.experiment.os.replace") as replace:
            with pytest.raises(OSError, match="flush failed"):
                write_json(path, {"completed": 1})
    replace.assert_not_called()
    assert not path.exists()
