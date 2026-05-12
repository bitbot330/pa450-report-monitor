# 🛡️ PA450 Report CSV Monitor

<p align="center">
  <img src="assets/images/pa450-report-monitor-hero.svg" alt="PA450 Report CSV Monitor Hero" width="820" />
</p>

<p align="center">
  <strong>Windows 本機執行的 PA450 custom report 下載、CSV 轉檔、AI 分析與 Review UI 工具</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-2563eb" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/python-3.10%2B-22c55e" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/PA450-PAN--OS%20XML%20API-f97316" alt="PAN-OS XML API">
  <img src="https://img.shields.io/badge/UI-localhost%20Review%20UI-8b5cf6" alt="Local Review UI">
</p>

PA450 Report CSV Monitor 會透過 **PAN-OS XML API** 下載指定的 PA450 custom report，轉成每日 CSV，交給 AI Gateway 分析，並提供本機 Review UI 讓使用者檢視 CSV / AI JSON 與針對單筆資料寫入 feedback。下一次分析前，程式會讀取尚未處理過的 feedback，萃取成可重用 review rules，讓 AI 分析逐步貼近實際環境。

---

## 文件入口

- 主程式：`src\report.py`
- AI 分析：`src\analyze.py`
- Review UI：`src\ui.py`
- Review memory：`.agent\review.md`
- Feedback 檔案：`output\report_YYYYMMDD.md`
- UI exe 打包：`scripts\build-ui-exe.ps1`

## 快速入口

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
python src\report.py --config config.yaml --output-dir output
python src\analyze.py --input output\YYYYMMDD_report.csv --output output\report_YYYYMMDD.json
```

---

## 概觀

<p align="center">
  <img src="assets/images/pa450-workflow.svg" alt="PA450 automation workflow" width="820" />
</p>

```text
PA450 custom report
→ src\report.py 下載 PAN-OS XML API 結果並轉成 CSV
→ output\YYYYMMDD_report.csv
→ src\analyze.py 先處理 feedback / review memory
→ 讀取 .agent\review.md 作為 review rules
→ AI 分析 CSV
→ output\report_YYYYMMDD.json
→ Review UI 檢視 CSV / AI JSON 並寫入 output\report_YYYYMMDD.md
→ 下一次分析前把 feedback 萃取成新的 review rules
```

## 功能特色

- **PA450 custom report 下載**：透過 PAN-OS XML API 取得指定 custom report。
- **每日 CSV 輸出**：輸出 `output\YYYYMMDD_report.csv`，欄位固定且可直接給 AI 分析。
- **目的地國家判斷**：CSV 支援 `目的地國家`，AI 分析會優先根據目的地國家判斷危險或需人工確認的地區。
- **AI Gateway 分析**：將 CSV context 送給指定 AI model，輸出 `output\report_YYYYMMDD.json`。
- **Review UI**：本機 UI 可檢視每日 CSV、AI 分析結果，並針對單筆資料寫入 feedback。
- **Review memory**：分析前自動讀取尚未處理的 `report_YYYYMMDD.md`，萃取成 `.agent\review.md` 長期規則。
- **不使用固定 bytes threshold**：高流量只作為候選訊號，最終判斷仍需結合 review rules 與 CSV 內容。

---

## 專案結構

```text
pa450-report-monitor/
├── AGENTS.md                    # runtime 預先載入的分析規則
├── .agent/
│   ├── review.md                # 長期 review rules
│   └── review_state.json        # feedback 處理 checkpoint
├── assets/
│   └── images/                  # README 圖片
├── output/                      # 每日 CSV / AI JSON / feedback markdown
├── scripts/
│   └── build-ui-exe.ps1         # Review UI exe 打包腳本
├── src/
│   ├── report.py                # PA450 report 下載、XML 轉 CSV
│   ├── analyze.py               # AI 分析 CSV，並在分析前處理 feedback / review memory
│   ├── ui.py                    # localhost-only Review UI 入口
│   ├── config.py                # .env / config.yaml 設定載入與 CSV 欄位定義
│   ├── ui_app/
│   │   ├── data.py              # UI 資料讀取、報告探索、feedback 寫入
│   │   └── assets/index.html    # UI HTML/CSS/JavaScript template
│   └── runtime/
│       ├── prompt_builder.py    # AGENTS.md / review rules prompt 組裝
│       └── review_tools.py      # review.md / review_state.json / feedback 掃描
├── .env.example                 # .env 範本
├── config.example.yaml          # PA450 report 設定範本
├── requirements.txt             # Python 套件
└── README.md
```

---

## 系統需求

- Windows 10/11
- Python 3.10+
- 可連線到 PA450 management API
- AI Gateway endpoint 與 API key

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
python src\ui.py --help
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
| `PA450_HOST` | PA450 management IP 或 hostname，例如 `YOUR_PA450_MANAGEMENT_IP` |
| `PA450_USERNAME` | PA450 使用者名稱 |
| `PA450_PASSWORD` | PA450 密碼 |
| `PA450_API_KEY` | PA450 API key |
| `AI_GATEWAY_URL` | AI Gateway base URL |
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
| `pa450.report_name` | PA450 custom report 名稱，例如 `YOUR_CUSTOM_REPORT_NAME` |
| `pa450.report_job_name` | PA450 dynamic report job 名稱 |

---

## PA450 custom report 欄位

PA450 custom report 建議至少包含下列欄位，程式會轉成固定中文 CSV 欄位：

| CSV 欄位 | 來源欄位用途 |
|---|---|
| `產生時間` | 產生時間 / generated time |
| `來源位址` | Source address |
| `來源主機名稱` | Source hostname |
| `來源使用者` | Source user |
| `目的地位址` | Destination address |
| `目的地國家` | Destination Country |
| `目的地主機名稱` | Destination hostname |
| `應用程式` | Application |
| `位元組` | Bytes |

> `目的地國家` 會用於 AI 分析危險或需人工確認的地區，例如俄羅斯相關目的地。若 PA450 API 回傳的實際欄位名稱不同，需要在 `src\config.py` 補上對應候選欄位。

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
output\YYYYMMDD_report.csv
```

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

## 打包 Review UI exe

在專案根目錄開啟 PowerShell，執行：

```powershell
.venv\Scripts\Activate
powershell -ExecutionPolicy Bypass -File scripts\build-ui-exe.ps1
```

打包完成後，exe 會輸出到：

```text
dist\PA450-Daily-Review-UI.exe
```

Review UI 會讀取：

```text
output\YYYYMMDD_report.csv
output\report_YYYYMMDD.json
output\report_YYYYMMDD.md
```

UI 可用來檢視每日 CSV、AI 分析結果，並針對單筆資料寫入回報。儲存回報時會顯示：`儲存中...`、`已儲存回報。`、`已暫存目前回報。` 或 `儲存失敗，請再試一次。`

---

## Feedback 與 review memory

人工 feedback 檔名格式固定為：

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

---

## 驗證指令

```powershell
python -m py_compile src\report.py src\config.py src\ui.py src\analyze.py src\runtime\review_tools.py src\runtime\prompt_builder.py
python src\report.py --help
python src\analyze.py --help
python src\ui.py --help
```

---

## 維護重點

- 不要重新加入固定 bytes threshold / alert 行為。
- AI 分析應避免把 top-sources / 高流量報表的所有列都列成異常。
- `目的地國家` 若存在，應優先作為危險地區判斷依據。
- `.agent\review.md` 的 review rules 是分析規則，不只是參考資訊。
