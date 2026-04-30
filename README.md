# PA450 Report CSV Monitor

Automate a Palo Alto Networks PA-450 custom report workflow:

1. get a PAN-OS XML API key, or call `type=keygen` with username/password when no key is provided,
2. retrieve the configured custom report definition,
3. print the exact XPath where the custom report was found,
4. enqueue a dynamic report job,
5. fetch the report result XML,
6. convert report rows to CSV using the fixed Excel column layout,
7. save outputs under an `output\YYYYMMDD\` folder,
8. check byte thresholds and optionally send a Discord webhook alert.

This project intentionally uses the PAN-OS XML API path because Palo Alto documentation confirms custom reports can be exported as CSV manually, while the built-in email scheduler is documented under **PDF Reports > Email Scheduler**. For automated CSV, this project fetches XML results from the API and converts them to CSV locally.

## Official documentation used

- Get API key: <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key>
- Custom Reports API: <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/get-reports-api/custom-reports>
- View Reports export formats: <https://docs.paloaltonetworks.com/ngfw/administration/monitoring/view-and-manage-reports/view-reports>

## Requirements

- Windows 10/11 or Windows Server with Python 3.10+
- Network access from the Windows machine to `https://<YOUR_PA450_MANAGEMENT_IP>/api/`
- A PA-450/PAN-OS administrator account allowed to use the XML API
- An existing custom report under `Monitor > Manage Custom Reports`

No Palo Alto credentials are committed to this repository.

## Windows setup

Open **PowerShell** in the project folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

The `pip install -e .` step is required. Without it, Windows can show this error when running the scheduler or CLI:

```text
C:\pa450-report-monitor\.venv\Scripts\python.exe: No module named pa450_report_monitor
```

If you already created the virtual environment and see that error, fix the existing environment from the project folder:

```powershell
.venv\Scripts\Activate
pip install -e .
```

## Configure `.env` on Windows

Open `.env` with Notepad:

```powershell
notepad .env
```

Edit these values:

```env
PA450_HOST=YOUR_PA450_MANAGEMENT_IP
PA450_USERNAME=YOUR_PA450_USERNAME
PA450_PASSWORD=YOUR_PA450_PASSWORD
PA450_API_KEY=
DISCORD_WEBHOOK_URL=
```

Only `.env` contains connection/account values. `config.yaml` does **not** repeat `PA450_HOST`, `PA450_USERNAME`, `PA450_PASSWORD`, or `PA450_API_KEY` because the program always reads those fixed environment variable names directly.

Example for a real firewall at `10.10.10.254`:

```env
PA450_HOST=10.10.10.254
PA450_USERNAME=report-api-user
PA450_PASSWORD=your-real-password
PA450_API_KEY=
DISCORD_WEBHOOK_URL=
```

## Configure `config.yaml`

Open `config.yaml`:

```powershell
notepad config.yaml
```

Edit this section:

```yaml
pa450:
  verify_tls: false
  report_name: top-sources
  report_job_name: pa450-custom-dynamic-report

monitor:
  bytes_field_candidates:
    - bytes
    - Bytes
    - 位元組
    - repeatcnt
  bytes_threshold: 1000000000
```

Concrete fields to edit:

- `pa450.report_name`: use your exact custom report name from `Monitor > Manage Custom Reports`; for your screenshot, this is `top-sources`.
- `monitor.bytes_threshold`: byte value that should trigger an alert.
- `monitor.bytes_field_candidates`: keep `bytes` / `Bytes` for the PA450 report bytes field.

The `top-sources` custom report path is now fixed from your confirmed output:

```text
/config/shared/reports/entry[@name='top-sources']
```

Because this report is under `/config/shared/reports`, `config.yaml` no longer needs a `vsys` setting for the report lookup.

Do **not** add an `output:` block to `config.yaml`. Output settings are fixed in code:

- Base folder: `output`
- Daily folder format: `YYYYMMDD`
- XML file name: `report_result.xml`
- CSV file name: `report_result.csv`
- CSV/Excel columns:
  1. `產生時間`
  2. `來源位址`
  3. `來源主機名稱`
  4. `來源使用者`
  5. `目的地位址`
  6. `目的地主機名稱`
  7. `應用程式`
  8. `位元組`

## Run on Windows

In PowerShell:

```powershell
.venv\Scripts\Activate
python -m pa450_report_monitor --config config.yaml
```

Expected output when rows are below threshold:

```text
OK: no rows exceeded threshold
CSV written: output\20260430\report_result.csv
XML written: output\20260430\report_result.xml
Custom report XPath: /config/shared/reports/entry[@name='top-sources']
```

Expected output when rows exceed threshold:

```text
ALERT: 2 rows exceeded threshold
CSV written: output\20260430\report_result.csv
XML written: output\20260430\report_result.xml
Custom report XPath: /config/shared/reports/entry[@name='top-sources']
```

The `Custom report XPath` line is still printed as a verification line, but the lookup is now fixed to the shared report path instead of probing multiple locations.

## Test XML to CSV only

If you already have a saved report XML and only want to test conversion:

```powershell
python -m pa450_report_monitor.convert output\20260430\report_result.xml output\20260430\report_result.csv
```

## Windows Task Scheduler

Create a scheduled task:

```text
Program/script:
C:\Path\To\pa450-report-monitor\.venv\Scripts\python.exe

Arguments:
-m pa450_report_monitor --config C:\Path\To\pa450-report-monitor\config.yaml

Start in:
C:\Path\To\pa450-report-monitor
```

Redirect logs by creating a small PowerShell wrapper, for example `run-pa450-monitor.ps1`:

```powershell
Set-Location "C:\Path\To\pa450-report-monitor"
.\.venv\Scripts\python.exe -m pa450_report_monitor --config config.yaml *> logs\monitor.log
```

Then set Task Scheduler to run:

```text
Program/script:
powershell.exe

Arguments:
-ExecutionPolicy Bypass -File C:\Path\To\pa450-report-monitor\run-pa450-monitor.ps1
```

## Linux or WSL quick reference

The project can also run on Linux/WSL, but Windows is the primary documented setup above.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
cp config.example.yaml config.yaml
python -m pa450_report_monitor --config config.yaml
```

Cron example:

```cron
0 8 * * * cd /path/to/pa450-report-monitor && . .venv/bin/activate && python -m pa450_report_monitor --config config.yaml >> logs/monitor.log 2>&1
```

## Security notes

- Do not commit `.env`, `config.yaml`, output XML, output CSV, or logs.
- Prefer a dedicated least-privilege API user for report access.
- If you set `verify_tls: false`, the script passes `-k` equivalent behavior for self-signed lab certificates. For production, install/verify the firewall certificate and set `verify_tls: true`.
