# 設定說明

HydroReOpLLM 支援兩種輸入方式。

- 既有入流資料：從 [`templates/prepared`](../templates/prepared/README.zh-TW.md) 開始。
- 原生 HydroCNHS 水文模式：從
  [`templates/coupled`](../templates/coupled/README.zh-TW.md) 開始。

耦合設定檔 `experiment.yaml` 會連結各自獨立的水文、水庫水系、操作員、模型、決策資訊與稽核設定檔。所有路徑皆相對於宣告該路徑的 YAML 或 JSON 檔案進行解析。`{file: ...}` 參照會取代整個對應區段，而非進行深層合併。

請依下列順序設定研究案例。

1. 在 `experiment.yaml` 中設定 `run_id`、尚未使用的 `output` 路徑，以及操作起訖日期。
2. 在 `hydrology.yaml` 中定義水文模式與入流量繫結關係。
3. 在 `reservoirs.yaml` 中定義庫容、放流量上下限、演算設定與出口節點。
4. 在操作員設定檔中，為每座受控水庫各指定一名操作員。
5. 若使用 LLM 操作員，請指定模型設定檔與明確的提示詞檔案。
6. 視需要選擇具名的[決策資訊設定檔](INFORMATION.zh-TW.md)。

`reservoir-experiment check` 會解析並驗證這組設定相依圖，過程中不會執行水文模擬，也不會連線至模型服務。

## 操作員

每座受控水庫皆僅配有一名操作員，且各自維持獨立狀態。

- `mode: offline` 會套用固定的合成操作指令，不發出任何模型請求。
- `type: rule_based` 會選用本機已註冊的規則程式碼。
- `type: llm` 會從 `models.yaml` 中選用明確指定的設定檔。

建議先以離線或規則式操作員驗證識別碼、日期、水庫物理參數與演算設定，待 `check` 通過後再切換為 LLM 操作員。請將機密金鑰存放在 `api_key_env` 所指定的環境變數中，切勿直接寫入 YAML 檔案。

在每個時間步中，操作員會提出一筆控制放流量請求。物理核心會套用放流量上下限與可用水量限制，另行計算溢流量，將控制放流量與溢流量合併演算，再把期末庫容結轉至下一個時間步。更換操作員不會影響先前已鎖定的水文前處理結果。

## 物理量與演算

庫容單位為 m3，流量為時段平均的 m3/s，`dt_seconds` 則代表操作時間步長。水庫總出流量為控制放流量與溢流量之和。連線會將該出流量的指定比例向下游演算。`unit_hydrograph` 權重為無因次數值且總和為 1，其中索引 0 對應當期時間步、索引 1 對應下一個時間步，依此類推。

在擴充範例檔案之前，請先參閱[多水庫系統](BUILD_SIMULATION.zh-TW.md)、[時間尺度](TIME_SCALES.zh-TW.md)與[模型服務](LLM_MODULES.zh-TW.md)，接著再依[執行生命週期](RUNNING.zh-TW.md)操作。
