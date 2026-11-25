# 決策時資訊

資訊設定檔可在決策時為單一操作員提供具名且唯讀的額外資料檢視。其內容可以是固定目標值、附帶時間戳記的觀測或預報資料，或是模擬系統已提交的數值，但不能更動蓄水量、入流量、放流量限制、演算設定或其他水庫的狀態。

## 操作員在每個時間步所掌握的資訊

正在執行決策的水庫會在常規觀測中取得當期時段平均入流量與期初蓄水量。這表示在逐日案例中，系統假設決定當日放流量時已知當日的平均入流量。已完成歷史資料僅包含先前時間步長的紀錄。其他水庫的數值則必須在該水庫完成當期步長提交後才會開放讀取。

針對外部 CSV 資料，決策時鐘即為當前時間步長的時間戳記。觀測資料唯有在 `valid_time` 與 `available_at` 皆不晚於該決策時鐘時，才具備取用資格。預報資料可描述未來的 `valid_time`，但其 `issued_at` 與 `available_at` 兩者皆不得晚於決策時點。所有時間戳記均須包含 `Z` 或明確的 UTC 偏移量。

## 設定資訊設定檔

請從 [`templates/coupled/information.yaml`](../templates/coupled/information.yaml) 開始著手。以下可執行的設定結構會以適用於提示詞的安全別名，公開一項靜態數值。

```yaml
sources:
  operating_target:
    type: static
    quantity: target_release
    unit: m3/s
    location: lake_a
    value: 2.5
profiles:
  operator_view:
    fields:
      operating_target_cms:
        source: operating_target
        required: true
```

先於耦合實驗設定中參照該資訊目錄，再於目標代理上指定所要選用的設定檔。

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.llm.yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

當通用 LLM 代理選用資訊設定檔時，請於其提示詞檔案中加入字面佔位符 `$information`，執行期會將選定的資料快照插入該處。規則式擴充模組則可透過 `observation.context.decision_information` 讀取同一份快照。選用特定設定檔並不會公開目錄中的其餘項目。

## 資料來源類型

| `type` | 必要來源欄位 | 可用性行為 |
|---|---|---|
| `static` | `quantity`、`unit`、`location`、`value` | 隨時可用。適合固定目標值或標籤。 |
| `csv` | 通用欄位加上 `kind` 與 `path` | 針對確切的 UTF-8 CSV 位元組計算雜湊值，並依因果時間戳記選取紀錄。 |
| `simulation` | 通用欄位 | 從當期或已提交的原生模擬狀態讀取 `inflow`、`storage`、`release` 或 `flow`。 |
| `extension` | 通用欄位加上已註冊的 `provider` | 呼叫由應用程式宣告、具版本控管的本機讀取器。 |

觀測資料 CSV 的欄位名稱固定為 `valid_time,available_at,value`。預報資料的欄位名稱則固定為 `issued_at,valid_time,available_at,value`。設定檔欄位亦可另行設定 `unit`、`history`、`max_age_seconds` 與 `required`。支援的單位換算包括 m3/s 與 cfs、m3 與 acre-ft，以及 m 與 ft。

若必要欄位找不到符合因果順序且仍在有效期限內的紀錄，決策流程便會中止。非必要欄位若缺漏，系統會明確記錄為 `status: MISSING`、`value: null` 並附上原因，絕不會將缺值改寫為零。可用的欄位則會包含所選數值、單位、位置、來源 ID、時間戳記、所請求的歷史樣本，以及適用的 CSV 雜湊值或擴充模組版本。

每次修改資訊目錄或代理設定後，請執行 `reservoir-experiment check path/to/experiment.yaml`。所選定的快照會儲存在每筆決策觀測紀錄中，並由 `verify` 進行查核。針對 static、CSV 與 simulation 來源，驗證工具會重新建構所選數值。針對已註冊的擴充模組，則會檢查已儲存的時間戳記、來源追蹤資訊與內部一致性，而不會再次呼叫外部讀取器。接下來可繼續閱讀[執行生命週期](RUNNING.zh-TW.md)或[結果解讀指南](RESULTS_GUIDE.zh-TW.md)。
