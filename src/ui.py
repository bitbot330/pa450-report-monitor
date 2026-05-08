from __future__ import annotations

import argparse
import csv
import errno
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
    .folder-picker {{ display: grid; gap: 10px; margin-top: 14px; }}
    .folder-picker-actions {{ display: grid; gap: 10px; }}
    .folder-row {{ display: grid; gap: 6px; }}
    .folder-button, .folder-load-button {{ width: 100%; border-radius: 10px; border: 1px solid var(--line); background: #0d1525; color: var(--text); padding: 10px 12px; cursor: pointer; text-align: left; }}
    .folder-load-button {{ text-align: center; font-weight: 700; }}
    .folder-button:hover, .folder-load-button:hover {{ border-color: var(--accent); background: var(--accent-bg); }}
    .folder-path {{ min-height: 18px; word-break: break-all; color: var(--muted); font-size: 12px; line-height: 1.35; }}
    .app.sidebar-collapsed .sidebar {{ padding: 16px 12px; }}
    .app.sidebar-collapsed .sidebar-top {{ justify-content: center; }}
    .app.sidebar-collapsed .brand, .app.sidebar-collapsed .folder-picker, .app.sidebar-collapsed .report-item .report-summary {{ display: none; }}
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
    select:disabled, textarea:disabled {{ opacity: 0.55; cursor: not-allowed; }}
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
            <div class="folder-picker">
              <div class="detail-key">載入資料夾</div>
              <div class="folder-picker-actions">
                <div class="folder-row">
                  <button id="selectCsvFolder" class="folder-button" type="button">選 CSV load folder</button>
                  <div id="csvFolderPath" class="folder-path">output/</div>
                </div>
                <div class="folder-row">
                  <button id="selectAnalysisFolder" class="folder-button" type="button">選 AI JSON load folder</button>
                  <div id="analysisFolderPath" class="folder-path">output/</div>
                </div>
                <div class="folder-row">
                  <button id="selectReviewFolder" class="folder-button" type="button">選回報 load folder</button>
                  <div id="reviewFolderPath" class="folder-path">output/</div>
                </div>
                <button id="reloadFolders" class="folder-load-button" type="button">讀取資料夾</button>
              </div>
              <p class="subtle">預設皆為 output/。按按鈕用資料夾選擇器挑選，不用手打路徑。</p>
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
              <div class="review-in-detail">
                <div class="panel-title"><h3>報告回報</h3><span class="pill">report_YYYYMMDD.md</span></div>
                <div class="detail-key">回報狀態</div>
                <select id="reviewStatus">
                  <option value="">未設定</option>
                  <option value="normal">整體正常</option>
                  <option value="follow-up">有異常需追蹤</option>
                  <option value="ai-adjustment">AI 判讀需調整</option>
                </select>
                <div class="detail-key" style="margin-top:12px;">備註</div>
                <textarea id="reviewNote" placeholder="請先點選 CSV 表格中的單筆資料列，再填寫這筆的回報。"></textarea>
                <button id="reviewSaveButton" type="button" style="margin-top:12px; width:100%; border-radius:10px; border:1px solid var(--line); background:#0d1525; color:var(--text); padding:10px 12px; cursor:pointer; font-weight:700;">儲存</button>
              </div>
            </article>
          </aside>
        </section>
      </div>
    </main>
  </div>

  <script>
    const DEFAULT_CSV_DIR = {csv_dir_json};
    const DEFAULT_ANALYSIS_DIR = {analysis_dir_json};
    const DEFAULT_REVIEW_DIR = {review_dir_json};
    const appState = {{ reports: [], current: null, selectedRowIndex: null }};
    const appShell = document.getElementById('appShell');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const selectCsvFolder = document.getElementById('selectCsvFolder');
    const selectAnalysisFolder = document.getElementById('selectAnalysisFolder');
    const selectReviewFolder = document.getElementById('selectReviewFolder');
    const csvFolderPath = document.getElementById('csvFolderPath');
    const analysisFolderPath = document.getElementById('analysisFolderPath');
    const reviewFolderPath = document.getElementById('reviewFolderPath');
    const reloadFolders = document.getElementById('reloadFolders');
    const folderState = {{
      csv: localStorage.getItem('pa450-csv-dir') || DEFAULT_CSV_DIR,
      analysis: localStorage.getItem('pa450-analysis-dir') || DEFAULT_ANALYSIS_DIR,
      review: localStorage.getItem('pa450-review-dir') || DEFAULT_REVIEW_DIR,
    }};
    const folderLabels = {{
      csv: csvFolderPath,
      analysis: analysisFolderPath,
      review: reviewFolderPath,
    }};
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
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewNote = document.getElementById('reviewNote');
    const reviewSaveButton = document.getElementById('reviewSaveButton');

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

    function setFolderPath(kind, path) {{
      folderState[kind] = path || 'output';
      if (folderLabels[kind]) folderLabels[kind].textContent = folderState[kind];
      persistFolderDirs();
    }}

    function currentCsvDir() {{
      return folderState.csv || DEFAULT_CSV_DIR;
    }}

    function currentAnalysisDir() {{
      return folderState.analysis || DEFAULT_ANALYSIS_DIR;
    }}

    function currentReviewDir() {{
      return folderState.review || DEFAULT_REVIEW_DIR;
    }}

    function apiUrl(path, extraParams = {{}}) {{
      const params = new URLSearchParams();
      params.set('csv_dir', currentCsvDir());
      params.set('analysis_dir', currentAnalysisDir());
      params.set('review_dir', currentReviewDir());
      Object.entries(extraParams).forEach(([key, value]) => params.set(key, value));
      return path + '?' + params.toString();
    }}

    function persistFolderDirs() {{
      localStorage.setItem('pa450-csv-dir', currentCsvDir());
      localStorage.setItem('pa450-analysis-dir', currentAnalysisDir());
      localStorage.setItem('pa450-review-dir', currentReviewDir());
    }}

    async function chooseFolder(kind) {{
      try {{
        clearError();
        const response = await fetch(apiUrl('/api/pick-folder', {{ kind }}));
        if (!response.ok) throw new Error(`選擇資料夾失敗：${{response.status}}`);
        const payload = await response.json();
        if (payload.selected && payload.path) setFolderPath(kind, payload.path);
      }} catch (error) {{
        showError(error.message || '選擇資料夾失敗');
      }}
    }}

    function renderFolderPaths() {{
      setFolderPath('csv', currentCsvDir());
      setFolderPath('analysis', currentAnalysisDir());
      setFolderPath('review', currentReviewDir());
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
      const normalized = csvText.replace(/^\\uFEFF/, '').replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n');
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
        if (char === '\\n' && !inQuotes) {{
          rows.push(current);
          current = '';
          continue;
        }}
        current += char;
      }}
      if (current || normalized.endsWith('\\n')) rows.push(current);
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
      const text = String(value).replace(/[^\\d-]/g, '');
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
      analysisText.split(/\\r?\\n/).forEach((rawLine) => {{
        const line = rawLine.trim();
        if (!line) return;
        const normalized = line.replace(/^[\\-\\s]+/, '');
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
      const matched = candidates.map((value) => String(value).match(/(\\d{{8}})/)).find(Boolean);
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

    function selectedRow() {{
      if (!appState.current || appState.selectedRowIndex === null) return null;
      return appState.current.rows[appState.selectedRowIndex] || null;
    }}

    function canSaveReviewToMarkdown() {{
      return appState.current
        && appState.selectedRowIndex !== null
        && /^\\d{{8}}$/.test(appState.current.date || '')
        && appState.current.source !== 'manual-upload';
    }}

    function rowSummary(row) {{
      const preferredHeaders = ['來源位址', '目的地位址', '應用程式', '傳輸量', '來源使用者', '使用者', '主機名稱'];
      return preferredHeaders
        .filter((header) => row && row[header])
        .map((header) => `${{header}}=${{row[header]}}`)
        .join('；');
    }}

    function setReviewControlsEnabled(enabled) {{
      reviewStatus.disabled = !enabled;
      reviewNote.disabled = !enabled;
      reviewSaveButton.disabled = !enabled || !canSaveReviewToMarkdown();
      if (!enabled) {{
        reviewStatus.value = '';
        reviewNote.value = '';
        reviewNote.placeholder = '請先點選 CSV 表格中的單筆資料列，再填寫這筆的回報。';
      }} else {{
        reviewNote.placeholder = '例如：這筆高流量其實是備份流量，AI 需要學會辨識。';
      }}
    }}

    function draftReviews() {{
      if (!appState.current) return {{}};
      if (!appState.current.draftReviews) appState.current.draftReviews = {{}};
      return appState.current.draftReviews;
    }}

    function buildCurrentReviewPayload() {{
      if (!appState.current) return null;
      if (appState.selectedRowIndex === null) {{
        setReviewControlsEnabled(false);
        return null;
      }}
      const row = selectedRow();
      if (!row) return null;
      return {{
        reviewStatus: reviewStatus.value,
        reviewNote: reviewNote.value,
        rowIndex: appState.selectedRowIndex,
        rowNumber: appState.selectedRowIndex + 1,
        csvLineNumber: appState.selectedRowIndex + 2,
        rowSummary: rowSummary(row),
        rowFields: row,
      }};
    }}

    function updateReviewDraft() {{
      const review = buildCurrentReviewPayload();
      if (!review || !appState.current) return;
      draftReviews()[String(appState.selectedRowIndex)] = review;
    }}

    async function saveReviewState() {{
      const review = buildCurrentReviewPayload();
      if (!review || !appState.current) return;
      if (!appState.current.reviews) appState.current.reviews = {{}};
      appState.current.reviews[String(appState.selectedRowIndex)] = review;
      if (!canSaveReviewToMarkdown()) {{
        return;
      }}
      try {{
        const response = await fetch(apiUrl('/api/reports/' + encodeURIComponent(appState.current.date) + '/review'), {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(review),
        }});
        if (!response.ok) throw new Error(`儲存 report_YYYYMMDD.md 失敗：${{response.status}}`);
        const payload = await response.json();
        if (payload.reviews) appState.current.reviews = payload.reviews;
        delete draftReviews()[String(appState.selectedRowIndex)];
      }} catch (error) {{
        showError(error.message || '儲存 report_YYYYMMDD.md 失敗');
      }}
    }}

    function loadReviewState() {{
      reviewStatus.value = '';
      reviewNote.value = '';
      if (!appState.current || appState.selectedRowIndex === null) {{
        setReviewControlsEnabled(false);
        return;
      }}
      setReviewControlsEnabled(true);
      const rowKey = String(appState.selectedRowIndex);
      const draft = draftReviews()[rowKey];
      if (draft) {{
        reviewStatus.value = draft.reviewStatus || '';
        reviewNote.value = draft.reviewNote || '';
        return;
      }}
      if (canSaveReviewToMarkdown()) {{
        const saved = (appState.current.reviews || {{}})[rowKey] || {{}};
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
        return;
      }}
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
      const rowNumber = appState.selectedRowIndex === null ? 0 : appState.selectedRowIndex + 1;
      if (rowNumber) {{
        rowDetail.appendChild(createDetailRow('單筆識別', `第 ${{rowNumber}} 筆（CSV 第 ${{rowNumber + 1}} 行）`));
      }}
      appState.current.headers.forEach((header) => {{
        rowDetail.appendChild(createDetailRow(header, row[header] || '—'));
      }});
      loadReviewState();
    }}

    function renderRows() {{
      clearNode(tableBody);
      const filtered = appState.current.rows
        .map((row, originalIndex) => ({{ row, originalIndex }}))
        .filter((item) => matchesFilters(item.row));
      filtered.forEach(({{ row, originalIndex }}) => {{
        const tr = document.createElement('tr');
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
      renderSidebar();
      renderSummary();
      renderAnalysis();
      renderHead();
      fillSelect(sourceFilter, '來源位址', '來源 IP');
      fillSelect(appFilter, '應用程式', '應用程式');
      setReviewControlsEnabled(false);
      renderRows();
    }}

    async function loadReport(date) {{
      persistFolderDirs();
      const response = await fetch(apiUrl('/api/reports/' + encodeURIComponent(date)));
      if (!response.ok) throw new Error(`載入報告失敗：${{response.status}}`);
      appState.current = await response.json();
      if (!appState.current.draftReviews) appState.current.draftReviews = {{}};
      renderCurrentReport();
    }}

    async function bootstrap() {{
      try {{
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        appState.current = null;
        appState.selectedRowIndex = null;
        persistFolderDirs();
        const response = await fetch(apiUrl('/api/reports'));
        if (!response.ok) throw new Error(`載入報告列表失敗：${{response.status}}`);
        const payload = await response.json();
        appState.reports = payload.reports || [];
        renderSidebar();
        if (!appState.reports.length) {{
          loading.hidden = true;
          setEmptyMessage(reportList, `找不到成對的 CSV/AI JSON。CSV：${{currentCsvDir()}}；AI JSON：${{currentAnalysisDir()}}`);
          return;
        }}
        await loadReport(appState.reports[0].date);
      }} catch (error) {{
        showError(error.message || '載入失敗');
      }}
    }}

    renderFolderPaths();
    selectCsvFolder.addEventListener('click', () => chooseFolder('csv'));
    selectAnalysisFolder.addEventListener('click', () => chooseFolder('analysis'));
    selectReviewFolder.addEventListener('click', () => chooseFolder('review'));
    reloadFolders.addEventListener('click', bootstrap);
    sidebarToggle.addEventListener('click', () => setSidebarCollapsed(!appShell.classList.contains('sidebar-collapsed')));
    setSidebarCollapsed(localStorage.getItem('pa450-sidebar-collapsed') === '1');
    searchInput.addEventListener('input', renderRows);
    sourceFilter.addEventListener('change', renderRows);
    appFilter.addEventListener('change', renderRows);
    reviewStatus.addEventListener('change', updateReviewDraft);
    reviewNote.addEventListener('input', updateReviewDraft);
    reviewSaveButton.addEventListener('click', saveReviewState);
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


REVIEW_STATUS_LABELS = {
    "": "未設定",
    "normal": "整體正常",
    "follow-up": "有異常需追蹤",
    "ai-adjustment": "AI 判讀需調整",
}


def _report_date_label(date_key: str) -> str:
    return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"


def _review_markdown_path(review_dir: str | Path, date_key: str | None = None) -> Path:
    if date_key is None:
        raise ValueError("date_key is required for review markdown path")
    _validated_date_key(date_key)
    return _normalized_base(review_dir) / f"report_{date_key}.md"


def _split_review_markdown_entries(text: str) -> list[str]:
    entries = [chunk.strip() for chunk in re.split(r"\n\s*---\s*\n", text.strip())]
    return [entry for entry in entries if entry]


def _parse_review_markdown(text: str) -> dict[str, str]:
    note = ""
    marker = "## 備註\n"
    if marker in text:
        note = text.split(marker, 1)[1].lstrip("\n").rstrip("\n")

    row_fields: dict[str, str] = {}
    for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]:
        match = re.search(rf"(?m)^- {re.escape(header)}：\s*(.*)$", text)
        row_fields[header] = match.group(1).strip() if match else ""

    return {
        "reviewStatus": "",
        "reviewNote": note,
        "rowFields": row_fields,
    }


def _minimal_review_markdown_content(review_note: str, row_fields: dict[str, Any] | None = None) -> str:
    row_fields = row_fields or {}
    lines = ["# 報告回報"]
    for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]:
        lines.append(f"- {header}：{str(row_fields.get(header) or '').strip()}")
    lines.append("## 備註")
    note = str(review_note or "").rstrip()
    if note:
        lines.extend(["", note])
    return "\n".join(lines).rstrip() + "\n"


def _review_identity_fields(row_fields: dict[str, Any] | None = None) -> dict[str, str]:
    row_fields = row_fields or {}
    return {
        header: str(row_fields.get(header) or "").strip()
        for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]
    }


def _same_review_identity(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    return _review_identity_fields(left) == _review_identity_fields(right)


def save_review_markdown(
    review_dir: str | Path,
    date_key: str,
    review_status: str,
    review_note: str,
    row_index: int,
    row_fields: dict[str, Any] | None = None,
    row_number: int | None = None,
    csv_line_number: int | None = None,
) -> Path:
    _validated_date_key(date_key)
    int(row_index)
    report_path = _review_markdown_path(review_dir, date_key)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_row_fields = _review_identity_fields(row_fields)
    entry = _minimal_review_markdown_content(review_note, normalized_row_fields).rstrip()
    separator = "\n---\n\n"
    if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
        report_path.write_text(entry + "\n", encoding="utf-8")
        return report_path

    existing_entries = [
        _parse_review_markdown(existing_entry)
        for existing_entry in _split_review_markdown_entries(report_path.read_text(encoding="utf-8"))
    ]
    replacement_index = next(
        (index for index, existing_entry in enumerate(existing_entries) if _same_review_identity(existing_entry.get("rowFields"), normalized_row_fields)),
        None,
    )
    rendered_entries = [
        _minimal_review_markdown_content(
            str(entry_payload.get("reviewNote") or ""),
            _review_identity_fields(entry_payload.get("rowFields") or {}),
        ).rstrip()
        for entry_payload in existing_entries
    ]
    if replacement_index is None:
        rendered_entries.append(entry)
    else:
        rendered_entries[replacement_index] = entry
    report_path.write_text(separator.join(rendered_entries) + "\n", encoding="utf-8")
    return report_path


def load_review_markdown(
    review_dir: str | Path,
    date_key: str,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    _validated_date_key(date_key)
    report_path = _review_markdown_path(review_dir, date_key)
    if not report_path.exists():
        return {}
    parsed_entries = [_parse_review_markdown(entry) for entry in _split_review_markdown_entries(report_path.read_text(encoding="utf-8"))]
    if not rows:
        return {
            str(index): {
                **entry,
                "rowIndex": index,
                "rowNumber": index + 1,
                "csvLineNumber": index + 2,
            }
            for index, entry in enumerate(parsed_entries)
        }

    reviews: dict[str, dict[str, Any]] = {}
    used_row_indexes: set[int] = set()
    tracked_headers = ["來源位址", "目的地位址", "應用程式", "傳輸量"]
    for entry in parsed_entries:
        matched_index: int | None = None
        entry_fields = entry.get("rowFields") or {}
        for index, row in enumerate(rows):
            if index in used_row_indexes:
                continue
            if all(str(row.get(header) or "").strip() == str(entry_fields.get(header) or "").strip() for header in tracked_headers):
                matched_index = index
                break
        if matched_index is None:
            continue
        used_row_indexes.add(matched_index)
        reviews[str(matched_index)] = {
            **entry,
            "rowIndex": matched_index,
            "rowNumber": matched_index + 1,
            "csvLineNumber": matched_index + 2,
        }
    return reviews


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


def build_report_map(csv_dir: str | Path, analysis_dir: str | Path) -> dict[str, dict[str, Path]]:
    csv_base = _normalized_base(csv_dir)
    analysis_base = _normalized_base(analysis_dir)
    report_map: dict[str, dict[str, Path]] = {}

    for path in _iter_files(csv_base):
        if path.suffix.lower() != ".csv":
            continue
        date_key = _csv_date_key(path)
        if date_key:
            _set_best_candidate(report_map, date_key, "csv", path, csv_base)

    for path in _iter_files(analysis_base):
        if path.suffix.lower() != ".json":
            continue
        date_key = _analysis_date_key(path)
        if date_key:
            _set_best_candidate(report_map, date_key, "analysis", path, analysis_base)

    return report_map


def discover_reports(csv_dir: str | Path, analysis_dir: str | Path) -> list[dict[str, str]]:
    csv_base = _normalized_base(csv_dir)
    analysis_base = _normalized_base(analysis_dir)
    report_map = build_report_map(csv_base, analysis_base)

    reports: list[dict[str, str]] = []
    for date_key, paths in sorted(report_map.items(), reverse=True):
        if "csv" not in paths or "analysis" not in paths:
            continue
        reports.append({
            "date": date_key,
            "label": _report_date_label(date_key),
            "summary": f"CSV: {_relative_label(csv_base, paths['csv'])} · AI: {_relative_label(analysis_base, paths['analysis'])}",
            "csv_path": str(paths["csv"]),
            "analysis_path": str(paths["analysis"]),
        })
    return reports


def locate_report_paths(csv_dir: str | Path, analysis_dir: str | Path, date_key: str) -> tuple[Path, Path]:
    report_map = build_report_map(csv_dir, analysis_dir)
    paths = report_map.get(date_key, {})
    csv_path = paths.get("csv")
    json_path = paths.get("analysis")
    if not csv_path or not json_path:
        raise FileNotFoundError(f"Report bundle not found for date: {date_key}")
    return csv_path, json_path


def select_folder_dialog(initial_dir: str | Path) -> str | None:
    initial_path = _normalized_base(initial_dir)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(f"Cannot open folder picker because tkinter is unavailable: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        selected = filedialog.askdirectory(
            parent=root,
            initialdir=str(initial_path if initial_path.exists() else Path.cwd()),
            title="選擇資料夾",
            mustexist=False,
        )
    finally:
        root.destroy()
    return selected or None


def load_report_bundle(csv_dir: str | Path, analysis_dir: str | Path, review_dir: str | Path, date_key: str) -> dict[str, Any]:
    date_key = _validated_date_key(date_key)
    csv_path, json_path = locate_report_paths(csv_dir, analysis_dir, date_key)

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
        "csv_dir": str(_normalized_base(csv_dir)),
        "analysis_dir": str(_normalized_base(analysis_dir)),
        "review_dir": str(_normalized_base(review_dir)),
        "csv_path": str(csv_path),
        "analysis_path": str(json_path),
        "headers": display_headers,
        "rows": display_rows,
        "summary": summarize_rows(rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
        "reviews": load_review_markdown(review_dir, date_key, display_rows),
    }


class ReportUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args: Any, data_dir: str, **kwargs: Any) -> None:
        self.default_data_dir = _normalized_base(data_dir)
        super().__init__(*args, **kwargs)

    def _request_folders(self, parsed) -> dict[str, Path]:
        params = parse_qs(parsed.query)
        legacy_data_dir = (params.get("data_dir") or [""])[0].strip()
        default_dir = _normalized_base(legacy_data_dir) if legacy_data_dir else self.default_data_dir

        def pick(name: str) -> Path:
            requested = (params.get(name) or [""])[0].strip()
            return _normalized_base(requested) if requested else default_dir

        return {
            "csv_dir": pick("csv_dir"),
            "analysis_dir": pick("analysis_dir"),
            "review_dir": pick("review_dir"),
        }

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        folders = self._request_folders(parsed)
        if parsed.path == "/":
            self._send_html(INDEX_HTML_TEMPLATE.format(
                title=escape(DASHBOARD_TITLE),
                csv_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
                analysis_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
                review_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
            ))
            return
        if parsed.path == "/api/pick-folder":
            params = parse_qs(parsed.query)
            kind = (params.get("kind") or [""])[0].strip()
            current_dir = {
                "csv": folders["csv_dir"],
                "analysis": folders["analysis_dir"],
                "review": folders["review_dir"],
            }.get(kind, self.default_data_dir)
            try:
                selected = select_folder_dialog(current_dir)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({"selected": bool(selected), "path": selected or ""})
            return
        if parsed.path == "/api/reports":
            self._send_json({
                "csv_dir": str(folders["csv_dir"]),
                "analysis_dir": str(folders["analysis_dir"]),
                "review_dir": str(folders["review_dir"]),
                "reports": discover_reports(folders["csv_dir"], folders["analysis_dir"]),
            })
            return
        if parsed.path.startswith("/api/reports/"):
            date_key = unquote(parsed.path.removeprefix("/api/reports/"))
            try:
                payload = load_report_bundle(folders["csv_dir"], folders["analysis_dir"], folders["review_dir"], date_key)
            except ValueError:
                self._send_json({"error": "Invalid report date"}, status=HTTPStatus.BAD_REQUEST)
                return
            except FileNotFoundError:
                self._send_json({"error": "Report not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        folders = self._request_folders(parsed)
        if parsed.path.startswith("/api/reports/") and parsed.path.endswith("/review"):
            date_key = unquote(parsed.path.removeprefix("/api/reports/").removesuffix("/review").strip("/"))
            try:
                date_key = _validated_date_key(date_key)
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("Review payload must be an object")
                row_index = payload.get("rowIndex")
                if row_index is None:
                    raise ValueError("rowIndex is required")
                row_fields = payload.get("rowFields") or {}
                if not isinstance(row_fields, dict):
                    raise ValueError("rowFields must be an object")
                report_path = save_review_markdown(
                    folders["review_dir"],
                    date_key,
                    str(payload.get("reviewStatus") or ""),
                    str(payload.get("reviewNote") or ""),
                    int(row_index),
                    row_fields,
                    int(payload.get("rowNumber") or int(row_index) + 1),
                    int(payload.get("csvLineNumber") or int(row_index) + 2),
                )
                csv_path, _json_path = locate_report_paths(folders["csv_dir"], folders["analysis_dir"], date_key)
                headers, rows = load_csv_rows(csv_path)
                _display_headers, display_rows = enrich_rows_for_display(headers, rows)
            except (ValueError, json.JSONDecodeError):
                self._send_json({"error": "Invalid review payload"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "path": str(report_path), "reviews": load_review_markdown(folders["review_dir"], date_key, display_rows)})
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


def create_server(handler, requested_port: int) -> tuple[ThreadingHTTPServer, int, bool]:
    try:
        server = ThreadingHTTPServer((LOCALHOST, requested_port), handler)
        return server, requested_port, False
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
    fallback_server = ThreadingHTTPServer((LOCALHOST, 0), handler)
    fallback_port = int(fallback_server.server_address[1])
    return fallback_server, fallback_port, True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a localhost-only PA450 daily review UI")
    parser.add_argument("--data-dir", default=Path("output"), type=Path, help="Folder containing daily CSV/JSON results")
    parser.add_argument("--port", default=8765, type=int, help="Localhost port to bind the UI server")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handler = partial(ReportUIHandler, data_dir=str(args.data_dir))
    server, active_port, used_fallback_port = create_server(handler, args.port)
    if used_fallback_port:
        print(
            f"Requested port {args.port} is already in use on {LOCALHOST}; "
            f"using http://{LOCALHOST}:{active_port} instead."
        )
    print(f"PA450 Daily Review UI running at http://{LOCALHOST}:{active_port}")
    if not args.no_browser:
        threading.Timer(0.6, open_browser_when_ready, args=(active_port,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
