# PA450 Report CSV Monitor

Automate a Palo Alto Networks PA-450 custom report workflow:

1. get a PAN-OS XML API key,
2. retrieve a configured custom report definition,
3. enqueue a dynamic report job,
4. fetch the report result XML,
5. convert report rows to CSV,
6. check byte thresholds,
7. save outputs and optionally send a Discord webhook alert.

This project intentionally uses the PAN-OS XML API path because Palo Alto documentation confirms custom reports can be exported as CSV manually, while the built-in email scheduler is documented under **PDF Reports > Email Scheduler**. For automated CSV, this project fetches XML results from the API and converts them to CSV locally.

## Official documentation used

- Get API key: <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key>
- Custom Reports API: <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/get-reports-api/custom-reports>
- View Reports export formats: <https://docs.paloaltonetworks.com/ngfw/administration/monitoring/view-and-manage-reports/view-reports>

## Requirements

- Python 3.10+
- Network access from this script host to `https://<PA450_IP>/api/`
- A PA-450/PAN-OS administrator account allowed to use the XML API
- An existing custom report under `Monitor > Manage Custom Reports`

No Palo Alto credentials are committed to this repository.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
```

## Configure `.env`

Edit `.env`:

```env
PA450_HOST=192.168.1.1
PA450_USERNAME=api-report-user
PA450_PASSWORD=change-me
# Optional. If set, the script uses this instead of calling type=keygen.
PA450_API_KEY=
# Optional. Used only when alert.discord_webhook_env points to DISCORD_WEBHOOK_URL.
DISCORD_WEBHOOK_URL=
```

## Configure `config.yaml`

Edit `config.yaml`:

```yaml
pa450:
  host_env: PA450_HOST
  username_env: PA450_USERNAME
  password_env: PA450_PASSWORD
  api_key_env: PA450_API_KEY
  verify_tls: false
  vsys: vsys1
  report_name: PA450-Traffic-Bytes-Report
  report_job_name: pa450-custom-dynamic-report

output:
  directory: output
  xml_file: report_result.xml
  csv_file: report_result.csv

monitor:
  bytes_field_candidates:
    - bytes
    - Bytes
    - repeatcnt
  bytes_threshold: 1000000000

alert:
  discord_webhook_env: DISCORD_WEBHOOK_URL
```

Concrete fields to edit:

- `pa450.report_name`: your exact custom report name from `Monitor > Manage Custom Reports`
- `pa450.vsys`: usually `vsys1`
- `monitor.bytes_threshold`: byte value that should trigger an alert
- `monitor.bytes_field_candidates`: keep `bytes` first if your selected report column is named `bytes`

## Run

```bash
source .venv/bin/activate
python -m pa450_report_monitor --config config.yaml
```

Expected output when rows are below threshold:

```text
OK: no rows exceeded threshold
CSV written: output/report_result.csv
XML written: output/report_result.xml
```

Expected output when rows exceed threshold:

```text
ALERT: 2 rows exceeded threshold
CSV written: output/report_result.csv
XML written: output/report_result.xml
```

## Dry-run XML to CSV only

If you already have a saved report XML and only want to test conversion:

```bash
python -m pa450_report_monitor.convert output/report_result.xml output/report_result.csv
```

## Scheduler examples

### Linux cron

Run every day at 08:00:

```cron
0 8 * * * cd /path/to/pa450-report-monitor && . .venv/bin/activate && python -m pa450_report_monitor --config config.yaml >> logs/monitor.log 2>&1
```

### Windows Task Scheduler

Action:

```text
Program/script: C:\Path\To\Python\python.exe
Arguments: -m pa450_report_monitor --config C:\Path\To\pa450-report-monitor\config.yaml
Start in: C:\Path\To\pa450-report-monitor
```

## Security notes

- Do not commit `.env`, `config.yaml`, output XML, output CSV, or logs.
- Prefer a dedicated least-privilege API user for report access.
- If you set `verify_tls: false`, the script passes `-k` equivalent behavior for self-signed lab certificates. For production, install/verify the firewall certificate and set `verify_tls: true`.
