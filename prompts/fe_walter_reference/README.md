# FE Walter reference system prompts

[Zero-shot system instructions](zeroshot_system.txt) · [DKP system instructions](dkp_system.txt)

These UTF-8 files are read at runtime by the integrated YAML runner, through `reference.system_prompt`. They contain system instructions only. Daily inflow, current level, implemented history, response schema and DKP retrieval remain dynamic in the strategy adapter; do not paste a dated state snapshot into these files.

`system_prompt_mode: original` checks effective text against the pinned original builder for the selected options. Windows CRLF is normalized to LF; source-byte and effective-prompt hashes are recorded separately. To edit instructions, copy the file, point YAML to your copy and set `system_prompt_mode: custom`. Trace labels it as a variant and keeps the actual prompt/hash, original hash and native audit. The cfs response schema, physical solver and routing contract still apply. Both offline and live reference transports preserve these builders; see [live preparation](../../docs/reference_live.md). The current example case remains not live-ready.

The original English text is preserved. Full first-day reading snapshots, including state and schema, remain in the [zero-shot](../../examples/fe_walter/zero_shot/prompt_preview.txt) and [DKP](../../examples/fe_walter/dkp/prompt_preview.txt) example folders. The integration uses the common reservoir engine, not the original standalone simulation driver.

## 繁體中文

這兩個 UTF-8 檔是整合版**實際讀取的 system prompt**，由 YAML 的 `reference.system_prompt` 指定。每日入流、水位、已實施的歷史、回覆 schema 與 DKP 檢索仍由策略 adapter 動態處理；不要把含日期的狀態快照貼進這裡。

`system_prompt_mode: original` 核對文字是否符合所選旗標下的原版 builder；Windows CRLF 轉為 LF，檔案 bytes 與實際指令文字的 hash 分別保存。修改指令時，複製一份檔案、更新 YAML 路徑並設 `system_prompt_mode: custom`。Trace 會標記為變體，保留實際 prompt／hash、原版 hash 與原始 audit；cfs 回覆格式、物理與 routing 契約仍適用。離線與真實原版 transport 都保留這些 builder，見 [真實執行準備](../../docs/reference_live.zh-TW.md)；現有 case 仍未就緒。

原版英文內容保持不變。完整第一天狀態與 schema 閱讀快照仍在上方兩個範例目錄。案例由整合版共用水庫引擎執行，不啟動原版獨立模擬主程式。
