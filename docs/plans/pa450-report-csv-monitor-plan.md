# PA450 Report CSV Monitor Implementation Plan

**Goal:**定期從 PA450 用 PAN-OS XML API 抓 custom report 結果，轉成 CSV，再依條件做監控/告警。

**Architecture:** Scheduler runs a Python CLI. The CLI loads `.env` and `config.yaml`, calls the PAN-OS XML API, writes raw XML and CSV outputs, evaluates byte thresholds, and optionally posts a Discord webhook alert.

**Tech Stack:** Python 3.10+, standard library HTTP/XML/CSV modules, PyYAML for config, pytest for tests.

## Steps

1. Confirm PA450 host, API user, VSYS, and exact custom report name.
2. Generate or reuse PAN-OS XML API key.
3. Retrieve custom report definition from `/config/devices/entry/vsys/entry[@name='vsys1']/reports/entry[@name='REPORT_NAME']`.
4. Enqueue a dynamic report job using `type=report`, `reporttype=dynamic`, and the report definition as `cmd`.
5. Poll/fetch the job result with `type=report`, `action=get`, and `job-id=...`.
6. Convert XML entries into CSV.
7. Check byte threshold against configured bytes field candidates.
8. Save XML/CSV and send alert if configured.
