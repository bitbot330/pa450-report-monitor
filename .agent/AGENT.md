# Agent startup workflow

1. On every startup, read this file before any other analysis control flow.
2. Prioritize scanning `output/report_YYYYMMDD.md`, preferring the report that matches the current analysis date when available.
3. Distill any new human feedback from that report into `.agent/review.md` as concise judgment rules only.
4. Read `.agent/review.md` before analysis.
5. Reference the human feedback rules from `review.md` during later analysis, while keeping the original analyze prompt text unchanged.
