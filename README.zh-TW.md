# HydroReOpLLM

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroReOpLLM 將 **LLM 水庫操作員**接到
[HydroCNHS](https://github.com/cylin928/HydroCNHS) 水文模擬。
透過 YAML 設定單一水庫或互相連接的水庫網路。

- 每座水庫可分別選擇 Rule-based 或 LLM 決策。
- 支援 Ollama、OpenAI-compatible、OpenAI、Anthropic 與 Gemini。
- 可自訂 prompt、操作知識與決策當時可取得的資訊。
- 保存請求、回覆、理由、水庫狀態、routing 流量及檢查紀錄。

## 安裝

使用 Python 3.12。在已啟用虛擬環境的 repository 根目錄執行：

```bash
python -m pip install -e .
reservoir-experiment --help
```

環境建立與選配依賴請見[安裝說明](https://wenyuchiou.github.io/HydroReOpLLM/docs/GETTING_STARTED.html)。
目前是研究候選包，尚未提供 PyPI 安裝。

## 手冊與範例

[使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/)依序介紹模擬設定、水文、水庫、LLM 與結果。

先從[單水庫](examples/daily_offline/README.md)開始，再看
[多水庫](examples/multiple_reservoirs/README.md)。
[FE Walter](examples/fe_walter/README.md)提供真實研究區的設定。
也可查看[範例目錄](examples/README.zh-TW.md)或跟著 [Notebook](tutorials/README.md)操作。

`examples/` 放可執行研究範例，`templates/` 放空白起始設定；
回歸測試輸入與歷史紀錄放在 `tests/fixtures/`。

## 引用與授權

報告實驗時請記錄專案 revision，依[引用說明](docs/REFERENCE.md)引用本專案及 HydroCNHS。
主專案授權尚待確定；隨附依賴保留各自的[授權與來源](THIRD_PARTY_NOTICES.md)。
