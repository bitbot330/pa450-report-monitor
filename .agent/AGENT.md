# Agent startup workflow

1. On every startup, read this file before any other analysis control flow.
2. Treat `output/report_YYYYMMDD.md` as a date-based filename pattern, not a literal path: scan actual files matching `output/report_*.md`, prefer the report whose `YYYYMMDD` matches the current analysis/input date when available, otherwise use the latest matching report file.
3. Distill any new human feedback from that resolved report into `.agent/review.md` as concise judgment rules only.
4. Read `.agent/review.md` before analysis.
5. Reference the human feedback rules from `review.md` during later analysis, while keeping the original analyze prompt text unchanged.
