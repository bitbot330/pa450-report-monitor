    // Browser-side controller for the PA450 Review UI.
    //
    // The Python server injects the three folder defaults below when rendering
    // index.html. All API calls send the currently selected CSV/analysis/review
    // folders explicitly so the backend remains stateless between requests.
    const DEFAULT_CSV_DIR = __CSV_DIR_JSON__;
    const DEFAULT_ANALYSIS_DIR = __ANALYSIS_DIR_JSON__;
    const DEFAULT_REVIEW_DIR = __REVIEW_DIR_JSON__;
    const REVIEW_QUICK_ACTIONS = [
      { value: '正常', label: '正常' },
      { value: '需追蹤', label: '需追蹤' },
      { value: '誤判', label: '誤判' },
      { value: '可忽略', label: '可忽略' },
      { value: '需要封鎖', label: '需要封鎖' },
      { value: '加入觀察名單', label: '觀察名單' },
    ];
    const appState = { reports: [], current: null, selectedRowIndex: null, analysisSlideIndex: 0, analysisSlideDirection: 0, rightRailOpen: true, sort: { key: '', direction: 'desc' } };
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
    const rightRail = document.getElementById('rightRail');
    const rightRailToggleButton = document.getElementById('rightRailToggleButton');
    const analysisCard = document.getElementById('analysisCard');
    const searchInput = document.getElementById('searchInput');
    const sourceFilter = document.getElementById('sourceFilter');
    const appFilter = document.getElementById('appFilter');
    const pageStatus = document.getElementById('pageStatus');
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const rowDetail = document.getElementById('rowDetail');
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewQuickActions = document.getElementById('reviewQuickActions');
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

    function setSidebarCollapsed(collapsed) {
      appShell.classList.toggle('sidebar-collapsed', collapsed);
      sidebarToggle.textContent = collapsed ? '›' : '‹';
      sidebarToggle.title = collapsed ? '展開側邊欄' : '收合側邊欄';
      sidebarToggle.setAttribute('aria-label', sidebarToggle.title);
      localStorage.setItem('pa450-sidebar-collapsed', collapsed ? '1' : '0');
    }

    function setRightRailOpen(open) {
      // Collapsing the right rail hides AI, row detail, and review feedback as
      // one accessibility region; keep aria-hidden/inert synchronized with CSS.
      appState.rightRailOpen = Boolean(open);
      contentGrid.classList.toggle('right-rail-collapsed', !appState.rightRailOpen);
      rightRailToggleButton.textContent = appState.rightRailOpen ? '隱藏 AI' : '顯示 AI';
      rightRailToggleButton.setAttribute('aria-expanded', appState.rightRailOpen ? 'true' : 'false');
      rightRail.setAttribute('aria-hidden', appState.rightRailOpen ? 'false' : 'true');
      rightRail.inert = !appState.rightRailOpen;
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
      // Folder paths are query parameters by design. This lets the same local
      // server serve independent CSV, AI JSON, and review directories.
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
      // Ask the Python backend to open the native folder picker because browser
      // JavaScript cannot select arbitrary local directories directly.
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

    function parseIntLike(value) {
      if (value === null || value === undefined) return null;
      const text = String(value).trim();
      if (!/^[+-]?\d[\d,]*\s*(?:bytes?)?$/i.test(text)) return null;
      const parsed = Number.parseInt(text.replace(/\s*(?:bytes?)\s*$/i, '').replace(/,/g, ''), 10);
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
      [...reviewQuickActions.querySelectorAll('button')].forEach((button) => { button.disabled = !enabled; });
      if (!enabled) {
        reviewStatus.value = '';
        reviewNote.value = '';
        reviewNote.placeholder = '請先點選 CSV 表格中的單筆資料列，再填寫這筆的回報。';
      } else {
        reviewNote.placeholder = '例如：這筆高流量其實是備份流量，AI 需要學會辨識。';
      }
      syncReviewQuickActions();
    }

    function syncReviewQuickActions() {
      [...reviewQuickActions.querySelectorAll('button')].forEach((button) => {
        const active = button.dataset.value === reviewStatus.value;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    }

    function applyReviewQuickAction(value) {
      if (reviewNote.disabled) return;
      reviewStatus.value = reviewStatus.value === value ? '' : value;
      syncReviewQuickActions();
      updateReviewDraft();
    }

    function renderReviewQuickActions() {
      clearNode(reviewQuickActions);
      REVIEW_QUICK_ACTIONS.forEach((action) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'review-chip';
        button.dataset.value = action.value;
        button.textContent = action.label;
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => applyReviewQuickAction(action.value));
        reviewQuickActions.appendChild(button);
      });
      syncReviewQuickActions();
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
      // Persist only server-backed reports. Manual local-file preview mode has no
      // safe browser permission to write report_YYYYMMDD.md back to disk.
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
        syncReviewQuickActions();
        return;
      }
      if (canSaveReviewToMarkdown()) {
        const saved = (appState.current.reviews || {})[rowKey] || {};
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
        syncReviewQuickActions();
        return;
      }
    }

    function currentDailyAnalysis() {
      if (!appState.current || appState.current.mode !== 'range') return null;
      const items = appState.current.daily_analyses || [];
      if (!items.length) return null;
      appState.analysisSlideIndex = Math.min(appState.analysisSlideIndex, items.length - 1);
      return items[appState.analysisSlideIndex] || null;
    }

    function currentAnalysisDate() {
      const dailyAnalysis = currentDailyAnalysis();
      return dailyAnalysis ? String(dailyAnalysis.date || '') : '';
    }

    function rowsForCurrentAnalysisDate() {
      // In range mode, the table follows the active AI carousel date instead of
      // showing all dates at once.
      if (!appState.current) return [];
      if (appState.current.mode !== 'range') return appState.current.rows;
      const activeDate = currentAnalysisDate();
      if (!activeDate) return appState.current.rows;
      return appState.current.rows.filter((row) => String(row.__report_date || '') === activeDate);
    }

    function uniqueValues(field) {
      if (!appState.current) return [];
      return [...new Set(rowsForCurrentAnalysisDate().map((row) => (row[field] || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
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
      const dailyAnalysis = currentDailyAnalysis();
      const summary = (dailyAnalysis && dailyAnalysis.summary) || appState.current.summary;
      const items = appState.current.mode === 'range' ? [
        ['AI 報告日期', dailyAnalysis ? dailyAnalysis.label : appState.current.label, dailyAnalysis ? dailyAnalysis.date : appState.current.date],
        ['日期區間', appState.current.label, appState.current.date],
        ['筆數', String(summary.total_rows), ''],
        ['來源 IP', String(summary.unique_sources), ''],
        ['目的地', String(summary.unique_destinations), ''],
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

    function focusAnalysisItem(item, analysisPayload = null) {
      const rowIndex = findRowIndexForAnalysisItem(item, analysisPayload);
      if (rowIndex === null) return;
      searchInput.value = '';
      if (item.source && [...sourceFilter.options].some((option) => option.value === item.source)) sourceFilter.value = item.source;
      if (item.application && [...appFilter.options].some((option) => option.value === item.application)) appFilter.value = item.application;
      selectRowByIndex(rowIndex);
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
          const rowIndex = findRowIndexForAnalysisItem(item, analysisPayload);
          const row = document.createElement('div');
          row.className = 'detail-row analysis-link-row';
          row.appendChild(createTextNode('div', `第${item.item_number}筆`, 'detail-key'));
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'analysis-row-link';
          button.disabled = rowIndex === null;
          button.textContent = `來源：${item.source || '—'} 目的地：${item.destination || '—'} 應用程式：${item.application || '—'} 位元組：${itemBytesDisplay}`;
          button.title = rowIndex === null ? 'CSV 表格找不到完整匹配列' : '跳到 CSV 表格對應列並套用來源/應用程式 filter';
          button.addEventListener('click', () => focusAnalysisItem(item, analysisPayload));
          row.appendChild(button);
          if (itemBytesSecondary) row.appendChild(createTextNode('div', itemBytesSecondary, 'subtle'));
          analysisCard.appendChild(row);
        });
      } else {
        analysisCard.appendChild(createDetailRow('異常項目', '—', ''));
      }
    }

    function moveAnalysisSlide(delta) {
      // delta > 0 moves to newer daily analysis because Python sorts
      // daily_analyses oldest → newest.
      const items = (appState.current && appState.current.daily_analyses) || [];
      if (!items.length) return;
      const nextIndex = Math.min(Math.max(appState.analysisSlideIndex + delta, 0), items.length - 1);
      if (nextIndex === appState.analysisSlideIndex) return;
      appState.analysisSlideDirection = delta;
      appState.analysisSlideIndex = nextIndex;
      renderAnalysis();
      syncDailyReportToAnalysisSlide();
    }

    function syncDailyReportToAnalysisSlide() {
      if (!appState.current || appState.current.mode !== 'range') return;
      appState.selectedRowIndex = null;
      setEmptyMessage(rowDetail, '尚未選取資料列。');
      setReviewControlsEnabled(false);
      fillSelect(sourceFilter, '來源位址', '來源 IP');
      fillSelect(appFilter, '應用程式', '應用程式');
      renderSummary();
      renderRows();
    }

    function animateAnalysisSlide() {
      analysisCard.classList.remove('analysis-slide-forward', 'analysis-slide-backward');
      if (!appState.analysisSlideDirection) return;
      void analysisCard.offsetWidth;
      analysisCard.classList.add(appState.analysisSlideDirection > 0 ? 'analysis-slide-forward' : 'analysis-slide-backward');
      appState.analysisSlideDirection = 0;
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
        animateAnalysisSlide();
        return;
      }
      renderAnalysisItem(appState.current);
    }

    function renderHead() {
      clearNode(tableHead);
      appState.current.headers.forEach((header) => {
        const th = document.createElement('th');
        th.className = tableColumnClass(header);
        th.title = `${header} 排序`;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'sort-header-button';
        button.textContent = header;
        button.setAttribute('aria-label', `${header} 排序`);
        const isActive = appState.sort.key === header;
        if (isActive) {
          button.classList.add('active');
          button.dataset.direction = appState.sort.direction;
          button.setAttribute('aria-sort', appState.sort.direction === 'asc' ? 'ascending' : 'descending');
        }
        button.addEventListener('click', () => toggleSort(header));
        th.appendChild(button);
        tableHead.appendChild(th);
      });
    }

    function tableColumnClass(header) {
      const normalized = String(header || '');
      if (normalized.includes('來源')) return 'col-source';
      if (normalized.includes('目的地國家')) return 'col-country';
      if (normalized.includes('目的地')) return 'col-destination';
      if (normalized.includes('應用程式')) return 'col-app';
      if (normalized.includes('使用者')) return 'col-user';
      if (normalized.includes('傳輸量') || normalized.includes('位元組')) return 'col-bytes';
      return '';
    }

    function toggleSort(header) {
      const nextDirection = appState.sort.key === header && appState.sort.direction === 'desc' ? 'asc' : 'desc';
      appState.sort = { key: header, direction: nextDirection };
      renderHead();
      renderRows();
    }

    function sortableValue(row, header) {
      if (header.includes('傳輸量') || header.includes('位元組')) {
        const byteValue = parseIntLike(row.__raw_bytes ?? row[header] ?? row['位元組'] ?? row['傳輸量']);
        return byteValue === null ? Number.NEGATIVE_INFINITY : byteValue;
      }
      return String(row[header] || '').trim().toLowerCase();
    }

    function sortRowsWithIndexes(items) {
      if (!appState.sort.key) return items;
      const direction = appState.sort.direction === 'asc' ? 1 : -1;
      const key = appState.sort.key;
      return [...items].sort((a, b) => {
        const av = sortableValue(a.row, key);
        const bv = sortableValue(b.row, key);
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * direction;
        return String(av).localeCompare(String(bv), 'zh-Hant', { numeric: true, sensitivity: 'base' }) * direction;
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

    function rowMatchesAnalysisItem(row, item) {
      // Match by CSV field values rather than visible row position because
      // filtering/sorting and date-range merges change table indexes.
      const rowBytes = parseIntLike(row.__raw_bytes ?? row['傳輸量'] ?? row['位元組']);
      const itemBytes = parseIntLike(item.bytes);
      const coreMatch = normalizeForAiMatch(row['來源位址']) === normalizeForAiMatch(item.source)
        && normalizeForAiMatch(row['目的地位址']) === normalizeForAiMatch(item.destination)
        && normalizeForAiMatch(row['應用程式']) === normalizeForAiMatch(item.application);
      if (!coreMatch) return false;
      if (itemBytes === null || rowBytes === null) return true;
      return rowBytes === itemBytes;
    }

    function rowMatchesAiReport(row) {
      const dailyAnalysis = dailyAnalysisForRow(row);
      const a = dailyAnalysis ? dailyAnalysis.analysis_sections || {} : {};
      const items = Array.isArray(a.items) ? a.items : [];
      if (!items.length) return false;
      return items.some((item) => rowMatchesAnalysisItem(row, item));
    }

    function findRowIndexForAnalysisItem(item, analysisPayload = null) {
      if (!appState.current || !item) return null;
      const analysisDate = analysisPayload && analysisPayload.date ? String(analysisPayload.date) : '';
      const match = appState.current.rows
        .map((row, originalIndex) => ({ row, originalIndex }))
        .find(({ row }) => {
          if (appState.current.mode === 'range' && analysisDate && String(row.__report_date || '') !== analysisDate) return false;
          return rowMatchesAnalysisItem(row, item);
        });
      return match ? match.originalIndex : null;
    }

    function selectRowByIndex(originalIndex) {
      if (!appState.current || originalIndex === null || originalIndex === undefined) return;
      const row = appState.current.rows[originalIndex];
      if (!row) return;
      appState.selectedRowIndex = originalIndex;
      setRightRailOpen(true);
      renderRows();
      renderDetails(row);
      const selected = tableBody.querySelector('tr.is-selected');
      if (selected) selected.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }

    function matchesFilters(row) {
      const activeDate = currentAnalysisDate();
      if (appState.current.mode === 'range' && activeDate && String(row.__report_date || '') !== activeDate) return false;
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
      return sortRowsWithIndexes(appState.current.rows
        .map((row, originalIndex) => ({ row, originalIndex }))
        .filter((item) => matchesFilters(item.row)));
    }

    function renderRowCount(totalRows) {
      pageStatus.textContent = `共 ${totalRows} 筆`;
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
      renderRowCount(filtered.length);
      filtered.forEach(({ row, originalIndex }) => {
        const tr = document.createElement('tr');
        const isAiMatch = rowMatchesAiReport(row);
        if (isAiMatch) {
          tr.classList.add('is-ai-match');
          tr.title = appState.current.mode === 'range'
            ? '完整命中 AI 報告異常項目：日期 + 來源 IP + 目的地 IP + 應用程式'
            : '完整命中 AI 報告異常項目：來源 IP + 目的地 IP + 應用程式';
        }
        if (appState.selectedRowIndex === originalIndex) tr.classList.add('is-selected');
        tr.addEventListener('click', () => selectRowByIndex(originalIndex));
        appState.current.headers.forEach((header) => {
          const td = document.createElement('td');
          td.className = tableColumnClass(header);
          const cellValue = row[header] || '';
          td.textContent = td.classList.contains('col-bytes') ? cellValue.replace(/\s*\(.*/, '') : cellValue;
          td.title = row[header] || '';
          if (isAiMatch && ['來源位址', '目的地位址', '應用程式'].includes(header)) {
            td.classList.add('ai-match-cell');
          }
          tr.appendChild(td);
        });
        tableBody.appendChild(tr);
      });
      if (!filtered.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = appState.current.headers.length;
        td.textContent = '沒有符合條件的 CSV 列。';
        tr.appendChild(td);
        tableBody.appendChild(tr);
      }
    }

    function renderCurrentReport() {
      // Central re-render entry point after loading a report, changing date range,
      // or resetting the active row/filter state.
      if (!appState.current) return;
      clearError();
      loading.hidden = true;
      reportApp.hidden = false;
      appState.selectedRowIndex = null;
      setRightRailOpen(true);
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
      // 左滑：往較新的日期；右滑：往較舊的日期。
      moveAnalysisSlide(deltaX < 0 ? 1 : -1);
    }

    function handleFilterChanged() {
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
      // Initial page load: restore folder preferences, fetch report metadata, and
      // auto-open the newest report when one is available.
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
    renderReviewQuickActions();
    setRightRailOpen(true);
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
    analysisCard.addEventListener('touchstart', handleAnalysisTouchStart, { passive: true });
    analysisCard.addEventListener('touchend', handleAnalysisTouchEnd, { passive: true });
    reviewStatus.addEventListener('change', () => { syncReviewQuickActions(); updateReviewDraft(); });
    reviewNote.addEventListener('input', updateReviewDraft);
    reviewSaveButton.addEventListener('click', saveReviewState);
    bootstrap();
