# 耦合模擬範本

建立新研究案例時，請複製整個資料夾。先從 `experiment.yaml` 著手，再依下表順序編輯各檔案。以 `YOUR_` 開頭的值皆為使用者必填項目。這些檔案在替換前雖符合 YAML 語法，但 `check` 會拒收不符合執行期契約的佔位符。

| 檔案 | 用途 |
|---|---|
| `experiment.yaml` | 全域執行識別碼、日期、輸出路徑與各區段檔案參照 |
| `hydrology.yaml` | 原生 HydroCNHS 水文模式、驅動資料與水庫操作流量繫結 |
| `reservoirs.yaml` | 水庫物理參數與有向水系網路 |
| `agents.rule.yaml` | 採用已註冊使用者規則的規則式操作員 |
| `agents.llm.yaml` | 可替換選用的 LLM 操作員 |
| `models.yaml` | 供 LLM 操作員使用的模型服務設定檔 |
| `auditors.yaml` | 由操作員選用的診斷稽核項目 |
| `information.yaml` | 選填的決策時刻資料目錄 |
| `prompts/*.txt` | 明確的 LLM 系統與操作員提示詞 |
| `extensions/user_registered_rule/__init__.py` | 精簡版使用者自訂規則套件 |

預設的 `experiment.yaml` 會選用 `agents.rule.yaml`。待該路徑完成檢查、執行與驗證後，即可將 `agents.file` 參照改為 `agents.llm.yaml` 以啟用 LLM 操作員。相關指令詳見 [`docs/RUNNING.md`](../../docs/RUNNING.zh-TW.md)。
此範本包含 `YOUR_` 佔位符，屬於供複製填寫的範本。在所有佔位符皆替換為實際研究數值或路徑之前，尚無法直接執行。規則式分支為預設驗證路徑，且無須存取模型服務。`information.yaml` 為選填的操作員決策背景資訊。在將其設定檔繫結至操作員前，請先參閱[決策時刻資訊指南](../../docs/INFORMATION.zh-TW.md)。
若您已具備既有的入流時間序列，而無須使用 HydroCNHS 水文模式，請改用 [`../prepared/README.md`](../prepared/README.zh-TW.md)。
