"""Offline provider-retry contract tests; no sockets or real models."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from copy import deepcopy
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from llm_reservoir_agent.configured_backend import (
    ConfiguredBackend,
    validate_model_settings,
)
from llm_reservoir_agent.contracts import ReservoirObservation
from llm_reservoir_agent.prompt import PromptSpec
from examples.fe_walter.extensions.reference_backend import _ReferenceChatTransport


ACTION_TEXT = '{"schema_version":"reservoir-action.v1","release_cms":4}'
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string", "enum": ["reservoir-action.v1"]},
        "release_cms": {"type": "number"},
    },
    "required": ["schema_version", "release_cms"],
    "additionalProperties": False,
}


def model(**updates):
    value = {
        "provider": "openai_compatible",
        "model": "fixture-model",
        "base_url": "http://localhost:11434/v1",
    }
    value.update(updates)
    return value


def openai_reply(content=ACTION_TEXT, *, finish_reason="stop", request_id=None):
    value = {
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    }
    if request_id is not None:
        value["id"] = request_id
    return value


def observation():
    return ReservoirObservation(
        timestep=0,
        timestamp="2016-01-01T00:00:00Z",
        inflow_cms=3.0,
        release_upper_bound_cms=9.0,
        state={"storage_m3": 50.0},
        context={"forecast": "dry"},
    )


def configured(transport, **model_updates):
    knowledge = "rule one\n"
    spec = PromptSpec(
        strategy_id="retry-fixture",
        version="1",
        template="$agent_id|$observation|$knowledge|$previous_transition",
        knowledge_package_ids=("operations",),
        knowledge_package_sha256={
            "operations": hashlib.sha256(knowledge.encode("utf-8")).hexdigest()
        },
    )
    return ConfiguredBackend(
        agent_id="reservoir-a",
        mode="llm",
        prompt_spec=spec,
        knowledge_texts={"operations": knowledge},
        model=model(**model_updates),
        transport=transport,
    )


class ConfiguredRetryTests(unittest.TestCase):
    def test_retry_settings_defaults_and_validation(self):
        settings = validate_model_settings(model())
        self.assertEqual(settings["max_attempts"], 1)
        self.assertEqual(settings["retry_delay_seconds"], 2.0)
        for value in (True, 0, -1, 1.5, "2"):
            with self.subTest(max_attempts=value), self.assertRaises((TypeError, ValueError)):
                validate_model_settings(model(max_attempts=value))
        for value in (True, -0.1, float("nan"), "0"):
            with self.subTest(retry_delay=value), self.assertRaises((TypeError, ValueError)):
                validate_model_settings(model(retry_delay_seconds=value))

    def test_default_remains_one_attempt(self):
        calls = []

        def timeout(*args):
            calls.append(args)
            raise TimeoutError("secret detail")

        item = configured(timeout)
        with self.assertRaises(TimeoutError):
            item.decide(observation())
        self.assertEqual(len(calls), 1)
        self.assertEqual(item.network_calls, 1)
        self.assertEqual(len(item.latest_trace["attempts"]), 1)
        self.assertNotIn("secret detail", json.dumps(item.latest_trace))

    def test_transient_timeout_retries_same_request_then_succeeds(self):
        calls = []

        def transport(url, payload, headers, timeout):
            calls.append((url, deepcopy(payload), dict(headers), timeout))
            if len(calls) == 1:
                raise TimeoutError("temporary")
            return openai_reply(request_id="success")

        item = configured(transport, max_attempts=2, retry_delay_seconds=0)
        self.assertEqual(item.decide(observation()).release_cms, 4.0)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(item.network_calls, 2)
        attempts = item.latest_trace["attempts"]
        self.assertEqual([a["error_class"] for a in attempts], ["TimeoutError", None])
        self.assertEqual({a["request_sha256"] for a in attempts}, {item.latest_trace["request_sha256"]})
        self.assertEqual(item.latest_trace["request_id"], "success")

    def test_truncated_and_invalid_json_replies_are_retryable(self):
        for first in (
            openai_reply(finish_reason="length", request_id="truncated"),
            openai_reply("{", request_id="invalid-json"),
        ):
            with self.subTest(first=first["id"]):
                replies = [first, openai_reply(request_id="success")]
                item = configured(
                    lambda *args: replies.pop(0),
                    max_attempts=2,
                    retry_delay_seconds=0,
                )
                self.assertEqual(item.decide(observation()).release_cms, 4.0)
                attempts = item.latest_trace["attempts"]
                self.assertEqual(len(attempts), 2)
                self.assertEqual(attempts[0]["provider_reply"]["id"], first["id"])
                self.assertEqual(
                    attempts[0]["usage"],
                    {"prompt_tokens": 3, "completion_tokens": 2},
                )
                self.assertEqual(attempts[0]["request_id"], first["id"])
                self.assertIsNotNone(attempts[0]["error_class"])
                self.assertTrue(attempts[1]["success"])

    def test_two_malformed_replies_fail_and_preserve_both_raws(self):
        replies = [
            openai_reply("{", request_id="bad-1"),
            openai_reply("[", request_id="bad-2"),
        ]
        item = configured(
            lambda *args: replies.pop(0), max_attempts=2, retry_delay_seconds=0
        )
        with self.assertRaises(json.JSONDecodeError):
            item.decide(observation())
        self.assertEqual(
            [a["provider_reply"]["id"] for a in item.latest_trace["attempts"]],
            ["bad-1", "bad-2"],
        )
        self.assertEqual(item.network_calls, 2)

    def test_permanent_http_and_missing_auth_do_not_retry(self):
        calls = []
        error = HTTPError(
            "http://localhost:11434/v1/chat/completions",
            401,
            "secret",
            {},
            BytesIO(),
        )

        def permanent(url, *args):
            calls.append(url)
            raise error

        item = configured(permanent, max_attempts=3, retry_delay_seconds=0)
        with self.assertRaises(HTTPError):
            item.decide(observation())
        error.close()
        self.assertEqual(len(calls), 1)

        evidence_calls = []

        def evidence_failure(*args):
            evidence_calls.append(args)
            raise RuntimeError("evidence fsync failed")

        evidence = configured(
            evidence_failure, max_attempts=3, retry_delay_seconds=0
        )
        with self.assertRaises(RuntimeError):
            evidence.decide(observation())
        self.assertEqual(len(evidence_calls), 1)

        auth_calls = []
        auth = configured(
            lambda *args: auth_calls.append(args),
            max_attempts=3,
            retry_delay_seconds=0,
            api_key_env="ABSENT_RETRY_TEST_KEY",
        )
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "unset"):
            auth.decide(observation())
        self.assertEqual(auth_calls, [])
        self.assertEqual(auth.network_calls, 0)

    def test_transport_counter_is_authoritative_without_double_count(self):
        class BudgetedTransport:
            def __init__(self):
                self.network_calls = 0

            def __call__(self, *args):
                self.network_calls += 1
                if self.network_calls == 1:
                    raise TimeoutError("temporary")
                return openai_reply()

        transport = BudgetedTransport()
        item = configured(transport, max_attempts=2, retry_delay_seconds=0)
        self.assertEqual(item.decide(observation()).release_cms, 4.0)
        self.assertEqual(transport.network_calls, 2)
        self.assertEqual(item.network_calls, 2)


class ReferenceRetryTests(unittest.TestCase):
    def test_reference_invalid_json_retries_and_keeps_native_stats(self):
        calls = []

        def transport(url, payload, headers, timeout):
            calls.append(deepcopy(payload))
            return openai_reply("{" if len(calls) == 1 else ACTION_TEXT)

        item = _ReferenceChatTransport(
            model(max_attempts=2, retry_delay_seconds=0), transport
        )
        self.assertEqual(item.decide("system", "prompt", schema=ACTION_SCHEMA)["release_cms"], 4)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(item.network_calls, 2)
        self.assertEqual(item.last_call_stats["backend_attempts"], 2)
        self.assertEqual(len(item.latest_trace["attempts"]), 2)

    def test_valid_strategy_fail_value_is_not_retried(self):
        schema = {
            "type": "object",
            "properties": {"audit_status": {"type": "string", "enum": ["FAIL"]}},
            "required": ["audit_status"],
            "additionalProperties": False,
        }
        calls = []

        def transport(*args):
            calls.append(args)
            return openai_reply('{"audit_status":"FAIL"}')

        item = _ReferenceChatTransport(
            model(max_attempts=3, retry_delay_seconds=0), transport
        )
        self.assertEqual(item.decide("system", "prompt", schema=schema), {"audit_status": "FAIL"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(item.last_call_stats["backend_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
