# Historical compatibility and evidence

The supported teaching entry is [three FE Walter methods](../examples/README.md).

Previous configs under `experiments/`, old synthetic cases under `cases/`, and the two generic prompt files at `prompts/` are retired teaching entries. Their original paths and bytes remain available because accepted provenance and historical tests reference them. The canonical synthetic fixtures now live in [tests/fixtures](../tests/fixtures/README.md).

Frozen `data/accepted`, `data/anik_v3_7`, `cases`, `third_party`, native `src/hydrocnhs`, and historical `results` retain their accepted bytes. This archive index does not move or rewrite scientific records. The existing `examples/fe_walter/*/experiment.yaml` files are historical reproductions; use the new `experiment.tutorial.yaml` files for new offline outputs.

Five-year historical results remain diagnostic: audit FAIL/WARN and unknown request costs are preserved. See [the inventory](../docs/PROJECT_INVENTORY.md) and [acceptance](../docs/upgrade_acceptance.md).

The earlier [configured-backend guide](CONFIGURED_BACKEND_GUIDE.zh-TW.md) remains available for historical/custom configurations; new users start with the current three-method tutorial.
