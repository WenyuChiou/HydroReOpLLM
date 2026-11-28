# 步驟 02：水庫物理與決策 Agent 設定

檢查 `case.json` 水庫庫容、放流上下限與單位歷線，並以 `load_settings`（離線 `check`）對照 `rule_based.yaml`、`seasonal_target.yaml` 與 `dkp.yaml`（`prompts/*.txt`、`dkp.md`）的 SHA-256 鎖定與第 1 天提示詞預覽。

```sh
python -m jupyterlab tutorials/02_reservoir_and_agent_setup/02_reservoir_and_agent_setup.ipynb
```

下一步：**[步驟 03：運行單庫模擬與驗證](../03_run_single_reservoir_simulation/README.zh-TW.md)** · **[實作課程總覽](../README.zh-TW.md)**
