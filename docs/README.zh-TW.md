# HydroReOpLLM 使用手冊

![HydroReOpLLM 水庫操作員及其集水區](assets/branding/cover.png)

使用既有的入流資料或 HydroCNHS 集水區模型建立水庫模擬實驗。建議先從指定放流量著手，檢視水量平衡結果，再為自身案例選用合適的操作策略。

<a id="first-run"></a>

[安裝並執行第一個案例](GETTING_STARTED.zh-TW.md) · [瀏覽逐日範例](../examples/daily_offline/README.zh-TW.md) · [English manual](README.md)

## 運作方式

既有的入流檔會直接提供局部入流量。在耦合案例中，系統會先執行 HydroCNHS，並將操作期間的入流量儲存備用。在每個時間步，操作員會提出放流量請求。物理模型則依可用水量與出流限制進行運算，更新庫容與溢流量，並沿水庫網路演算水流。驗證步驟會讀取已儲存的決策紀錄與水量平衡結果。解讀實際研究案例時，請另行評估模擬結果與觀測資料的吻合程度。

![結合 HydroCNHS 水文模擬、規則或 LLM 操作員、規則稽核與追蹤紀錄的 HydroReOpLLM 系統架構圖](assets/diagrams/framework.png)

## 建議閱讀順序

| 章節 | 本章內容 |
| --- | --- |
| [安裝說明](GETTING_STARTED.zh-TW.md)與[入門教學](../tutorials/README.zh-TW.md) | 安裝軟體、執行四天合成案例並檢視期末庫容。 |
| [設定檔說明](CONFIGURATION.zh-TW.md) | 設定實驗時間窗、輸入檔案、操作員與輸出目錄。 |
| [既有入流資料](../templates/prepared/README.zh-TW.md)或[水文設定](HYDROLOGY_SETUP.zh-TW.md) | 直接提供局部入流量，或透過[耦合案例範本](../templates/coupled/README.zh-TW.md)搭配氣象資料與原生模型產生入流量。 |
| [水庫網路](BUILD_SIMULATION.zh-TW.md)與[時間尺度](TIME_SCALES.zh-TW.md) | 為每座水庫指派操作員、連接水流路徑並選擇時間步長。 |
| [模型服務](LLM_MODULES.zh-TW.md)與[可用資訊](INFORMATION.zh-TW.md) | 決定 LLM 可見的資訊內容，並記錄所使用的模型識別資訊。 |
| [執行與驗證](RUNNING.zh-TW.md) | 檢查設定檔、準備輸入資料、完成水庫操作模擬並驗證已儲存的執行結果。 |
| [判讀結果](RESULTS_GUIDE.zh-TW.md) | 比較請求放流量與實際放流量、庫容變化以及下游流量。 |

## 選擇範例

| 範例 | 輸入與探討問題 |
| --- | --- |
| [單座水庫與串聯水庫](../examples/daily_offline/README.zh-TW.md) | 當水庫彼此串聯時，指定放流量會如何影響下游庫容？ |
| [雙水庫各自出流範例](../examples/multiple_reservoirs/README.zh-TW.md) | 氣象驅動的入流量如何進入由各自獨立操作員管理的兩座水庫？ |
| [逐日、逐時與固定間隔](../examples/time_scales/README.zh-TW.md) | 時間戳記、平均流量與時段體積如何隨時間步長改變？ |
| [MOSART-Urban 規則](../examples/rules/mosart_urban/README.zh-TW.md) | 如何在維持相同物理水庫案例的前提下替換操作規則？ |

每個範例皆採用合成輸入資料。若要建立新的流域案例，請從[耦合案例範本](../templates/coupled/README.zh-TW.md)開始。若執行過程出現預期外的狀況，請參閱[疑難排解](TROUBLESHOOTING.zh-TW.md)。

## 離線閱讀使用手冊

在已完成安裝的 Git 本機專案目錄中建置網站，再以瀏覽器開啟 `site/zh-TW.html`。若要使用全文搜尋功能，請透過本機 HTTP 伺服器提供該資料夾，並開啟 `http://127.0.0.1:8000/zh-TW.html`。

```sh
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py
python -m http.server 8000 --directory site --bind 127.0.0.1
```
