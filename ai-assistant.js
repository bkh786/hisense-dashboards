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
    const title = (document.title || '').toLowerCase();
    if (path.includes('display_comparison') || title.includes('display comparison') || document.getElementById('tblBM')) {
      return 'display_comparison';
    }
    if (path.includes('display') || title.includes('display')) {
      return 'display';
    }
    if (path.includes('attendance') || title.includes('attendance')) {
      return 'attendance';
    }
    if (path.includes('hiring') || title.includes('hiring')) {
      return 'hiring';
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
  // LIVE DATASET DATE RESOLUTION & CLIENT-SIDE IN-MEMORY PIPE TABLE COMPILER
  // =========================================================================
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  let lastSyncedDatasetDate = '';

  function formatPrettyDate(iso) {
    if (!iso) return '';
    const parts = String(iso).trim().split('-');
    if (parts.length === 3 && parts[0].length === 4) {
      const y = parts[0];
      const m = parseInt(parts[1], 10);
      const d = parseInt(parts[2], 10);
      if (m >= 1 && m <= 12) {
        return `${d} ${MONTHS[m - 1]} ${y}`;
      }
    }
    return String(iso);
  }

  function formatDashDate(iso) {
    if (!iso) return '';
    const parts = String(iso).trim().split('-');
    if (parts.length === 3 && parts[0].length === 4) {
      const y = parts[0];
      const m = parseInt(parts[1], 10);
      const d = parseInt(parts[2], 10);
      if (m >= 1 && m <= 12) {
        return `${String(d).padStart(2, '0')}-${MONTHS[m - 1]}-${y}`;
      }
    }
    // Convert "31 Oct 2026" -> "31-Oct-2026"
    const m2 = String(iso).trim().match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$/);
    if (m2) {
      return `${String(parseInt(m2[1], 10)).padStart(2, '0')}-${m2[2]}-${m2[3]}`;
    }
    return String(iso);
  }

  function parsePrettyToIso(str) {
    if (!str) return '';
    const s = String(str).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const m = s.match(/^(\d{1,2})[\s\-]([A-Za-z]{3})[\s\-](\d{4})$/);
    if (m) {
      const mi = MONTHS.findIndex(x => x.toLowerCase() === m[2].toLowerCase());
      if (mi >= 0) {
        return `${m[3]}-${String(mi + 1).padStart(2, '0')}-${String(parseInt(m[1], 10)).padStart(2, '0')}`;
      }
    }
    return '';
  }

  function getPageMaxDateIso() {
    if (window.MAX_DATE && typeof window.MAX_DATE === 'string' && /^\d{4}-\d{2}-\d{2}/.test(window.MAX_DATE)) {
      return window.MAX_DATE.slice(0, 10);
    }
    const label = document.getElementById('maxDateLabel');
    if (label && label.textContent) {
      const parsed = parsePrettyToIso(label.textContent.trim());
      if (parsed) return parsed;
    }
    if (window.STORES && window.STORES instanceof Map && window.STORES.size > 0) {
      let mx = '';
      window.STORES.forEach(s => {
        if (s && s.d1Date && s.d1Date > mx) mx = s.d1Date;
      });
      if (mx) return mx;
    }
    if (window.RECORDS && Array.isArray(window.RECORDS) && window.RECORDS.length > 0) {
      let mx = '';
      for (let i = 0; i < window.RECORDS.length; i++) {
        const r = window.RECORDS[i];
        const d = r && (r.saleDate || r.subDate || r.date);
        if (d && d > mx) mx = d;
      }
      if (mx) return mx;
    }
    return '';
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

    // 2. ISO Max Date from window.MAX_DATE / STORES / RECORDS
    const iso = getPageMaxDateIso();
    if (iso) return formatPrettyDate(iso);

    return null;
  }

  function fmtSignedDiff(n) {
    const v = Math.round(Number(n) || 0);
    return (v >= 0 ? '+' : '') + v.toLocaleString('en-IN');
  }

  function fmtSignedPct(diff, base) {
    if (!base) return diff > 0 ? 'New' : '0.0%';
    const pct = (diff / base) * 100;
    return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%';
  }

  function scrapeVisibleKpisAndHighlights() {
    const out = [];
    const kpiCards = document.querySelectorAll('#kpiGrid .kpi');
    if (kpiCards && kpiCards.length) {
      out.push('KPI Tile|Displayed Value|Subtitle / Pill');
      kpiCards.forEach(card => {
        const lbl = (card.querySelector('.kpi-label') || {}).textContent || '';
        const val = (card.querySelector('.kpi-value') || {}).textContent || '';
        const pill = (card.querySelector('.kpi-pill') || {}).textContent || '';
        const sub = (card.querySelector('.kpi-sub') || card.querySelector('.kpi-bottom-info') || {}).textContent || '';
        const meta = [pill.trim(), sub.trim()].filter(Boolean).join(' · ');
        if (lbl.trim()) {
          out.push(`${lbl.trim()}|${val.replace(/\s+/g, ' ').trim()}|${meta.replace(/\s+/g, ' ').trim()}`);
        }
      });
    }
    const hlItems = document.querySelectorAll('#highlights .hl-item');
    if (hlItems && hlItems.length) {
      out.push('');
      out.push('Key Highlights Visible on Screen:');
      hlItems.forEach(item => {
        const txt = (item.textContent || '').replace(/\s+/g, ' ').trim();
        if (txt) out.push(`- ${txt}`);
      });
    }
    return out.join('\n');
  }

  function buildLiveDisplayPipeTable() {
    const storesMap = window.STORES;
    const records = window.RECORDS;
    if (!storesMap || !(storesMap instanceof Map) || storesMap.size === 0 || !Array.isArray(records) || records.length === 0) {
      return '';
    }

    const maxDateIso = getPageMaxDateIso() || window.MAX_DATE || '2026-10-31';
    const asOfDash = formatDashDate(maxDateIso);
    const asOfPretty = formatPrettyDate(maxDateIso);

    const GEO_KEYS = ['region', 'state', 'branch', 'bm', 'tl'];
    const PROD_KEYS = ['ptype', 'category', 'size'];
    const stFilters = (window.state && window.state.filters) ? window.state.filters : {};
    const basis = (window.state && window.state.basis) ? window.state.basis : 'all';

    const hasActiveFilter = basis !== 'all' || [...GEO_KEYS, ...PROD_KEYS].some(k => stFilters[k] && stFilters[k].size > 0);

    function computeDisplaySlice(useActiveFilters) {
      const geoPass = s => !useActiveFilters || GEO_KEYS.every(k => !stFilters[k] || !stFilters[k].size || stFilters[k].has(s[k]));
      const prodPass = r => !useActiveFilters || PROD_KEYS.every(k => !stFilters[k] || !stFilters[k].size || stFilters[k].has(r[k]));
      const useBasis = useActiveFilters ? basis : 'all';

      const prodActive = useActiveFilters && PROD_KEYS.some(k => stFilters[k] && stFilters[k].size > 0);
      const storesWithProd = prodActive ? new Set(records.filter(prodPass).map(r => r.store)) : null;

      const outlets = new Map();
      storesMap.forEach((s, code) => {
        if (!geoPass(s)) return;
        if (useBasis === 'lfl' && !s.d2Date) return;
        if (storesWithProd && !storesWithProd.has(code)) return;
        outlets.set(code, { s, d1: 0, d2: 0, tvD1: 0, tvD2: 0 });
      });

      const byPtype = new Map();
      const byRegion = new Map();
      const byState = new Map();
      const byBM = new Map();
      const byTL = new Map();
      const byCat = new Map();
      const bySize = new Map();

      outlets.forEach(({ s }) => {
        const regKey = s.region || 'NA';
        const stKey = `${s.state || 'NA'} (${regKey})`;
        const bmKey = `${s.bm || 'NA'} (${regKey})`;
        const tlKey = `${s.tl || 'NA'} (${s.state || 'NA'})`;
        [
          [byRegion, regKey],
          [byState, stKey],
          [byBM, bmKey],
          [byTL, tlKey]
        ].forEach(([m, k]) => {
          if (!m.has(k)) m.set(k, { key: k, outlets: 0, d1: 0, d2: 0, up: 0, down: 0, same: 0 });
          m.get(k).outlets += 1;
        });
      });

      records.forEach(r => {
        const o = outlets.get(r.store);
        if (!o || !prodPass(r)) return;
        const cnt = Number(r.cnt) || 0;
        const s = o.s;
        const pt = r.ptype || 'NA';
        const catKey = `${pt} > ${r.category || 'NA'}`;
        const szKey = `${pt} > ${r.size || 'NA'}`;

        if (!byPtype.has(pt)) byPtype.set(pt, { key: pt, d1: 0, d2: 0 });
        if (!byCat.has(catKey)) byCat.set(catKey, { key: catKey, d1: 0, d2: 0 });
        if (!bySize.has(szKey)) bySize.set(szKey, { key: szKey, d1: 0, d2: 0 });

        const regKey = s.region || 'NA';
        const stKey = `${s.state || 'NA'} (${regKey})`;
        const bmKey = `${s.bm || 'NA'} (${regKey})`;
        const tlKey = `${s.tl || 'NA'} (${s.state || 'NA'})`;

        if (r.date === s.d1Date) {
          o.d1 += cnt;
          if (pt === 'TV') o.tvD1 += cnt;
          byPtype.get(pt).d1 += cnt;
          byCat.get(catKey).d1 += cnt;
          bySize.get(szKey).d1 += cnt;
          byRegion.get(regKey).d1 += cnt;
          byState.get(stKey).d1 += cnt;
          byBM.get(bmKey).d1 += cnt;
          byTL.get(tlKey).d1 += cnt;
        } else if (s.d2Date && r.date === s.d2Date) {
          o.d2 += cnt;
          if (pt === 'TV') o.tvD2 += cnt;
          byPtype.get(pt).d2 += cnt;
          byCat.get(catKey).d2 += cnt;
          bySize.get(szKey).d2 += cnt;
          byRegion.get(regKey).d2 += cnt;
          byState.get(stKey).d2 += cnt;
          byBM.get(bmKey).d2 += cnt;
          byTL.get(tlKey).d2 += cnt;
        }
      });

      const list = Array.from(outlets.values());
      list.forEach(o => {
        const s = o.s;
        const regKey = s.region || 'NA';
        const stKey = `${s.state || 'NA'} (${regKey})`;
        const bmKey = `${s.bm || 'NA'} (${regKey})`;
        const tlKey = `${s.tl || 'NA'} (${s.state || 'NA'})`;
        const dir = o.d1 > o.d2 ? 'up' : (o.d1 < o.d2 ? 'down' : 'same');
        [byRegion.get(regKey), byState.get(stKey), byBM.get(bmKey), byTL.get(tlKey)].forEach(g => {
          if (g) g[dir] += 1;
        });
      });

      const D1 = Math.round(list.reduce((a, o) => a + o.d1, 0));
      const D2 = Math.round(list.reduce((a, o) => a + o.d2, 0));
      const CH = D1 - D2;
      const withD1 = list.filter(o => o.d1 > 0).length;
      const withD2 = list.filter(o => o.d2 > 0).length;
      const baselineCnt = list.filter(o => !!o.s.d2Date).length;
      const singleCnt = list.length - baselineCnt;
      const up = list.filter(o => o.d1 > o.d2).length;
      const down = list.filter(o => o.d1 < o.d2).length;
      const same = list.length - up - down;
      const avg1 = withD1 ? (D1 / withD1) : 0;
      const avg2 = withD2 ? (D2 / withD2) : 0;
      const tvLt5 = list.filter(o => o.tvD1 < 5).length;
      const tvZero = list.filter(o => o.tvD1 === 0).length;
      const attnList = list
        .filter(o => (o.d2 - o.d1) > 3)
        .sort((a, b) => (a.d1 - a.d2) - (b.d1 - b.d2) || b.d2 - a.d2);

      return {
        list, D1, D2, CH, withD1, withD2, baselineCnt, singleCnt,
        up, down, same, avg1, avg2, tvLt5, tvZero, attnList,
        byPtype, byRegion, byState, byBM, byTL, byCat, bySize
      };
    }

    const nat = computeDisplaySlice(false);
    const lines = [];

    lines.push('### HISENSE DISPLAY COMPARISON MASTER METRICS (LIVE IN-MEMORY BROWSER DATASET - D-1 vs D-2):');
    lines.push(`- Authoritative Dataset Recency: Live as on ${asOfDash} (${asOfPretty}) | Max Audit Date: ${maxDateIso}`);
    lines.push('- Benchmark Definition: D-1 is the Latest Audit Visit per outlet; D-2 is the Previous Audit Visit.');
    lines.push(`- Total Monitored Outlets: ${nat.list.length.toLocaleString('en-IN')} (${nat.baselineCnt.toLocaleString('en-IN')} with D-2 baseline, ${nat.singleCnt.toLocaleString('en-IN')} single-visit new outlets at D-1) | Latest Data Date: ${asOfDash} (${asOfPretty})`);
    lines.push(`- Current D-1 Displays: ${nat.D1.toLocaleString('en-IN')} Units | Previous D-2 Displays: ${nat.D2.toLocaleString('en-IN')} Units`);
    lines.push(`- Net Change vs D-2: ${nat.CH >= 0 ? '▲ +' : '▼ '}${nat.CH.toLocaleString('en-IN')} Units (${fmtSignedPct(nat.CH, nat.D2)})`);
    lines.push(`- Outlets with Display: D-1 has ${nat.withD1.toLocaleString('en-IN')} (${nat.list.length ? Math.round((nat.withD1 / nat.list.length) * 100) : 0}% of outlets) vs D-2: ${nat.withD2.toLocaleString('en-IN')} outlets`);
    lines.push(`- Average Displays / Outlet: ${nat.avg1.toFixed(2)} on D-1 vs ${nat.avg2.toFixed(2)} on D-2 (${(nat.avg1 - nat.avg2) >= 0 ? '+' : ''}${(nat.avg1 - nat.avg2).toFixed(2)})`);
    lines.push(`- Outlet Movement / Dynamics: ${nat.up.toLocaleString('en-IN')} Outlets Gained (▲), ${nat.down.toLocaleString('en-IN')} Outlets Dropped (▼), ${nat.same.toLocaleString('en-IN')} Outlets Unchanged`);
    lines.push(`- TV Display Depth: ${nat.tvLt5.toLocaleString('en-IN')} of ${nat.list.length.toLocaleString('en-IN')} outlets have fewer than 5 TV display units at D-1 (${nat.tvZero.toLocaleString('en-IN')} with no TV display)`);
    const lostUnitsTotal = nat.attnList.reduce((a, o) => a + (o.d2 - o.d1), 0);
    const zeroedAttn = nat.attnList.filter(o => o.d1 === 0).length;
    lines.push(`- Outlets Needing Attention (Dropped > 3 units): ${nat.attnList.length} outlets (Units lost: ${Math.round(lostUnitsTotal)}, Avg drop/outlet: ${nat.attnList.length ? (lostUnitsTotal / nat.attnList.length).toFixed(1) : '0.0'}, Outlets now at zero display: ${zeroedAttn})`);
    lines.push('');

    if (hasActiveFilter) {
      const flt = computeDisplaySlice(true);
      lines.push('### 🎯 ACTIVE FILTERED VIEW METRICS ON USER SCREEN:');
      lines.push(`- Filtered Outlets: ${flt.list.length.toLocaleString('en-IN')} | D-1 Displays: ${flt.D1.toLocaleString('en-IN')} Units | D-2 Displays: ${flt.D2.toLocaleString('en-IN')} Units | Net Change: ${flt.CH >= 0 ? '▲ +' : '▼ '}${flt.CH.toLocaleString('en-IN')} Units (${fmtSignedPct(flt.CH, flt.D2)})`);
      lines.push(`- Filtered Outlets with Display: D-1 ${flt.withD1.toLocaleString('en-IN')} vs D-2 ${flt.withD2.toLocaleString('en-IN')} | Avg Displays/Outlet: ${flt.avg1.toFixed(2)} (D-1) vs ${flt.avg2.toFixed(2)} (D-2)`);
      lines.push(`- Filtered Outlet Movement: ▲ ${flt.up} Gained, ▼ ${flt.down} Dropped, ${flt.same} Unchanged | Needs Attention (>3 drop): ${flt.attnList.length} outlets`);
      lines.push('');
    }

    const domKpis = scrapeVisibleKpisAndHighlights();
    if (domKpis) {
      lines.push('### 🖥️ VERIFIED ON-SCREEN KPI TILES & KEY HIGHLIGHTS:');
      lines.push(domKpis);
      lines.push('');
    }

    // Product Type Breakdown (TV, AC, WM)
    lines.push('### DISPLAY BY PRODUCT TYPE (TV, AC, WASHING MACHINE):');
    lines.push('Product Type|D-2 Displays|D-1 Displays|Net Change|Change %');
    lines.push(`Total|${nat.D2}|${nat.D1}|${fmtSignedDiff(nat.CH)}|${fmtSignedPct(nat.CH, nat.D2)}`);
    Array.from(nat.byPtype.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        const ptLabel = g.key === 'WM' ? 'WM (Washing Machine)' : g.key;
        lines.push(`${ptLabel}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}`);
      });
    lines.push('');

    // Region Breakdown
    lines.push('### REGION-WISE DISPLAY COMPARISON:');
    lines.push('Region|Outlets|D-2 Displays|D-1 Displays|Net Change|% Growth|Avg/Outlet (D-1)|Gained|Dropped|Unchanged');
    Array.from(nat.byRegion.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        const avg = g.outlets ? (d1 / g.outlets).toFixed(2) : '0.00';
        lines.push(`${g.key}|${g.outlets}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}|${avg}|${g.up}|${g.down}|${g.same}`);
      });
    lines.push('');

    // State Breakdown
    lines.push('### STATE-WISE DISPLAY COMPARISON:');
    lines.push('State (Region)|Outlets|D-2 Displays|D-1 Displays|Net Change|% Growth|Gained|Dropped');
    Array.from(nat.byState.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        lines.push(`${g.key}|${g.outlets}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}|${g.up}|${g.down}`);
      });
    lines.push('');

    // Branch Manager Breakdown
    lines.push('### BRANCH MANAGER (BM) PERFORMANCE:');
    lines.push('Branch Manager (Region)|Outlets|D-2 Displays|D-1 Displays|Net Change|% Growth|Gained|Dropped');
    Array.from(nat.byBM.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        lines.push(`${g.key}|${g.outlets}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}|${g.up}|${g.down}`);
      });
    lines.push('');

    // Team Leader Breakdown
    lines.push('### TEAM LEADER (TL) PERFORMANCE:');
    lines.push('Team Leader (State)|Outlets|D-2 Displays|D-1 Displays|Net Change|% Growth|Gained|Dropped');
    Array.from(nat.byTL.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        lines.push(`${g.key}|${g.outlets}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}|${g.up}|${g.down}`);
      });
    lines.push('');

    // Product Category Breakdown
    lines.push('### PRODUCT CATEGORY COMPARISON:');
    lines.push('Product > Category|D-2 Displays|D-1 Displays|Net Change|% Growth');
    Array.from(nat.byCat.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        lines.push(`${g.key}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}`);
      });
    lines.push('');

    // Size / Tonnage Breakdown
    lines.push('### SIZE / TONNAGE COMPARISON:');
    lines.push('Product > Size|D-2 Displays|D-1 Displays|Net Change|% Growth');
    Array.from(nat.bySize.values())
      .sort((a, b) => b.d1 - a.d1)
      .forEach(g => {
        const d1 = Math.round(g.d1), d2 = Math.round(g.d2), chg = d1 - d2;
        lines.push(`${g.key}|${d2}|${d1}|${fmtSignedDiff(chg)}|${fmtSignedPct(chg, d2)}`);
      });
    lines.push('');

    // Outlets Needing Attention (Dropped > 3 units)
    lines.push(`### OUTLETS NEEDING ATTENTION (DROPPED > 3 UNITS: ${nat.attnList.length} OUTLETS):`);
    lines.push('Rank|Store Name|Code|State|Region|BM|TL|D-2|D-1|Net Drop|D-2 Date -> D-1 Date');
    nat.attnList.forEach((o, idx) => {
      const s = o.s;
      const d1 = Math.round(o.d1), d2 = Math.round(o.d2), chg = d1 - d2;
      lines.push(`#${idx + 1}|${s.name}|${s.code}|${s.state}|${s.region}|${s.bm}|${s.tl}|${d2}|${d1}|${fmtSignedDiff(chg)}|${s.d2Date || 'NA'} -> ${s.d1Date || 'NA'}`);
    });
    lines.push('');

    // Top 20 Outlets by D-1 Display Volume
    lines.push('### TOP 20 OUTLETS WITH HIGHEST D-1 DISPLAY VOLUME:');
    lines.push('Rank|Store Name|Code|State|Region|TL|BM|D-1 Displays|D-2 Displays|Net Change');
    nat.list.slice().sort((a, b) => b.d1 - a.d1 || b.d2 - a.d2).slice(0, 20).forEach((o, idx) => {
      const s = o.s;
      const d1 = Math.round(o.d1), d2 = Math.round(o.d2), chg = d1 - d2;
      lines.push(`#${idx + 1}|${s.name}|${s.code}|${s.state}|${s.region}|${s.tl}|${s.bm}|${d1}|${d2}|${fmtSignedDiff(chg)}`);
    });
    lines.push('');

    // Top 20 Outlets by D-2 Display Volume
    lines.push('### TOP 20 OUTLETS WITH HIGHEST D-2 DISPLAY VOLUME:');
    lines.push('Rank|Store Name|Code|State|Region|TL|BM|D-1 Displays|D-2 Displays|Net Change');
    nat.list.slice().sort((a, b) => b.d2 - a.d2 || b.d1 - a.d1).slice(0, 20).forEach((o, idx) => {
      const s = o.s;
      const d1 = Math.round(o.d1), d2 = Math.round(o.d2), chg = d1 - d2;
      lines.push(`#${idx + 1}|${s.name}|${s.code}|${s.state}|${s.region}|${s.tl}|${s.bm}|${d1}|${d2}|${fmtSignedDiff(chg)}`);
    });
    lines.push('');

    // Top 20 Gaining Outlets
    lines.push('### TOP 20 OUTLETS WITH HIGHEST DISPLAY GAIN (D-1 vs D-2):');
    lines.push('Rank|Store Name|Code|State|Region|TL|BM|D-2|D-1|Net Gain');
    nat.list.filter(o => o.d1 > o.d2).sort((a, b) => (b.d1 - b.d2) - (a.d1 - a.d2) || b.d1 - a.d1).slice(0, 20).forEach((o, idx) => {
      const s = o.s;
      const d1 = Math.round(o.d1), d2 = Math.round(o.d2), chg = d1 - d2;
      lines.push(`#${idx + 1}|${s.name}|${s.code}|${s.state}|${s.region}|${s.tl}|${s.bm}|${d2}|${d1}|${fmtSignedDiff(chg)}`);
    });

    return lines.join('\n');
  }

  function buildLiveSalesPipeTable() {
    const allRecords = window.RECORDS;
    if (!Array.isArray(allRecords) || allRecords.length === 0) {
      return '';
    }

    const maxDateIso = getPageMaxDateIso() || window.MAX_DATE || '2026-10-30';
    const asOfDash = formatDashDate(maxDateIso);
    const asOfPretty = formatPrettyDate(maxDateIso);

    const activeRows = (typeof window.getFiltered === 'function') ? window.getFiltered() : allRecords;
    const activeSales = (typeof window.getSalesRows === 'function')
      ? window.getSalesRows(activeRows)
      : activeRows.filter(r => r.anySale === 'Yes' && r.sku && r.qty > 0);

    const isPromoterFn = (typeof window.isPromoterRecord === 'function')
      ? window.isPromoterRecord
      : (r => !r.role || String(r.role).toLowerCase().includes('promoter'));

    const computeRoiFn = (typeof window.computeRoiAggregate === 'function')
      ? window.computeRoiAggregate
      : ((fRows, sRows) => {
          const m = new Map();
          fRows.forEach(r => { if (r.userCode && r.ctc && !m.has(r.userCode)) m.set(r.userCode, r.ctc); });
          const totalCtc = Array.from(m.values()).reduce((a, b) => a + b, 0) * 1.20 * 1.035;
          const totalSales = sRows.reduce((a, r) => a + (Number(r.value) || 0), 0);
          return { roi: totalCtc > 0 ? totalSales / totalCtc : 0, totalCtc, promoterCount: m.size };
        });

    const lines = [];
    lines.push('### HISENSE SALES PERFORMANCE MASTER METRICS (LIVE IN-MEMORY BROWSER DATASET):');
    lines.push(`- Authoritative Dataset Recency: Live as on ${asOfDash} (${asOfPretty}) | Max Logged Date: ${maxDateIso}`);

    // Monthly overview across all records
    const byMonth = new Map();
    allRecords.forEach(r => {
      const m = r.salesMonth || 'Unknown';
      if (!byMonth.has(m)) byMonth.set(m, { rows: [], sales: [] });
      byMonth.get(m).rows.push(r);
      if (r.anySale === 'Yes' && r.sku && r.qty > 0) byMonth.get(m).sales.push(r);
    });
    lines.push('');
    lines.push('### MONTHLY PROGRAM SUMMARY (ALL AVAILABLE MONTHS IN LIVE DATASET):');
    lines.push('Month|Submissions|Sales Rows|Units Sold|Total Sales Value (₹)|TV Sales (₹)|AC Sales (₹)|Promoters|Expected ROI');
    Array.from(byMonth.entries()).forEach(([m, obj]) => {
      const val = obj.sales.reduce((a, r) => a + (Number(r.value) || 0), 0);
      const qty = obj.sales.reduce((a, r) => a + (Number(r.qty) || 0), 0);
      const tvV = obj.sales.filter(r => r.category === 'TV').reduce((a, r) => a + (Number(r.value) || 0), 0);
      const acV = obj.sales.filter(r => r.category === 'AC').reduce((a, r) => a + (Number(r.value) || 0), 0);
      const roiM = computeRoiFn(obj.rows, obj.sales);
      lines.push(`${m}|${obj.rows.length.toLocaleString('en-IN')}|${obj.sales.length.toLocaleString('en-IN')}|${Math.round(qty).toLocaleString('en-IN')}|₹${Math.round(val).toLocaleString('en-IN')}|₹${Math.round(tvV).toLocaleString('en-IN')}|₹${Math.round(acV).toLocaleString('en-IN')}|${roiM.promoterCount}|${roiM.roi.toFixed(2)}`);
    });
    lines.push('');

    // Active Screen View Metrics (matches exact KPI tiles on index.html)
    const totalVal = activeSales.reduce((a, r) => a + (Number(r.value) || 0), 0);
    const totalUnits = activeSales.reduce((a, r) => a + (Number(r.qty) || 0), 0);
    const uniqueSkus = new Set(activeSales.map(r => r.sku).filter(Boolean)).size;
    const tvRows = activeSales.filter(r => r.category === 'TV');
    const acRows = activeSales.filter(r => r.category === 'AC');
    const tvVal = tvRows.reduce((a, r) => a + (Number(r.value) || 0), 0);
    const acVal = acRows.reduce((a, r) => a + (Number(r.value) || 0), 0);
    const tvUnits = tvRows.reduce((a, r) => a + (Number(r.qty) || 0), 0);
    const acUnits = acRows.reduce((a, r) => a + (Number(r.qty) || 0), 0);
    const b2bRows = activeSales.filter(r => r.saleType && String(r.saleType).toLowerCase().includes('b2b'));
    const retailRows = activeSales.filter(r => !r.saleType || !String(r.saleType).toLowerCase().includes('b2b'));
    const b2bVal = b2bRows.reduce((a, r) => a + (Number(r.value) || 0), 0);
    const retailVal = retailRows.reduce((a, r) => a + (Number(r.value) || 0), 0);
    const b2bUnits = b2bRows.reduce((a, r) => a + (Number(r.qty) || 0), 0);
    const retailUnits = retailRows.reduce((a, r) => a + (Number(r.qty) || 0), 0);
    const roiInfo = computeRoiFn(activeRows, activeSales);

    const activeFilterText = getActiveFilterSummaryText(getActiveFilters());
    lines.push(`### 🖥️ ACTIVE SCREEN VIEW METRICS (${activeFilterText}):`);
    lines.push(`- Filtered Submissions: ${activeRows.length.toLocaleString('en-IN')} | Sales Rows: ${activeSales.length.toLocaleString('en-IN')}`);
    lines.push(`- Total Sales Value: ₹${Math.round(totalVal).toLocaleString('en-IN')} | Total Units Sold: ${Math.round(totalUnits).toLocaleString('en-IN')} | Unique SKUs Sold: ${uniqueSkus}`);
    lines.push(`- TV Sales: ₹${Math.round(tvVal).toLocaleString('en-IN')} (${totalVal > 0 ? ((tvVal / totalVal) * 100).toFixed(1) : '0.0'}%) · ${Math.round(tvUnits).toLocaleString('en-IN')} units`);
    lines.push(`- AC Sales: ₹${Math.round(acVal).toLocaleString('en-IN')} (${totalVal > 0 ? ((acVal / totalVal) * 100).toFixed(1) : '0.0'}%) · ${Math.round(acUnits).toLocaleString('en-IN')} units`);
    lines.push(`- Retail Sales: ₹${Math.round(retailVal).toLocaleString('en-IN')} (${Math.round(retailUnits).toLocaleString('en-IN')} units) | B2B Sales: ₹${Math.round(b2bVal).toLocaleString('en-IN')} (${Math.round(b2bUnits).toLocaleString('en-IN')} units)`);
    lines.push(`- Expected ROI per Promoter: ${roiInfo.roi.toFixed(2)} (${((roiInfo.roi / 15) * 100).toFixed(1)}% of 15 target, across ${roiInfo.promoterCount} promoters, Total CTC: ₹${Math.round(roiInfo.totalCtc).toLocaleString('en-IN')})`);
    lines.push('');

    const domKpis = scrapeVisibleKpisAndHighlights();
    if (domKpis) {
      lines.push('### VERIFIED ON-SCREEN KPI TILES:');
      lines.push(domKpis);
      lines.push('');
    }

    // Zone Breakdown (Active View)
    const byZone = new Map();
    activeRows.forEach(r => {
      const z = r.zone || 'Unknown';
      if (!byZone.has(z)) byZone.set(z, { rows: [], sales: [], tvVal: 0, acVal: 0, tvQty: 0, acQty: 0, val: 0, qty: 0 });
      byZone.get(z).rows.push(r);
    });
    activeSales.forEach(r => {
      const z = r.zone || 'Unknown';
      const g = byZone.get(z);
      if (!g) return;
      g.sales.push(r);
      const v = Number(r.value) || 0, q = Number(r.qty) || 0;
      g.val += v; g.qty += q;
      if (r.category === 'TV') { g.tvVal += v; g.tvQty += q; }
      else if (r.category === 'AC') { g.acVal += v; g.acQty += q; }
    });
    lines.push('### ZONE-WISE SALES & ROI BREAKDOWN (ACTIVE VIEW):');
    lines.push('Zone|Total Sales (₹)|Units|TV Sales (₹)|AC Sales (₹)|Promoters|Expected ROI');
    Array.from(byZone.entries())
      .sort((a, b) => b[1].val - a[1].val)
      .forEach(([z, g]) => {
        const zRoi = computeRoiFn(g.rows, g.sales);
        lines.push(`${z}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}|₹${Math.round(g.tvVal).toLocaleString('en-IN')}|₹${Math.round(g.acVal).toLocaleString('en-IN')}|${zRoi.promoterCount}|${zRoi.roi.toFixed(2)}`);
      });
    lines.push('');

    // State Breakdown (Active View)
    const byState = new Map();
    activeSales.forEach(r => {
      const k = `${r.state || 'Unknown'} (${r.zone || ''})`;
      if (!byState.has(k)) byState.set(k, { val: 0, qty: 0, tx: 0 });
      const g = byState.get(k);
      g.val += Number(r.value) || 0;
      g.qty += Number(r.qty) || 0;
      g.tx += 1;
    });
    lines.push('### STATE SALES RANKING (ACTIVE VIEW):');
    lines.push('State (Zone)|Sales Value (₹)|Units Sold|Transactions');
    Array.from(byState.entries()).sort((a, b) => b[1].val - a[1].val).forEach(([k, g]) => {
      lines.push(`${k}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}|${g.tx}`);
    });
    lines.push('');

    // RSM & TL Breakdown
    const byRSM = new Map();
    const byTL = new Map();
    activeSales.forEach(r => {
      const rsm = r.rsm || 'Unknown';
      const tl = `${r.tl || 'Unknown'} [RSM: ${rsm}]`;
      if (!byRSM.has(rsm)) byRSM.set(rsm, { val: 0, qty: 0, zone: r.zone || '' });
      byRSM.get(rsm).val += Number(r.value) || 0;
      byRSM.get(rsm).qty += Number(r.qty) || 0;
      if (!byTL.has(tl)) byTL.set(tl, { val: 0, qty: 0, zone: r.zone || '' });
      byTL.get(tl).val += Number(r.value) || 0;
      byTL.get(tl).qty += Number(r.qty) || 0;
    });
    lines.push('### RSM LEADERBOARD (ACTIVE VIEW):');
    lines.push('RSM Name|Zone|Sales Value (₹)|Units Sold');
    Array.from(byRSM.entries()).sort((a, b) => b[1].val - a[1].val).forEach(([k, g]) => {
      lines.append ? lines.append(`${k}|${g.zone}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`) : lines.push(`${k}|${g.zone}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`);
    });
    lines.push('');

    lines.push('### TEAM LEADER (TL) LEADERBOARD (ACTIVE VIEW):');
    lines.push('Team Leader [RSM]|Zone|Sales Value (₹)|Units Sold');
    Array.from(byTL.entries()).sort((a, b) => b[1].val - a[1].val).forEach(([k, g]) => {
      lines.push(`${k}|${g.zone}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`);
    });
    lines.push('');

    // Product & Tech Category Breakdown
    const byCat = new Map();
    activeSales.forEach(r => {
      const k = `${r.category || 'Unknown'} > ${r.techCat || 'General'}${r.subCat ? ` (${r.subCat})` : ''}`;
      if (!byCat.has(k)) byCat.set(k, { val: 0, qty: 0 });
      byCat.get(k).val += Number(r.value) || 0;
      byCat.get(k).qty += Number(r.qty) || 0;
    });
    lines.push('### PRODUCT & TECH CATEGORY BREAKDOWN (ACTIVE VIEW):');
    lines.push('Category|Sales Value (₹)|Units Sold');
    Array.from(byCat.entries()).sort((a, b) => b[1].val - a[1].val).forEach(([k, g]) => {
      lines.push(`${k}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`);
    });
    lines.push('');

    // Promoters (Strictly Promoter Role matching index.html)
    const promMap = new Map();
    activeRows.filter(isPromoterFn).forEach(r => {
      const code = r.userCode || r.promoter;
      if (!code) return;
      if (!promMap.has(code)) {
        promMap.set(code, {
          code, name: r.promoter || code, store: r.store || '—',
          tl: r.tl || '—', zone: r.zone || '—', state: r.state || '—',
          val: 0, qty: 0
        });
      }
    });
    activeSales.filter(isPromoterFn).forEach(r => {
      const code = r.userCode || r.promoter;
      if (!code) return;
      if (!promMap.has(code)) {
        promMap.set(code, {
          code, name: r.promoter || code, store: r.store || '—',
          tl: r.tl || '—', zone: r.zone || '—', state: r.state || '—',
          val: 0, qty: 0
        });
      }
      const p = promMap.get(code);
      p.val += Number(r.value) || 0;
      p.qty += Number(r.qty) || 0;
    });

    const allProms = Array.from(promMap.values());
    const activeProms = allProms.filter(p => p.val > 0).sort((a, b) => b.val - a.val);
    const zeroProms = allProms.filter(p => p.val === 0).sort((a, b) => a.name.localeCompare(b.name));

    lines.push('### TOP 25 PROMOTERS BY SALES VALUE (ACTIVE VIEW):');
    lines.push('Rank|Promoter|User Code|Store|TL|Zone|State|Units|Sales Value (₹)');
    activeProms.slice(0, 25).forEach((p, idx) => {
      lines.push(`#${idx + 1}|${p.name}|${p.code}|${p.store}|${p.tl}|${p.zone}|${p.state}|${Math.round(p.qty)}|₹${Math.round(p.val).toLocaleString('en-IN')}`);
    });
    lines.push('');

    lines.push(`### PROMOTERS WITH ZERO SALES IN ACTIVE VIEW (${zeroProms.length} Promoters):`);
    lines.push('Promoter|Store|TL|Zone|State');
    zeroProms.slice(0, 40).forEach(p => {
      lines.push(`${p.name}|${p.store}|${p.tl}|${p.zone}|${p.state}`);
    });
    lines.push('');

    // Top 20 Stores & Top 20 SKUs
    const byStore = new Map();
    const bySku = new Map();
    activeSales.forEach(r => {
      const st = `${r.store || 'Unknown'} (${r.zone || ''})`;
      if (!byStore.has(st)) byStore.set(st, { val: 0, qty: 0 });
      byStore.get(st).val += Number(r.value) || 0;
      byStore.get(st).qty += Number(r.qty) || 0;

      if (r.sku) {
        if (!bySku.has(r.sku)) bySku.set(r.sku, { val: 0, qty: 0, cat: r.category || '' });
        bySku.get(r.sku).val += Number(r.value) || 0;
        bySku.get(r.sku).qty += Number(r.qty) || 0;
      }
    });

    lines.push('### TOP 20 STORES BY SALES VALUE (ACTIVE VIEW):');
    lines.push('Rank|Store (Zone)|Sales Value (₹)|Units Sold');
    Array.from(byStore.entries()).sort((a, b) => b[1].val - a[1].val).slice(0, 20).forEach(([k, g], idx) => {
      lines.push(`#${idx + 1}|${k}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`);
    });
    lines.push('');

    lines.push('### TOP 20 SKUs BY SALES VALUE (ACTIVE VIEW):');
    lines.push('Rank|SKU|Category|Sales Value (₹)|Units Sold');
    Array.from(bySku.entries()).sort((a, b) => b[1].val - a[1].val).slice(0, 20).forEach(([k, g], idx) => {
      lines.push(`#${idx + 1}|${k}|${g.cat}|₹${Math.round(g.val).toLocaleString('en-IN')}|${Math.round(g.qty).toLocaleString('en-IN')}`);
    });

    return lines.join('\n');
  }

  function buildLiveClientPipeTable(dashboardType) {
    try {
      if (dashboardType === 'display_comparison') {
        return buildLiveDisplayPipeTable();
      }
      return buildLiveSalesPipeTable();
    } catch (err) {
      console.warn('[AI Copilot] Client pipe table build warning:', err);
      return '';
    }
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
    const isDisplayComp = currentDashboard === 'display_comparison';
    const isDisplay = currentDashboard === 'display';
    const isAttendance = currentDashboard === 'attendance';
    const isHiring = currentDashboard === 'hiring';

    let initialChips = [];
    if (isDisplayComp) {
      initialChips = [
        'D-1 vs D-2 Display Summary',
        'Which States saw highest Gain?',
        'Top Outlets Needing Attention',
        'TV vs AC vs Washing Machine Change',
        'Branch Managers with Highest Growth'
      ];
    } else if (isDisplay) {
      initialChips = [
        'Display Overview & Total Units',
        'Top Performing Outlets by Display',
        'Category-wise Display Share (TV, AC, WM)',
        'State-wise Display Units Breakdown'
      ];
    } else if (isAttendance) {
      initialChips = [
        'Today\'s Attendance Rate & Present Count',
        'Absenteeism Summary by State',
        'Promoter Punch-in Compliance',
        'Top Regions by Attendance'
      ];
    } else if (isHiring) {
      initialChips = [
        'Hiring & Vacancy Summary',
        'Open Positions by Region',
        'Promoter Deployment Status',
        'Positions Needing Urgent Hiring'
      ];
    } else {
      initialChips = [
        'Top 5 Promoters by Sales',
        'TV vs AC Sales Breakdown',
        'Which Zone leads in Sales Value?',
        'Show Promoters with Zero Sales',
        'Expected ROI per Zone'
      ];
    }

    widget.innerHTML = `
      <!-- Right-Edge Vertical Tab Launcher -->
      <button id="aiCopilotLauncher" class="ai-copilot-launcher hisense-ai-launcher" aria-label="Toggle AI Copilot" title="Open Hisense AI Copilot" aria-expanded="false">
        <svg class="ai-copilot-chevron hisense-ai-chevron" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        <div class="ai-copilot-launcher-icon hisense-ai-launcher-icon">
          <div class="hisense-ai-launcher-pulse"></div>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
        </div>
        <span class="ai-copilot-launcher-text hisense-ai-launcher-label">AI Copilot</span>
        <span class="ai-copilot-status-dot hisense-ai-launcher-status-dot" id="hisenseLauncherDot" title="Live connected"></span>
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
              📊 Dataset update status: Live as on <b>${getPageDatasetDate() || (isSales ? '30 Oct 2026' : '31 Oct 2026')}</b>
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
              placeholder="Ask anything about ${
                isDisplayComp ? 'D-1 vs D-2 displays, growth, or outlets' :
                isDisplay ? 'product displays, categories, or outlets' :
                isAttendance ? 'attendance, present rates, or promoters' :
                isHiring ? 'vacancies, hiring status, or roles' :
                'sales, ROI, promoters, or zones'
              }..."
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
    const launcher = document.getElementById('aiCopilotLauncher') || document.getElementById('hisenseAiLauncher');
    const drawer = document.getElementById('hisenseAiDrawer');
    const closeBtn = document.getElementById('hisenseCloseBtn');
    const maxBtn = document.getElementById('hisenseMaxBtn');
    const clearBtn = document.getElementById('hisenseClearBtn');
    const statusPill = document.getElementById('hisenseStatusPill');
    const contextRefresh = document.getElementById('hisenseContextRefresh');
    const input = document.getElementById('hisenseInput');
    const sendBtn = document.getElementById('hisenseSendBtn');
    const chipsWrap = document.getElementById('hisenseChips');

    // Centralized Drawer Toggle Function
    function toggleDrawer(forceState) {
      isOpen = (typeof forceState === 'boolean') ? forceState : !isOpen;
      drawer.classList.toggle('is-open', isOpen);
      drawer.classList.toggle('open', isOpen);
      if (launcher) {
        launcher.classList.toggle('is-open', isOpen);
        launcher.classList.toggle('open', isOpen);
        launcher.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        launcher.title = isOpen ? 'Close Hisense AI Copilot' : 'Open Hisense AI Copilot';
      }
      if (isOpen) {
        if (typeof window.closeFilterSidebar === 'function') {
          window.closeFilterSidebar();
        }
        if (!isConnected) {
          checkHealth();
        }
        syncFilters();
        setTimeout(() => input.focus(), 150);
      }
    }

    window.hisenseAiAssistant = {
      closeDrawer: () => toggleDrawer(false),
      openDrawer: () => toggleDrawer(true),
      toggleDrawer: (state) => toggleDrawer(state),
    };

    // Toggle Drawer on Launcher click
    if (launcher) {
      launcher.addEventListener('click', () => {
        toggleDrawer();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        toggleDrawer(false);
      });
    }

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) {
        toggleDrawer(false);
      }
    });

    // Observe maxDateLabel and kpiGrid updates on page to synchronize dataset date & live SharePoint data
    const maxDateEl = document.getElementById('maxDateLabel');
    if (maxDateEl && window.MutationObserver) {
      try {
        const observer = new MutationObserver(() => {
          syncFilters();
        });
        observer.observe(maxDateEl, { childList: true, characterData: true, subtree: true });
      } catch (e) {}
    }
    const kpiGridEl = document.getElementById('kpiGrid');
    if (kpiGridEl && window.MutationObserver) {
      try {
        const kpiObserver = new MutationObserver(() => {
          syncFilters();
        });
        kpiObserver.observe(kpiGridEl, { childList: true });
      } catch (e) {}
    }
    window.addEventListener('hisense:data-updated', () => {
      syncFilters();
    });

    // Auto-reconnect interval when disconnected
    setInterval(() => {
      if (!isConnected && !isCheckingHealth) {
        checkHealth();
      }
    }, 15000);

    // Maximize / Restore
    if (maxBtn) {
      maxBtn.addEventListener('click', () => {
        isMaximized = !isMaximized;
        drawer.classList.toggle('is-maximized', isMaximized);
        maxBtn.title = isMaximized ? 'Restore Drawer' : 'Expand Drawer';
      });
    }

    // Clear history
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        conversationHistory = [];
        const msgs = document.getElementById('hisenseMessages');
        if (msgs) {
          const welcome = msgs.querySelector('.hisense-ai-welcome-card');
          msgs.innerHTML = '';
          if (welcome) msgs.appendChild(welcome);
        }
      });
    }

    // Status Pill Health Check on Click
    if (statusPill) {
      statusPill.addEventListener('click', () => {
        checkHealth(true);
      });
    }

    // Refresh context manually
    if (contextRefresh) {
      contextRefresh.addEventListener('click', () => {
        syncFilters();
      });
    }

    // Auto-resizing textarea
    if (input) {
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
    }

    if (sendBtn) {
      sendBtn.addEventListener('click', submitQuery);
    }

    // Suggestion chips click delegation
    if (chipsWrap) {
      chipsWrap.addEventListener('click', (e) => {
        const chip = e.target.closest('.hisense-ai-chip');
        if (chip && input) {
          input.value = chip.textContent.trim();
          submitQuery();
        }
      });
    }

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
          const asOf = getPageDatasetDate() || backendAsOf || (isSalesDashboard ? '30 Oct 2026' : '31 Oct 2026');
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
      if (lastSyncedDatasetDate && lastSyncedDatasetDate !== pageDate) {
        // Dataset recency updated from live SharePoint; drop stale model replies from history
        conversationHistory = [];
      }
      lastSyncedDatasetDate = pageDate;
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

    // Wait for in-flight live SharePoint fetch if currently running on page load
    if (window.LIVE_DATA_PROMISE) {
      try {
        await Promise.race([
          window.LIVE_DATA_PROMISE,
          new Promise(resolve => setTimeout(resolve, 8000))
        ]);
      } catch (e) {}
    }

    // Prepare payload with live in-memory client pipe table
    syncFilters();
    const activeDate = getPageDatasetDate();
    const maxDateIso = getPageMaxDateIso();
    const clientPipeTable = buildLiveClientPipeTable(currentDashboard);
    const payload = {
      prompt: prompt,
      history: conversationHistory.slice(-8),
      activeFilters: cachedActiveFilters,
      dashboard: currentDashboard,
      pageDate: activeDate,
      maxDateIso: maxDateIso,
      clientPipeTable: clientPipeTable
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
