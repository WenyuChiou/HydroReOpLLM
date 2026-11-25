# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [English](README.md)

![水庫、河川與 LLM 操作員示意圖](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM 以 HydroCNHS 為基礎，使用既有入流資料或氣象資料模擬水庫操作，並支援規則式、指定放流量或由 LLM 作出的放流決策。

## 快速開始

用指定放流量執行四天的合成單庫案例。執行模擬無需 API 金鑰。請在空白工作目錄中啟用 Python 3.12 或更新版本的虛擬環境。[建立虛擬環境](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html#install-from-pypi)。

```sh
python -m pip install hydroreopllm
python -c "from pathlib import Path
from shutil import copytree
from sysconfig import get_path
source = Path(get_path('data')) / 'share/llm-reservoir-agent/examples'
copytree(source, 'examples')"
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

確認驗證輸出顯示 `PASS`、執行 4 天及 `observed_network_calls: 0`。開啟 `runs/daily-single/summary.json`，確認執行狀態為 `COMPLETED`，且 `Lake_1` 的期末庫容為 **1,345,600 m³**。如要重跑，請[設定新的執行 ID 與輸出路徑](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html#repeat-a-run)。

## 複製儲存庫並執行筆記本

PyPI 套件內含可直接執行的範例。若要使用筆記本與完整的範例、範本，請複製儲存庫。[下載並安裝 HydroReOpLLM](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html#install-from-a-clone) · [開啟筆記本教學](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)

## 選擇範例

| 你想做什麼 | 從這裡開始 |
| --- | --- |
| 追蹤單座水庫或串聯水庫的放流 | [單庫與串聯範例](https://wenyuchiou.github.io/HydroReOpLLM/examples/daily_offline/index.zh-TW.html) |
| 以氣象資料驅動兩座水庫，各自操作並排入各自的下游出口 | [雙水庫各自出流範例](https://wenyuchiou.github.io/HydroReOpLLM/examples/multiple_reservoirs/index.zh-TW.html) |
| 執行逐日、逐時或固定時距模擬 | [時間步長範例](https://wenyuchiou.github.io/HydroReOpLLM/examples/time_scales/index.zh-TW.html) |
| 建立自己的案例並檢視決策、庫容與水量平衡 | [設定檔](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-TW.html) · [結果指南](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html) |

## 測試與授權

在下載的專案中，以 `python -m pip install -c environment/requirements-bundled.txt ".[test]"` 安裝測試依賴，再執行 `python -m pytest -q`。

[BSD 3-Clause 授權](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [第三方授權與來源](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
