# PA450 Report CSV Monitor

PA450 Report CSV Monitor 是一個 Windows 本機執行的 PA450 report 下載與 AI 分析工具。

---

## 功能

- 透過 PAN-OS XML API 下載指定的 PA450 custom report。
- 將 report 轉成 CSV。
- 檢查 bytes threshold，並在終端機輸出 alert 結果。
- 將 CSV 餵給 AI Gateway 分析，輸出 JSON 分析結果。

---

## 流程

```text
PA450 custom report
→ src/report.py 下載並輸出 CSV
→ src/analyze.py 分析 CSV
→ 輸出 JSON
```

兩個指令可分開執行：

| 指令 | 用途 |
|---|---|
| `src\report.py` | 下載 PA450 report、輸出 CSV、檢查 bytes threshold |
| `src\analyze.py` | 讀取 CSV、送 AI Gateway 分析、輸出 JSON |

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

執行時會使用：

```text
.env
config.yaml
output/
```

---

## 系統需求

- Windows 10/11 或 Windows Server
- Python 3.10 以上
- 執行主機可連線到 PA450 management API
- PA450 帳號可使用 XML API
- PA450 上已建立要下載的 custom report
- 執行主機可連線到 AI Gateway

---

## 安裝

### 1. 建立 Python venv

在專案根目錄開啟 PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
```

### 2. 安裝套件

```powershell
pip install -r requirements.txt
```

### 3. 建立本機設定檔

```powershell
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

### 4. 確認指令可使用

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

`.env` 欄位：

| 欄位 | 用途 |
|---|---|
| `PA450_HOST` | PA450 management IP 或 hostname |
| `PA450_USERNAME` | PA450 使用者名稱 |
| `PA450_PASSWORD` | PA450 密碼 |
| `PA450_API_KEY` | PA450 API key |
| `AI_GATEWAY_URL` | AI Gateway URL |
| `AI_GATEWAY_API_KEY` | AI Gateway API key |
| `AI_MODEL` | AI model 名稱 |
| `AI_TEMPERATURE` | AI temperature |

`PA450_API_KEY` 與 `PA450_USERNAME` / `PA450_PASSWORD` 二選一即可：

- 有 `PA450_API_KEY`：程式直接使用 API key。
- 沒有 `PA450_API_KEY`：程式會使用 `PA450_USERNAME` / `PA450_PASSWORD` 取得 API key。

---

## 設定 `config.yaml`

開啟 `config.yaml`：

```powershell
notepad config.yaml
```

主要設定項目：

| 欄位 | 用途 |
|---|---|
| `pa450.verify_tls` | 是否驗證 PA450 TLS 憑證 |
| `pa450.report_name` | PA450 custom report 名稱 |
| `pa450.report_job_name` | PA450 dynamic report job 名稱 |
| `monitor.bytes_field_candidates` | 判斷流量大小時可接受的 bytes 欄位名稱 |
| `monitor.bytes_threshold` | bytes alert 門檻 |

---

## 執行 PA450 report 下載

```powershell
.venv\Scripts\Activate
python src\report.py --config config.yaml --output-dir output
```

參數：

| 參數 | 用途 |
|---|---|
| `--config config.yaml` | 指定設定檔 |
| `--output-dir output` | 指定 CSV 輸出資料夾 |

CSV 輸出位置：

```text
<output-dir>\YYYYMMDD_report.csv
```

例如：

```text
output\YYYYMMDD_report.csv
```

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

如果有資料超過 bytes threshold，`report.py` 會輸出：

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

```powershell
.venv\Scripts\Activate
python src\analyze.py --input output\YYYYMMDD_report.csv --output output\YYYYMMDD.json
```

參數：

| 參數 | 用途 |
|---|---|
| `--input` | 要餵給 AI 的 CSV 檔案 |
| `--output` | AI 分析結果 JSON 輸出位置 |
| `--query` | 可選，覆蓋預設分析問題 |

JSON 輸出格式：

```json
{
  "analysis": "AI 回答內容"
}
```
