# 時尺度 GWLF 衍生逕流計算

`run_GWLF_hourly` 直接依據各時間步的氣象驅動資料計算逕流，而非將既有的日流量歷線重新分配至各時段。此為實驗性質、源自 GWLF 的工程公式實作。程式順利執行或水量平衡閉合，均不代表已完成時尺度逕流率定或具備實測吻合度。

## 獨立合成範例

在已完成安裝的儲存庫複本中，無需連接模型服務即可直接執行核心函式。

```python
from hydrocnhs.rainfall_runoff_model.gwlf_hourly import run_GWLF_hourly

parameters = {
    "CN2": 70, "IS": 0.2, "Res": 0.02, "Sep": 0.01,
    "Alpha": 0.12, "Beta": 0.2, "Ur": 8, "Kc": 0.8, "Df": 0.12,
}
initial = {"Area": 1000, "S0": 10, "U0": 4, "SnowS": 0.2, "B0": 1}
diagnostics = []
flow_cms, state = run_GWLF_hourly(
    parameters,
    initial,
    temp=[5.0] * 48,          # interval-mean degrees C
    prec=[0.01] * 48,         # accumulated cm in each hour
    pet=[0.003] * 48,         # accumulated cm in each hour
    monthly_Tavg=[5.0] * 48,  # aligned seasonal mean, degrees C
    dt_seconds=3600,
    diagnostics=diagnostics,
)
assert len(flow_cms) == 48
```

此 API 接受 3600、1800 與 900 秒的時間步長。呼叫端須提供連續且對齊的時間軸與氣象驅動資料。降雨量與潛在蒸發散量（PET）必須換算為各時間步的累積水深，切勿傳入強度速率或重複使用日總量。`Area` 的單位為公頃，各蓄水狀態單位為公分，回傳流量則為該時間步長的平均值（單位為 m3/s）。

## 狀態、接續重啟與驗證

回傳的狀態包含土壤含水量、淺層地下水、深層地下水、積雪、前期土壤含水量與降雨事件記憶。僅能將該狀態傳遞至參數與時間步長皆相同的下一個連續時段區塊，不可跳過、重疊、重新排序或自行補齊驅動資料時段。既有的日尺度基流水深不可直接作為時尺度的深層蓄水數值使用。

診斷資訊會輸出各時間步的蓄水項、通量項以及水量平衡殘差。請依據研究尺度與精度要求自行檢視殘差大小。核心函式僅會拒絕無效或非有限值的物理狀態。在解讀任何水庫操作比較結果之前，請先以獨立實測資料驗證參數、初始狀態暖機（spinup）、事件記憶假設、逕流與演算結果。

公開範例皆為逐日既有入流案例。將此核心函式連接至水庫案例前，請先建立並驗證個別研究所需的驅動資料。時距規則請參閱[時間尺度與單位](TIME_SCALES.zh-TW.md)。
