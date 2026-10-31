/**
 * Hisense AI Copilot - Ultra-Premium Client-Side Assistant (ai-assistant.js)
 * Standalone injection, active filter synchronization, status pill, and markdown rendering.
 */

(function () {
  'use strict';

  // Prevent multiple injections
  if (window.__HISENSE_AI_COPILOT_INITIALIZED__) return;
  window.__HISENSE_AI_COPILOT_INITIALIZED__ = true;

  // State
  let isOpen = false;
  let isMaximized = false;
  let isConnected = (function () {
    try { return sessionStorage.getItem('hisense_ai_connected') === 'true'; } catch (e) { return false; }
  })();
  let isCheckingHealth = false;
  let isSending = false;
  let conversationHistory = [];
  let cachedActiveFilters = {};
  let currentDashboard = 'sales';
  let resolvedApiUrl = '/api/chat';

  // Determine current dashboard type
  function detectDashboardType() {
    const path = window.location.pathname.toLowerCase();
    const title = document.title.toLowerCase();
    if (path.includes('display_comparison') || title.includes('display comparison') || document.getElementById('tblBM')) {
      return 'display_comparison';
    }
    return 'sales';
  }

  // Inspect active filter selections on the dashboard
  function getActiveFilters() {
    const filters = {};
    const dType = detectDashboardType();

    // 1. Check Date Range inputs (if present on sales dashboard)
    const dFrom = document.getElementById('dateFromInput');
    const dTo = document.getElementById('dateToInput');
    if (dFrom && dFrom.value) filters['dateFrom'] = dFrom.value;
    if (dTo && dTo.value) filters['dateTo'] = dTo.value;

    // 2. Check DOM Multi-select dropdowns (.msel)
    const mselElements = document.querySelectorAll('.filterbar .msel, #filterGrid .msel');
    mselElements.forEach(wrap => {
      const key = wrap.dataset.key || '';
      const lblEl = wrap.querySelector('.lbl');
      const valEl = wrap.querySelector('.val');
      const label = lblEl ? lblEl.textContent.trim() : key;
      const value = valEl ? valEl.textContent.trim() : '';
      if (value && value !== 'All' && value !== 'all') {
        filters[label || key] = value;
      }
    });

    // 3. Check outlet basis toggle on Display Comparison
    const basisActive = document.querySelector('.seg button.active');
    if (basisActive && dType === 'display_comparison') {
      const bText = basisActive.textContent.trim();
      if (bText && !bText.toLowerCase().includes('all')) {
        filters['Outlet Scope'] = bText;
      }
    }

    // 4. Fallback/Supplement from window.state if available
    if (window.state && window.state.filters) {
      Object.keys(window.state.filters).forEach(k => {
        const valSet = window.state.filters[k];
        if (valSet instanceof Set && valSet.size > 0) {
          const arr = Array.from(valSet);
          // Only add if not already captured from DOM label
          if (!Object.values(filters).includes(arr.join(', '))) {
            const prettyKey = k.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
            filters[prettyKey] = arr.join(', ');
          }
        }
      });
    }

    return filters;
  }

  // Format active filters as a readable banner string
  function getActiveFilterSummaryText(filters) {
    const keys = Object.keys(filters);
    if (!keys.length) {
      return 'National / All Outlets & Promoters';
    }
    return keys.map(k => `${k}: ${filters[k]}`).join(' • ');
  }

  // =========================================================================
  // LIVE DATASET DATE RESOLUTION
  // =========================================================================
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  function formatPrettyDate(iso) {
    if (!iso) return '';
    const parts = String(iso).trim().split('-');
    if (parts.length === 3) {
      const y = parts[0];
      const m = parseInt(parts[1], 10);
      const d = parseInt(parts[2], 10);
      if (m >= 1 && m <= 12) {
        return `${d} ${MONTHS[m - 1]} ${y}`;
      }
    }
    return String(iso);
  }

  function getPageDatasetDate() {
    // 1. Direct text in #maxDateLabel (populated by display_comparison.html or index.html)
    const label = document.getElementById('maxDateLabel');
    if (label && label.textContent) {
      const text = label.textContent.trim();
      if (text && text !== '–' && text !== '-' && text !== '—') {
        return text;
      }
    }

    // 2. window.MAX_DATE
    if (window.MAX_DATE && typeof window.MAX_DATE === 'string') {
      return formatPrettyDate(window.MAX_DATE);
    }

    // 3. window.RECORDS (index.html)
    if (window.RECORDS && Array.isArray(window.RECORDS) && window.RECORDS.length > 0) {
      try {
        let mx = '';
        const len = Math.min(window.RECORDS.length, 5000);
        for (let i = 0; i < len; i++) {
          const d = window.RECORDS[i].saleDate || window.RECORDS[i].subDate;
          if (d && d > mx) mx = d;
        }
        if (mx) return formatPrettyDate(mx);
      } catch (e) {}
    }

    return null;
  }


  // =========================================================================
  // DOM INJECTION & TEMPLATE
  // =========================================================================
  function injectWidget() {
    currentDashboard = detectDashboardType();

    const widget = document.createElement('div');
    widget.className = 'hisense-ai-widget';
    widget.id = 'hisenseAiWidget';

    const isSales = currentDashboard === 'sales';
    const initialChips = isSales ? [
      'Top 5 Promoters by Sales',
      'TV vs AC Sales Breakdown',
      'Which Zone leads in Sales Value?',
      'Show Promoters with Zero Sales',
      'Expected ROI per Zone'
    ] : [
      'D-1 vs D-2 Display Summary',
      'Which States saw highest Gain?',
      'Top Outlets Needing Attention',
      'TV vs AC vs Washing Machine Change',
      'Branch Managers with Highest Growth'
    ];

    widget.innerHTML = `
      <!-- Launcher Button -->
      <button class="hisense-ai-launcher" id="hisenseAiLauncher" title="Open Hisense AI Copilot">
        <div class="hisense-ai-launcher-icon-wrap">
          <div class="hisense-ai-launcher-pulse"></div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
        </div>
        <span class="hisense-ai-launcher-label">AI Copilot</span>
        <span class="hisense-ai-launcher-status-dot" id="hisenseLauncherDot"></span>
      </button>

      <!-- Chat Drawer -->
      <div class="hisense-ai-drawer" id="hisenseAiDrawer">
        <!-- Header -->
        <div class="hisense-ai-header">
          <div class="hisense-ai-header-left">
            <div class="hisense-ai-avatar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
            </div>
            <div class="hisense-ai-title-wrap">
              <div class="hisense-ai-title">
                Hisense AI Copilot
              </div>
              <div class="hisense-ai-sub">In-Memory Analytical Intelligence</div>
            </div>
          </div>

          <!-- Live Status Pill (No model names, clickable for health check) -->
          <div class="hisense-ai-status-pill ${isConnected ? '' : 'is-checking'}" id="hisenseStatusPill" title="${isConnected ? 'Connected & Live. Click to re-verify.' : 'Connecting to Hisense AI Copilot...'}">
            <span class="hisense-ai-status-dot-pulse"></span>
            <span id="hisenseStatusText">${isConnected ? 'Connected & Live' : 'Connecting...'}</span>
          </div>

          <!-- Controls -->
          <div class="hisense-ai-header-actions">
            <button class="hisense-ai-btn-icon" id="hisenseClearBtn" title="Clear Conversation">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
            <button class="hisense-ai-btn-icon" id="hisenseMaxBtn" title="Expand Drawer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 3 21 3 21 9"/>
                <polyline points="9 21 3 21 3 15"/>
                <line x1="21" y1="3" x2="14" y2="10"/>
                <line x1="3" y1="21" x2="10" y2="14"/>
              </svg>
            </button>
            <button class="hisense-ai-btn-icon" id="hisenseCloseBtn" title="Close">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Active Context Banner -->
        <div class="hisense-ai-context-banner" id="hisenseContextBanner">
          <div class="hisense-ai-context-left">
            <span class="hisense-ai-context-badge">🎯 Active View</span>
            <span class="hisense-ai-context-text" id="hisenseContextText">National / All Outlets & Promoters</span>
          </div>
          <span class="hisense-ai-context-refresh" id="hisenseContextRefresh" title="Resync Active Screen Filters">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
          </span>
        </div>

        <!-- Messages Area -->
        <div class="hisense-ai-messages" id="hisenseMessages">
          <div class="hisense-ai-welcome-card">
            👋 <b>Welcome to Hisense AI Copilot!</b><br>
            I have the entire <b>${isSales ? 'Sales Performance' : 'Display Comparison (D-1 vs D-2)'}</b> dataset pre-loaded in working memory.
            <div class="hisense-ai-dataset-status" id="hisenseDatasetStatus">
              📊 Dataset update status: Live as on <b>${getPageDatasetDate() || (isSales ? '29 Oct 2026' : '30 Oct 2026')}</b>
            </div>
            <ul>
              <li><b>Zero Lag:</b> Instant analysis without external database queries.</li>
              <li><b>Screen-Aware:</b> Your active filters above are automatically synchronized.</li>
              <li><b>Granular Accuracy:</b> Ask about units, values, leaders, ROI, and out-of-stock trends.</li>
            </ul>
            <div class="hisense-ai-chips-wrap" id="hisenseChips">
              ${initialChips.map(c => `<button class="hisense-ai-chip" type="button">${c}</button>`).join('')}
            </div>
          </div>
        </div>

        <!-- Footer / Input -->
        <div class="hisense-ai-footer">
          <div class="hisense-ai-input-wrap">
            <textarea
              class="hisense-ai-input"
              id="hisenseInput"
              rows="1"
              placeholder="Ask anything about ${isSales ? 'sales, ROI, promoters, or zones' : 'D-1 vs D-2 displays, growth, or outlets'}..."
            ></textarea>
            <button class="hisense-ai-send-btn" id="hisenseSendBtn" type="button" title="Send (Enter)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <div class="hisense-ai-footnote">Hisense Program Analytics &middot; Powered by Google Gemini &middot; Shift+Enter for newline</div>
        </div>
      </div>
    `;

    document.body.appendChild(widget);
    bindEvents();
    checkHealth();
    syncFilters();
  }

  // =========================================================================
  // EVENT BINDINGS & INTERACTIONS
  // =========================================================================
  function bindEvents() {
    const launcher = document.getElementById('hisenseAiLauncher');
    const drawer = document.getElementById('hisenseAiDrawer');
    const closeBtn = document.getElementById('hisenseCloseBtn');
    const maxBtn = document.getElementById('hisenseMaxBtn');
    const clearBtn = document.getElementById('hisenseClearBtn');
    const statusPill = document.getElementById('hisenseStatusPill');
    const contextRefresh = document.getElementById('hisenseContextRefresh');
    const input = document.getElementById('hisenseInput');
    const sendBtn = document.getElementById('hisenseSendBtn');
    const chipsWrap = document.getElementById('hisenseChips');

    // Toggle Drawer
    launcher.addEventListener('click', () => {
      isOpen = !isOpen;
      drawer.classList.toggle('is-open', isOpen);
      if (isOpen) {
        if (!isConnected) {
          checkHealth();
        }
        syncFilters();
        setTimeout(() => input.focus(), 150);
      }
    });

    // Observe maxDateLabel updates on page to synchronize dataset date
    const maxDateEl = document.getElementById('maxDateLabel');
    if (maxDateEl && window.MutationObserver) {
      try {
        const observer = new MutationObserver(() => {
          syncFilters();
        });
        observer.observe(maxDateEl, { childList: true, characterData: true, subtree: true });
      } catch (e) {}
    }

    // Auto-reconnect interval when disconnected
    setInterval(() => {
      if (!isConnected && !isCheckingHealth) {
        checkHealth();
      }
    }, 15000);

    closeBtn.addEventListener('click', () => {
      isOpen = false;
      drawer.classList.remove('is-open');
    });

    // Maximize / Restore
    maxBtn.addEventListener('click', () => {
      isMaximized = !isMaximized;
      drawer.classList.toggle('is-maximized', isMaximized);
      maxBtn.title = isMaximized ? 'Restore Drawer' : 'Expand Drawer';
    });

    // Clear history
    clearBtn.addEventListener('click', () => {
      conversationHistory = [];
      const msgs = document.getElementById('hisenseMessages');
      const welcome = msgs.querySelector('.hisense-ai-welcome-card');
      msgs.innerHTML = '';
      if (welcome) msgs.appendChild(welcome);
    });

    // Status Pill Health Check on Click
    statusPill.addEventListener('click', () => {
      checkHealth(true);
    });

    // Refresh context manually
    contextRefresh.addEventListener('click', () => {
      syncFilters();
    });

    // Auto-resizing textarea
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 100) + 'px';
    });

    // Submit on Enter (Shift+Enter for newline)
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitQuery();
      }
    });

    sendBtn.addEventListener('click', submitQuery);

    // Suggestion chips click delegation
    chipsWrap.addEventListener('click', (e) => {
      const chip = e.target.closest('.hisense-ai-chip');
      if (chip) {
        input.value = chip.textContent.trim();
        submitQuery();
      }
    });

    // Listen to filter change events on the host page
    const filterbar = document.querySelector('.filterbar') || document.getElementById('filterGrid');
    if (filterbar) {
      filterbar.addEventListener('click', () => setTimeout(syncFilters, 150));
      filterbar.addEventListener('change', () => setTimeout(syncFilters, 150));
    }
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => setTimeout(syncFilters, 200));
    }

    // MutationObserver to catch cascading filter updates
    if (window.MutationObserver && filterbar) {
      const observer = new MutationObserver(() => {
        syncFilters();
      });
      observer.observe(filterbar, { childList: true, subtree: true, characterData: true });
    }
  }

  // =========================================================================
  // HEALTH CHECK (LIVE STATUS PILL & MULTI-ENDPOINT RESOLVER)
  // =========================================================================
  async function testEndpoint(url) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(url, { 
        method: 'GET', 
        cache: 'no-store',
        signal: controller.signal 
      });
      clearTimeout(timeoutId);
      if (!res.ok) return null;
      const data = await res.json();
      return data;
    } catch (err) {
      return null;
    }
  }

  async function checkHealth(manual = false) {
    if (isCheckingHealth) return;
    isCheckingHealth = true;

    const pill = document.getElementById('hisenseStatusPill');
    const statusText = document.getElementById('hisenseStatusText');
    const launcherDot = document.getElementById('hisenseLauncherDot');

    if (pill && !isConnected) {
      pill.className = 'hisense-ai-status-pill is-checking';
      if (statusText) statusText.textContent = manual ? 'Verifying...' : 'Connecting...';
    }

    try {
      // 1. Build prioritized list of candidate endpoints
      const candidates = [resolvedApiUrl];
      if (resolvedApiUrl !== '/api/chat') candidates.push('/api/chat');

      // Local dev fallback if running locally
      const isLocal = window.location.hostname === 'localhost' || 
                      window.location.hostname === '127.0.0.1' || 
                      window.location.protocol === 'file:';
      if (isLocal) {
        if (!candidates.includes('http://localhost:8000/api/chat')) {
          candidates.push('http://localhost:8000/api/chat');
        }
      }

      // Always include production Vercel cloud endpoint fallback
      if (!candidates.includes('https://hisense-dashboards.vercel.app/api/chat')) {
        candidates.push('https://hisense-dashboards.vercel.app/api/chat');
      }

      let workingData = null;
      let workingUrl = null;

      for (const url of candidates) {
        const data = await testEndpoint(url);
        if (data && data.status === 'online') {
          workingData = data;
          workingUrl = url;
          break;
        }
      }

      if (workingData && workingUrl) {
        resolvedApiUrl = workingUrl;
        if (workingData.apiKeyConfigured) {
          isConnected = true;
          try { sessionStorage.setItem('hisense_ai_connected', 'true'); } catch (e) {}
          if (pill) pill.className = 'hisense-ai-status-pill';
          if (statusText) statusText.textContent = 'Connected & Live';
          if (launcherDot) launcherDot.className = 'hisense-ai-launcher-status-dot';
          const isSalesDashboard = (currentDashboard || detectDashboardType()) === 'sales';
          const backendAsOf = isSalesDashboard ? (workingData.salesPretty || workingData.salesAsOf) : (workingData.displayPretty || workingData.displayAsOf);
          const asOf = getPageDatasetDate() || backendAsOf || (isSalesDashboard ? '29 Oct 2026' : '30 Oct 2026');
          const dsEl = document.getElementById('hisenseDatasetStatus');
          if (dsEl) {
            dsEl.innerHTML = `📊 Dataset update status: Live as on <b>${asOf}</b>`;
          }
        } else {
          isConnected = false;
          try { sessionStorage.removeItem('hisense_ai_connected'); } catch (e) {}
          if (pill) pill.className = 'hisense-ai-status-pill is-warning';
          if (statusText) statusText.textContent = 'Key Missing';
          if (launcherDot) launcherDot.className = 'hisense-ai-launcher-status-dot offline';
          if (pill) pill.title = 'Backend online but GEMINI_API_KEY is not set. Add to .env or Vercel Settings. Click to re-check.';
        }
      } else {
        isConnected = false;
        try { sessionStorage.removeItem('hisense_ai_connected'); } catch (e) {}
        if (pill) pill.className = 'hisense-ai-status-pill is-error';
        if (statusText) statusText.textContent = 'Not Connected';
        if (launcherDot) launcherDot.className = 'hisense-ai-launcher-status-dot offline';
        if (pill) pill.title = 'Unable to reach backend /api/chat. Click to retry.';
      }
    } catch (err) {
      console.error('[AI Copilot] checkHealth error:', err);
      isConnected = false;
      try { sessionStorage.removeItem('hisense_ai_connected'); } catch (e) {}
      if (pill) pill.className = 'hisense-ai-status-pill is-error';
      if (statusText) statusText.textContent = 'Not Connected';
      if (launcherDot) launcherDot.className = 'hisense-ai-launcher-status-dot offline';
      if (pill) pill.title = 'Unable to reach backend. Click to retry.';
    } finally {
      isCheckingHealth = false;
    }
  }

  // =========================================================================
  // ACTIVE SCREEN CONTEXT SYNCHRONIZER
  // =========================================================================
  function syncFilters() {
    cachedActiveFilters = getActiveFilters();
    const contextText = document.getElementById('hisenseContextText');
    if (contextText) {
      contextText.textContent = getActiveFilterSummaryText(cachedActiveFilters);
    }
    const pageDate = getPageDatasetDate();
    if (pageDate) {
      const dsEl = document.getElementById('hisenseDatasetStatus');
      if (dsEl) {
        dsEl.innerHTML = `📊 Dataset update status: Live as on <b>${pageDate}</b>`;
      }
    }
  }

  // =========================================================================
  // LIGHTWEIGHT MARKDOWN & TABLE PARSER
  // =========================================================================
  function renderMarkdown(text) {
    if (!text) return '';

    // Escape raw HTML tags
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```lang ... ```
    html = html.replace(/```([\w-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
    html = html.replace(/\*([^*]+)\*/g, '<i>$1</i>');

    // Process Tables (| a | b |)
    const lines = html.split('\n');
    let inTable = false;
    let tableHtml = [];
    const outputLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|')) {
        // Table row
        const cells = line.split('|').slice(1, -1).map(c => c.trim());
        // Check if header separator e.g. |---|---|
        const isSeparator = cells.every(c => /^:?-+:?$/.test(c));

        if (!inTable) {
          inTable = true;
          tableHtml = ['<div class="table-responsive"><table><thead><tr>'];
          cells.forEach(c => tableHtml.push(`<th>${c}</th>`));
          tableHtml.push('</tr></thead><tbody>');
        } else if (isSeparator) {
          // Skip separator line
          continue;
        } else {
          tableHtml.push('<tr>');
          cells.forEach(c => tableHtml.push(`<td>${c}</td>`));
          tableHtml.push('</tr>');
        }
      } else {
        if (inTable) {
          inTable = false;
          tableHtml.push('</tbody></table></div>');
          outputLines.push(tableHtml.join(''));
          tableHtml = [];
        }
        outputLines.push(line);
      }
    }
    if (inTable) {
      tableHtml.push('</tbody></table></div>');
      outputLines.push(tableHtml.join(''));
    }

    html = outputLines.join('\n');

    // Unordered lists
    html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // Paragraph breaks
    html = html.split(/\n{2,}/).map(para => {
      para = para.trim();
      if (!para) return '';
      if (para.startsWith('<h') || para.startsWith('<div') || para.startsWith('<ul') || para.startsWith('<pre')) {
        return para;
      }
      return `<p>${para.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    return html;
  }

  // =========================================================================
  // MESSAGE APPEND & QUERY SUBMISSION
  // =========================================================================
  function appendMessage(role, text) {
    const msgs = document.getElementById('hisenseMessages');
    const row = document.createElement('div');
    row.className = `hisense-ai-msg-row ${role}`;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const isUser = role === 'user';
    row.innerHTML = `
      <div class="hisense-ai-msg-avatar">
        ${isUser ? 'U' : 'AI'}
      </div>
      <div class="hisense-ai-msg-body">
        <div class="hisense-ai-msg-bubble">
          ${isUser ? text.replace(/\n/g, '<br>') : renderMarkdown(text)}
        </div>
        <div class="hisense-ai-msg-time">${timeStr}</div>
      </div>
    `;

    msgs.appendChild(row);
    msgs.scrollTop = msgs.scrollHeight;
    return row;
  }

  function showTypingIndicator() {
    const msgs = document.getElementById('hisenseMessages');
    const typing = document.createElement('div');
    typing.className = 'hisense-ai-msg-row bot';
    typing.id = 'hisenseAiTyping';
    typing.innerHTML = `
      <div class="hisense-ai-msg-avatar">AI</div>
      <div class="hisense-ai-typing">
        <span class="hisense-ai-typing-dot"></span>
        <span class="hisense-ai-typing-dot"></span>
        <span class="hisense-ai-typing-dot"></span>
      </div>
    `;
    msgs.appendChild(typing);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function removeTypingIndicator() {
    const el = document.getElementById('hisenseAiTyping');
    if (el) el.remove();
  }

  async function submitQuery() {
    if (isSending) return;

    const input = document.getElementById('hisenseInput');
    const sendBtn = document.getElementById('hisenseSendBtn');
    const prompt = input.value.trim();
    if (!prompt) return;

    // Reset input
    input.value = '';
    input.style.height = 'auto';

    // Append user message
    appendMessage('user', prompt);
    conversationHistory.push({ role: 'user', text: prompt });

    // Lock sending
    isSending = true;
    sendBtn.disabled = true;
    showTypingIndicator();

    // Prepare payload
    syncFilters();
    const activeDate = getPageDatasetDate();
    const payload = {
      prompt: prompt,
      history: conversationHistory.slice(-8),
      activeFilters: cachedActiveFilters,
      dashboard: currentDashboard,
      pageDate: activeDate
    };

    try {
      let res;
      try {
        res = await fetch(resolvedApiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: jsonSafeStringify(payload)
        });
      } catch (netErr) {
        if (resolvedApiUrl !== 'https://hisense-dashboards.vercel.app/api/chat') {
          resolvedApiUrl = 'https://hisense-dashboards.vercel.app/api/chat';
          res = await fetch(resolvedApiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: jsonSafeStringify(payload)
          });
        } else {
          throw netErr;
        }
      }

      removeTypingIndicator();
      const data = await res.json();

      if (!res.ok) {
        const errorMsg = data.error || `Server responded with status ${res.status}`;
        appendMessage('bot', `⚠️ **Error:** ${errorMsg}`);
        checkHealth();
      } else {
        const reply = data.reply || 'No response returned from the assistant.';
        appendMessage('bot', reply);
        conversationHistory.push({ role: 'model', text: reply });
        // Mark status as live
        isConnected = true;
        try { sessionStorage.setItem('hisense_ai_connected', 'true'); } catch (e) {}
        const pill = document.getElementById('hisenseStatusPill');
        const statusText = document.getElementById('hisenseStatusText');
        const launcherDot = document.getElementById('hisenseLauncherDot');
        if (pill) pill.className = 'hisense-ai-status-pill';
        if (statusText) statusText.textContent = 'Connected & Live';
        if (launcherDot) launcherDot.className = 'hisense-ai-launcher-status-dot';
      }
    } catch (err) {
      removeTypingIndicator();
      appendMessage('bot', `⚠️ **Connection Failed:** Could not reach the AI Copilot server. Please check that \`dev_server.py\` or your Vercel deployment is active.`);
      checkHealth();
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  function jsonSafeStringify(obj) {
    return JSON.stringify(obj, (key, value) => {
      if (value instanceof Set) return Array.from(value);
      return value;
    });
  }

  // =========================================================================
  // BOOTSTRAP
  // =========================================================================
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
  } else {
    injectWidget();
  }
})();
