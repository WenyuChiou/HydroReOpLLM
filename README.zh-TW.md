<img src="docs/figures/assets/branding/hydroopslm-logo.png" align="right" width="64" height="64" alt="HydroOpsLM logo">

# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![閱讀使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroOpsLM/)

![HydroOpsLM 封面](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** 是以語言模型進行水庫操作、耦合
[HydroCNHS](https://github.com/cylin928/HydroCNHS) 的模擬框架。
研究者可為每座水庫設定決策資訊、prompt、操作方法與檢查。
HydroCNHS 提供水文與河川 routing；HydroOpsLM 加入水庫收支計算，
連結放流提案、audit 與實際執行結果。

![HydroOpsLM 概念圖](docs/figures/hydrocnhs-coupling-framework-en.png)

## 安裝

使用 Python 3.12。先 clone repo、建立虛擬環境，再安裝：

```powershell
git clone https://github.com/WenyuChiou/HydroOpsLM.git
cd HydroOpsLM
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

[User Manual](https://wenyuchiou.github.io/HydroOpsLM/) 提供其他平台的安裝方式、
案例建立、操作方法、範例、audit／trace 與引用來源。
