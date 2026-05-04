# PA450 Report CSV Monitor

PA450 Report CSV Monitor 是一個 Windows 本機執行的 PA450 report 下載工具。

它目前只負責一件事：

> 透過 PAN-OS XML API 下載指定的 PA450 custom report，並輸出成 CSV。

---

## 專案流程

```text
PA450 custom report
→ PAN-OS XML API
→ Python 下載 report
→ 轉成 CSV
→ 輸出 YYYYMMDD_report.csv
```

目前主流程不做 AI 判斷，也不負責排程。
AI 分析、告警通知、自動排程可由外部流程再呼叫本工具。

---

## 專案結構

```text
pa450-report-monitor/
├── src/pa450_report_monitor/      # 主程式
├── tests/                         # 測試
├── .env.example                   # PA450 連線設定範本
├── config.example.yaml            # report 與監控設定範本
├── requirements.txt               # Python 套件
├── pyproject.toml                 # Python package 設定
└── README.md
```

實際執行時會另外建立：

```text
.env                              # 本機 PA450 連線資料，不 commit
config.yaml                       # 本機執行設定，不 commit
output/                           # CSV 輸出資料夾，不 commit
```

---

## 系統需求

- Windows 10/11 或 Windows Server
- Python 3.10 以上
- 執行主機可連線到 PA450 management API
- PA450 帳號需可使用 XML API
- PA450 上已建立要下載的 custom report

---

## 安裝

在專案根目錄開啟 PowerShell，執行：

```powershell
python -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

確認 CLI 可使用：

```powershell
python -m pa450_report_monitor --help
```

如果出現以下錯誤：

```text
No module named pa450_report_monitor
```

代表尚未執行：

```powershell
pip install -e .
```

---

## 設定 `.env`

開啟 `.env`：

```powershell
notepad .env
```

依照 `.env.example` 的欄位填入 PA450 連線資料。

`.env` 用來放：

- PA450 management IP 或 hostname
- PA450 使用者名稱
- PA450 密碼
- PA450 API key
- Discord webhook URL（如果需要）

注意：

- `.env` 是本機設定檔。
- `.env` 不要 commit。
- README 不放實際 `.env` 內容。

---

## 設定 `config.yaml`

開啟 `config.yaml`：

```powershell
notepad config.yaml
```

依照 `config.example.yaml` 的欄位調整。

主要設定項目：

- custom report 名稱
- report job 名稱
- TLS 驗證設定
- bytes 欄位候選名稱
- bytes threshold

注意：

- `config.yaml` 是本機設定檔。
- `config.yaml` 不要 commit。
- README 不放實際 `config.yaml` 內容。
- 不需要在 `config.yaml` 加 `output` 設定。
- 輸出資料夾由 CLI 的 `--output-dir` 指定。

---

## 執行 PA450 report 下載

PowerShell：

```powershell
.venv\Scripts\Activate
python -m pa450_report_monitor --config config.yaml --output-dir output
```

參數說明：

- `--config config.yaml`：指定本機設定檔。
- `--output-dir output`：指定 CSV 輸出資料夾。

---

## 輸出結果

主流程只輸出 CSV。

輸出位置：

```text
<output-dir>\YYYYMMDD_report.csv
```

例如指定：

```powershell
--output-dir output
```

則輸出格式為：

```text
output\YYYYMMDD_report.csv
```

輸出規則：

- 不建立每日資料夾。
- 不輸出 XML。
- 只輸出 CSV。
- 檔名固定為 `YYYYMMDD_report.csv`。

---

## CSV 欄位

CSV 固定輸出以下欄位：

1. `產生時間`
2. `來源位址`
3. `來源主機名稱`
4. `來源使用者`
5. `目的地位址`
6. `目的地主機名稱`
7. `應用程式`
8. `位元組`

---

## 執行結果訊息

成功產生 CSV 時，終端機會顯示：

```text
CSV written: <output-dir>\YYYYMMDD_report.csv
Custom report XPath: ...
```

如果有資料超過 bytes threshold，會顯示：

```text
ALERT: <COUNT> rows exceeded threshold
```

---

## 單獨測試 XML 轉 CSV

如果手上已有 XML 檔案，可單獨測試轉換：

```powershell
python -m pa450_report_monitor.convert input_report.xml output_report.csv
```

這只是轉換測試工具。
主下載流程不會輸出 XML。

---

## 注意事項

- `.env` 不要 commit。
- `config.yaml` 不要 commit。
- API key、密碼不要寫進 README。
- 輸出的 CSV 不要 commit。
- log 檔案不要 commit。
- 建議使用專用 PA450 API 帳號。

---

## 官方文件

- PAN-OS XML API key：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key>
- Custom Reports API：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/get-reports-api/custom-reports>
- View Reports export formats：<https://docs.paloaltonetworks.com/ngfw/administration/monitoring/view-and-manage-reports/view-reports>
