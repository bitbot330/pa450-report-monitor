# PA450 Report CSV Monitor

這個專案用 PAN-OS XML API 下載 PA450 custom report，並轉成 CSV 檔案。

目前功能：

- 透過 API 取得 PA450 custom report。
- 將 report 結果轉成 CSV。
- CSV 欄位固定成 Excel 方便閱讀的格式。
- 只輸出 CSV，不輸出 XML。
- CSV 檔案直接放在 `--output-dir` 指定的資料夾。
- CSV 檔名格式為 `YYYYMMDD_report.csv`。

## 需求

- Windows 10/11 或 Windows Server。
- Python 3.10 以上。
- 執行主機可以連到 PA450 management API。
- PA450 帳號需有 XML API 權限。
- PA450 上已存在要下載的 custom report。

## 安裝

在專案資料夾開啟 PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

`pip install -e .` 必須執行。否則可能出現：

```text
No module named pa450_report_monitor
```

## 設定 `.env`

開啟 `.env`：

```powershell
notepad .env
```

依照 `.env.example` 內的欄位填入 PA450 連線資訊。

注意：

- `.env` 放主機、帳號、密碼、API key 等連線資料。
- `.env` 不要 commit。
- README 不放實際 `.env` 內容。

## 設定 `config.yaml`

開啟 `config.yaml`：

```powershell
notepad config.yaml
```

依照 `config.example.yaml` 內的欄位調整設定。

主要需要確認：

- custom report 名稱。
- bytes 判斷欄位候選名稱。
- bytes threshold。
- TLS 驗證設定。

注意：

- `config.yaml` 不要 commit。
- README 不放實際 `config.yaml` 內容。
- 不需要在 `config.yaml` 加 `output` 區塊。
- 輸出資料夾由 CLI 參數 `--output-dir` 指定。

## 執行下載

PowerShell：

```powershell
.venv\Scripts\Activate
python -m pa450_report_monitor --config config.yaml --output-dir output
```

輸出檔案會直接產生在 `output` 資料夾下：

```text
output\YYYYMMDD_report.csv
```

範例格式：

```text
output\20260504_report.csv
```

## 輸出規則

- 不建立每日資料夾。
- 不輸出 XML。
- 只輸出 CSV。
- 檔名格式：`YYYYMMDD_report.csv`。
- 輸出資料夾由 `--output-dir` 決定。

## CSV 欄位

CSV 會依照固定欄位輸出：

1. `產生時間`
2. `來源位址`
3. `來源主機名稱`
4. `來源使用者`
5. `目的地位址`
6. `目的地主機名稱`
7. `應用程式`
8. `位元組`

## 執行結果判斷

成功時會看到類似訊息：

```text
CSV written: output\YYYYMMDD_report.csv
Custom report XPath: ...
```

如果流量超過設定門檻，會看到：

```text
ALERT: <COUNT> rows exceeded threshold
```

## 單獨測試 XML 轉 CSV

如果手上已有 XML 檔案，可單獨測試轉換：

```powershell
python -m pa450_report_monitor.convert input_report.xml output_report.csv
```

這個功能只用於測試轉換，不代表主流程會輸出 XML。

## 安全注意事項

不要 commit 以下檔案或資料：

- `.env`
- `config.yaml`
- API key
- 密碼
- 輸出的 CSV
- log 檔案

建議使用專用的 PA450 API 帳號，並只給必要權限。

## 官方文件

- PAN-OS XML API key：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-the-pan-os-xml-api/get-your-api-key>
- Custom Reports API：<https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/pan-os-xml-api-request-types/get-reports-api/custom-reports>
- View Reports export formats：<https://docs.paloaltonetworks.com/ngfw/administration/monitoring/view-and-manage-reports/view-reports>
