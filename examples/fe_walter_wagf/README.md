# F.E. Walter with WAGF checks
Each simulated day a model proposes a release, WAGF checks it against the rules of the chosen
arm (`none`, `physical` or `full`), and HydroCNHS applies the result.

## Run

From the repository root. `WAGF_ROOT` is your WAGF checkout.
```bash
export WAGF_ROOT=/path/to/governed_broker_framework
export PYTHONPATH=src
python -m llm_reservoir_agent.workflow check examples/fe_walter_wagf/run_2021_full.yaml
python -m llm_reservoir_agent.workflow run   examples/fe_walter_wagf/run_2021_full.yaml --allow-network
```

Two folders are written: the HydroCNHS run (`output`) and the WAGF folder (`wagf.output`). A local model needs a running Ollama server.

## Resume after a crash

Use the same run file. Point `--from-run` at the folder that died, with a new output and run id:
```bash
python -m llm_reservoir_agent.workflow resume examples/fe_walter_wagf/run_2021_full.yaml \
  --from-run runs/fe-walter-wagf-2021-full \
  --output runs/fe-walter-wagf-2021-full-resume1 --run-id fe-walter-wagf-2021-full-resume1 \
  --allow-network
```

Saved days are replayed from the saved replies and send no request; new requests start at the
first unsaved day. The crashed folder is not changed. After a second crash, resume from the
latest resume folder. Do not edit the run file, `config/`, the extension or the WAGF code in
between: the resume refuses if they changed. Keep the WAGF folder as well. Without it the saved
days' versions cannot be compared, so the resume stops on the first replayed day. If the crash
came in the middle of that day, one new request can go out before it stops. A saved provider
error of a type the replay does not know (an SSL error, for example) also stops the resume with
an error; run that case again from the start.

## Earlier WAGF output is kept

Starting never overwrites the WAGF folder. If it holds files from the same run identity, all of
it moves to `<name>.previous-1` (then `-2`, ...) and a clean folder starts. If the identity
differs, the start stops before any request and names the differing fields; choose a new
`wagf.output`.

## run_identity.json

Written to the WAGF folder before the first request. It records:

- the arm and the WAGF seed;
- the WAGF git commit and dirty flag (null without git), and a SHA-256 of the code and YAML files
  in `broker/`;
- SHA-256 of `config/agent_types.yaml` and `config/skill_registry.yaml`;
- the model provider, requested name and base URL (never a key);
- for a local Ollama model: digest, family, parameter size, quantization, server version and
  read time. The digest is read again after the last day. If it changed, the run fails and
  `model_changed_during_run` is true. If it cannot be read, the run also fails, and
  `digest_at_end_error` says why. The saved results stay on disk in both cases.

`wagf.expected_model_digest` (with or without `sha256:`) is an optional pin for a local model.
A resume needs the stable fields to match, including the digest and the Ollama server version,
so upgrading Ollama blocks a resume. Read time, git commit and dirty flag do not count.

## Cloud models

A cloud model name cannot prove which build answered, and there is no digest, so none is
claimed. `observed_provider_models` lists the names the provider returned, with counts, as a
hint only. Use a dated model name where the provider offers one.
