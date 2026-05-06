# PA450 Report CSV Monitor

PA450 Report CSV Monitor 是一個 Windows 本機執行的 PA450 report 下載與 AI 分析工具。

---

## 專案流程

```text
PA450 custom report
→ PAN-OS XML API
→ src/report.py 下載 report 並輸出 CSV
→ src/analyze.py 讀 CSV 並送 AI Gateway 分析
→ 輸出 JSON 分析結果
```

`report.py` 與 `analyze.py` 是兩條獨立指令：

- `src/report.py`：下載 PA450 custom report、轉 CSV、檢查 bytes threshold、輸出 alert 訊息。
- `src/analyze.py`：讀取 CSV，餵給 AI Gateway，輸出 JSON。

---

## 專案結構

```text
pa450-report-monitor/
├── src/
│   ├── report.py        # PA450 report 下載、CSV 輸出、bytes alert
│   ├── analyze.py       # AI 分析 CSV
│   ├── config.py        # .env / config.yaml 設定載入
│   └── __init__.py
├── .env.example         # .env 範本
├── config.example.yaml  # report 與監控設定範本
├── requirements.txt     # Python 套件
└── README.md
```

實際執行時會另外建立：

```text
.env                 # 本機設定，不 commit
config.yaml          # 本機執行設定，不 commit
output/              # CSV / JSON 輸出資料夾，不 commit
```

---

## 系統需求

- Windows 10/11 或 Windows Server
- Python 3.10 以上
- 執行主機可連線到 PA450 management API
- PA450 帳號需可使用 XML API
- PA450 上已建立要下載的 custom report
- 執行主機可連線到 AI Gateway

---

## 安裝

在專案根目錄開啟 PowerShell，執行：

```powershell
python -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

確認指令可使用：

```powershell
python src\report.py --help
python src\analyze.py --help
```

---

## 設定 `.env`

開啟 `.env`：

```powershell
notepad .env
```

依照 `.env.example` 的欄位填入 PA450 連線資料與 AI Gateway 設定。

`.env` 用來放：

- PA450 management IP 或 hostname
- PA450 使用者名稱
- PA450 密碼
- PA450 API key
- AI Gateway URL
- AI Gateway API key
- AI model 與 temperature

欄位用途：

- `PA450_*`：PA450 report 下載使用。
- `AI_*`：AI 分析使用。

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
python src\report.py --config config.yaml --output-dir output
```

參數說明：

- `--config config.yaml`：指定本機設定檔。
- `--output-dir output`：指定 CSV 輸出資料夾。

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

## Report alert 輸出

如果有資料超過 bytes threshold，`report.py` 會在終端機輸出：

```text
ALERT: <COUNT> rows exceeded bytes threshold <THRESHOLD>.
- <超標資料摘要>
```

如果沒有超過 threshold，會輸出：

```text
OK: no rows exceeded threshold
```

---

## 執行 AI 分析

PowerShell：

```powershell
.venv\Scripts\Activate
python src\analyze.py --input output\YYYYMMDD_report.csv --output output\YYYYMMDD.json
```

參數說明：

- `--input`：要餵給 AI 的 CSV 檔案。
- `--output`：AI 分析結果 JSON 輸出位置。
- `--query`：可選，覆蓋預設分析問題。

輸出格式：

```json
{
  "analysis": "AI 回答內容"
}
```

---

## 注意事項

- `.env` 不要 commit。
- `config.yaml` 不要 commit。
- API key、密碼不要寫進 README。
- 輸出的 CSV / JSON 不要 commit。
- log 檔案不要 commit。
- 建議使用專用 PA450 API 帳號。

---

## 官方文件

- PAN-OS XML API key：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key>
- Custom Reports API：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/get-reports-api/custom-reports>
- View Reports export formats：<https://docs.paloaltonetworks.com/ngfw/administration/monitoring/view-and-manage-reports/view-reports>
