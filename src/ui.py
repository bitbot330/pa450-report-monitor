from __future__ import annotations

import argparse
import csv
import json
import os
import re
import threading
import webbrowser
from collections import Counter
from functools import partial
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from report import parse_int

DASHBOARD_TITLE = "PA450 Daily Review UI"
LOCALHOST = "127.0.0.1"
DATE_KEY_RE = re.compile(r"^\d{8}$")


INDEX_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b1220;
      --panel: #111b2e;
      --panel-2: #16223a;
      --line: #29405f;
      --text: #e8eefc;
      --muted: #9eb2d0;
      --accent: #65b7ff;
      --accent-bg: rgba(101, 183, 255, 0.18);
      --sidebar-w: 280px;
      --sidebar-collapsed-w: 72px;
      --right-rail-w: 320px;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, "Noto Sans TC", sans-serif; background: var(--bg); color: var(--text); }}
    h1, h2, h3, p {{ margin: 0; }}
    button, input, select, textarea {{ font: inherit; }}
    .app {{ display: grid; grid-template-columns: var(--sidebar-w) minmax(0, 1fr); min-height: 100vh; transition: grid-template-columns 180ms ease; }}
    .app.sidebar-collapsed {{ grid-template-columns: var(--sidebar-collapsed-w) minmax(0, 1fr); }}
    .sidebar {{ position: sticky; top: 0; height: 100vh; overflow: hidden; border-right: 1px solid var(--line); background: #0f1728; padding: 16px; }}
    .sidebar-inner {{ height: 100%; overflow-y: auto; overflow-x: hidden; padding-right: 2px; }}
    .sidebar-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 14px; }}
    .sidebar-toggle {{ flex: 0 0 auto; width: 40px; height: 40px; border-radius: 12px; border: 1px solid var(--line); background: #0d1525; color: var(--text); cursor: pointer; }}
    .sidebar-toggle:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
    .brand {{ min-width: 0; }}
    .brand h1 {{ font-size: 20px; line-height: 1.2; margin-bottom: 8px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .base-picker, .file-picker {{ display: grid; gap: 8px; margin-top: 14px; }}
    .base-picker-actions {{ display: flex; gap: 8px; }}
    .base-picker-actions input {{ min-width: 0; }}
    .base-picker-actions button, .file-picker-actions button, .file-chip {{ flex: 0 0 auto; border-radius: 10px; border: 1px solid var(--line); background: #0d1525; color: var(--text); padding: 8px 12px; cursor: pointer; }}
    .base-picker-actions button:hover, .file-picker-actions button:hover, .file-chip:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
    .file-picker-actions {{ display: grid; gap: 8px; }}
    .file-chip-row {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .file-chip {{ width: 100%; text-align: center; }}
    .file-picker-actions button {{ width: 100%; }}
    .file-picker-actions input[type="file"] {{ display: none; }}
    .file-name {{ min-height: 18px; word-break: break-all; }}
    .app.sidebar-collapsed .sidebar {{ padding: 16px 12px; }}
    .app.sidebar-collapsed .sidebar-top {{ justify-content: center; }}
    .app.sidebar-collapsed .brand, .app.sidebar-collapsed .base-picker, .app.sidebar-collapsed .file-picker, .app.sidebar-collapsed .report-item .report-summary {{ display: none; }}
    .app.sidebar-collapsed .report-list {{ margin-top: 10px; }}
    .app.sidebar-collapsed .report-item {{ min-height: 48px; padding: 8px 6px; text-align: center; border-radius: 14px; }}
    .app.sidebar-collapsed .report-date {{ font-size: 12px; line-height: 1.15; word-break: break-all; }}
    .main {{ min-width: 0; padding: 18px 20px 24px; }}
    .report-list {{ display: grid; gap: 10px; margin-top: 14px; }}
    .report-item {{ width: 100%; text-align: left; padding: 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--panel); color: var(--text); cursor: pointer; }}
    .report-item:hover, .report-item.active {{ border-color: var(--accent); background: var(--accent-bg); }}
    .report-date {{ font-size: 16px; color: var(--text); }}
    .layout {{ display: grid; gap: 14px; }}
    .summary-grid {{ display: grid; gap: 10px; grid-template-columns: repeat(6, minmax(110px, 1fr)); overflow-x: auto; padding-bottom: 2px; }}
    .content-grid {{ display: grid; grid-template-columns: minmax(0, 1fr) var(--right-rail-w); gap: 16px; align-items: stretch; }}
    .right-rail {{ display: grid; gap: 12px; align-content: start; }}
    .card {{ background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18); }}
    .csv-card {{ display: flex; flex-direction: column; min-height: calc(100vh - 150px); }}
    .summary-grid .card {{ min-width: 0; min-height: 82px; padding: 10px 12px; }}
    .metric {{ font-size: 20px; line-height: 1.12; font-weight: 700; margin-top: 6px; word-break: break-word; }}
    .summary-grid .subtle {{ font-size: 11px; margin-top: 4px; word-break: break-all; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; font-size: 12px; border: 1px solid var(--line); color: var(--muted); white-space: nowrap; }}
    .panel-title {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }}
    .panel-title h2 {{ font-size: 22px; line-height: 1.2; }}
    .right-rail .panel-title h2 {{ font-size: 18px; }}
    .detail-list {{ display: grid; gap: 10px; }}
    .detail-row {{ border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 10px; }}
    .detail-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .detail-key {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .ai-card {{ font-size: 13px; }}
    .ai-card .detail-list {{ gap: 8px; }}
    .ai-card .detail-row {{ padding-bottom: 8px; }}
    .ai-card .detail-row > div:not(.detail-key):not(.subtle) {{ line-height: 1.55; }}
    .report-text {{ white-space: pre-wrap; line-height: 1.7; font-size: 14px; }}
    .toolbar {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr) minmax(0, 0.75fr); gap: 12px; margin-bottom: 14px; min-width: 0; }}
    .control {{ min-width: 0; }}
    input, select, textarea {{ width: 100%; min-width: 0; background: #0d1525; color: var(--text); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }}
    textarea {{ min-height: 92px; resize: vertical; }}
    .table-wrap {{ flex: 1 1 auto; min-height: 0; overflow: auto; border: 1px solid var(--line); border-radius: 14px; max-height: none; }}
    .row-detail-card {{ display: grid; gap: 14px; }}
    .review-in-detail {{ border-top: 1px solid rgba(255,255,255,0.10); padding-top: 14px; }}
    .review-in-detail h3 {{ font-size: 17px; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
    thead th {{ position: sticky; top: 0; background: #13213a; z-index: 1; text-align: left; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 13px; vertical-align: top; }}
    tbody tr {{ cursor: pointer; }}
    tbody tr:hover {{ background: rgba(101, 183, 255, 0.08); }}
    tbody tr.is-selected {{ background: rgba(101, 183, 255, 0.18); }}
    .empty {{ padding: 18px; border: 1px dashed var(--line); border-radius: 12px; color: var(--muted); }}
    .error {{ color: #ff9a9a; }}
    @media (max-width: 1320px) {{
      .summary-grid {{ grid-template-columns: repeat(6, minmax(100px, 1fr)); }}
      .content-grid {{ grid-template-columns: minmax(0, 1fr) 300px; }}
    }}
    @media (max-width: 1080px) {{
      .app, .app.sidebar-collapsed {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: relative; height: auto; border-right: none; border-bottom: 1px solid var(--line); }}
      .app.sidebar-collapsed .brand {{ display: block; }}
      .summary-grid {{ grid-template-columns: repeat(6, minmax(96px, 1fr)); }}
      .content-grid {{ grid-template-columns: 1fr; }}
      .right-rail {{ grid-row: 2; }}
      .toolbar {{ grid-template-columns: 1fr; }}
      .csv-card {{ min-height: auto; }}
      .table-wrap {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="app" id="appShell">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-inner">
        <div class="sidebar-top">
          <div class="brand">
            <h1>{title}</h1>
            <p class="subtle">同一個 UI 直接切換每日報告，不用每次重生 dashboard。</p>
            <p class="subtle">僅限本機 localhost 使用。</p>
            <div class="base-picker">
              <div class="detail-key">資料夾 base</div>
              <div class="base-picker-actions">
                <input id="dataDirInput" type="text" placeholder="例如：C:\\pa450\\output 或 ./output">
                <button id="reloadDataDir" type="button">讀取</button>
              </div>
              <p class="subtle">CSV 與 JSON 可在 base 底下不同子目錄。</p>
            </div>
            <div class="file-picker">
              <div class="detail-key">手動載入檔案</div>
              <div class="file-picker-actions">
                <div class="file-chip-row">
                  <label class="file-chip" for="csvFileInput">選 CSV</label>
                  <label class="file-chip" for="jsonFileInput">選 AI JSON</label>
                </div>
                <input id="csvFileInput" type="file" accept=".csv,text/csv">
                <input id="jsonFileInput" type="file" accept=".json,application/json">
                <button id="loadSelectedFiles" type="button">載入已選檔案</button>
              </div>
              <div id="csvFileName" class="subtle file-name">尚未選擇 CSV</div>
              <div id="jsonFileName" class="subtle file-name">尚未選擇 AI JSON</div>
              <div id="manualLoadState" class="subtle file-name">CSV 與 AI JSON 可分別從不同資料夾挑選；兩個都選好後再載入。</div>
              <p class="subtle">直接用瀏覽器分開選本機 CSV/JSON，不改動磁碟上的 base 掃描流程。</p>
            </div>
          </div>
          <button class="sidebar-toggle" id="sidebarToggle" type="button" aria-label="收合側邊欄" title="收合側邊欄">‹</button>
        </div>
        <div class="report-list" id="reportList"></div>
      </div>
    </aside>
    <main class="main">
      <div id="loading" class="empty">載入中...</div>
      <div id="errorBox" class="empty error" hidden></div>
      <div id="reportApp" class="layout" hidden>
        <section class="summary-grid" id="summaryGrid"></section>
        <section class="content-grid">
          <article class="card csv-card">
            <div class="panel-title"><h2>CSV 完整檢視</h2><span class="pill">Evidence</span></div>
            <div class="toolbar">
              <div class="control">
                <div class="detail-key">搜尋 CSV</div>
                <input id="searchInput" type="search" placeholder="輸入 IP、使用者、應用程式、主機名稱...">
              </div>
              <div class="control">
                <div class="detail-key">來源 IP</div>
                <select id="sourceFilter"></select>
              </div>
              <div class="control">
                <div class="detail-key">應用程式</div>
                <select id="appFilter"></select>
              </div>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr id="tableHead"></tr></thead>
                <tbody id="tableBody"></tbody>
              </table>
            </div>
          </article>
          <aside class="right-rail">
            <article class="card ai-card">
              <div class="panel-title"><h2>AI 報告</h2><span class="pill">摘要</span></div>
              <div class="detail-list" id="analysisCard"></div>
            </article>
            <article class="card row-detail-card">
              <div>
                <div class="panel-title"><h2>列明細</h2><span class="pill">點表格列</span></div>
                <div id="rowDetail" class="empty">尚未選取資料列。</div>
              </div>
              <div>
                <div class="panel-title"><h3>該列對應報告</h3><span class="pill">row match</span></div>
                <div id="rowReportDetail" class="empty">選取資料列後，這裡會顯示與該列最相關的 AI 報告與比對證據。</div>
              </div>
              <div class="review-in-detail">
                <div class="panel-title"><h3>報告回報</h3><span class="pill">localStorage</span></div>
                <div class="detail-key">回報狀態</div>
                <select id="reviewStatus">
                  <option value="">未設定</option>
                  <option value="normal">整體正常</option>
                  <option value="follow-up">有異常需追蹤</option>
                  <option value="ai-adjustment">AI 判讀需調整</option>
                </select>
                <div class="detail-key" style="margin-top:12px;">備註</div>
                <textarea id="reviewNote" placeholder="例如：這次高流量其實是備份流量，AI 需要學會辨識。"></textarea>
              </div>
            </article>
          </aside>
        </section>
      </div>
    </main>
  </div>

  <script>
    const DEFAULT_DATA_DIR = {data_dir_json};
    const appState = {{ reports: [], current: null, selectedRowIndex: null }};
    const appShell = document.getElementById('appShell');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const dataDirInput = document.getElementById('dataDirInput');
    const reloadDataDir = document.getElementById('reloadDataDir');
    const csvFileInput = document.getElementById('csvFileInput');
    const jsonFileInput = document.getElementById('jsonFileInput');
    const loadSelectedFilesButton = document.getElementById('loadSelectedFiles');
    const csvFileName = document.getElementById('csvFileName');
    const jsonFileName = document.getElementById('jsonFileName');
    const manualLoadState = document.getElementById('manualLoadState');
    const reportList = document.getElementById('reportList');
    const loading = document.getElementById('loading');
    const errorBox = document.getElementById('errorBox');
    const reportApp = document.getElementById('reportApp');
    const summaryGrid = document.getElementById('summaryGrid');
    const analysisCard = document.getElementById('analysisCard');
    const searchInput = document.getElementById('searchInput');
    const sourceFilter = document.getElementById('sourceFilter');
    const appFilter = document.getElementById('appFilter');
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const rowDetail = document.getElementById('rowDetail');
    const rowReportDetail = document.getElementById('rowReportDetail');
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewNote = document.getElementById('reviewNote');

    function clearNode(node) {{
      while (node.firstChild) node.removeChild(node.firstChild);
    }}

    function setEmptyMessage(container, message, className = 'empty') {{
      clearNode(container);
      container.className = className;
      container.textContent = message;
    }}

    function createTextNode(tag, text, className = '') {{
      const node = document.createElement(tag);
      if (className) node.className = className;
      node.textContent = text;
      return node;
    }}

    function createDetailRow(key, value, secondary = '') {{
      const row = document.createElement('div');
      row.className = 'detail-row';
      row.appendChild(createTextNode('div', key, 'detail-key'));
      row.appendChild(createTextNode('div', value || '—'));
      if (secondary) row.appendChild(createTextNode('div', secondary, 'subtle'));
      return row;
    }}

    function createPreformattedDetailRow(key, value, secondary = '') {{
      const row = document.createElement('div');
      row.className = 'detail-row';
      row.appendChild(createTextNode('div', key, 'detail-key'));
      const valueNode = createTextNode('div', value || '—', 'report-text');
      row.appendChild(valueNode);
      if (secondary) row.appendChild(createTextNode('div', secondary, 'subtle'));
      return row;
    }}

    function setSidebarCollapsed(collapsed) {{
      appShell.classList.toggle('sidebar-collapsed', collapsed);
      sidebarToggle.textContent = collapsed ? '›' : '‹';
      sidebarToggle.title = collapsed ? '展開側邊欄' : '收合側邊欄';
      sidebarToggle.setAttribute('aria-label', sidebarToggle.title);
      localStorage.setItem('pa450-sidebar-collapsed', collapsed ? '1' : '0');
    }}

    function currentDataDir() {{
      return dataDirInput.value.trim() || DEFAULT_DATA_DIR;
    }}

    function apiUrl(path) {{
      const params = new URLSearchParams();
      params.set('data_dir', currentDataDir());
      return path + '?' + params.toString();
    }}

    function persistDataDir() {{
      localStorage.setItem('pa450-data-dir', currentDataDir());
    }}

    function updateSelectedFileNames() {{
      csvFileName.textContent = csvFileInput.files[0] ? `CSV：${{csvFileInput.files[0].name}}` : '尚未選擇 CSV';
      jsonFileName.textContent = jsonFileInput.files[0] ? `AI JSON：${{jsonFileInput.files[0].name}}` : '尚未選擇 AI JSON';
      const hasCsv = Boolean(csvFileInput.files[0]);
      const hasJson = Boolean(jsonFileInput.files[0]);
      loadSelectedFilesButton.disabled = !(hasCsv && hasJson);
      if (hasCsv && hasJson) {{
        manualLoadState.textContent = '已分開記住目前選擇的 CSV 與 AI JSON；即使來自不同資料夾也可直接一起載入。';
      }} else if (hasCsv) {{
        manualLoadState.textContent = 'CSV 已選好；可切換到另一個資料夾再挑 AI JSON。';
      }} else if (hasJson) {{
        manualLoadState.textContent = 'AI JSON 已選好；可切換到另一個資料夾再挑 CSV。';
      }} else {{
        manualLoadState.textContent = 'CSV 與 AI JSON 可分別從不同資料夾挑選；兩個都選好後再載入。';
      }}
    }}

    function showError(message) {{
      errorBox.hidden = false;
      errorBox.textContent = message;
      loading.hidden = true;
      reportApp.hidden = true;
    }}

    function clearError() {{
      errorBox.hidden = true;
      errorBox.textContent = '';
    }}

    function readFileAsText(file) {{
      return new Promise((resolve, reject) => {{
        const reader = new FileReader();
        reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
        reader.onerror = () => reject(new Error(`讀取檔案失敗：${{file.name}}`));
        reader.readAsText(file, 'utf-8');
      }});
    }}

    function splitCsvLine(line) {{
      const values = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i += 1) {{
        const char = line[i];
        if (char === '"') {{
          if (inQuotes && line[i + 1] === '"') {{
            current += '"';
            i += 1;
          }} else {{
            inQuotes = !inQuotes;
          }}
          continue;
        }}
        if (char === ',' && !inQuotes) {{
          values.push(current);
          current = '';
          continue;
        }}
        current += char;
      }}
      values.push(current);
      return values;
    }}

    function parseCsvText(csvText) {{
      const normalized = csvText.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      const rows = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < normalized.length; i += 1) {{
        const char = normalized[i];
        if (char === '"') {{
          current += char;
          if (inQuotes && normalized[i + 1] === '"') {{
            current += normalized[i + 1];
            i += 1;
          }} else {{
            inQuotes = !inQuotes;
          }}
          continue;
        }}
        if (char === '\n' && !inQuotes) {{
          rows.push(current);
          current = '';
          continue;
        }}
        current += char;
      }}
      if (current || normalized.endsWith('\n')) rows.push(current);
      const nonEmptyRows = rows.filter((line) => line.length > 0);
      if (!nonEmptyRows.length) throw new Error('CSV 內容是空的');
      const headers = splitCsvLine(nonEmptyRows[0]);
      if (!headers.length || headers.every((header) => !header.trim())) throw new Error('CSV 缺少表頭');
      const dataRows = nonEmptyRows.slice(1).map((line) => {{
        const values = splitCsvLine(line);
        const row = {{}};
        headers.forEach((header, index) => {{
          row[header] = values[index] || '';
        }});
        return row;
      }});
      return {{ headers, rows: dataRows }};
    }}

    function parseIntLike(value) {{
      if (value === null || value === undefined) return null;
      const text = String(value).replace(/[^\d-]/g, '');
      if (!text || text === '-') return null;
      const parsed = Number.parseInt(text, 10);
      return Number.isNaN(parsed) ? null : parsed;
    }}

    function formatBytesHuman(value) {{
      if (value === null || value === undefined) return '—';
      const units = ['bytes', 'KB', 'MB', 'GB', 'TB'];
      let size = Number(value);
      let unit = units[0];
      for (const currentUnit of units) {{
        unit = currentUnit;
        if (size < 1024 || currentUnit === units[units.length - 1]) break;
        size /= 1024;
      }}
      return unit === 'bytes' ? `${{Number(value).toLocaleString('en-US')}} bytes` : `${{size.toFixed(1)}} ${{unit}}`;
    }}

    function parseAnalysisSections(analysisText) {{
      const parsed = {{ status: '', summary: '', source: '', destination: '', application: '', bytes: '', reason: '' }};
      analysisText.split(/\r?\n/).forEach((rawLine) => {{
        const line = rawLine.trim();
        if (!line) return;
        const normalized = line.replace(/^[\-\s]+/, '');
        if (normalized.startsWith('異常狀態：')) parsed.status = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('摘要：')) parsed.summary = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('來源：')) parsed.source = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('目的地：')) parsed.destination = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('應用程式：')) parsed.application = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('位元組：')) parsed.bytes = normalized.split('：', 2)[1].trim();
        else if (normalized.startsWith('原因：')) parsed.reason = normalized.split('：', 2)[1].trim();
      }});
      return parsed;
    }}

    function summarizeRows(rows) {{
      const sourceSet = new Set();
      const destinationSet = new Set();
      const byteValues = [];
      rows.forEach((row) => {{
        const source = (row['來源位址'] || '').trim();
        const destination = (row['目的地位址'] || '').trim();
        if (source) sourceSet.add(source);
        if (destination) destinationSet.add(destination);
        const byteValue = parseIntLike(row['位元組']);
        if (byteValue !== null) byteValues.push(byteValue);
      }});
      const maxBytes = byteValues.length ? Math.max(...byteValues) : 0;
      const totalBytes = byteValues.reduce((sum, value) => sum + value, 0);
      return {{
        total_rows: rows.length,
        unique_sources: sourceSet.size,
        unique_destinations: destinationSet.size,
        max_bytes_human: formatBytesHuman(maxBytes),
        max_bytes_raw: `${{maxBytes.toLocaleString('en-US')}} bytes`,
        total_bytes_human: formatBytesHuman(totalBytes),
        total_bytes_raw: `${{totalBytes.toLocaleString('en-US')}} bytes`,
      }};
    }}

    function enrichRowsForDisplay(headers, rows) {{
      const displayHeaders = headers.map((header) => header === '位元組' ? '傳輸量' : header);
      const displayRows = rows.map((row) => {{
        const displayRow = {{ ...row }};
        if (Object.prototype.hasOwnProperty.call(row, '位元組')) {{
          const byteValue = parseIntLike(row['位元組']);
          displayRow['傳輸量'] = byteValue === null ? (row['位元組'] || '') : `${{formatBytesHuman(byteValue)}} (${{byteValue.toLocaleString('en-US')}} bytes)`;
          delete displayRow['位元組'];
        }}
        return displayRow;
      }});
      return {{ displayHeaders, displayRows }};
    }}

    function deriveManualLabel(csvFile, jsonFile, analysisPayload) {{
      const candidates = [analysisPayload.date, analysisPayload.report_date, analysisPayload.date_key, csvFile.name, jsonFile.name].filter(Boolean);
      const matched = candidates.map((value) => String(value).match(/(\d{{8}})/)).find(Boolean);
      if (matched) {{
        const dateKey = matched[1];
        return {{ date: `manual-${{dateKey}}`, label: `${{dateKey.slice(0, 4)}}-${{dateKey.slice(4, 6)}}-${{dateKey.slice(6, 8)}}` }};
      }}
      return {{ date: `manual-${{csvFile.name}}-${{jsonFile.name}}`, label: '手動載入' }};
    }}

    function buildManualReport(csvFile, jsonFile, csvText, jsonText) {{
      const parsedCsv = parseCsvText(csvText);
      const analysisPayload = JSON.parse(jsonText);
      if (!analysisPayload || typeof analysisPayload !== 'object' || Array.isArray(analysisPayload)) {{
        throw new Error('AI JSON 必須是物件');
      }}
      const analysisText = String(analysisPayload.analysis || '');
      const analysisSections = parseAnalysisSections(analysisText);
      const analysisBytesValue = parseIntLike(analysisSections.bytes);
      analysisSections.bytes_human = analysisBytesValue === null ? '' : formatBytesHuman(analysisBytesValue);
      analysisSections.bytes_raw = analysisBytesValue === null ? (analysisSections.bytes || '') : `${{analysisBytesValue.toLocaleString('en-US')}} bytes`;
      const {{ displayHeaders, displayRows }} = enrichRowsForDisplay(parsedCsv.headers, parsedCsv.rows);
      const labelInfo = deriveManualLabel(csvFile, jsonFile, analysisPayload);
      return {{
        date: labelInfo.date,
        label: labelInfo.label,
        data_dir: 'browser-upload',
        csv_path: csvFile.name,
        analysis_path: jsonFile.name,
        headers: displayHeaders,
        rows: displayRows,
        summary: summarizeRows(parsedCsv.rows),
        analysis_text: analysisText,
        analysis_sections: analysisSections,
        source: 'manual-upload',
      }};
    }}

    async function loadSelectedFiles() {{
      const csvFile = csvFileInput.files[0];
      const jsonFile = jsonFileInput.files[0];
      if (!csvFile || !jsonFile) {{
        showError('請先各選 1 個 CSV 與 1 個 AI JSON。');
        return;
      }}
      try {{
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        const [csvText, jsonText] = await Promise.all([readFileAsText(csvFile), readFileAsText(jsonFile)]);
        appState.current = buildManualReport(csvFile, jsonFile, csvText, jsonText);
        appState.selectedRowIndex = null;
        renderCurrentReport();
      }} catch (error) {{
        showError(error.message || '載入選擇檔案失敗');
      }}
    }}

    function reviewStorageKey() {{
      return appState.current ? `pa450-review::${{appState.current.date}}` : 'pa450-review';
    }}

    function saveReviewState() {{
      if (!appState.current) return;
      localStorage.setItem(reviewStorageKey(), JSON.stringify({{
        reviewStatus: reviewStatus.value,
        reviewNote: reviewNote.value,
      }}));
    }}

    function loadReviewState() {{
      reviewStatus.value = '';
      reviewNote.value = '';
      if (!appState.current) return;
      try {{
        const raw = localStorage.getItem(reviewStorageKey());
        if (!raw) return;
        const saved = JSON.parse(raw);
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
      }} catch (_error) {{}}
    }}

    function uniqueValues(field) {{
      if (!appState.current) return [];
      return [...new Set(appState.current.rows.map((row) => (row[field] || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
    }}

    function fillSelect(selectEl, field, label) {{
      clearNode(selectEl);
      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = `全部${{label}}`;
      selectEl.appendChild(defaultOption);
      uniqueValues(field).forEach((value) => {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        selectEl.appendChild(option);
      }});
    }}

    function renderSidebar() {{
      clearNode(reportList);
      appState.reports.forEach((report) => {{
        const btn = document.createElement('button');
        btn.className = 'report-item';
        if (appState.current && report.date === appState.current.date) btn.classList.add('active');
        btn.appendChild(createTextNode('div', report.label, 'report-date'));
        btn.appendChild(createTextNode('div', report.summary, 'subtle report-summary'));
        btn.addEventListener('click', () => loadReport(report.date));
        reportList.appendChild(btn);
      }});
      if (!appState.reports.length) {{
        setEmptyMessage(reportList, '目前找不到任何每日報告。');
      }}
    }}

    function renderSummary() {{
      clearNode(summaryGrid);
      const summary = appState.current.summary;
      const cards = [
        ['報告日期', appState.current.label, appState.current.date],
        ['總資料筆數', String(summary.total_rows), ''],
        ['來源 IP 數', String(summary.unique_sources), ''],
        ['目的地數', String(summary.unique_destinations), ''],
        ['最大傳輸量', summary.max_bytes_human, summary.max_bytes_raw],
        ['總傳輸量', summary.total_bytes_human, summary.total_bytes_raw],
      ];
      cards.forEach(([label, value, secondary]) => {{
        const card = document.createElement('div');
        card.className = 'card';
        card.appendChild(createTextNode('div', label, 'detail-key'));
        card.appendChild(createTextNode('div', value, 'metric'));
        if (secondary) card.appendChild(createTextNode('div', secondary, 'subtle'));
        summaryGrid.appendChild(card);
      }});
    }}

    function renderAnalysis() {{
      clearNode(analysisCard);
      const a = appState.current.analysis_sections;
      [
        ['異常狀態', a.status || '資料不足，需人工確認', ''],
        ['摘要', a.summary || appState.current.analysis_text || '資料不足，需人工確認', ''],
        ['來源', a.source || '', ''],
        ['目的地', a.destination || '', ''],
        ['應用程式', a.application || '', ''],
        ['傳輸量', a.bytes_human || a.bytes || '—', a.bytes_raw || ''],
        ['原因', a.reason || '', ''],
      ].forEach(([key, value, secondary]) => analysisCard.appendChild(createDetailRow(key, value, secondary)));
    }}

    function normalizeMatchText(value) {{
      return String(value || '').trim().toLowerCase();
    }}

    function getRowBytesValue(row) {{
      const displayValue = String(row['傳輸量'] || row['位元組'] || '');
      const bytesMatch = displayValue.match(/\(([\d,]+) bytes\)/i);
      if (bytesMatch) return parseIntLike(bytesMatch[1]);
      return parseIntLike(displayValue);
    }}

    function buildRowReportMatch(row) {{
      const analysis = appState.current.analysis_sections || {{}};
      const evidence = [];
      const matchedFields = [];
      const mismatchedFields = [];

      const source = row['來源位址'] || '';
      const destination = row['目的地位址'] || '';
      const application = row['應用程式'] || '';
      const rowBytes = getRowBytesValue(row);
      const analysisBytes = parseIntLike(analysis.bytes);

      const comparisons = [
        ['來源', source, analysis.source],
        ['目的地', destination, analysis.destination],
        ['應用程式', application, analysis.application],
      ];

      comparisons.forEach(([label, rowValue, analysisValue]) => {{
        const normalizedRow = normalizeMatchText(rowValue);
        const normalizedAnalysis = normalizeMatchText(analysisValue);
        if (!normalizedAnalysis) {{
          evidence.push(`${{label}}：AI 報告未提供可比對值；此列為「${{rowValue || '—'}}」。`);
          return;
        }}
        if (normalizedRow && normalizedRow === normalizedAnalysis) {{
          matchedFields.push(label);
          evidence.push(`${{label}}吻合：${{rowValue}}`);
        }} else {{
          mismatchedFields.push(label);
          evidence.push(`${{label}}不一致：此列是「${{rowValue || '—'}}」，AI 報告寫的是「${{analysisValue}}」。`);
        }}
      }});

      if (analysisBytes === null) {{
        evidence.push(`傳輸量：AI 報告未提供可比對位元組；此列為 ${{row['傳輸量'] || '—'}}。`);
      }} else if (rowBytes !== null && rowBytes === analysisBytes) {{
        matchedFields.push('傳輸量');
        evidence.push(`傳輸量吻合：${{row['傳輸量'] || formatBytesHuman(rowBytes)}}`);
      }} else {{
        mismatchedFields.push('傳輸量');
        evidence.push(`傳輸量不一致：此列為 ${{row['傳輸量'] || '—'}}，AI 報告寫的是 ${{analysis.bytes_human || analysis.bytes || '—'}}。`);
      }}

      let matchLevel = '未明確對應';
      let summary = '這列沒有和 AI 報告中的來源 / 目的地 / 應用程式 / 傳輸量形成足夠強的對應，請人工再確認。';
      if (matchedFields.length >= 3) {{
        matchLevel = '高度吻合';
        summary = analysis.summary || '這列和 AI 報告描述高度吻合，可視為該報告主要指向的明細列。';
      }} else if (matchedFields.length >= 1) {{
        matchLevel = '部分吻合';
        summary = analysis.summary || '這列和 AI 報告部分欄位對得上，但還不足以完全確認就是同一筆。';
      }}

      let reasonText = analysis.reason || 'AI 報告沒有額外原因文字。';
      if (!matchedFields.length) {{
        reasonText = '目前只找到弱關聯或無明確關聯，因此不直接把整份 AI 報告視為這列的結論。';
      }}

      return {{
        matchLevel,
        summary,
        reasonText,
        matchedFields,
        mismatchedFields,
        evidence,
      }};
    }}

    function renderRowReport(row) {{
      clearNode(rowReportDetail);
      rowReportDetail.className = 'detail-list';
      const rowMatch = buildRowReportMatch(row);
      rowReportDetail.appendChild(createDetailRow('比對結果', rowMatch.matchLevel, rowMatch.matchedFields.length ? `吻合欄位：${{rowMatch.matchedFields.join('、')}}` : '目前沒有明確吻合欄位'));
      rowReportDetail.appendChild(createDetailRow('列級摘要', rowMatch.summary));
      rowReportDetail.appendChild(createDetailRow('列級原因 / 判讀', rowMatch.reasonText, rowMatch.mismatchedFields.length ? `未完全吻合：${{rowMatch.mismatchedFields.join('、')}}` : ''));
      rowReportDetail.appendChild(createPreformattedDetailRow('證據比對', rowMatch.evidence.join('\n')));
    }}

    function renderHead() {{
      clearNode(tableHead);
      appState.current.headers.forEach((header) => {{
        const th = document.createElement('th');
        th.textContent = header;
        tableHead.appendChild(th);
      }});
    }}

    function matchesFilters(row) {{
      const search = searchInput.value.trim().toLowerCase();
      const source = sourceFilter.value;
      const app = appFilter.value;
      const textBlob = appState.current.headers.map((header) => row[header] || '').join(' ').toLowerCase();
      if (search && !textBlob.includes(search)) return false;
      if (source && (row['來源位址'] || '') !== source) return false;
      if (app && (row['應用程式'] || '') !== app) return false;
      return true;
    }}

    function renderDetails(row) {{
      clearNode(rowDetail);
      rowDetail.className = 'detail-list';
      appState.current.headers.forEach((header) => {{
        rowDetail.appendChild(createDetailRow(header, row[header] || '—'));
      }});
      renderRowReport(row);
    }}

    function renderRows() {{
      clearNode(tableBody);
      const filtered = appState.current.rows.filter(matchesFilters);
      filtered.forEach((row) => {{
        const tr = document.createElement('tr');
        const originalIndex = appState.current.rows.indexOf(row);
        if (appState.selectedRowIndex === originalIndex) tr.classList.add('is-selected');
        tr.addEventListener('click', () => {{
          appState.selectedRowIndex = originalIndex;
          renderRows();
          renderDetails(row);
        }});
        appState.current.headers.forEach((header) => {{
          const td = document.createElement('td');
          td.textContent = row[header] || '';
          tr.appendChild(td);
        }});
        tableBody.appendChild(tr);
      }});
      if (!filtered.length) {{
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = appState.current.headers.length;
        td.textContent = '沒有符合條件的 CSV 列。';
        tr.appendChild(td);
        tableBody.appendChild(tr);
      }}
    }}

    function renderCurrentReport() {{
      if (!appState.current) return;
      clearError();
      loading.hidden = true;
      reportApp.hidden = false;
      appState.selectedRowIndex = null;
      setEmptyMessage(rowDetail, '尚未選取資料列。');
      setEmptyMessage(rowReportDetail, '選取資料列後，這裡會顯示與該列最相關的 AI 報告與比對證據。');
      renderSidebar();
      renderSummary();
      renderAnalysis();
      renderHead();
      fillSelect(sourceFilter, '來源位址', '來源 IP');
      fillSelect(appFilter, '應用程式', '應用程式');
      loadReviewState();
      renderRows();
    }}

    async function loadReport(date) {{
      persistDataDir();
      const response = await fetch(apiUrl('/api/reports/' + encodeURIComponent(date)));
      if (!response.ok) throw new Error(`載入報告失敗：${{response.status}}`);
      appState.current = await response.json();
      renderCurrentReport();
    }}

    async function bootstrap() {{
      try {{
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        appState.current = null;
        appState.selectedRowIndex = null;
        persistDataDir();
        const response = await fetch(apiUrl('/api/reports'));
        if (!response.ok) throw new Error(`載入報告列表失敗：${{response.status}}`);
        const payload = await response.json();
        appState.reports = payload.reports || [];
        renderSidebar();
        if (!appState.reports.length) {{
          loading.hidden = true;
          setEmptyMessage(reportList, `此 base 找不到成對的 CSV/JSON：${{currentDataDir()}}`);
          return;
        }}
        await loadReport(appState.reports[0].date);
      }} catch (error) {{
        showError(error.message || '載入失敗');
      }}
    }}

    dataDirInput.value = localStorage.getItem('pa450-data-dir') || DEFAULT_DATA_DIR;
    reloadDataDir.addEventListener('click', bootstrap);
    csvFileInput.addEventListener('change', updateSelectedFileNames);
    jsonFileInput.addEventListener('change', updateSelectedFileNames);
    loadSelectedFilesButton.addEventListener('click', loadSelectedFiles);
    dataDirInput.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter') bootstrap();
    }});
    sidebarToggle.addEventListener('click', () => setSidebarCollapsed(!appShell.classList.contains('sidebar-collapsed')));
    setSidebarCollapsed(localStorage.getItem('pa450-sidebar-collapsed') === '1');
    searchInput.addEventListener('input', renderRows);
    sourceFilter.addEventListener('change', renderRows);
    appFilter.addEventListener('change', renderRows);
    reviewStatus.addEventListener('change', saveReviewState);
    reviewNote.addEventListener('input', saveReviewState);
    updateSelectedFileNames();
    bootstrap();
  </script>
</body>
</html>
"""

def format_bytes_human(value: int | None) -> str:
    if value is None:
        return "—"
    units = ["bytes", "KB", "MB", "GB", "TB"]
    size = float(value)
    unit = units[0]
    for current_unit in units:
        unit = current_unit
        if size < 1024 or current_unit == units[-1]:
            break
        size /= 1024
    if unit == "bytes":
        return f"{value:,} bytes"
    return f"{size:.1f} {unit}"


def parse_analysis_sections(analysis_text: str) -> dict[str, str]:
    parsed = {
        "status": "",
        "summary": "",
        "source": "",
        "destination": "",
        "application": "",
        "bytes": "",
        "reason": "",
    }
    for raw_line in analysis_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lstrip("- ")
        if normalized.startswith("異常狀態："):
            parsed["status"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("摘要："):
            parsed["summary"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("來源："):
            parsed["source"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("目的地："):
            parsed["destination"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("應用程式："):
            parsed["application"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("位元組："):
            parsed["bytes"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("原因："):
            parsed["reason"] = normalized.split("：", 1)[1].strip()
    return parsed


def load_csv_rows(csv_path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [{key: value or "" for key, value in row.items()} for row in reader]
    if not headers:
        raise ValueError(f"CSV file has no headers: {csv_path}")
    return headers, rows


def load_analysis_payload(analysis_json_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(analysis_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Analysis JSON must be an object: {analysis_json_path}")
    return payload


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    source_counter = Counter(row.get("來源位址", "").strip() for row in rows if row.get("來源位址", "").strip())
    destination_counter = Counter(row.get("目的地位址", "").strip() for row in rows if row.get("目的地位址", "").strip())
    byte_values = [parse_int(row.get("位元組")) for row in rows]
    valid_bytes = [value for value in byte_values if value is not None]
    max_bytes = max(valid_bytes, default=0)
    total_bytes = sum(valid_bytes)
    top_source_value, top_source_count = source_counter.most_common(1)[0] if source_counter else ("-", 0)
    return {
        "total_rows": len(rows),
        "unique_sources": len(source_counter),
        "unique_destinations": len(destination_counter),
        "max_bytes_human": format_bytes_human(max_bytes),
        "max_bytes_raw": f"{max_bytes:,} bytes",
        "total_bytes_human": format_bytes_human(total_bytes),
        "total_bytes_raw": f"{total_bytes:,} bytes",
        "top_source": {"value": top_source_value, "row_count": top_source_count},
    }


def enrich_rows_for_display(headers: list[str], rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    display_headers = ["傳輸量" if header == "位元組" else header for header in headers]
    display_rows: list[dict[str, str]] = []
    for row in rows:
        display_row = dict(row)
        if "位元組" in row:
            byte_value = parse_int(row.get("位元組"))
            display_row["傳輸量"] = row.get("位元組", "") if byte_value is None else f"{format_bytes_human(byte_value)} ({byte_value:,} bytes)"
            display_row.pop("位元組", None)
        display_rows.append(display_row)
    return display_headers, display_rows


def _report_date_label(date_key: str) -> str:
    return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"


def _validated_date_key(date_key: str) -> str:
    if not DATE_KEY_RE.fullmatch(date_key):
        raise ValueError(f"Invalid report date: {date_key}")
    return date_key


def _normalized_base(data_dir: str | Path) -> Path:
    return Path(data_dir).expanduser()


def _date_key_from_ancestors(path: Path) -> str | None:
    for part in reversed(path.parent.parts):
        if DATE_KEY_RE.fullmatch(part):
            return part
    return None


def _csv_date_key(path: Path) -> str | None:
    name = path.name
    if name.endswith("_report.csv"):
        date_key = path.stem.removesuffix("_report")
        if DATE_KEY_RE.fullmatch(date_key):
            return date_key
    if name == "report.csv":
        return _date_key_from_ancestors(path)
    return None


def _analysis_date_key(path: Path) -> str | None:
    if path.suffix.lower() != ".json":
        return None
    if DATE_KEY_RE.fullmatch(path.stem):
        return path.stem
    if path.name == "analysis.json":
        return _date_key_from_ancestors(path)
    return None


def _iter_files(base: Path):
    if not base.exists() or not base.is_dir():
        return
    for root, _dirs, files in os.walk(base):
        for filename in files:
            yield Path(root) / filename


def _candidate_score(base: Path, path: Path) -> tuple[int, int, str]:
    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = path
    # 越靠近 base 越優先；同層級時以較新的檔案優先。
    try:
        mtime = int(path.stat().st_mtime)
    except OSError:
        mtime = 0
    return (len(relative.parts), -mtime, str(relative))


def _set_best_candidate(report_map: dict[str, dict[str, Path]], date_key: str, kind: str, path: Path, base: Path) -> None:
    current = report_map.setdefault(date_key, {}).get(kind)
    if current is None or _candidate_score(base, path) < _candidate_score(base, current):
        report_map[date_key][kind] = path


def _relative_label(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def build_report_map(data_dir: str | Path) -> dict[str, dict[str, Path]]:
    base = _normalized_base(data_dir)
    report_map: dict[str, dict[str, Path]] = {}

    for path in _iter_files(base):
        if path.suffix.lower() == ".csv":
            date_key = _csv_date_key(path)
            if date_key:
                _set_best_candidate(report_map, date_key, "csv", path, base)
            continue

        if path.suffix.lower() == ".json":
            date_key = _analysis_date_key(path)
            if date_key:
                _set_best_candidate(report_map, date_key, "analysis", path, base)

    return report_map


def discover_reports(data_dir: str | Path) -> list[dict[str, str]]:
    base = _normalized_base(data_dir)
    report_map = build_report_map(base)

    reports: list[dict[str, str]] = []
    for date_key, paths in sorted(report_map.items(), reverse=True):
        if "csv" not in paths or "analysis" not in paths:
            continue
        reports.append({
            "date": date_key,
            "label": _report_date_label(date_key),
            "summary": f"{_relative_label(base, paths['csv'])} · {_relative_label(base, paths['analysis'])}",
            "csv_path": str(paths["csv"]),
            "analysis_path": str(paths["analysis"]),
        })
    return reports


def locate_report_paths(data_dir: str | Path, date_key: str) -> tuple[Path, Path]:
    base = _normalized_base(data_dir)
    report_map = build_report_map(base)
    paths = report_map.get(date_key, {})
    csv_path = paths.get("csv")
    json_path = paths.get("analysis")
    if not csv_path or not json_path:
        raise FileNotFoundError(f"Report bundle not found for date: {date_key}")
    return csv_path, json_path

def load_report_bundle(data_dir: str | Path, date_key: str) -> dict[str, Any]:
    date_key = _validated_date_key(date_key)
    csv_path, json_path = locate_report_paths(data_dir, date_key)

    headers, rows = load_csv_rows(csv_path)
    analysis_payload = load_analysis_payload(json_path)
    analysis_text = str(analysis_payload.get("analysis") or "")
    display_headers, display_rows = enrich_rows_for_display(headers, rows)
    analysis_sections = parse_analysis_sections(analysis_text)
    analysis_bytes_value = parse_int(analysis_sections.get("bytes"))
    analysis_sections["bytes_human"] = format_bytes_human(analysis_bytes_value) if analysis_bytes_value is not None else ""
    analysis_sections["bytes_raw"] = f"{analysis_bytes_value:,} bytes" if analysis_bytes_value is not None else analysis_sections.get("bytes", "")

    return {
        "date": date_key,
        "label": _report_date_label(date_key),
        "data_dir": str(_normalized_base(data_dir)),
        "csv_path": str(csv_path),
        "analysis_path": str(json_path),
        "headers": display_headers,
        "rows": display_rows,
        "summary": summarize_rows(rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
    }


class ReportUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args: Any, data_dir: str, **kwargs: Any) -> None:
        self.default_data_dir = _normalized_base(data_dir)
        super().__init__(*args, **kwargs)

    def _request_data_dir(self, parsed) -> Path:
        params = parse_qs(parsed.query)
        requested = (params.get("data_dir") or [""])[0].strip()
        return _normalized_base(requested) if requested else self.default_data_dir

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        data_dir = self._request_data_dir(parsed)
        if parsed.path == "/":
            self._send_html(INDEX_HTML_TEMPLATE.format(
                title=escape(DASHBOARD_TITLE),
                data_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
            ))
            return
        if parsed.path == "/api/reports":
            self._send_json({"data_dir": str(data_dir), "reports": discover_reports(data_dir)})
            return
        if parsed.path.startswith("/api/reports/"):
            date_key = unquote(parsed.path.removeprefix("/api/reports/"))
            try:
                payload = load_report_bundle(data_dir, date_key)
            except ValueError:
                self._send_json({"error": "Invalid report date"}, status=HTTPStatus.BAD_REQUEST)
                return
            except FileNotFoundError:
                self._send_json({"error": "Report not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def open_browser_when_ready(port: int) -> None:
    webbrowser.open(f"http://{LOCALHOST}:{port}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a localhost-only PA450 daily review UI")
    parser.add_argument("--data-dir", default=Path("output"), type=Path, help="Folder containing daily CSV/JSON results")
    parser.add_argument("--port", default=8765, type=int, help="Localhost port to bind the UI server")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handler = partial(ReportUIHandler, data_dir=str(args.data_dir))
    server = ThreadingHTTPServer((LOCALHOST, args.port), handler)
    print(f"PA450 Daily Review UI running at http://{LOCALHOST}:{args.port}")
    if not args.no_browser:
        threading.Timer(0.6, open_browser_when_ready, args=(args.port,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
