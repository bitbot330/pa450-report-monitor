# src layout

`src/` contains the executable scripts and the supporting modules they use.

```text
src/
  report.py              # PA450 custom report download and CSV conversion CLI
  analyze.py             # AI analysis CLI; processes pending feedback before analysis
  config.py              # YAML/env configuration loader shared by report.py
  ui.py                  # Local review UI server/CLI entrypoint only
  ui_app/
    data.py              # UI backend data loading, report discovery, review markdown persistence
    assets/
      index.html         # UI HTML/CSS/JavaScript template
  runtime/
    prompt_builder.py    # Runtime prompt construction, including AGENTS.md/review rules
    review_tools.py      # Review memory and feedback checkpoint helpers
```

Entry scripts stay directly under `src/` so existing commands such as `python src\report.py`, `python src\analyze.py`, and `python src\ui.py` keep working. New UI internals should go under `src/ui_app/` instead of growing `src/ui.py`.
