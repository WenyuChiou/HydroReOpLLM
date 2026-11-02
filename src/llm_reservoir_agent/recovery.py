"""Resume a pinned interrupted run by replaying replies into fresh native physics.

``workflow`` supplies current validated settings. ``RecoveryTape`` reads the
source run, pins journal/raw bytes and requires identical settings, inputs,
package/adapter bytes, Python version and host-core metadata. During execution,
matching regenerated requests reuse saved responses and committed prompt values;
native routing/storage/history are reconstructed and compared to saved physics.
No source files are changed. A distinct run ID and new output directory preserve
the interrupted evidence; any newly needed request remains subject to explicit
network opt-in and the cumulative attempt budget. STARTED reservations count even
when a terminal reply was not saved. Flow/storage retain native m3/s and m3.
Dynamic numeric extension information is rejected without a durable replay
contract. Incomplete final journal lines remain in the source and are reported.
"""
import hashlib
import json
from pathlib import Path
import platform

from .audit import canonical_sha256, json_snapshot


def _sha(path):
    """Read and hash exact saved bytes; missing/unreadable source evidence must stop recovery."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(path):
    """Read a strict finite JSON object using the backend parser; reject nonobject evidence instead of accepting a partial contract."""

    from .configured_backend import _strict_json
    value = _strict_json(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("recovery requires a JSON object: " + path.name)
    return value


class RecoveryTape:
    """Validate interrupted-run evidence before any replay or new request.

    Construction only reads source evidence. Replay advances an in-memory cursor and reconstructs host physics; it does not resume by mutating saved storage or overwrite the interrupted directory.

    Parameters
    ----------
    source : str or pathlib.Path
        Interrupted output directory; a completed run must be verified instead.
    settings : ExperimentSettings
        Current validated network, inflows, settings, file pins and request plan.
    runtime_root : str or pathlib.Path
        Runtime checkout containing core metadata and the ABM source used by the saved run.

    Raises
    ------
    ValueError
        Runtime/input hashes, journal scope, replay contracts or evidence integrity differ.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """

    def __init__(self, source, settings, runtime_root):
        self.source = Path(source).resolve()
        # Number of saved request attempts consumed; independent of physical-step count.
        self._cursor = 0
        self._checked_physics = set()
        self._physics = {}
        self._replies = []
        self._contexts = {}
        self._hashes = {}
        self._incomplete_tails = {}
        experiment = _object(self.source / "experiment.json")
        self.source_run_id = experiment["run_id"]
        from .experiment import _adapter_implementation_files, _implementation_files
        implementations = _implementation_files()
        root = Path(runtime_root)
        if (experiment.get("implementation_files") != implementations
                or experiment.get("adapter_implementation_files") != _adapter_implementation_files()
                or experiment.get("python") != platform.python_version()
                or experiment.get("hydrocnhs_core") != _object(root / "environment/hydrocnhs-core.json")
                or experiment.get("abm_module_sha256") != _sha(root / "examples/llm_reservoir_abm.py")):
            raise ValueError("recovery runtime or implementation changed; use a new experiment")
        if experiment["network"] != settings.network or experiment["inflow_records"] != settings.rows:
            raise ValueError("recovery network or inflow differs from the saved run")
        # Dynamic external information needs its own durable replay contract.
        if any(source.get("type") == "extension" for source in settings.data.get("information_sources", {}).values()):
            raise ValueError("recovery of numeric extension information requires a durable provider replay contract")
        summary = None
        if (self.source / "summary.json").exists():
            summary = _object(self.source / "summary.json")
            if summary.get("status") == "COMPLETED":
                raise ValueError("the source run already completed; verify it instead")
        # STARTED is a conservative reservation: after a crash an in-flight
        # request may have reached the provider even without a terminal event.
        ledger = self.source / "provider_attempts.jsonl"
        if settings.report["planned_llm_calls"] and not ledger.is_file():
            raise ValueError("recovery requires the original provider-attempt accounting ledger")
        prior = experiment.get("recovery", {}).get("prior_network_calls", 0)
        if isinstance(prior, bool) or not isinstance(prior, int) or prior < 0:
            raise ValueError("invalid inherited recovery request count")
        started = []
        if ledger.exists():
            from .configured_backend import _strict_json
            raw = ledger.read_bytes()
            self._hashes[ledger.name] = hashlib.sha256(raw).hexdigest()
            expected = (summary or {}).get("summary", {}).get("provider_attempts_sha256")
            if expected and expected != self._hashes[ledger.name]:
                raise ValueError("provider-attempt ledger integrity hash mismatch")
            for line in raw.splitlines(keepends=True):
                if line.endswith(b"\n"):
                    item = _strict_json(line.decode("utf-8"))
                    if item.get("status") == "STARTED":
                        started.append(item["attempt"])
            if len(set(started)) != len(started):
                raise ValueError("duplicate provider-attempt reservation")
        # Cumulative reservations include requests that may have been in flight at a crash.
        self.prior_network_calls = prior + len(started)
        streams = {}
        for name in ("decisions", "physics", "audit", "backend_events"):
            path = self.source / (name + ".jsonl")
            raw = path.read_bytes()
            self._hashes[path.name] = hashlib.sha256(raw).hexdigest()
            spec = (summary or {}).get("streams", {}).get(name)
            if spec and spec.get("sha256") != self._hashes[path.name]:
                raise ValueError("recovery journal integrity hash mismatch")
            lines = raw.splitlines(keepends=True)
            if lines and not lines[-1].endswith(b"\n"):
                self._incomplete_tails[name] = len(lines.pop())
            from .configured_backend import _strict_json
            streams[name] = [_strict_json(line.decode("utf-8")) for line in lines]
        decisions = streams["decisions"]
        provenance = experiment.get("provenance") or (
            decisions[0].get("provenance", {}) if decisions else {})
        if (provenance.get("settings") != settings.data
                or provenance.get("source_files") != settings.files):
            raise ValueError("recovery settings or pinned source files changed")
        self._hashes["experiment.json"] = _sha(self.source / "experiment.json")
        if summary is not None:
            self._hashes["summary.json"] = _sha(self.source / "summary.json")
        # Validate all referenced raw bytes, including failed attempts and audits.
        for events in streams.values():
            for event in events:
                if event.get("run_id") != self.source_run_id:
                    raise ValueError("recovery journal run identity mismatch")
                for key, ref in event.items():
                    if key.endswith("_ref") and isinstance(ref, dict) and "path" in ref:
                        self._reference(ref)
        by_id = {}
        for event in decisions:
            key = (event["reservoir_id"], event["timestep"])
            if key in by_id:
                raise ValueError("duplicate saved decision")
            by_id[key] = event
            if event.get("provenance", {}).get("model_used") is False:
                continue
            raw = self._reference(event["raw_policy_ref"])
            trace = raw.get("backend_trace", raw)
            if not trace or trace.get("model_used") is False:
                continue
            contexts = trace.get("context_provenance", {})
            if contexts:
                self._contexts[key] = json_snapshot(contexts)
            requests = trace.get("requests")
            if requests and isinstance(trace.get("attempts"), list):
                by_request = {request["request_sha256"]: request for request in requests}
                for attempt in trace["attempts"]:
                    request = by_request.get(attempt["request_sha256"])
                    if request is None:
                        raise ValueError("saved attempt has no matching provider request")
                    response = attempt.get("provider_reply")
                    if response is None and not attempt.get("error_class"):
                        raise ValueError("saved attempt has neither response nor error evidence")
                    self._replies.append(dict(reservoir_id=event["reservoir_id"],
                        request_sha256=canonical_sha256({"url": request["url"], "payload": request["payload"]}),
                        provider=request["provider"], response=response,
                        error_class=attempt.get("error_class"), http_status=attempt.get("http_status"),
                        hash_with_provider=False))
                continue
            provider = trace.get("provider") or trace.get("model", {}).get("provider")
            response = trace.get("provider_reply")
            if response is None and isinstance(trace.get("raw_reply"), dict):
                response = trace["raw_reply"]
            if provider not in ("ollama", "openai_compatible", "openai", "anthropic", "gemini") or response is None:
                raise ValueError("saved decision has no replayable provider response")
            self._replies.append(dict(reservoir_id=event["reservoir_id"],
                                      request_sha256=trace["request_sha256"],
                                      provider=provider, response=response,
                                      hash_with_provider=None))
        for event in streams["physics"]:
            key = (event["reservoir_id"], event["timestep"])
            decision = by_id.get(key)
            if key in self._physics or decision is None:
                raise ValueError("saved physical record has no unique decision")
            record = event["record"]
            if (record["observation"] != decision["observation"]
                    or record["action"] != decision["action"]):
                raise ValueError("saved physical record differs from its decision")
            self._physics[key] = record

    def _reference(self, ref):
        """Resolve raw references inside the source directory and verify exact SHA256 before strict JSON reads; escaping paths or mismatched bytes fail."""

        path = (self.source / ref["path"]).resolve()
        if not path.is_relative_to(self.source) or _sha(path) != ref["sha256"]:
            raise ValueError("recovery raw checksum mismatch or escaping reference")
        self._hashes[ref["path"]] = ref["sha256"]
        return _object(path)

    def next_reply(self, reservoir_id, url, payload):
        """Reuse the next saved response only for an identical regenerated request.

        Both documented legacy request-hash conventions are checked against actual content. Consuming a recorded failure advances the cursor; it does not issue a network request.

        Parameters
        ----------
        reservoir_id : str
            Acting physical reservoir identity; replay order must match source evidence.
        url : str
            Regenerated provider endpoint, included in the request-content hash.
        payload : Mapping
            Regenerated provider payload; exact canonical content must match saved evidence.

        Returns
        -------
        tuple[bool, object]
            True with a detached saved response, or False/None after the complete saved prefix has been reconstructed.

        Raises
        ------
        ValueError
            Request identity/content/order differs or saved-prefix physics is not fully reconstructed.
        HTTPError, URLError, TimeoutError or ConnectionError
            A retained provider failure is reproduced from its saved error class/status.
        """
        if self._cursor == len(self._replies):
            if self._checked_physics != set(self._physics):
                raise ValueError("recovery prefix physics has not been reconstructed")
            return False, None
        item = self._replies[self._cursor]
        request = {"url": url, "payload": payload}
        hashes = {canonical_sha256(request)}
        # Legacy traces used both hash conventions. Compare their actual bytes,
        # rather than guessing the convention from a compatibility alias.
        if item.get("hash_with_provider") is not False:
            hashes.add(canonical_sha256(dict(request, provider=item["provider"])))
        if item["reservoir_id"] != reservoir_id or item["request_sha256"] not in hashes:
            raise ValueError("reconstructed provider request differs from recovery evidence")
        self._cursor += 1
        if item["response"] is None:
            from urllib.error import HTTPError, URLError
            error = item.get("error_class")
            if error == "HTTPError" and isinstance(item.get("http_status"), int):
                raise HTTPError(url, item["http_status"], "recorded provider failure", {}, None)
            if error == "TimeoutError":
                raise TimeoutError("recorded provider timeout")
            if error == "ConnectionError":
                raise ConnectionError("recorded provider connection failure")
            if error == "URLError":
                raise URLError(ConnectionError("recorded provider connection failure"))
            raise ValueError("saved provider failure cannot be reconstructed safely")
        return True, json_snapshot(item["response"])

    def context_value(self, reservoir_id, timestep, alias):
        """Reuse a retained prompt binding before constructing its retriever.

        Parameters
        ----------
        reservoir_id : str
            Acting physical reservoir identity.
        timestep : int
            Zero-based decision step in the source run.
        alias : str
            Selected prompt-binding name.

        Returns
        -------
        tuple[bool, ContextValue or None]
            True with the validated saved binding, or False/None when that alias has no saved value.

        Raises
        ------
        ValueError
            Saved context fields do not match the supported replay contract.
        TypeError
            A value has the wrong type or is not finite JSON.
        ValueError
            A required field, version, numeric bound or digest is invalid.
        """
        values = self._contexts.get((reservoir_id, timestep), {})
        if alias not in values:
            return False, None
        from .context import ContextValue
        value = values[alias]
        if not isinstance(value, dict) or set(value) != {"value", "provenance", "available"}:
            raise ValueError("saved prompt context has an unsupported replay contract")
        return True, ContextValue(**value)

    def check_physics(self, reservoir_id, record):
        """Compare regenerated completed physics with the saved prefix.

        Comparison is exact across the full record, so requested action, implemented release/spill, storage and causal inputs must all match.

        Parameters
        ----------
        reservoir_id : str
            Physical reservoir identity.
        record : Mapping
            Regenerated observation/action/transition; native storage m3 and flow m3/s.

        Returns
        -------
        None
            A matching saved record is marked reconstructed; steps absent from the saved prefix require no comparison.

        Raises
        ------
        ValueError
            Any regenerated record content differs from its saved counterpart.
        """

        key = (reservoir_id, record["observation"]["timestep"])
        if key in self._physics:
            original = self._physics[key]
            if record != original:
                raise ValueError("reconstructed physical state differs from recovery evidence")
            self._checked_physics.add(key)

    def finish(self):
        """Require complete saved-response consumption and prefix-physics reconstruction.

        Returns
        -------
        None
            All saved replies and physical records were consumed/checked.

        Raises
        ------
        ValueError
            The run ended before its entire saved prefix was reconstructed.
        """

        if self._cursor != len(self._replies) or self._checked_physics != set(self._physics):
            raise ValueError("recovery did not consume and verify its saved prefix")

    def describe(self):
        """Describe recovery provenance and cumulative replay accounting.

        Prior network calls count inherited reservations plus source STARTED events, including potentially in-flight requests after a crash.

        Returns
        -------
        dict
            Source path/ID, exact-file hashes, consumed replies, prior attempt reservations, reconstructed record count and retained incomplete-tail byte counts.
        """

        return {"source_run": str(self.source), "source_run_id": self.source_run_id,
                "source_files": dict(self._hashes),
                "replayed_provider_replies": self._cursor,
                "prior_network_calls": self.prior_network_calls,
                "reconstructed_physical_records": len(self._checked_physics),
                "incomplete_tail_bytes_retained_in_source": dict(self._incomplete_tails),
                "method": "replay unchanged requests/replies; reconstruct native routing and policy history"}


def resume_settings(settings, source, *, output, run_id, allow_network=False,
                    runtime_root=None, transport=None):
    """Reconstruct an unchanged interrupted prefix and continue in a new run.

    Recovery checks implementation bytes and Python version as well as scientific inputs. Newly executed backend/callback failures propagate under normal workflow accounting.

    Parameters
    ----------
    settings : ExperimentSettings
        Current validated settings matching the source experiment.
    source : str or pathlib.Path
        Interrupted run directory retained unchanged.
    output : str or pathlib.Path
        Distinct new output directory; it must not exist.
    run_id : str
        Nonempty identity distinct from the source run ID.
    allow_network : bool, optional
        Explicit permission for missing decisions after replay; saved replies need no new request.
    runtime_root : str or pathlib.Path or None, optional
        Pinned runtime checkout, defaulting to network.PROJECT_ROOT.
    transport : callable or None, optional
        Injected transport used only for newly needed authorized requests.

    Returns
    -------
    tuple[dict, dict]
        Completed records and new trace summary returned by run_settings, with recovery provenance.

    Raises
    ------
    FileExistsError
        The output already exists or would overwrite the source.
    ValueError
        Run identity or saved/current evidence is incompatible.
    OSError
        A required file cannot be read, created, flushed or replaced.
    """
    from .network import PROJECT_ROOT
    from .workflow import run_settings
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source:
        raise FileExistsError("recovery requires a new output directory")
    tape = RecoveryTape(source, settings, runtime_root or PROJECT_ROOT)
    if not isinstance(run_id, str) or not run_id.strip() or run_id == tape.source_run_id:
        raise ValueError("recovery requires a distinct nonempty run_id")
    return run_settings(settings, allow_network=allow_network,
                        runtime_root=runtime_root or PROJECT_ROOT,
                        transport=transport, recovery=tape, output=output, run_id=run_id)
