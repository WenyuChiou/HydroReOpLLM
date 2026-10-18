# Historical prompt recovery

The maintained case has two system files:
[available_information.txt](../../../examples/fe_walter/prompts/available_information.txt)
and [retrieved_knowledge.txt](../../../examples/fe_walter/prompts/retrieved_knowledge.txt).
Daily state, history, retrieved passages and the reply schema are assembled separately.

Historical prompt bytes are preserved outside the repository in the verified
[recovery package](../README.md). Saved replies and source hashes retain their original values.

For an optional historical comparison, restore that package to a separate directory
and set `HYDROOPS_FE_WALTER_HISTORY_DIR` to its `verified-restoration` root.
The loader checks each declared prompt hash and rejects missing or changed inputs.
Current configurations select their system files explicitly and need no recovery package.

## 繁體中文

目前案例使用上方連結的兩個 system 檔。每日狀態、歷史、檢索段落與回覆 schema 另行組合。
舊 prompt 原文保存在 repo 外的已驗證恢復包；歷史回覆與雜湊維持原值。
選用的歷史比較須將恢復包放在另一個目錄，並把 `HYDROOPS_FE_WALTER_HISTORY_DIR`
設為其 `verified-restoration` 根目錄。Loader 會核對宣告的 prompt 雜湊。
目前設定明確指定 system 檔，無須恢復包。
