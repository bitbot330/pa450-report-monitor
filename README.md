# PA450 Report CSV Monitor

PA450 Report CSV Monitor 是一個 Windows 本機執行的 PA450 report 下載與 AI 分析工具。

---

## 功能

- 透過 PAN-OS XML API 下載指定的 PA450 custom report。
- 將 report 轉成 CSV。
- 將 CSV 餵給 AI Gateway 分析，輸出 JSON 分析結果。
- 分析開始前自動掃描 `output/report_YYYYMMDD.md`，將尚未處理過的多日人工 feedback 萃取成可重用規則，寫入 `.agent/review.md`。
- 每次 AI 分析開始前，讀取 `.agent/review.md` 作為歷史 review 規則。

---

## 流程

```text
PA450 custom report
→ src/report.py 下載並輸出 CSV
→ src/analyze.py 分析開始前處理 output/report_YYYYMMDD.md feedback
→ 讀取 .agent/review.md 作為 review rules
→ 分析 CSV
→ 輸出 output/report_YYYYMMDD.json
```

兩個指令可分開執行：

| 指令 | 用途 |
|---|---|
| `src\report.py` | 下載 PA450 report、輸出 CSV |
| `src\analyze.py` | 分析開始前處理 feedback / review memory，讀取 CSV、送 AI Gateway 分析、輸出 JSON |

---

## 專案結構

```text
pa450-report-monitor/
├── AGENTS.md             # runtime 預先載入的分析規則
├── .agent/
│   ├── review.md         # 歷史 review 規則
│   └── review_state.json # feedback 已處理到哪一天的 checkpoint
├── src/
│   ├── report.py         # PA450 report 下載、CSV 輸出
│   ├── analyze.py        # AI 分析 CSV，並在分析前處理 feedback / review memory
│   ├── config.py         # .env / config.yaml 設定載入
│   └── runtime/
│       ├── prompt_builder.py # AGENTS.md / review rules prompt 組裝
│       └── review_tools.py   # review.md / review_state.json / feedback 掃描
├── .env.example          # .env 範本
├── config.example.yaml   # report 與監控設定範本
├── requirements.txt      # Python 套件
└── README.md
```

執行時會使用：

```text
.env
config.yaml
output/
.agent/review.md
.agent/review_state.json
```

---

## 系統需求

- Windows 10/11
- Python 3.10 
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

## 執行 AI 分析

```powershell
.venv\Scripts\Activate
python src\analyze.py --input output\YYYYMMDD_report.csv --output output\report_YYYYMMDD.json
```

分析開始前，`src\analyze.py` 會先執行 review memory 流程：

1. 讀取 `.agent\review.md` 內既有的 review rules。
2. 掃描 `output\report_YYYYMMDD.md`。
3. 只處理日期晚於 `.agent\review_state.json` 內 `last_processed_feedback_date` 的 feedback 檔。
4. 一次讀取多日 feedback，交給 AI 萃取簡短、可重用規則。
5. 將新規則寫回 `.agent\review.md`。
6. 更新 `.agent\review_state.json`，記錄已處理到哪一天。
7. 使用更新後的 review rules 執行本次 CSV 分析。

參數：

| 參數 | 用途 |
|---|---|
| `--input` | 要餵給 AI 的 CSV 檔案 |
| `--output` | AI 分析結果 JSON 輸出位置，例如 `output\report_YYYYMMDD.json` |
| `--query` | 可選，覆蓋預設分析問題 |

JSON 輸出格式：

```json
{
  "analysis": "AI 回答內容"
}
```

---

## Feedback 與 review memory

人工 feedback 由既有流程寫在專案根目錄的 `output` 資料夾，檔名格式固定為：

```text
output\report_YYYYMMDD.md
```

`YYYYMMDD` 是 report 下載日期，由外部流程產生。`src\analyze.py` 不負責產生 feedback markdown，只在下一次分析開始前讀取尚未處理過的檔案。

長期 review 規則儲存在：

```text
.agent\review.md
```

feedback 處理 checkpoint 儲存在：

```json
{
  "last_processed_feedback_date": "YYYYMMDD"
}
```

位置：

```text
.agent\review_state.json
```
