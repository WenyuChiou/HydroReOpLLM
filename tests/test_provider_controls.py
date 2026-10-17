"""Offline tests for generic provider request and retry controls."""

from __future__ import annotations

import hashlib
import unittest
from urllib.error import HTTPError

from llm_reservoir_agent.configured_backend import (
    ConfiguredBackend,
    chat_request,
    validate_model_settings,
)
from llm_reservoir_agent.contracts import ReservoirObservation
from llm_reservoir_agent.experiment import ProviderEvidenceError
from llm_reservoir_agent.prompt import PromptSpec


ACTION = '{"schema_version":"reservoir-action.v1","release_cms":4}'


def model(**updates):
    value = {
        "provider": "ollama",
        "model": "fixture-model",
        "base_url": "http://localhost:11434",
    }
    value.update(updates)
    return value


def configured(transport, **model_updates):
    knowledge = "rule one\n"
    spec = PromptSpec(
        strategy_id="provider-controls",
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


def observation():
    return ReservoirObservation(
        timestep=0,
        timestamp="2016-01-01T00:00:00Z",
        inflow_cms=3.0,
        release_upper_bound_cms=9.0,
        state={"storage_m3": 50.0},
        context={},
    )


def ollama_reply():
    return {"done": True, "done_reason": "stop", "message": {"content": ACTION}}


class ProviderControlTests(unittest.TestCase):
    def test_ollama_controls_are_opt_in_and_preserve_existing_order(self):
        default = validate_model_settings(model())
        _, default_payload = chat_request(default, [{"role": "user", "content": "x"}])
        self.assertNotIn("options", default_payload)
        self.assertNotIn("think", default_payload)
        self.assertNotIn("keep_alive", default_payload)

        settings = validate_model_settings(
            model(temperature=0.7, max_tokens=512, num_ctx=16384, think=False, keep_alive="30m")
        )
        schema = {"type": "object", "properties": {"z": {}, "a": {}}}
        messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        _, payload = chat_request(settings, messages, schema=schema)

        self.assertEqual(payload["messages"], messages)
        self.assertEqual(list(payload), ["model", "messages", "stream", "options", "format", "think", "keep_alive"])
        self.assertEqual(
            payload["options"],
            {"temperature": 0.7, "num_predict": 512, "num_ctx": 16384},
        )
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "30m")
        self.assertEqual(list(payload["format"]["properties"]), ["z", "a"])
        self.assertEqual(
            validate_model_settings(model(keep_alive=0))["keep_alive"], 0
        )

    def test_provider_controls_validation_rejects_unsafe_values(self):
        invalid = {
            "num_ctx": (True, 0, -1, 1.5, "16384"),
            "think": (0, "false", None),
            "keep_alive": (True, 1.5, "", " \t", "30m\nextra"),
            "retryable_http_statuses": (500, [True], [99], [600], [500, 500], ["500"]),
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises((TypeError, ValueError)):
                    validate_model_settings(model(**{key: value}))

        with self.assertRaises(ValueError):
            validate_model_settings(
                {
                    **model(provider="openai_compatible"),
                    "num_ctx": 1024,
                }
            )

    def test_selected_http_status_retries_with_identical_request_evidence(self):
        requests = []

        def transport(url, payload, headers, timeout):
            requests.append((url, payload, headers, timeout))
            if len(requests) == 1:
                raise HTTPError(url, 503, "unavailable", {}, None)
            return ollama_reply()

        item = configured(
            transport,
            max_attempts=2,
            retry_delay_seconds=0,
            retryable_http_statuses=[503],
        )
        self.assertEqual(item.decide(observation()).release_cms, 4)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0], requests[1])
        self.assertEqual(
            [attempt["request_sha256"] for attempt in item.latest_trace["attempts"]],
            [item.latest_trace["request_sha256"]] * 2,
        )

    def test_429_and_timeout_retry_only_within_declared_attempt_budget(self):
        for first_failure in (
            lambda url: HTTPError(url, 429, "rate limited", {}, None),
            lambda url: TimeoutError("timed out"),
        ):
            calls = []
            def transport(url, payload, headers, timeout):
                calls.append(url)
                if len(calls) == 1:
                    raise first_failure(url)
                return ollama_reply()
            item = configured(transport, max_attempts=2, retry_delay_seconds=0,
                              retryable_http_statuses=[429])
            with self.subTest(first_failure=first_failure):
                self.assertEqual(item.decide(observation()).release_cms, 4)
                self.assertEqual(len(calls), 2)

    def test_unselected_http_status_and_evidence_failure_never_retry(self):
        for failure in (
            lambda url: HTTPError(url, 503, "unavailable", {}, None),
            lambda url: ProviderEvidenceError("provider evidence fsync failed"),
        ):
            calls = []

            def transport(url, payload, headers, timeout):
                calls.append(url)
                raise failure(url)

            item = configured(
                transport,
                max_attempts=3,
                retry_delay_seconds=0,
                retryable_http_statuses=[429],
            )
            with self.subTest(failure=failure), self.assertRaises((HTTPError, ProviderEvidenceError)):
                item.decide(observation())
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
