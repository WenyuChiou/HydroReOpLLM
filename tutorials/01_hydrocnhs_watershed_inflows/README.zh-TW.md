# 步驟 01：HydroCNHS 集水區水文與入流準備

檢視 [`hydrology.yaml`](../../examples/multi_reservoir/hydrology/hydrology.yaml) 與 [`xindian_catchments.yaml`](../../examples/multi_reservoir/hydrology/xindian_catchments.yaml)，驗證子集水區 `inflow_bindings` 零重疊，並跑通 HydroCNHS（`GWLF + Lohmann`）檢驗 10 年（`2016–2025`）驗證成效與 [`inflows.csv`](../../examples/multi_reservoir/inflows.csv) 一致性。

> **註記：** 台灣新店溪（`U1–U2`、`D1–D2`，TFRA 與經濟部水利署資料）為 **Repo 專屬範例，未收錄於論文**。

```sh
python -m jupyterlab tutorials/01_hydrocnhs_watershed_inflows/01_hydrocnhs_watershed_inflows.ipynb
```

下一步：**[步驟 02：水庫與 Agent 設定](../02_reservoir_and_agent_setup/README.zh-TW.md)** · **[實作課程總覽](../README.zh-TW.md)**
