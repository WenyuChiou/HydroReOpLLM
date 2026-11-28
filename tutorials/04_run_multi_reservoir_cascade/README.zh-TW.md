# 步驟 04：運行多庫串聯耦合模擬（新店溪）

執行 2025 全年雙庫串聯模擬（`feitsui -> zhitan -> xindian_outlet`），對比雙庫 Hanasaki（`rule_based.yaml`）與翡翠 LLM ＋ 直潭規則混合調度（`hybrid_llm.yaml`），驗證 Lohmann 河道演算與系統水量平衡，並檢視颱風洪峰聯合減洪表現。

> **註記：** 本案例為 **Repo 專屬範例（未收錄於論文）**，觀測資料來源為 **TFRA** 與 **經濟部水利署（MOEA/WRA）**。

```sh
python -m jupyterlab tutorials/04_run_multi_reservoir_cascade/04_run_multi_reservoir_cascade.ipynb
```

返回：**[實作課程總覽](../README.zh-TW.md)** · **[新店溪多庫案例](../../examples/multi_reservoir/README.zh-TW.md)**
