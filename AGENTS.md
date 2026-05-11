# AGENTS.md

此檔案由 runtime 預先讀取並放進 LLM analysis call 的 system prompt；模型不需要、也不應該自己去找專案檔案。

## Runtime preload

1. 每次執行 AI analysis 前，runtime 必須先讀取專案內的 `AGENTS.md`，再把內容合併到 `SystemMessage`。
2. `AGENTS.md` 的用途只是在 system prompt 補充專案執行規則；不要把它當成完整 AI agent framework。
3. 目前只需要支援 `AGENTS.md`，不需要支援 `.hermes.md`、`HERMES.md`、`CLAUDE.md`、`.cursorrules` 或其他 agent context 檔案。

## Review memory workflow

1. 每次分析開始前，runtime 必須先讀取 `.agent/review.md`。
2. runtime 必須把 `.agent/review.md` 的內容放入本次分析 prompt，作為 review rules。
3. AI 分析時可以參考 review rules，但最終結論仍只能根據本次 CSV context 中真實存在的資料列。
4. AI 不得假裝自己讀取或寫入 `.agent/review.md`。
5. 使用者提供 feedback 後，runtime 才啟動 feedback review 流程。
6. feedback review 流程會要求 AI 從 feedback 中萃取簡短、可重用規則。
7. 只有可重用規則可以寫回 `.agent/review.md`。
8. 實際寫入 `.agent/review.md` 的動作只能由 runtime 執行。
9. 不得把本次 CSV 原始資料、一次性結論、冗長分析或敏感資訊寫入 `.agent/review.md`。
10. 下次分析開始時，runtime 再重新讀取更新後的 `.agent/review.md`。

## Analysis constraints

1. 回答必須以本次 CSV context 為唯一資料來源。
2. 異常項目必須能對應到 CSV 中真實存在的單筆資料列。
3. 不可把多列資料混成一筆，不可捏造欄位，不可補充 context 以外的外部資訊。
4. 若 CSV context 或欄位不足以判斷，必須明確回答「資料不足，需人工確認」。
