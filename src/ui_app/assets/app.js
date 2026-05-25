    const DEFAULT_CSV_DIR = __CSV_DIR_JSON__;
    const DEFAULT_ANALYSIS_DIR = __ANALYSIS_DIR_JSON__;
    const DEFAULT_REVIEW_DIR = __REVIEW_DIR_JSON__;
    const DEFAULT_PAGE_SIZE = 50;
    const appState = { reports: [], current: null, selectedRowIndex: null, analysisSlideIndex: 0, currentPage: 1, pageSize: DEFAULT_PAGE_SIZE, rightRailOpen: false };
    const appShell = document.getElementById('appShell');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const selectCsvFolder = document.getElementById('selectCsvFolder');
    const selectAnalysisFolder = document.getElementById('selectAnalysisFolder');
    const selectReviewFolder = document.getElementById('selectReviewFolder');
    const csvFolderPath = document.getElementById('csvFolderPath');
    const analysisFolderPath = document.getElementById('analysisFolderPath');
    const reviewFolderPath = document.getElementById('reviewFolderPath');
    const reloadFolders = document.getElementById('reloadFolders');
    const rangeStartDate = document.getElementById('rangeStartDate');
    const rangeEndDate = document.getElementById('rangeEndDate');
    const loadRangeButton = document.getElementById('loadRangeButton');
    const folderState = {
      csv: localStorage.getItem('pa450-csv-dir') || DEFAULT_CSV_DIR,
      analysis: localStorage.getItem('pa450-analysis-dir') || DEFAULT_ANALYSIS_DIR,
      review: localStorage.getItem('pa450-review-dir') || DEFAULT_REVIEW_DIR,
    };
    const folderLabels = {
      csv: csvFolderPath,
      analysis: analysisFolderPath,
      review: reviewFolderPath,
    };
    const reportList = document.getElementById('reportList');
    const loading = document.getElementById('loading');
    const errorBox = document.getElementById('errorBox');
    const reportApp = document.getElementById('reportApp');
    const summaryGrid = document.getElementById('summaryGrid');
    const contentGrid = document.getElementById('contentGrid');
    const rightRailToggleButton = document.getElementById('rightRailToggleButton');
    const analysisCard = document.getElementById('analysisCard');
    const searchInput = document.getElementById('searchInput');
    const sourceFilter = document.getElementById('sourceFilter');
    const appFilter = document.getElementById('appFilter');
    const pageStatus = document.getElementById('pageStatus');
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    const pagePrevButton = document.getElementById('pagePrevButton');
    const pageNextButton = document.getElementById('pageNextButton');
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const rowDetail = document.getElementById('rowDetail');
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewNote = document.getElementById('reviewNote');
    const reviewSaveButton = document.getElementById('reviewSaveButton');
    const reviewSaveMessage = document.getElementById('reviewSaveMessage');

    function clearNode(node) {
      while (node.firstChild) node.removeChild(node.firstChild);
    }

    function setEmptyMessage(container, message, className = 'empty') {
      clearNode(container);
      container.className = className;
      container.textContent = message;
    }

    function createTextNode(tag, text, className = '') {
      const node = document.createElement(tag);
      if (className) node.className = className;
      node.textContent = text;
      return node;
    }

    function createDetailRow(key, value, secondary = '') {
      const row = document.createElement('div');
      row.className = 'detail-row';
      row.appendChild(createTextNode('div', key, 'detail-key'));
      row.appendChild(createTextNode('div', value || '—'));
      if (secondary) row.appendChild(createTextNode('div', secondary, 'subtle'));
      return row;
    }

    function createPreformattedDetailRow(key, value, secondary = '') {
      const row = document.createElement('div');
      row.className = 'detail-row';
      row.appendChild(createTextNode('div', key, 'detail-key'));
      const valueNode = createTextNode('div', value || '—', 'report-text');
      row.appendChild(valueNode);
      if (secondary) row.appendChild(createTextNode('div', secondary, 'subtle'));
      return row;
    }

    function setSidebarCollapsed(collapsed) {
      appShell.classList.toggle('sidebar-collapsed', collapsed);
      sidebarToggle.textContent = collapsed ? '›' : '‹';
      sidebarToggle.title = collapsed ? '展開側邊欄' : '收合側邊欄';
      sidebarToggle.setAttribute('aria-label', sidebarToggle.title);
      localStorage.setItem('pa450-sidebar-collapsed', collapsed ? '1' : '0');
    }

    function setRightRailOpen(open) {
      appState.rightRailOpen = Boolean(open);
      contentGrid.classList.toggle('right-rail-collapsed', !appState.rightRailOpen);
      rightRailToggleButton.textContent = appState.rightRailOpen ? '隱藏 AI / 明細' : '顯示 AI / 明細';
      rightRailToggleButton.setAttribute('aria-expanded', appState.rightRailOpen ? 'true' : 'false');
    }

    function setFolderPath(kind, path) {
      folderState[kind] = path || 'output';
      if (folderLabels[kind]) folderLabels[kind].textContent = folderState[kind];
      persistFolderDirs();
    }

    function currentCsvDir() {
      return folderState.csv || DEFAULT_CSV_DIR;
    }

    function currentAnalysisDir() {
      return folderState.analysis || DEFAULT_ANALYSIS_DIR;
    }

    function currentReviewDir() {
      return folderState.review || DEFAULT_REVIEW_DIR;
    }

    function apiUrl(path, extraParams = {}) {
      const params = new URLSearchParams();
      params.set('csv_dir', currentCsvDir());
      params.set('analysis_dir', currentAnalysisDir());
      params.set('review_dir', currentReviewDir());
      Object.entries(extraParams).forEach(([key, value]) => params.set(key, value));
      return path + '?' + params.toString();
    }

    function persistFolderDirs() {
      localStorage.setItem('pa450-csv-dir', currentCsvDir());
      localStorage.setItem('pa450-analysis-dir', currentAnalysisDir());
      localStorage.setItem('pa450-review-dir', currentReviewDir());
    }

    async function chooseFolder(kind) {
      try {
        clearError();
        const response = await fetch(apiUrl('/api/pick-folder', { kind }));
        if (!response.ok) throw new Error(`選擇資料夾失敗：${response.status}`);
        const payload = await response.json();
        if (payload.selected && payload.path) setFolderPath(kind, payload.path);
      } catch (error) {
        showError(error.message || '選擇資料夾失敗');
      }
    }

    function renderFolderPaths() {
      setFolderPath('csv', currentCsvDir());
      setFolderPath('analysis', currentAnalysisDir());
      setFolderPath('review', currentReviewDir());
    }

    function updateSelectedFileNames() {
      csvFileName.textContent = csvFileInput.files[0] ? `CSV：${csvFileInput.files[0].name}` : '尚未選擇 CSV';
      jsonFileName.textContent = jsonFileInput.files[0] ? `AI JSON：${jsonFileInput.files[0].name}` : '尚未選擇 AI JSON';
      const hasCsv = Boolean(csvFileInput.files[0]);
      const hasJson = Boolean(jsonFileInput.files[0]);
      loadSelectedFilesButton.disabled = !(hasCsv && hasJson);
      if (hasCsv && hasJson) {
        manualLoadState.textContent = '已分開記住目前選擇的 CSV 與 AI JSON；即使來自不同資料夾也可直接一起載入。';
      } else if (hasCsv) {
        manualLoadState.textContent = 'CSV 已選好；可切換到另一個資料夾再挑 AI JSON。';
      } else if (hasJson) {
        manualLoadState.textContent = 'AI JSON 已選好；可切換到另一個資料夾再挑 CSV。';
      } else {
        manualLoadState.textContent = 'CSV 與 AI JSON 可分別從不同資料夾挑選；兩個都選好後再載入。';
      }
    }

    function showError(message) {
      errorBox.hidden = false;
      errorBox.textContent = message;
      loading.hidden = true;
      reportApp.hidden = true;
    }

    function clearError() {
      errorBox.hidden = true;
      errorBox.textContent = '';
    }

    function readFileAsText(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
        reader.onerror = () => reject(new Error(`讀取檔案失敗：${file.name}`));
        reader.readAsText(file, 'utf-8');
      });
    }

    function splitCsvLine(line) {
      const values = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i += 1) {
        const char = line[i];
        if (char === '"') {
          if (inQuotes && line[i + 1] === '"') {
            current += '"';
            i += 1;
          } else {
            inQuotes = !inQuotes;
          }
          continue;
        }
        if (char === ',' && !inQuotes) {
          values.push(current);
          current = '';
          continue;
        }
        current += char;
      }
      values.push(current);
      return values;
    }

    function parseCsvText(csvText) {
      const normalized = csvText.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      const rows = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < normalized.length; i += 1) {
        const char = normalized[i];
        if (char === '"') {
          current += char;
          if (inQuotes && normalized[i + 1] === '"') {
            current += normalized[i + 1];
            i += 1;
          } else {
            inQuotes = !inQuotes;
          }
          continue;
        }
        if (char === '\n' && !inQuotes) {
          rows.push(current);
          current = '';
          continue;
        }
        current += char;
      }
      if (current || normalized.endsWith('\n')) rows.push(current);
      const nonEmptyRows = rows.filter((line) => line.length > 0);
      if (!nonEmptyRows.length) throw new Error('CSV 內容是空的');
      const headers = splitCsvLine(nonEmptyRows[0]);
      if (!headers.length || headers.every((header) => !header.trim())) throw new Error('CSV 缺少表頭');
      const dataRows = nonEmptyRows.slice(1).map((line) => {
        const values = splitCsvLine(line);
        const row = {};
        headers.forEach((header, index) => {
          row[header] = values[index] || '';
        });
        return row;
      });
      return { headers, rows: dataRows };
    }

    function parseIntLike(value) {
      if (value === null || value === undefined) return null;
      const text = String(value).replace(/[^\d-]/g, '');
      if (!text || text === '-') return null;
      const parsed = Number.parseInt(text, 10);
      return Number.isNaN(parsed) ? null : parsed;
    }

    function formatBytesHuman(value) {
      if (value === null || value === undefined) return '—';
      const units = ['bytes', 'KB', 'MB', 'GB', 'TB'];
      let size = Number(value);
      let unit = units[0];
      for (const currentUnit of units) {
        unit = currentUnit;
        if (size < 1024 || currentUnit === units[units.length - 1]) break;
        size /= 1024;
      }
      return unit === 'bytes' ? `${Number(value).toLocaleString('en-US')} bytes` : `${size.toFixed(1)} ${unit}`;
    }

    function analysisItemFromMatch(match, fallbackItemNumber = '') {
      return {
        item_number: (match.groups && (match.groups.itemNumber || match.groups.prefixItemNumber) || fallbackItemNumber || '').trim(),
        source: (match.groups && match.groups.source || '').trim(),
        destination: (match.groups && match.groups.destination || '').trim(),
        application: (match.groups && match.groups.application || '').trim(),
        bytes: (match.groups && match.groups.bytes || '').trim(),
      };
    }

    function parseAnalysisSections(analysisText) {
      const parsed = { status: '', summary: '', source: '', destination: '', application: '', bytes: '', reason: '', items: [] };
      let pendingItemNumber = '';
      analysisText.split(/\r?\n/).forEach((rawLine) => {
        const line = rawLine.trim();
        if (!line) return;
        const normalized = line.replace(/^[\-\s]+/, '');
        const itemMatch = normalized.match(/^第(?<itemNumber>\d+)筆的來源：(?<source>.*?)\s+目的地：(?<destination>.*?)\s+應用程式：(?<application>.*?)\s+位元組：(?<bytes>.*)$/);
        const itemDetailMatch = normalized.match(/^(?:第(?<prefixItemNumber>\d+)筆(?:的)?\s*)?來源：(?<source>.*?)\s+目的地：(?<destination>.*?)\s+(?:目的地國家：?.*?\s+)?應用程式：(?<application>.*?)\s+位元組：(?<bytes>.*)$/);
        const itemHeadingMatch = normalized.match(/^第(?<itemNumber>\d+)筆[：:]?$/);
        if (normalized.startsWith('異常狀態：')) { parsed.status = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (normalized.startsWith('摘要：')) { parsed.summary = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (itemMatch) { parsed.items.push(analysisItemFromMatch(itemMatch)); pendingItemNumber = ''; }
        else if (itemDetailMatch && (pendingItemNumber || (itemDetailMatch.groups && itemDetailMatch.groups.prefixItemNumber))) { parsed.items.push(analysisItemFromMatch(itemDetailMatch, pendingItemNumber)); pendingItemNumber = ''; }
        else if (/^\d[\d,]*\s*bytes$/i.test(normalized) && parsed.items.length) parsed.items[parsed.items.length - 1].bytes = normalized;
        else if (itemHeadingMatch) pendingItemNumber = itemHeadingMatch.groups.itemNumber.trim();
        else if (normalized.startsWith('來源：')) { parsed.source = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (normalized.startsWith('目的地：')) { parsed.destination = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (normalized.startsWith('應用程式：')) { parsed.application = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (normalized.startsWith('位元組：')) { parsed.bytes = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
        else if (normalized.startsWith('原因：')) { parsed.reason = normalized.split('：', 2)[1].trim(); pendingItemNumber = ''; }
      });
      if (parsed.items.length) {
        const firstItem = parsed.items[0];
        parsed.source = parsed.source || firstItem.source;
        parsed.destination = parsed.destination || firstItem.destination;
        parsed.application = parsed.application || firstItem.application;
        parsed.bytes = parsed.bytes || firstItem.bytes;
      }
      return parsed;
    }

    function summarizeRows(rows) {
      const sourceSet = new Set();
      const destinationSet = new Set();
      const byteValues = [];
      rows.forEach((row) => {
        const source = (row['來源位址'] || '').trim();
        const destination = (row['目的地位址'] || '').trim();
        if (source) sourceSet.add(source);
        if (destination) destinationSet.add(destination);
        const byteValue = parseIntLike(row['位元組']);
        if (byteValue !== null) byteValues.push(byteValue);
      });
      const maxBytes = byteValues.length ? Math.max(...byteValues) : 0;
      const totalBytes = byteValues.reduce((sum, value) => sum + value, 0);
      return {
        total_rows: rows.length,
        unique_sources: sourceSet.size,
        unique_destinations: destinationSet.size,
        max_bytes_human: formatBytesHuman(maxBytes),
        max_bytes_raw: `${maxBytes.toLocaleString('en-US')} bytes`,
        total_bytes_human: formatBytesHuman(totalBytes),
        total_bytes_raw: `${totalBytes.toLocaleString('en-US')} bytes`,
      };
    }

    function enrichRowsForDisplay(headers, rows) {
      const displayHeaders = headers.map((header) => header === '位元組' ? '傳輸量' : header);
      const displayRows = rows.map((row) => {
        const displayRow = { ...row };
        if (Object.prototype.hasOwnProperty.call(row, '位元組')) {
          const byteValue = parseIntLike(row['位元組']);
          displayRow['傳輸量'] = byteValue === null ? (row['位元組'] || '') : `${formatBytesHuman(byteValue)} (${byteValue.toLocaleString('en-US')} bytes)`;
          displayRow.__raw_bytes = row['位元組'] || '';
          delete displayRow['位元組'];
        }
        return displayRow;
      });
      return { displayHeaders, displayRows };
    }

    function deriveManualLabel(csvFile, jsonFile, analysisPayload) {
      const candidates = [analysisPayload.date, analysisPayload.report_date, analysisPayload.date_key, csvFile.name, jsonFile.name].filter(Boolean);
      const matched = candidates.map((value) => String(value).match(/(\d{8})/)).find(Boolean);
      if (matched) {
        const dateKey = matched[1];
        return { date: `manual-${dateKey}`, label: `${dateKey.slice(0, 4)}-${dateKey.slice(4, 6)}-${dateKey.slice(6, 8)}` };
      }
      return { date: `manual-${csvFile.name}-${jsonFile.name}`, label: '手動載入' };
    }

    function buildManualReport(csvFile, jsonFile, csvText, jsonText) {
      const parsedCsv = parseCsvText(csvText);
      const analysisPayload = JSON.parse(jsonText);
      if (!analysisPayload || typeof analysisPayload !== 'object' || Array.isArray(analysisPayload)) {
        throw new Error('AI JSON 必須是物件');
      }
      const analysisText = String(analysisPayload.analysis || '');
      const analysisSections = parseAnalysisSections(analysisText);
      const analysisBytesValue = parseIntLike(analysisSections.bytes);
      analysisSections.bytes_human = analysisBytesValue === null ? '' : formatBytesHuman(analysisBytesValue);
      analysisSections.bytes_raw = analysisBytesValue === null ? (analysisSections.bytes || '') : `${analysisBytesValue.toLocaleString('en-US')} bytes`;
      const { displayHeaders, displayRows } = enrichRowsForDisplay(parsedCsv.headers, parsedCsv.rows);
      const labelInfo = deriveManualLabel(csvFile, jsonFile, analysisPayload);
      return {
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
      };
    }

    async function loadSelectedFiles() {
      const csvFile = csvFileInput.files[0];
      const jsonFile = jsonFileInput.files[0];
      if (!csvFile || !jsonFile) {
        showError('請先各選 1 個 CSV 與 1 個 AI JSON。');
        return;
      }
      try {
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        const [csvText, jsonText] = await Promise.all([readFileAsText(csvFile), readFileAsText(jsonFile)]);
        appState.current = buildManualReport(csvFile, jsonFile, csvText, jsonText);
        appState.selectedRowIndex = null;
        renderCurrentReport();
      } catch (error) {
        showError(error.message || '載入選擇檔案失敗');
      }
    }

    function selectedRow() {
      if (!appState.current || appState.selectedRowIndex === null) return null;
      return appState.current.rows[appState.selectedRowIndex] || null;
    }

    function canSaveReviewToMarkdown() {
      return appState.current
        && appState.selectedRowIndex !== null
        && /^\d{8}$/.test(currentReviewDate() || '')
        && appState.current.source !== 'manual-upload';
    }

    function currentReviewDate() {
      if (!appState.current || appState.selectedRowIndex === null) return '';
      if (appState.current.mode === 'range') {
        const row = selectedRow();
        return row ? String(row.__report_date || '') : '';
      }
      return String(appState.current.date || '');
    }

    function currentReviewRowIndex() {
      if (!appState.current || appState.selectedRowIndex === null) return null;
      if (appState.current.mode === 'range') {
        const row = selectedRow();
        if (!row) return null;
        const rowIndex = Number.parseInt(String(row.__report_row_index), 10);
        return Number.isNaN(rowIndex) ? null : rowIndex;
      }
      return appState.selectedRowIndex;
    }

    function rowSummary(row) {
      const preferredHeaders = ['來源位址', '目的地位址', '應用程式', '傳輸量', '來源使用者', '使用者', '主機名稱'];
      return preferredHeaders
        .filter((header) => row && row[header])
        .map((header) => `${header}=${row[header]}`)
        .join('；');
    }

    function setReviewControlsEnabled(enabled) {
      reviewStatus.disabled = !enabled;
      reviewNote.disabled = !enabled;
      reviewSaveButton.disabled = !enabled || !canSaveReviewToMarkdown();
      if (!enabled) {
        reviewStatus.value = '';
        reviewNote.value = '';
        reviewNote.placeholder = '請先點選 CSV 表格中的單筆資料列，再填寫這筆的回報。';
      } else {
        reviewNote.placeholder = '例如：這筆高流量其實是備份流量，AI 需要學會辨識。';
      }
    }

    function setReviewSaveMessage(message, className = 'subtle') {
      reviewSaveMessage.textContent = message || '';
      reviewSaveMessage.className = `review-save-message ${className}`;
    }

    function setReviewSaving(isSaving) {
      reviewSaveButton.disabled = isSaving || !canSaveReviewToMarkdown();
      if (isSaving) {
        reviewSaveButton.textContent = '儲存中...';
      } else {
        reviewSaveButton.textContent = '儲存';
      }
    }

    function draftReviews() {
      if (!appState.current) return {};
      if (!appState.current.draftReviews) appState.current.draftReviews = {};
      return appState.current.draftReviews;
    }

    function buildCurrentReviewPayload() {
      if (!appState.current) return null;
      if (appState.selectedRowIndex === null) {
        setReviewControlsEnabled(false);
        return null;
      }
      const row = selectedRow();
      if (!row) return null;
      const rowIndex = currentReviewRowIndex();
      if (rowIndex === null) return null;
      return {
        reviewStatus: reviewStatus.value,
        reviewNote: reviewNote.value,
        rowIndex,
        rowNumber: rowIndex + 1,
        csvLineNumber: rowIndex + 2,
        rowSummary: rowSummary(row),
        rowFields: row,
      };
    }

    function updateReviewDraft() {
      const review = buildCurrentReviewPayload();
      if (!review || !appState.current) return;
      setReviewSaveMessage('', 'subtle');
      draftReviews()[String(appState.selectedRowIndex)] = review;
    }

    async function saveReviewState() {
      const review = buildCurrentReviewPayload();
      if (!review || !appState.current) return;
      setReviewSaveMessage('儲存中...', 'subtle');
      setReviewSaving(true);
      if (!appState.current.reviews) appState.current.reviews = {};
      appState.current.reviews[String(appState.selectedRowIndex)] = review;
      if (!canSaveReviewToMarkdown()) {
        setReviewSaveMessage('已暫存目前回報。', 'success');
        setReviewSaving(false);
        return;
      }
      try {
        const response = await fetch(apiUrl('/api/reports/' + encodeURIComponent(currentReviewDate()) + '/review'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(review),
        });
        if (!response.ok) throw new Error(`儲存 report_YYYYMMDD.md 失敗：${response.status}`);
        const payload = await response.json();
        if (payload.reviews) {
          if (appState.current.mode === 'range') {
            appState.current.reviews[String(appState.selectedRowIndex)] = payload.reviews[String(review.rowIndex)] || review;
          } else {
            appState.current.reviews = payload.reviews;
          }
        }
        delete draftReviews()[String(appState.selectedRowIndex)];
        setReviewSaveMessage('已儲存回報。', 'success');
      } catch (error) {
        setReviewSaveMessage('儲存失敗，請再試一次。', 'error');
        showError(error.message || '儲存 report_YYYYMMDD.md 失敗');
      } finally {
        setReviewSaving(false);
      }
    }

    function loadReviewState() {
      reviewStatus.value = '';
      reviewNote.value = '';
      setReviewSaveMessage('', 'subtle');
      if (!appState.current || appState.selectedRowIndex === null) {
        setReviewControlsEnabled(false);
        return;
      }
      setReviewControlsEnabled(true);
      const rowKey = String(appState.selectedRowIndex);
      const draft = draftReviews()[rowKey];
      if (draft) {
        reviewStatus.value = draft.reviewStatus || '';
        reviewNote.value = draft.reviewNote || '';
        return;
      }
      if (canSaveReviewToMarkdown()) {
        const saved = (appState.current.reviews || {})[rowKey] || {};
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
        return;
      }
    }

    function uniqueValues(field) {
      if (!appState.current) return [];
      return [...new Set(appState.current.rows.map((row) => (row[field] || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
    }

    function fillSelect(selectEl, field, label) {
      clearNode(selectEl);
      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = `全部${label}`;
      selectEl.appendChild(defaultOption);
      uniqueValues(field).forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        selectEl.appendChild(option);
      });
    }

    function renderReportButton(report) {
      const btn = document.createElement('button');
      btn.className = 'report-item';
      if (appState.current && report.date === appState.current.date) btn.classList.add('active');
      btn.appendChild(createTextNode('div', report.label, 'report-date'));
      btn.appendChild(createTextNode('div', report.summary, 'subtle report-summary'));
      btn.addEventListener('click', () => loadReport(report.date));
      return btn;
    }

    function renderSidebar() {
      clearNode(reportList);
      let currentMonthGroup = '';
      let currentMonthItems = null;
      appState.reports.forEach((report, index) => {
        const monthGroup = report.month_group || String(report.date || '').slice(0, 6).replace(/^(\d{4})(\d{2})$/, '$1-$2');
        if (monthGroup !== currentMonthGroup) {
          currentMonthGroup = monthGroup;
          const group = document.createElement('details');
          group.className = 'report-month-group';
          const monthReports = appState.reports.filter((candidate) => (candidate.month_group || String(candidate.date || '').slice(0, 6).replace(/^(\d{4})(\d{2})$/, '$1-$2')) === monthGroup);
          const hasCurrentReport = appState.current && monthReports.some((candidate) => candidate.date === appState.current.date);
          group.open = hasCurrentReport || (!appState.current && index === 0);
          group.appendChild(createTextNode('summary', report.month_label || monthGroup, 'report-month-heading'));
          currentMonthItems = document.createElement('div');
          currentMonthItems.className = 'report-month-items';
          group.appendChild(currentMonthItems);
          reportList.appendChild(group);
        }
        currentMonthItems.appendChild(renderReportButton(report));
      });
      if (!appState.reports.length) {
        setEmptyMessage(reportList, '目前找不到任何每日報告。');
      }
    }

    function renderSummary() {
      clearNode(summaryGrid);
      const summary = appState.current.summary;
      const items = appState.current.mode === 'range' ? [
        ['日期區間', appState.current.label, appState.current.date],
        ['天數', String(summary.covered_days || 0), ''],
        ['筆數', String(summary.total_rows), ''],
        ['來源 IP', String(summary.unique_sources), ''],
        ['最大傳輸量', summary.max_bytes_human, summary.max_bytes_raw],
        ['總傳輸量', summary.total_bytes_human, summary.total_bytes_raw],
      ] : [
        ['報告日期', appState.current.label, appState.current.date],
        ['筆數', String(summary.total_rows), ''],
        ['來源 IP', String(summary.unique_sources), ''],
        ['目的地', String(summary.unique_destinations), ''],
        ['最大傳輸量', summary.max_bytes_human, summary.max_bytes_raw],
        ['總傳輸量', summary.total_bytes_human, summary.total_bytes_raw],
      ];
      items.forEach(([label, value, secondary]) => {
        const item = document.createElement('div');
        item.className = 'summary-item';
        item.appendChild(createTextNode('div', label, 'detail-key'));
        item.appendChild(createTextNode('div', value, 'summary-value'));
        if (secondary) item.appendChild(createTextNode('div', secondary, 'summary-meta'));
        summaryGrid.appendChild(item);
      });
    }

    function renderAnalysisItem(analysisPayload) {
      const a = analysisPayload.analysis_sections || {};
      [
        ['異常狀態', a.status || '資料不足，需人工確認', ''],
        ['摘要', a.summary || analysisPayload.analysis_text || '資料不足，需人工確認', ''],
        ['原因', a.reason || '', ''],
      ].forEach(([key, value, secondary]) => analysisCard.appendChild(createDetailRow(key, value, secondary)));
      if (a.items && a.items.length) {
        a.items.forEach((item) => {
          const itemBytesValue = parseIntLike(item.bytes);
          const itemBytesDisplay = itemBytesValue === null ? (item.bytes || '—') : formatBytesHuman(itemBytesValue);
          const itemBytesSecondary = itemBytesValue === null ? '' : `${itemBytesValue.toLocaleString('en-US')} bytes`;
          analysisCard.appendChild(createDetailRow(
            `第${item.item_number}筆`,
            `來源：${item.source || '—'} 目的地：${item.destination || '—'} 應用程式：${item.application || '—'} 位元組：${itemBytesDisplay}`,
            itemBytesSecondary,
          ));
        });
      } else {
        analysisCard.appendChild(createDetailRow('異常項目', '—', ''));
      }
    }

    function moveAnalysisSlide(delta) {
      const items = (appState.current && appState.current.daily_analyses) || [];
      if (!items.length) return;
      appState.analysisSlideIndex = Math.min(Math.max(appState.analysisSlideIndex + delta, 0), items.length - 1);
      renderAnalysis();
    }

    function renderAnalysisCarouselControls(items) {
      const controls = document.createElement('div');
      controls.className = 'analysis-carousel-controls';
      const prev = document.createElement('button');
      prev.type = 'button';
      prev.className = 'analysis-carousel-button';
      prev.textContent = '‹';
      prev.disabled = appState.analysisSlideIndex <= 0;
      prev.addEventListener('click', () => moveAnalysisSlide(-1));
      const date = createTextNode(
        'div',
        `${items[appState.analysisSlideIndex].label}（${appState.analysisSlideIndex + 1}/${items.length}）`,
        'analysis-carousel-date',
      );
      const next = document.createElement('button');
      next.type = 'button';
      next.className = 'analysis-carousel-button';
      next.textContent = '›';
      next.disabled = appState.analysisSlideIndex >= items.length - 1;
      next.addEventListener('click', () => moveAnalysisSlide(1));
      controls.appendChild(prev);
      controls.appendChild(date);
      controls.appendChild(next);
      analysisCard.appendChild(controls);
    }

    function renderAnalysis() {
      clearNode(analysisCard);
      if (appState.current.mode === 'range') {
        const items = appState.current.daily_analyses || [];
        if (!items.length) {
          analysisCard.appendChild(createDetailRow('AI 摘要', '區間內沒有每日 AI 摘要', ''));
          return;
        }
        appState.analysisSlideIndex = Math.min(appState.analysisSlideIndex, items.length - 1);
        renderAnalysisCarouselControls(items);
        renderAnalysisItem(items[appState.analysisSlideIndex]);
        return;
      }
      renderAnalysisItem(appState.current);
    }

    function renderHead() {
      clearNode(tableHead);
      appState.current.headers.forEach((header) => {
        const th = document.createElement('th');
        th.textContent = header;
        tableHead.appendChild(th);
      });
    }

    function normalizeForAiMatch(value) {
      return String(value || '').trim();
    }

    function dailyAnalysisForRow(row) {
      if (!appState.current) return null;
      if (appState.current.mode !== 'range') return appState.current;
      const rowDate = String(row.__report_date || '');
      return (appState.current.daily_analyses || []).find((analysis) => analysis.date === rowDate) || null;
    }

    function rowMatchesAiReport(row) {
      const dailyAnalysis = dailyAnalysisForRow(row);
      const a = dailyAnalysis ? dailyAnalysis.analysis_sections || {} : {};
      const items = Array.isArray(a.items) ? a.items : [];
      if (!items.length) return false;
      const rowBytes = parseIntLike(row.__raw_bytes ?? row['傳輸量'] ?? row['位元組']);
      return items.some((item) => {
        const itemBytes = parseIntLike(item.bytes);
        const coreMatch = normalizeForAiMatch(row['來源位址']) === normalizeForAiMatch(item.source)
          && normalizeForAiMatch(row['目的地位址']) === normalizeForAiMatch(item.destination)
          && normalizeForAiMatch(row['應用程式']) === normalizeForAiMatch(item.application);
        if (!coreMatch) return false;
        if (itemBytes === null || rowBytes === null) return true;
        return rowBytes === itemBytes;
      });
    }

    function matchesFilters(row) {
      const search = searchInput.value.trim().toLowerCase();
      const source = sourceFilter.value;
      const app = appFilter.value;
      const textBlob = appState.current.headers.map((header) => row[header] || '').join(' ').toLowerCase();
      if (search && !textBlob.includes(search)) return false;
      if (source && (row['來源位址'] || '') !== source) return false;
      if (app && (row['應用程式'] || '') !== app) return false;
      return true;
    }

    function filteredRowsWithIndexes() {
      if (!appState.current) return [];
      return appState.current.rows
        .map((row, originalIndex) => ({ row, originalIndex }))
        .filter((item) => matchesFilters(item.row));
    }

    function maxPageFor(totalRows) {
      return Math.max(1, Math.ceil(totalRows / appState.pageSize));
    }

    function clampCurrentPage(totalRows) {
      appState.currentPage = Math.min(Math.max(appState.currentPage, 1), maxPageFor(totalRows));
    }

    function renderPaginationControls(totalRows) {
      clampCurrentPage(totalRows);
      const totalPages = maxPageFor(totalRows);
      const start = totalRows ? ((appState.currentPage - 1) * appState.pageSize) + 1 : 0;
      const end = totalRows ? Math.min(appState.currentPage * appState.pageSize, totalRows) : 0;
      pageStatus.textContent = `第 ${start}-${end} 筆，共 ${totalRows} 筆（第 ${appState.currentPage}/${totalPages} 頁）`;
      pageSizeSelect.value = String(appState.pageSize);
      pagePrevButton.disabled = appState.currentPage <= 1;
      pageNextButton.disabled = appState.currentPage >= totalPages;
    }

    function resetPagination() {
      appState.currentPage = 1;
    }

    function renderDetails(row) {
      clearNode(rowDetail);
      rowDetail.className = 'detail-list';
      appState.current.headers.forEach((header) => {
        rowDetail.appendChild(createDetailRow(header, row[header] || '—'));
      });
      loadReviewState();
    }

    function renderRows() {
      clearNode(tableBody);
      const filtered = filteredRowsWithIndexes();
      renderPaginationControls(filtered.length);
      const pageStart = (appState.currentPage - 1) * appState.pageSize;
      const pageItems = filtered.slice(pageStart, pageStart + appState.pageSize);
      pageItems.forEach(({ row, originalIndex }) => {
        const tr = document.createElement('tr');
        const isAiMatch = rowMatchesAiReport(row);
        if (isAiMatch) {
          tr.classList.add('is-ai-match');
          tr.title = appState.current.mode === 'range'
            ? '完整命中 AI 報告異常項目：日期 + 來源 IP + 目的地 IP + 應用程式'
            : '完整命中 AI 報告異常項目：來源 IP + 目的地 IP + 應用程式';
        }
        if (appState.selectedRowIndex === originalIndex) tr.classList.add('is-selected');
        tr.addEventListener('click', () => {
          appState.selectedRowIndex = originalIndex;
          setRightRailOpen(true);
          renderRows();
          renderDetails(row);
        });
        appState.current.headers.forEach((header) => {
          const td = document.createElement('td');
          td.textContent = row[header] || '';
          if (isAiMatch && ['來源位址', '目的地位址', '應用程式'].includes(header)) {
            td.classList.add('ai-match-cell');
          }
          tr.appendChild(td);
        });
        tableBody.appendChild(tr);
      });
      if (!pageItems.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = appState.current.headers.length;
        td.textContent = '沒有符合條件的 CSV 列。';
        tr.appendChild(td);
        tableBody.appendChild(tr);
      }
    }

    function renderCurrentReport() {
      if (!appState.current) return;
      clearError();
      loading.hidden = true;
      reportApp.hidden = false;
      appState.selectedRowIndex = null;
      setRightRailOpen(false);
      resetPagination();
      setEmptyMessage(rowDetail, '尚未選取資料列。');
      renderSidebar();
      renderSummary();
      renderAnalysis();
      renderHead();
      fillSelect(sourceFilter, '來源位址', '來源 IP');
      fillSelect(appFilter, '應用程式', '應用程式');
      setReviewControlsEnabled(false);
      renderRows();
    }

    async function loadReport(date) {
      persistFolderDirs();
      appState.analysisSlideIndex = 0;
      const response = await fetch(apiUrl('/api/reports/' + encodeURIComponent(date)));
      if (!response.ok) throw new Error(`載入報告失敗：${response.status}`);
      appState.current = await response.json();
      if (!appState.current.draftReviews) appState.current.draftReviews = {};
      renderCurrentReport();
    }

    function dateKeyToInputValue(dateKey) {
      const text = String(dateKey || '');
      if (!/^\d{8}$/.test(text)) return '';
      return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
    }

    function inputValueToDateKey(value) {
      return String(value || '').replace(/-/g, '');
    }

    let analysisTouchStartX = null;

    function handleAnalysisTouchStart(event) {
      analysisTouchStartX = event.changedTouches && event.changedTouches.length ? event.changedTouches[0].clientX : null;
    }

    function handleAnalysisTouchEnd(event) {
      if (analysisTouchStartX === null || !event.changedTouches || !event.changedTouches.length) return;
      const deltaX = event.changedTouches[0].clientX - analysisTouchStartX;
      analysisTouchStartX = null;
      if (Math.abs(deltaX) < 45) return;
      moveAnalysisSlide(deltaX < 0 ? 1 : -1);
    }

    function handleFilterChanged() {
      resetPagination();
      renderRows();
    }

    function changePage(delta) {
      appState.currentPage += delta;
      renderRows();
    }

    function handlePageSizeChanged() {
      const nextPageSize = Number.parseInt(pageSizeSelect.value, 10);
      appState.pageSize = Number.isNaN(nextPageSize) ? DEFAULT_PAGE_SIZE : nextPageSize;
      resetPagination();
      renderRows();
    }

    function setRangeDefaults() {
      if (!appState.reports.length) return;
      const newest = appState.reports[0].date;
      const oldest = appState.reports[appState.reports.length - 1].date;
      if (!rangeStartDate.value) rangeStartDate.value = dateKeyToInputValue(oldest);
      if (!rangeEndDate.value) rangeEndDate.value = dateKeyToInputValue(newest);
    }

    async function loadDateRange() {
      const startDate = inputValueToDateKey(rangeStartDate.value);
      const endDate = inputValueToDateKey(rangeEndDate.value);
      if (!/^\d{8}$/.test(startDate) || !/^\d{8}$/.test(endDate)) {
        showError('請先選擇開始日期與結束日期。');
        return;
      }
      if (startDate > endDate) {
        showError('開始日期不可晚於結束日期。');
        return;
      }
      try {
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        persistFolderDirs();
        appState.analysisSlideIndex = 0;
        const response = await fetch(apiUrl('/api/reports/range', { start_date: startDate, end_date: endDate }));
        if (!response.ok) throw new Error(`載入日期區間失敗：${response.status}`);
        appState.current = await response.json();
        if (!appState.current.draftReviews) appState.current.draftReviews = {};
        renderCurrentReport();
      } catch (error) {
        showError(error.message || '載入日期區間失敗');
      }
    }

    async function bootstrap() {
      try {
        clearError();
        loading.hidden = false;
        reportApp.hidden = true;
        appState.current = null;
        appState.selectedRowIndex = null;
        persistFolderDirs();
        const response = await fetch(apiUrl('/api/reports'));
        if (!response.ok) throw new Error(`載入報告列表失敗：${response.status}`);
        const payload = await response.json();
        appState.reports = payload.reports || [];
        setRangeDefaults();
        renderSidebar();
        if (!appState.reports.length) {
          loading.hidden = true;
          setEmptyMessage(reportList, `找不到成對的 CSV/AI JSON。CSV：${currentCsvDir()}；AI JSON：${currentAnalysisDir()}`);
          return;
        }
        await loadReport(appState.reports[0].date);
      } catch (error) {
        showError(error.message || '載入失敗');
      }
    }

    renderFolderPaths();
    selectCsvFolder.addEventListener('click', () => chooseFolder('csv'));
    selectAnalysisFolder.addEventListener('click', () => chooseFolder('analysis'));
    selectReviewFolder.addEventListener('click', () => chooseFolder('review'));
    reloadFolders.addEventListener('click', bootstrap);
    loadRangeButton.addEventListener('click', loadDateRange);
    rightRailToggleButton.addEventListener('click', () => setRightRailOpen(!appState.rightRailOpen));
    sidebarToggle.addEventListener('click', () => setSidebarCollapsed(!appShell.classList.contains('sidebar-collapsed')));
    setSidebarCollapsed(localStorage.getItem('pa450-sidebar-collapsed') === '1');
    searchInput.addEventListener('input', handleFilterChanged);
    sourceFilter.addEventListener('change', handleFilterChanged);
    appFilter.addEventListener('change', handleFilterChanged);
    pageSizeSelect.addEventListener('change', handlePageSizeChanged);
    pagePrevButton.addEventListener('click', () => changePage(-1));
    pageNextButton.addEventListener('click', () => changePage(1));
    analysisCard.addEventListener('touchstart', handleAnalysisTouchStart, { passive: true });
    analysisCard.addEventListener('touchend', handleAnalysisTouchEnd, { passive: true });
    reviewStatus.addEventListener('change', updateReviewDraft);
    reviewNote.addEventListener('input', updateReviewDraft);
    reviewSaveButton.addEventListener('click', saveReviewState);
    bootstrap();
