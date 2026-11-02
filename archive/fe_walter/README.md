# F.E. Walter historical inputs

The maintained case uses two current [system prompts](../../examples/fe_walter/prompts)
and one [operating reference](../../examples/fe_walter/knowledge/operating_rules.md).
This index records recovery sources for earlier configurations and prompt hashes.

The supplied original Anik program is **not distributed in the current source
tree or wheel**. Its original file hashes are retained in
[`original_source_manifest.json`](original_source_manifest.json). The normal
FE Walter backend uses our case formatter/parser and the generic framework;
it does not import that original program.

For an optional original-program comparison, obtain the verified recovery package
from the maintainer and set `HYDROOPS_ANIK_SOURCE_DIR` to its external
`verified-restoration/third_party/anik_v3_7` directory. The comparison loader
checks all four original Python file hashes before import. No file is downloaded
or restored automatically.

Recovery package: `HydroOpsLLM-reference-cleanup-20261018-58dc232`, preserved
outside this repository under `../_recovery/`.

| Artifact | SHA256 |
|---|---|
| `reference-inputs.zip` | `e68caf069e01f17fb95c49d0386fc2c8c8fa8301121e127bb222d765e2a7cef7` |
| `complete-history.bundle` | `208f0794d16b685ac52aea47f56e2fdae1fcbc222987131d2097d205191e7bd3` |

The ZIP includes original input bytes and incidental local cache files; only the
six original source/manifest files are the reference program. All source files
were restored and verified by hash before removal from the tracked tree. The Git
bundle passed verification and preserves the full history through `58dc232`.
Historical result files and their original paths/hashes were not rewritten.

The duplicate `coupled/current/` and model-version-named YAML entries were later
consolidated into `examples/fe_walter/coupled/`. Their original files remain in
the history bundle above. Resolving the maintained configurations before and
after that path change produced identical settings and referenced resources.

Framework tests run without the artifact. Tests that execute the original program
report explicit skips when the environment variable is absent. This is not a
passing original-program equivalence check. To inspect a frozen older executor,
restore its recorded revision into a separate directory; do not repin or rerun it.

## Retired case configurations and prompts

The earlier method YAMLs, prompt snapshots and annual preparation script are
preserved in `HydroOpsLLM-case-entries-cleanup-20261018-5696dc1` outside this
repository under `../_recovery/`. The ZIP's 34 files were restored and checked byte
for byte; the Git bundle was verified before retirement. Historical result files
remain in the repository. The maintained entry is the [coupled tutorial](../../tutorials/README.md).

| Artifact | SHA256 |
|---|---|
| `historical-case-entries.zip` | `ff489dd2a41452695f681da694393a2fef1697e46ec282398056b33cad5d99d4` |
| `complete-history.bundle` | `fc4fd71eb029f6b9c7877dcbf3d2c7fbc706eb721149509c8ff440e72726e438` |

`HYDROOPS_FE_WALTER_HISTORY_DIR` selects the restored root for optional historical
prompt checks. This is separate from `HYDROOPS_ANIK_SOURCE_DIR`, which selects the
original program. Neither is needed for the maintained custom-prompt configurations.
The historical profile retains its original paths and hashes as provenance.
Restore frozen executors at their recorded revision for reproduction.

Equivalent offline aliases were also retired: `benchmark/experiment.yaml` and
`tutorials/config/multi_reservoir.offline.yaml` retain the same inputs, agents,
rules, fixture decisions and zero-call settings. Their run IDs and output paths
remain independently chosen. Original aliases and the pre-deletion working-tree test snapshot for the retired
annual generator are retained in `retired-aliases-and-tests.zip` beside the recovery
package. The Git bundle preserves the exact baseline revision.
