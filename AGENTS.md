# AGENTS.md

1. On every startup, runtime must preload this file into the system prompt before any LLM analysis call.
2. Runtime provides review tools for `.agent/review.md`; do not rely on the model to read or write files by itself.
3. Before analysis, the model should call the provided `read_review_md` tool to read existing human feedback rules from `.agent/review.md`.
4. If the model determines new concise review rules should be remembered, it may call the provided `write_review_md` tool. The model decides whether writing is needed; the actual file write must be performed only by the runtime tool.
5. Reference review rules returned by `read_review_md` during later analysis when they are relevant to the current CSV context, while keeping the original analyze prompt text unchanged.
