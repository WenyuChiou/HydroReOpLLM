# Historical recovery index

[File inventory](inventory.csv) records all **1,026** pre-cleanup tracked paths,
their dependencies, original bytes/SHA256 and disposition.

The seven historical root launchers and retired guides/notebooks are in the
external **HydroOpsLM-pre-cleanup-20261012-fbd9a993** recovery package.
The maintained entry is [run_experiment.py](../run_experiment.py).

| Recovery artifact | SHA256 |
|---|---|
| `tracked-working-tree.zip` — original paths/bytes | `3c5ec105f1d854aca54745032771e3c6cd55b368aba0eb997d2dd1ed500fc92d` |
| `complete-history.bundle` — complete Git history | `d25ed82b340a69d0e61347644a0537b52272ef37bbb7791e83d56d586aab67d2` |

Base commit: `fbd9a993731ce979835dcc46f7a9cbad6aa7387b`.
The package is kept outside the repo at `../_recovery/`; request it from the
maintainer to reproduce a retired entry. All 1,026 paths were restored and
verified byte-for-byte in `verified-restoration/`; `git bundle verify` passed.

After checking both archive hashes, restore into a **new directory**:

```powershell
git clone --branch main complete-history.bundle restored-repo
python -m zipfile -e tracked-working-tree.zip restored-repo
```

Git supplies history; ZIP restores exact working-tree bytes, including original
line endings. Compare each file with `inventory.csv`. Do not overwrite an active
checkout or rerun an experiment to inspect it. Ignored runs, environments and
credentials are excluded; existing local evidence remains in its original place.

Required helpers remain under `src/delaware_operations` and `third_party`:
the formal DKP adapter/auditor uses the preserved original policy loader.
The historical recovery module requires its restored launchers and original
revision. Existing console entrypoints, accepted inputs, C&V, raw replies,
audit failures and unknown costs remain preserved.

歷史入口與文件已移至 repo 外的恢復包；原始 hash 及去向見 CSV。
正式操作使用 `run_experiment.py`。恢復到新目錄並逐項核對 bytes，
不要覆寫目前 repo 或重跑已完成實驗。必要 helper 與原始紀錄保留。
