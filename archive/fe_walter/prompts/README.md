# Historical F.E. Walter prompts

These files preserve instructions used by earlier configurations. The current
tutorial uses only [available_information.txt](../../../examples/fe_walter/prompts/available_information.txt)
and [retrieved_knowledge.txt](../../../examples/fe_walter/prompts/retrieved_knowledge.txt).

| File | Historical purpose |
|---|---|
| [available_original.txt](available_original.txt) | Original instructions without retrieved knowledge |
| [retrieved_original.txt](retrieved_original.txt) | Original instructions with retrieved knowledge |
| [retrieved_default.txt](retrieved_default.txt) | Earlier retrieved-knowledge default |
| [retrieved_previous.txt](retrieved_previous.txt) | Previous seasonal instructions |

Their text is preserved without revision. Older configuration paths now point
here; recorded prompts and hashes in historical results retain their original
paths. These files are system instructions only. Daily state, decision history,
retrieved text and the reply schema are assembled separately.

Reproducing an original-program comparison requires the opt-in artifact in the
[recovery index](../README.md). Restore frozen executors with their recorded
revision rather than substituting these files into a completed experiment.

## 繁體中文

這裡保留舊設定使用的 system prompt；目前教學只使用上方連結的兩個現行檔案。
舊設定的引用路徑已更新至此，歷史結果內的原始 prompt、路徑與雜湊保持不變。
每日狀態、決策歷史、檢索文字及回覆 schema 由其他程式組合，不包含在這些檔案中。
原版程式對照須自行提供恢復包；檢查舊執行器時應恢復其記錄的版本。
