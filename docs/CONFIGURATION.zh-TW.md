# 設定說明

公開的起始案例為使用既有入流資料的 [`examples/template`](../examples/template/README.zh-TW.md)。替換合成入流量、物理參數、日期或操作員前，請先複製整個目錄。

![HydroReOpLLM 套件結構與設定檔關聯圖](assets/diagrams/package-structure.svg)

`experiment.yaml` 為主設定入口。YAML、JSON、CSV、提示詞與知識檔案的路徑，皆相對於宣告該路徑的檔案解析。`{file: ...}` 參照會取代整個對應區段，而非進行深層合併。複製範例時，請將案例、入流量、提示詞與知識檔案一併保留。

請依下列順序設定研究案例：

1. 設定 `run_id`、尚未使用的 `output` 路徑及操作日期。
2. 定義或參照既有入流案例，並確認資料雜湊值。
3. 在水系案例中定義庫容、放流量上下限、演算設定與出口節點。
4. 為每座受控水庫指定且僅指定一名操作員。
5. 使用 LLM 操作員時，指定模型設定檔及明確的系統、使用者提示詞檔案。
6. 僅加入該操作員應取得的決策時資訊與知識。

`reservoir-experiment check` 會解析並驗證設定相依圖，不會執行模擬或連線至模型服務。

## 公開設定檔格式

| `schema_version` | 公開用途 | 操作員欄位 |
| --- | --- | --- |
| `llm-reservoir-experiment.v1` | 通用範本與 F.E. Walter 既有入流案例 | `reservoir`，搭配 `mode: offline` 或 `mode: llm` |

執行期亦支援拆檔式 HydroCNHS 研究。這類案例需要個別研究所專屬的驅動資料、率定與驗證；公開儲存庫不會將通用耦合案例描述為完整研究。

## 操作員

- `mode: offline` 套用固定操作，不發出模型請求。
- `type: rule_based` 選用本機已註冊的規則程式碼。
- `type: llm` 選用明確的模型設定檔與具名提示詞。

請先以離線模式確認識別碼、日期、資料雜湊、物理參數與演算設定，再於明確授權網路後執行 LLM。機密金鑰應存放於 `api_key_env` 指定的環境變數中。

每個時間步中，操作員會提出控制放流量。物理核心套用放流限制與可用水量，另行計算溢流量，將控制放流量與溢流量一併演算，並把期末庫容結轉至下一步。

## 物理量與演算

庫容單位為 m3，流量為時段平均 m3/s，`dt_seconds` 代表操作時間步長。連線比例會分配總出流量。`unit_hydrograph` 權重為無因次數值且總和為 1；索引 0 對應當期、索引 1 對應下一期，依此類推。

擴充範本前，請先閱讀[水庫網路](BUILD_SIMULATION.zh-TW.md)、[時間尺度](TIME_SCALES.zh-TW.md)、[模型服務](LLM_MODULES.zh-TW.md)與[執行生命週期](RUNNING.zh-TW.md)。
