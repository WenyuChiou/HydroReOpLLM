# 時間尺度與單位

逐日工作流程為目前持續維護的預設模式。透過明確設定時間步長，系統亦支援 [`examples/time_scales`](../examples/time_scales/README.zh-TW.md) 中的逐時或固定時距教學案例。

| 物理量 | 單位或慣例 |
|---|---|
| 蓄水量、庫容 | m3 |
| 放流量、溢流量、入流量 | 時段平均 m3/s |
| `dt_seconds` | 每個操作時間步的秒數 |
| 演算權重 | 無因次，總和為 1 |
| 逐日降雨量／PET | 該日累積水深 |
| 逐時降雨量／PET | 該時段的累積水深 |
| 氣溫 | 時段平均值（°C） |

在恆定的時段平均流量下，體積變化量為 `flow * dt_seconds`。切勿將逐日驅動資料或逐日單位歷線時段誤標為逐時資料。使用較細尺度的驅動資料時，還必須搭配支援對應時距的逕流核心、連續的時間戳記、正確積分的水深、對應時距的演算設定，以及相容的水庫操作步長。

[實驗性逐時 GWLF 流程](HOURLY_GWLF.zh-TW.md)接受 3600、1800 或 900 秒的時間步長。這是一套工程化公式實作，並不代表已具備經率定驗證的逐時模擬能力。其合成輸入資料可參考以下可重複執行的基本測試程式。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -X utf8 examples/time_scales/hourly_gwlf_smoke.py --output NEW_FOLDER
```
