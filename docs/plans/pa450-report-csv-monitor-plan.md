# PA450 Report CSV Monitor Implementation Plan

**Goal:**定期從 PA450 用 PAN-OS XML API 抓 custom report 結果，轉成 CSV，再提供 AI 分析使用。

**Architecture:** Scheduler runs a Python CLI. The CLI loads `.env` and `config.yaml`, calls the PAN-OS XML API, and writes CSV outputs for the AI analysis step.

**Tech Stack:** Python 3.10+, standard library HTTP/XML/CSV modules, PyYAML for config, pytest for tests.

## Steps

1. Confirm PA450 host, API user, VSYS, and exact custom report name.
2. Generate or reuse PAN-OS XML API key.
3. Retrieve custom report definition from `/config/devices/entry/vsys/entry[@name='vsys1']/reports/entry[@name='REPORT_NAME']`.
4. Enqueue a dynamic report job using `type=report`, `reporttype=dynamic`, and the report definition as `cmd`.
5. Poll/fetch the job result with `type=report`, `action=get`, and `job-id=...`.
6. Convert XML entries into CSV.
7. Use the CSV as input for the AI analysis step.
