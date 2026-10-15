# 建立模擬

先定義河川系統與每座水庫操作者可取得的資訊，再選擇操作方法。
[FE Walter 案例](../examples/fe_walter/README.zh-TW.md)示範這些選擇如何套用到同一地點。

## 1. 設定物理案例

準備水庫、河川連接、每日 local inflow 與初始蓄水。
流量使用 **m³/s**、體積使用 **m³**，日期使用 ISO 格式。

案例設定容量、出口限制、損失與 routing。每座受控水庫配置一個獨立決策單元；被動出口不配置。
河網連接決定上游放流是否到達下游水庫。

半分佈式水文模型保留各子集水區的氣象、面積及參數。
HydroCNHS 先計算產流與上游 routing，再進入水庫操作。
給定的 experiment CLI 使用已有且來源明確的入流序列，FE Walter 範例即採此方式。
氣象驅動的原生執行需設定水文模型與 Dam-policy 綁定，不能只改 experiment YAML 欄位。
選擇方法前，先閱讀[耦合流程](../examples/fe_walter/coupling.zh-TW.md)。

[準備 input 與案例設定](USER_GUIDE.zh-TW.md) · [原生 HydroCNHS 設定](HYDROLOGY_SETUP.md)

## 2. 選擇操作方法

| 方法 | 提供內容 | 決策 |
|---|---|---|
| 規則式 | 已發表規則與參數 | 規則計算 requested release |
| 使用可用資訊的 LLM | Prompt 與選定資訊 | 模型提出放流及解釋 |
| 使用檢索知識的 LLM | 相同介面加上有來源的知識流程 | 模型同時使用選定操作指引 |

三種 FE Walter 方法使用相同水庫收支計算。其他水庫需設定自己的物理 profile 與操作準則。

## 3. 決定操作者看得到什麼

區分**固定指令**與**每一步更新的資訊**。

| 元件 | 例子 | 設定位置 |
|---|---|---|
| Prompt | 操作目的、指令與輸出欄位 | 獨立 UTF-8 prompt 檔 |
| Available information | 當期入流、水位、過去實際放流 | Host observation 與選定 information profile |
| 額外資訊 | 下游測站流量、預報入流、用水需求 | 有時間戳的來源與 agent information profile |
| 可選知識 | 可識別的操作文件 | Knowledge 設定或方法專用的檢索流程 |

來源需宣告單位與觀測／預報可取得的時間。下游測站值只有在決策當時可取得，才能作為 input。
使用模擬下游回饋時，取已完成的前一步；當日 routing 結果在放流後才計算。

[決策資訊](INFORMATION.zh-TW.md) · [Prompt 與知識設定](LLM_MODULES.zh-TW.md)

## 4. 設定提案與檢查

提案包含 requested release；各方法也可保留 rationale、目標與引用規則。
回覆檢查在執行前驗證完整性、必要欄位、單位及數值。

水庫計算執行可行放流、計算 spill 並更新蓄水。操作 audit 另行評估設定準則。
Trace 連結 **資訊 → prompt → 回覆 → 提案 → 檢查 → 實際操作 → 下一步資訊**。

[提案、checker 與 auditor 設定](USER_GUIDE.zh-TW.md)

## 5. 檢查、執行與驗證

保存 case、prompt 與 experiment YAML，選擇新的 run ID 與輸出目錄。
先驗證設定，再開始模擬，最後驗證保存輸出。

[設定指南](USER_GUIDE.zh-TW.md)提供完整指令與輸出保護。
執行模型需明確授予網路權限；查看既有紀錄不會呼叫模型。

接著閱讀 [FE Walter：地點與共用設定](../examples/fe_walter/README.zh-TW.md)。
