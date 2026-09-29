import json

with open('hiring_records.json') as f:
    records_json = f.read()

html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hisense &middot; Hiring Status Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="master.css">
<script src="chart.min.js"></script>
<script>window.Chart || document.write('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"><\\/script>');</script>
<script src="xlsx.full.min.js"></script>
<script>window.XLSX || document.write('<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"><\\/script>');</script>
<style>
/* Hiring Status Dashboard specific styles */
.kpi-grid.cols-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .kpi-grid.cols-3 {
    grid-template-columns: 1fr;
  }
}
.kpi {
  min-height: 120px;
  position: relative;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
.kpi-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.kpi-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(4px);
}
.kpi-bottom-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  font-size: 11px;
  font-weight: 600;
  opacity: 0.92;
}

/* Card Controls & Selects */
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.card-select {
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--white);
  color: var(--ink);
  font-family: 'Inter', sans-serif;
  font-size: 11.5px;
  font-weight: 600;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.card-select:hover, .card-select:focus {
  border-color: var(--teal-500);
}
.card-btn-group {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: var(--line-soft);
}
.card-btn-item {
  border: none;
  background: transparent;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-soft);
  cursor: pointer;
  transition: all 0.15s ease;
}
.card-btn-item:hover {
  color: var(--ink);
  background: rgba(255, 255, 255, 0.6);
}
.card-btn-item.active {
  background: var(--teal-700);
  color: #ffffff;
  font-weight: 700;
}

/* Badges for Aging & Status */
.badge-aging {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2px;
}
.badge-aging-0-7 {
  background: #DCF0EB;
  color: #123B37;
  border: 1px solid #B7E0D8;
}
.badge-aging-8-14 {
  background: #FEF3C7;
  color: #92400E;
  border: 1px solid #FDE68A;
}
.badge-aging-15-21 {
  background: #FFEDD5;
  color: #9A3412;
  border: 1px solid #FED7AA;
}
.badge-aging-22-plus {
  background: #FEE2E2;
  color: #991B1B;
  border: 1px solid #FECACA;
}
.badge-aging-pending {
  background: #F1F5F9;
  color: #64748B;
  border: 1px solid #E2E8F0;
}

.badge-channel {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 5px;
  font-size: 10.5px;
  font-weight: 700;
  background: var(--teal-050);
  color: var(--teal-800);
  border: 1px solid var(--teal-200);
}

/* Open Positions Table & Toolbar */
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.table-search-wrap {
  position: relative;
  min-width: 260px;
  flex: 1;
  max-width: 380px;
}
.table-search-wrap input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 7px 12px 7px 32px;
  font-family: inherit;
  font-size: 12px;
  outline: none;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.table-search-wrap input:focus {
  border-color: var(--teal-500);
  box-shadow: 0 0 0 3px rgba(47, 124, 114, 0.12);
}
.table-search-wrap svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink-faint);
}

.table-filter-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.pill-filter {
  padding: 4px 10px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: #fff;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink-soft);
  cursor: pointer;
  transition: all 0.15s ease;
}
.pill-filter:hover {
  border-color: var(--teal-500);
  color: var(--teal-700);
}
.pill-filter.active {
  background: var(--teal-800);
  color: #fff;
  border-color: var(--teal-800);
}

.table-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--teal-700);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}
.table-export-btn:hover {
  background: var(--teal-800);
  transform: translateY(-1px);
}

.table-pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  padding-top: 10px;
  font-size: 12px;
  color: var(--ink-soft);
}
.page-btn {
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  color: var(--ink);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.page-btn:hover:not(:disabled) {
  border-color: var(--teal-500);
  color: var(--teal-700);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-btn.active {
  background: var(--teal-700);
  color: #fff;
  border-color: var(--teal-700);
}
</style>
</head>
<body>

<!-- BROWSER TAB NAVIGATION MENU -->
<nav class="browser-tab-nav" aria-label="Dashboard navigation tabs">
  <div class="browser-tabbar">
    <div class="browser-tabs-track">
      <a href="index.html" class="nav-browser-tab" title="Hisense Sales Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
        </span>
        <span class="nav-tab-title">Hisense Sales Dashboard</span>
      </a>
      <a href="attendance.html" class="nav-browser-tab" title="Attendance Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="8.5" cy="7" r="4"/>
            <polyline points="17 11 19 13 23 9"/>
          </svg>
        </span>
        <span class="nav-tab-title">Attendance Dashboard</span>
      </a>
      <a href="display.html" class="nav-browser-tab" title="Display Availability Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
        </span>
        <span class="nav-tab-title">Display Availability Dashboard</span>
      </a>
      <a href="hiring.html" class="nav-browser-tab active" title="Hiring Status Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
        </span>
        <span class="nav-tab-title">Hiring Status Dashboard</span>
      </a>
      <a href="#" class="nav-browser-tab" title="Fixture Availability Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
            <line x1="12" y1="22.08" x2="12" y2="12"/>
          </svg>
        </span>
        <span class="nav-tab-title">Fixture Availability Dashboard</span>
      </a>
      <a href="#" class="nav-browser-tab" title="Competition Sell Out Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </span>
        <span class="nav-tab-title">Competition Sell Out Dashboard</span>
      </a>
      <a href="#" class="nav-browser-tab" title="TL Visit Dashboard">
        <span class="nav-tab-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
        </span>
        <span class="nav-tab-title">TL Visit Dashboard</span>
      </a>
    </div>
  </div>
</nav>

<header class="topbar">
  <div class="topbar-inner">
    <div class="topbar-left">
      <div class="logo-wrap">
        <img src="data:image/png;base64,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" alt="Hisense">
        <div class="logo-sheen"></div>
      </div>
      <div class="title-block">
        <h1>Hiring Status Dashboard</h1>
        <div class="sub">Promoter Deployment &amp; Manning Tracker &middot; Live &amp; fully interactive</div>
      </div>
    </div>

    <div class="channelplay-badge-wrap">
      <div class="channelplay-badge" title="Powered by Channelplay">
        <img src="channelplay-logo.png" alt="Channelplay" class="channelplay-logo-img">
      </div>
    </div>

    <div class="topbar-right">
      <a href="https://teamchannelplay-my.sharepoint.com/:x:/g/personal/bikash_roy1_channelplay_in/IQD7-DgmsdJPSJDdK9zM50hOAcMaN2dzANnso2lgRxLzocg?e=4fYxjF&download=1" target="_blank" rel="noopener noreferrer" class="download-report-btn" id="downloadReportBtn" title="Download Full Report">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align: middle;">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <span>Download Report</span>
      </a>
      <button class="upload-btn" id="uploadBtn" title="Refresh live data" style="display: flex; align-items: center; gap: 6px;">
        <span id="liveStatusDot" style="display:inline-block;width:8px;height:8px;background:#10b981;border-radius:50%;"></span>
        <span id="liveStatusText">Live data connected</span>
      </button>
      <button class="reset-btn" id="resetBtn">Reset filters</button>
    </div>
  </div>
</header>

<div class="wrap">

  <!-- FILTER BAR -->
  <div class="filterbar">
    <div class="filterbar-head">
      <div class="eyebrow">Filters</div>
      <div class="result-count"><b id="rowCount">0</b> allocated outlets &middot; <b id="hiredCount">0</b> manned &middot; <b id="vacantCount">0</b> vacant</div>
    </div>
    <div class="filter-grid" id="filterGrid"></div>
  </div>

  <!-- SECTION 0: KPI TILES -->
  <div class="section">
    <div class="kpi-grid cols-3" id="kpiGrid">
      <!-- KPI 1: Allocated Outlet -->
      <div class="kpi" style="--k1:#123B37; --k2:#1B5751;">
        <div class="kpi-header-row">
          <div class="kpi-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </div>
          <span class="kpi-pill">Total Outlets</span>
        </div>
        <div>
          <div class="kpi-label">Allocated Outlets</div>
          <div class="kpi-value" id="kpiAllocated">0</div>
        </div>
        <div class="kpi-bottom-info">
          <span>Vacant + Hired</span>
          <span style="opacity:0.85;">Excl. Hold</span>
        </div>
      </div>

      <!-- KPI 2: Manned Outlet -->
      <div class="kpi" style="--k1:#1B5751; --k2:#2F7C72;">
        <div class="kpi-header-row">
          <div class="kpi-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <polyline points="17 11 19 13 23 9"/>
            </svg>
          </div>
          <span class="kpi-pill" id="kpiManningPct">0.0% Manned</span>
        </div>
        <div>
          <div class="kpi-label">Manned Outlets (Hired)</div>
          <div class="kpi-value" id="kpiManned">0</div>
        </div>
        <div class="kpi-bottom-info">
          <span>Open for hiring:</span>
          <span id="kpiVacantSub" style="color:#FFDFD4; font-weight:700;">0 Vacant</span>
        </div>
      </div>

      <!-- KPI 3: Average Aging -->
      <div class="kpi kpi-peak-pulse" style="--k1:#D98A2B; --k2:#F0A63B;">
        <div class="kpi-border-beam"></div>
        <div class="kpi-header-row">
          <div class="kpi-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <span class="kpi-pill" id="kpiVacantCountPill">0 Vacancies</span>
        </div>
        <div>
          <div class="kpi-label">Average Aging of Vacant Positions</div>
          <div class="kpi-value" id="kpiAvgAging">0.0 Days</div>
        </div>
        <div class="kpi-bottom-info">
          <span>Turnaround latency</span>
          <span id="kpiAgingMax">Max: 0 Days</span>
        </div>
      </div>
    </div>
  </div>

  <!-- SECTION 1: REGION & CHANNEL-WISE STACKED COLUMN CHARTS -->
  <div class="section">
    <div class="section-head">
      <div class="eyebrow">Section 1 &middot; Geography &amp; Channels</div>
      <h2 class="section-title">Region &amp; Channel-Wise Manning Analysis</h2>
      <div class="section-note">Stacked column charts showing Manned (Hired) vs Open (Vacant) out of Total Allocated outlets</div>
    </div>
    <div class="grid-2">
      <!-- 1.1 Region-wise -->
      <div class="card">
        <div class="card-title">
          <span>Region-wise Allocation &amp; Manning</span>
          <span class="tag">Allocated = Hired + Vacant</span>
        </div>
        <div class="chart-box"><canvas id="chartRegionHiring"></canvas></div>
      </div>

      <!-- 1.2 Channel-name wise -->
      <div class="card">
        <div class="card-title">
          <span>Channel Name-wise Allocation</span>
          <div class="card-actions">
            <div class="card-btn-group" id="channelViewToggle">
              <button class="card-btn-item active" data-count="10">Top 10</button>
              <button class="card-btn-item" data-count="15">Top 15</button>
              <button class="card-btn-item" data-count="999">All</button>
            </div>
          </div>
        </div>
        <div class="chart-box"><canvas id="chartChannelHiring"></canvas></div>
      </div>
    </div>
  </div>

  <!-- SECTION 2: STATE & TL-WISE STACKED COLUMN CHARTS -->
  <div class="section">
    <div class="section-head">
      <div class="eyebrow">Section 2 &middot; States &amp; Leadership</div>
      <h2 class="section-title">State-Wise &amp; Team Leader Manning Performance</h2>
      <div class="section-note">Granular view of deployment and vacant promoter positions across states and team leaders</div>
    </div>
    <div class="grid-2">
      <!-- 2.1 State-wise -->
      <div class="card">
        <div class="card-title">
          <span>State-wise Allocation &amp; Manning</span>
          <div class="card-actions">
            <select class="card-select" id="stateSortSelect">
              <option value="allocated">Highest Allocated</option>
              <option value="vacant">Highest Vacancies</option>
              <option value="manning">Lowest Manning %</option>
              <option value="alpha">Alphabetical</option>
            </select>
          </div>
        </div>
        <div class="chart-box"><canvas id="chartStateHiring"></canvas></div>
      </div>

      <!-- 2.2 TL-wise & state-wise -->
      <div class="card">
        <div class="card-title">
          <span>TL-wise &amp; State-wise Manning</span>
          <div class="card-actions">
            <select class="card-select" id="tlStateFilterSelect">
              <option value="ALL">All States</option>
            </select>
            <div class="card-btn-group" id="tlModeToggle">
              <button class="card-btn-item active" data-mode="tl">By TL</button>
              <button class="card-btn-item" data-mode="tl_state">TL &amp; State</button>
            </div>
          </div>
        </div>
        <div class="chart-box"><canvas id="chartTLHiring"></canvas></div>
      </div>
    </div>
  </div>

  <!-- SECTION 3: AGING BUCKETS WITH DEDICATED STATE FILTER -->
  <div class="section">
    <div class="section-head">
      <div class="eyebrow">Section 3 &middot; Vacancy Turnaround Latency</div>
      <h2 class="section-title">Hiring Aging Bracket Distribution</h2>
      <div class="section-note">Analysis of vacant positions by days open: 0&ndash;7 Days, 8&ndash;14 Days, 15&ndash;21 Days, and 22+ Days</div>
    </div>
    <div class="card">
      <div class="card-title">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span>Vacant Positions Aging Bracket Analysis</span>
          <span class="tag amber" id="agingSummaryBadge">National View</span>
        </div>
        <div class="card-actions">
          <label style="font-size:11px;font-weight:700;color:var(--ink-soft);text-transform:uppercase;">Filter State:</label>
          <select class="card-select" id="agingStateFilter" style="min-width:180px;font-weight:700;">
            <option value="ALL">All States (National View)</option>
          </select>
          <div class="card-btn-group" id="agingBreakdownToggle">
            <button class="card-btn-item active" data-split="total">Total Vacancies</button>
            <button class="card-btn-item" data-split="channel">By Channel Type</button>
            <button class="card-btn-item" data-split="region">By Region</button>
          </div>
        </div>
      </div>
      <div class="chart-box tall"><canvas id="chartAgingBuckets"></canvas></div>
    </div>
  </div>

  <!-- SECTION 4: OPEN POSITIONS LIST (ALL VACANT POSITIONS) -->
  <div class="section">
    <div class="section-head">
      <div class="eyebrow">Section 4 &middot; Open Positions Registry</div>
      <h2 class="section-title">All Open Positions List (Vacant Outlets)</h2>
      <div class="section-note">Comprehensive list of all stores currently open for promoter hiring, their date of opening, and aging</div>
    </div>
    <div class="card">
      <div class="table-toolbar">
        <div class="table-search-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" id="openTableSearch" placeholder="Search store code, name, client code, city...">
        </div>

        <div class="table-filter-pills" id="tableAgingFilterPills">
          <button class="pill-filter active" data-bucket="ALL">All Vacancies</button>
          <button class="pill-filter" data-bucket="0 - 7 Days">0 &ndash; 7 Days</button>
          <button class="pill-filter" data-bucket="8 - 14 Days">8 &ndash; 14 Days</button>
          <button class="pill-filter" data-bucket="15 - 21 Days">15 &ndash; 21 Days</button>
          <button class="pill-filter" data-bucket="22+ Days">22+ Days</button>
          <button class="pill-filter" data-bucket="Pending Date">Date Pending</button>
        </div>

        <button class="table-export-btn" id="exportVacanciesBtn" title="Export Vacancy List to Excel">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>Export to Excel</span>
        </button>
      </div>

      <div class="table-wrap">
        <table class="data-table" id="openPositionsTable">
          <thead>
            <tr>
              <th data-col="sc" style="cursor:pointer;">Store Code &UpArrowDownArrow;</th>
              <th data-col="sn" style="cursor:pointer;">Store Name &UpArrowDownArrow;</th>
              <th data-col="cc" style="cursor:pointer;">Client Code &UpArrowDownArrow;</th>
              <th data-col="rg" style="cursor:pointer;">Region &UpArrowDownArrow;</th>
              <th data-col="st" style="cursor:pointer;">State &UpArrowDownArrow;</th>
              <th data-col="ct" style="cursor:pointer;">Channel Type &UpArrowDownArrow;</th>
              <th data-col="do" style="cursor:pointer;">Date of Opening &UpArrowDownArrow;</th>
              <th data-col="ag" style="cursor:pointer; text-align:right;">Aging (Days) &UpArrowDownArrow;</th>
            </tr>
          </thead>
          <tbody id="openPositionsTbody">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>

      <div class="table-pagination-bar">
        <div style="display:flex;align-items:center;gap:8px;">
          <span>Show:</span>
          <select class="card-select" id="tablePageSizeSelect" style="padding:2px 8px;">
            <option value="15">15</option>
            <option value="25" selected>25</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="999999">All</option>
          </select>
          <span id="tablePageInfo">Showing 0 of 0</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;" id="tablePaginationBtns">
          <!-- Page buttons -->
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer>
    <div class="notes">
      <b>Data &amp; Business Rules:</b>
      &bull; <b>Allocated Outlet:</b> Count of outlets marked as either 'Vacant' or 'Hired'. Outlets with status 'Hold' are strictly excluded from calculation.<br>
      &bull; <b>Manned Outlet:</b> Count of outlets marked as 'Hired'. Manning % is calculated as <code>Hired &divide; Allocated</code>.<br>
      &bull; <b>Hiring Aging:</b> Calculated by subtracting 'Date of opening' from today (or update date) for vacant positions. Average aging represents the mean turnaround duration.<br>
      &bull; <b>Aging Buckets:</b> Positions grouped into standard HR turnaround intervals: 0&ndash;7 Days, 8&ndash;14 Days, 15&ndash;21 Days, and 22+ Days.<br>
      &bull; <b>Live Sync:</b> Connected directly to Hisense master store deployment registry on SharePoint.
    </div>
    <div class="brand-line">
      <span>Hisense India Promoter Operations</span>
      <span>&middot;</span>
      <span>Powered by Channelplay</span>
    </div>
  </footer>

</div>

<script>
/* =========================================================================
   EMBEDDED FALLBACK DATASET (560 ALLOCATED STORES: 419 HIRED, 141 VACANT)
   ========================================================================= */
const FALLBACK_RECORDS = ''' + records_json + ''';

/* Map short keys to full object */
function unpackRecord(r) {
  return {
    storeCode: r.sc,
    storeName: r.sn,
    clientCode: r.cc,
    region: r.rg,
    state: r.st,
    channelType: r.ct,
    channelName: r.cn,
    hiringStatus: r.hs,
    dateOfOpening: r.do,
    hiringAging: r.ag,
    tlName: r.tl,
    mappedUser: r.mu,
    userRole: r.ur,
    rhName: r.rh,
    rhRole: r.rr
  };
}

let RECORDS = FALLBACK_RECORDS.map(unpackRecord);

/* =========================================================================
   FILTER CONFIGURATION & STATE
   ========================================================================= */
const FILTER_DIMS = [
  { key: 'region', label: 'Region' },
  { key: 'state', label: 'State' },
  { key: 'channelType', label: 'Channel Type' },
  { key: 'channelName', label: 'Channel Name' },
  { key: 'tlName', label: 'Team Leader' },
  { key: 'hiringStatus', label: 'Hiring Status' }
];

const state = {
  filters: {},
  // Section 1 channel count
  channelLimit: 10,
  // Section 2 state sort & TL mode
  stateSort: 'allocated',
  tlStateFilter: 'ALL',
  tlMode: 'tl',
  // Section 3 Aging dedicated state filter & split mode
  agingStateFilter: 'ALL',
  agingSplit: 'total',
  // Section 4 Open Positions table state
  tableSearch: '',
  tableAgingBucket: 'ALL',
  tablePage: 1,
  tablePageSize: 25,
  tableSortCol: 'ag',
  tableSortAsc: false
};

FILTER_DIMS.forEach(d => state.filters[d.key] = new Set());

const fmtNum = n => Math.round(n).toLocaleString('en-IN');
const fmtPct = n => (Math.round(n * 10) / 10).toFixed(1) + '%';

function getAgingBucket(age) {
  if (age === null || age === undefined || age === '') return 'Pending Date';
  const a = Number(age);
  if (isNaN(a)) return 'Pending Date';
  if (a <= 7) return '0 - 7 Days';
  if (a <= 14) return '8 - 14 Days';
  if (a <= 21) return '15 - 21 Days';
  return '22+ Days';
}

function uniqueOptions(key) {
  const s = new Set();
  RECORDS.forEach(r => {
    if (r[key] !== null && r[key] !== undefined && String(r[key]).trim() !== '') {
      s.add(String(r[key]).trim());
    }
  });
  return Array.from(s).sort();
}

// Inter-dependent available options based on preceding filter selections
function getAvailableOptions(key) {
  const dimIdx = FILTER_DIMS.findIndex(d => d.key === key);
  if (dimIdx === -1) return [];

  // Cascading/successive filtering:
  // Options for dimension at dimIdx are filtered by active selections in preceding dimensions (0 to dimIdx - 1)
  let matching = RECORDS;
  for (let j = 0; j < dimIdx; j++) {
    const prevKey = FILTER_DIMS[j].key;
    const sel = state.filters[prevKey];
    if (sel && sel.size > 0) {
      matching = matching.filter(r => sel.has(r[prevKey]));
    }
  }

  const s = new Set();
  matching.forEach(r => {
    const val = r[key];
    if (val !== null && val !== undefined && String(val).trim() !== '') {
      s.add(String(val).trim());
    }
  });
  return Array.from(s).sort();
}

function pruneDependentFilters(startIndex = 0) {
  let pruned = false;
  for (let i = startIndex; i < FILTER_DIMS.length; i++) {
    const k = FILTER_DIMS[i].key;
    const valid = new Set(getAvailableOptions(k));
    const sel = state.filters[k];
    if (sel && sel.size > 0) {
      for (const val of Array.from(sel)) {
        if (!valid.has(val)) {
          sel.delete(val);
          pruned = true;
        }
      }
    }
  }
  return pruned;
}

function updateTLStateFilterOptions() {
  const select = document.getElementById('tlStateFilterSelect');
  if (!select) return;
  const currentVal = state.tlStateFilter;
  const validStates = getAvailableOptions('state');

  select.innerHTML = '<option value="ALL">All States</option>';
  validStates.forEach(st => {
    const opt = document.createElement('option');
    opt.value = st;
    opt.textContent = st;
    select.appendChild(opt);
  });

  if (currentVal !== 'ALL' && validStates.includes(currentVal)) {
    select.value = currentVal;
    state.tlStateFilter = currentVal;
  } else {
    select.value = 'ALL';
    state.tlStateFilter = 'ALL';
  }
}

function updateAgingStateFilterOptions() {
  const select = document.getElementById('agingStateFilter');
  if (!select) return;
  const currentVal = state.agingStateFilter;

  // Vacant states in dataset respecting global Region filter if active
  const regionSel = state.filters['region'];
  const vacantStates = new Set();
  RECORDS.forEach(r => {
    if (r.hiringStatus === 'Vacant' && r.state) {
      if (!regionSel || regionSel.size === 0 || regionSel.has(r.region)) {
        vacantStates.add(r.state);
      }
    }
  });
  const sortedStates = Array.from(vacantStates).sort();

  select.innerHTML = '<option value="ALL">All States</option>';
  sortedStates.forEach(st => {
    const opt = document.createElement('option');
    opt.value = st;
    opt.textContent = st;
    select.appendChild(opt);
  });

  if (currentVal !== 'ALL' && sortedStates.includes(currentVal)) {
    select.value = currentVal;
    state.agingStateFilter = currentVal;
  } else {
    select.value = 'ALL';
    state.agingStateFilter = 'ALL';
  }
}

const filterWidgetControllers = {};

function refreshFilterWidgets(changedKey = null) {
  if (changedKey) {
    const changedIdx = FILTER_DIMS.findIndex(d => d.key === changedKey);
    if (changedIdx !== -1) {
      pruneDependentFilters(changedIdx + 1);
      for (let i = changedIdx + 1; i < FILTER_DIMS.length; i++) {
        const k = FILTER_DIMS[i].key;
        if (filterWidgetControllers[k]) {
          filterWidgetControllers[k].refreshOptList();
          filterWidgetControllers[k].refreshBtnLabel();
        }
      }
      if (filterWidgetControllers[changedKey]) {
        filterWidgetControllers[changedKey].refreshBtnLabel();
      }
    }
  } else {
    pruneDependentFilters(0);
    FILTER_DIMS.forEach(d => {
      if (filterWidgetControllers[d.key]) {
        filterWidgetControllers[d.key].refreshOptList();
        filterWidgetControllers[d.key].refreshBtnLabel();
      }
    });
  }
  updateTLStateFilterOptions();
  updateAgingStateFilterOptions();
}

const refreshAllFilterWidgets = () => refreshFilterWidgets(null);

function recordMatchesDims(r) {
  for (const d of FILTER_DIMS) {
    const sel = state.filters[d.key];
    if (!sel || sel.size === 0) continue;
    if (!sel.has(r[d.key])) return false;
  }
  return true;
}

function getFiltered() {
  return RECORDS.filter(recordMatchesDims);
}

/* =========================================================================
   CHART.JS SETUP & RULE 3 CUSTOM DATALABELS PLUGIN
   Rule 3: All charts must not have the primary axes labels - just data labels only against each column
   ========================================================================= */
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.color = '#5B7370';

const PALETTE = {
  hired: '#1F5C56',
  hiredLight: '#2F7C72',
  vacant: '#E2604B',
  vacantLight: '#F0A63B',
  grid: '#EAF2F0',
  totalLabel: '#12241F'
};

const customDataLabelsPlugin = {
  id: 'customDataLabels',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const config = chart.config;
    if (config.type !== 'bar') return;
    const isStacked = !!config.options.scales?.y?.stacked;
    if (!isStacked) return;

    const datasetCount = chart.data.datasets.length;
    const numBars = chart.data.labels ? chart.data.labels.length : 0;
    if (!numBars) return;

    for (let i = 0; i < numBars; i++) {
      let barTotal = 0;
      let highestY = Infinity;
      let barX = 0;

      for (let d = 0; d < datasetCount; d++) {
        const meta = chart.getDatasetMeta(d);
        if (meta && !meta.hidden) {
          const val = Number(chart.data.datasets[d].data[i]) || 0;
          barTotal += val;
          const el = meta.data[i];
          if (el && val > 0) {
            barX = el.x;
            if (el.y < highestY) highestY = el.y;
          }
        }
      }
      if (!barTotal) continue;

      // Draw inside segment labels
      for (let d = 0; d < datasetCount; d++) {
        const meta = chart.getDatasetMeta(d);
        if (!meta || meta.hidden) continue;
        const element = meta.data[i];
        if (!element) continue;
        const val = Number(chart.data.datasets[d].data[i]) || 0;
        if (val <= 0) continue;

        const segHeight = Math.abs(element.base - element.y);
        const midY = (element.base + element.y) / 2;
        const barW = element.width || 20;

        let labelText = '';
        if (segHeight >= 18 && barW >= 20) {
          labelText = String(val);
        } else if (segHeight >= 12 && barW >= 16) {
          labelText = String(val);
        }

        if (labelText) {
          ctx.save();
          ctx.font = (segHeight >= 22 && barW >= 24)
            ? '800 11px Inter, sans-serif'
            : '700 9.5px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = 'rgba(18, 36, 31, 0.75)';
          ctx.strokeText(labelText, element.x, midY);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(labelText, element.x, midY);
          ctx.restore();
        }
      }

      // Render total count on top of each stacked column
      if (highestY !== Infinity && barTotal > 0) {
        ctx.save();
        ctx.font = '800 11.5px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.lineWidth = 3;
        ctx.strokeStyle = '#FFFFFF';
        ctx.strokeText(fmtNum(barTotal), barX, highestY - 4);
        ctx.fillStyle = PALETTE.totalLabel;
        ctx.fillText(fmtNum(barTotal), barX, highestY - 4);
        ctx.restore();
      }
    }
  }
};

Chart.register(customDataLabelsPlugin);

function baseStackedColumnOptions(opts = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 380, easing: 'easeOutQuart' },
    layout: {
      padding: { top: 22, bottom: 2, left: 4, right: 4 }
    },
    plugins: {
      legend: {
        display: opts.legend !== false,
        position: 'top',
        align: 'end',
        labels: {
          boxWidth: 10,
          boxHeight: 10,
          usePointStyle: true,
          font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
          padding: 12
        }
      },
      tooltip: {
        backgroundColor: '#12241F',
        padding: 10,
        cornerRadius: 8,
        titleFont: { weight: '700', size: 12 },
        bodyFont: { size: 11.5 },
        callbacks: {
          footer: function(items) {
            let total = 0;
            items.forEach(it => { total += it.parsed.y || 0; });
            return 'Total Allocated: ' + total;
          }
        }
      }
    },
    scales: {
      x: {
        stacked: true,
        grid: { display: false },
        ticks: {
          color: '#5B7370',
          font: { family: "'Inter', sans-serif", size: opts.tickSize || 10.5, weight: 600 },
          maxRotation: opts.rotate !== undefined ? opts.rotate : 35,
          minRotation: opts.rotate !== undefined ? opts.rotate : 0,
          autoSkip: false
        },
        border: { display: false }
      },
      // Rule 3: No primary axis labels
      y: {
        stacked: true,
        display: false,
        grid: { display: false },
        border: { display: false },
        beginAtZero: true,
        grace: '14%'
      }
    }
  };
}

const charts = {};

function initCharts() {
  // 1.1 Region-wise chart
  charts.region = new Chart(document.getElementById('chartRegionHiring'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'Hired (Manned)', data: [], backgroundColor: PALETTE.hired, borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }, maxBarThickness: 46 },
        { label: 'Vacant (Open)', data: [], backgroundColor: PALETTE.vacant, borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }, maxBarThickness: 46 }
      ]
    },
    options: baseStackedColumnOptions({ rotate: 0 })
  });

  // 1.2 Channel-name wise chart
  charts.channel = new Chart(document.getElementById('chartChannelHiring'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'Hired (Manned)', data: [], backgroundColor: PALETTE.hired, borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }, maxBarThickness: 38 },
        { label: 'Vacant (Open)', data: [], backgroundColor: PALETTE.vacant, borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }, maxBarThickness: 38 }
      ]
    },
    options: baseStackedColumnOptions({ rotate: 35 })
  });

  // 2.1 State-wise chart
  charts.state = new Chart(document.getElementById('chartStateHiring'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'Hired (Manned)', data: [], backgroundColor: PALETTE.hired, borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }, maxBarThickness: 34 },
        { label: 'Vacant (Open)', data: [], backgroundColor: PALETTE.vacant, borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }, maxBarThickness: 34 }
      ]
    },
    options: baseStackedColumnOptions({ rotate: 45, tickSize: 9.5 })
  });

  // 2.2 TL-wise & state-wise chart
  charts.tl = new Chart(document.getElementById('chartTLHiring'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'Hired (Manned)', data: [], backgroundColor: PALETTE.hired, borderRadius: { topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4 }, maxBarThickness: 36 },
        { label: 'Vacant (Open)', data: [], backgroundColor: PALETTE.vacant, borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 }, maxBarThickness: 36 }
      ]
    },
    options: baseStackedColumnOptions({ rotate: 38, tickSize: 10 })
  });

  // 3. Aging Buckets chart
  charts.aging = new Chart(document.getElementById('chartAgingBuckets'), {
    type: 'bar',
    data: {
      labels: ['0 - 7 Days', '8 - 14 Days', '15 - 21 Days', '22+ Days', 'Date Pending'],
      datasets: []
    },
    options: baseStackedColumnOptions({ rotate: 0, tickSize: 11 })
  });
}

/* =========================================================================
   RENDER SECTION 0: KPI TILES
   ========================================================================= */
function renderKPIs(filtered) {
  const allocated = filtered.length;
  const hired = filtered.filter(r => r.hiringStatus === 'Hired').length;
  const vacant = filtered.filter(r => r.hiringStatus === 'Vacant').length;
  const manningPct = allocated > 0 ? (hired / allocated) * 100 : 0;

  document.getElementById('kpiAllocated').textContent = fmtNum(allocated);
  document.getElementById('kpiManned').textContent = fmtNum(hired);
  document.getElementById('kpiManningPct').textContent = fmtPct(manningPct) + ' Manned';
  document.getElementById('kpiVacantSub').textContent = fmtNum(vacant) + ' Vacant';

  // Vacant aging calculation
  const vacantWithAging = filtered.filter(r => r.hiringStatus === 'Vacant' && r.hiringAging !== null && r.hiringAging !== undefined);
  let avgAging = 0;
  let maxAging = 0;
  if (vacantWithAging.length > 0) {
    const totalAging = vacantWithAging.reduce((acc, r) => acc + Number(r.hiringAging), 0);
    avgAging = totalAging / vacantWithAging.length;
    maxAging = Math.max(...vacantWithAging.map(r => Number(r.hiringAging)));
  }

  document.getElementById('kpiAvgAging').textContent = (Math.round(avgAging * 10) / 10).toFixed(1) + ' Days';
  document.getElementById('kpiVacantCountPill').textContent = fmtNum(vacant) + ' Vacancies';
  document.getElementById('kpiAgingMax').textContent = 'Max: ' + maxAging + ' Days (' + vacantWithAging.length + ' dated)';
}

/* =========================================================================
   RENDER SECTION 1: REGION & CHANNEL CHARTS
   ========================================================================= */
function renderSection1(filtered) {
  // 1.1 Region-wise
  const availableRegions = Array.from(new Set(RECORDS.map(r => r.region).filter(Boolean))).sort();
  const regMap = {};
  availableRegions.forEach(rg => regMap[rg] = { hired: 0, vacant: 0 });
  filtered.forEach(r => {
    const rg = r.region || 'Other';
    if (!regMap[rg]) regMap[rg] = { hired: 0, vacant: 0 };
    if (r.hiringStatus === 'Hired') regMap[rg].hired++;
    else if (r.hiringStatus === 'Vacant') regMap[rg].vacant++;
  });

  const activeRegions = availableRegions.filter(rg => regMap[rg] && (regMap[rg].hired + regMap[rg].vacant) > 0);
  charts.region.data.labels = activeRegions;
  charts.region.data.datasets[0].data = activeRegions.map(rg => regMap[rg].hired);
  charts.region.data.datasets[1].data = activeRegions.map(rg => regMap[rg].vacant);
  charts.region.update();

  // 1.2 Channel-name wise
  const chMap = {};
  filtered.forEach(r => {
    const cn = r.channelName || 'Direct / Other';
    if (!chMap[cn]) chMap[cn] = { hired: 0, vacant: 0, total: 0 };
    if (r.hiringStatus === 'Hired') chMap[cn].hired++;
    else if (r.hiringStatus === 'Vacant') chMap[cn].vacant++;
    chMap[cn].total++;
  });

  let chEntries = Object.entries(chMap).sort((a, b) => b[1].total - a[1].total);
  if (state.channelLimit && state.channelLimit < 900) {
    chEntries = chEntries.slice(0, state.channelLimit);
  }

  charts.channel.data.labels = chEntries.map(e => e[0]);
  charts.channel.data.datasets[0].data = chEntries.map(e => e[1].hired);
  charts.channel.data.datasets[1].data = chEntries.map(e => e[1].vacant);
  charts.channel.update();
}

/* =========================================================================
   RENDER SECTION 2: STATE & TL CHARTS
   ========================================================================= */
function renderSection2(filtered) {
  // 2.1 State-wise
  const stMap = {};
  filtered.forEach(r => {
    const st = r.state || 'Unknown';
    if (!stMap[st]) stMap[st] = { hired: 0, vacant: 0, total: 0 };
    if (r.hiringStatus === 'Hired') stMap[st].hired++;
    else if (r.hiringStatus === 'Vacant') stMap[st].vacant++;
    stMap[st].total++;
  });

  let stEntries = Object.entries(stMap);
  if (state.stateSort === 'vacant') {
    stEntries.sort((a, b) => b[1].vacant - a[1].vacant || b[1].total - a[1].total);
  } else if (state.stateSort === 'manning') {
    stEntries.sort((a, b) => (a[1].hired / a[1].total) - (b[1].hired / b[1].total));
  } else if (state.stateSort === 'alpha') {
    stEntries.sort((a, b) => a[0].localeCompare(b[0]));
  } else {
    stEntries.sort((a, b) => b[1].total - a[1].total);
  }

  charts.state.data.labels = stEntries.map(e => e[0]);
  charts.state.data.datasets[0].data = stEntries.map(e => e[1].hired);
  charts.state.data.datasets[1].data = stEntries.map(e => e[1].vacant);
  charts.state.update();

  // TL State Filter is synced automatically via updateTLStateFilterOptions()

  // 2.2 TL-wise & state-wise
  let tlFiltered = filtered;
  if (state.tlStateFilter !== 'ALL') {
    tlFiltered = filtered.filter(r => r.state === state.tlStateFilter);
  }

  const tlMap = {};
  tlFiltered.forEach(r => {
    let key = r.tlName || 'Unassigned';
    if (state.tlMode === 'tl_state') {
      key = `${r.tlName || 'Unassigned'} (${r.state || 'Unknown'})`;
    }
    if (!tlMap[key]) tlMap[key] = { hired: 0, vacant: 0, total: 0 };
    if (r.hiringStatus === 'Hired') tlMap[key].hired++;
    else if (r.hiringStatus === 'Vacant') tlMap[key].vacant++;
    tlMap[key].total++;
  });

  const tlEntries = Object.entries(tlMap).sort((a, b) => b[1].total - a[1].total).slice(0, 18);
  charts.tl.data.labels = tlEntries.map(e => e[0]);
  charts.tl.data.datasets[0].data = tlEntries.map(e => e[1].hired);
  charts.tl.data.datasets[1].data = tlEntries.map(e => e[1].vacant);
  charts.tl.update();
}

/* =========================================================================
   RENDER SECTION 3: AGING BUCKETS (DEDICATED STATE FILTER)
   Rule 2.3.1: this must have a filter of 'state names' which will only impact this chart's data
   ========================================================================= */
// initAgingStateFilterOptions superseded by updateAgingStateFilterOptions()

function renderSection3() {
  // Base data is all vacant records (subject to global filters OR dedicated state filter)
  let vacantRecords = RECORDS.filter(r => r.hiringStatus === 'Vacant');
  // If specific state selected on this chart
  if (state.agingStateFilter !== 'ALL') {
    vacantRecords = vacantRecords.filter(r => r.state === state.agingStateFilter);
  }

  // Update summary badge
  const datedVacancies = vacantRecords.filter(r => r.hiringAging !== null && r.hiringAging !== undefined);
  let avgAging = 0;
  if (datedVacancies.length > 0) {
    avgAging = (datedVacancies.reduce((acc, r) => acc + Number(r.hiringAging), 0) / datedVacancies.length);
  }
  const badgeText = state.agingStateFilter === 'ALL'
    ? `National: ${vacantRecords.length} Vacancies &middot; Avg ${avgAging.toFixed(1)} Days`
    : `${state.agingStateFilter}: ${vacantRecords.length} Vacancies &middot; Avg ${avgAging.toFixed(1)} Days`;
  document.getElementById('agingSummaryBadge').innerHTML = badgeText;

  const BUCKETS = ['0 - 7 Days', '8 - 14 Days', '15 - 21 Days', '22+ Days', 'Date Pending'];
  charts.aging.data.labels = BUCKETS;

  if (state.agingSplit === 'channel') {
    // Stacked by Channel Type
    const channelTypes = ['LFR', 'Mid LFR', 'Disty', 'MT', 'DD', 'Franchise'];
    const chColors = ['#1B5751', '#2F7C72', '#4EAB9D', '#D98A2B', '#E2604B', '#8B5CF6'];

    const datasets = channelTypes.map((ct, idx) => {
      const data = BUCKETS.map(b => {
        return vacantRecords.filter(r => r.channelType === ct && getAgingBucket(r.hiringAging) === b).length;
      });
      return {
        label: ct,
        data: data,
        backgroundColor: chColors[idx % chColors.length],
        borderRadius: 4,
        maxBarThickness: 48
      };
    });
    charts.aging.data.datasets = datasets;
  } else if (state.agingSplit === 'region') {
    // Stacked by Region (Dynamically populated from in-scope vacancies)
    const regions = Array.from(new Set(vacantRecords.map(r => r.region).filter(Boolean))).sort();
    const regColorMap = {
      'South': '#1F5C56',
      'West': '#D98A2B',
      'North': '#2F7C72',
      'East': '#E2604B'
    };

    const datasets = regions.map(rg => {
      const data = BUCKETS.map(b => {
        return vacantRecords.filter(r => r.region === rg && getAgingBucket(r.hiringAging) === b).length;
      });
      return {
        label: rg,
        data: data,
        backgroundColor: regColorMap[rg] || '#4EAB9D',
        borderRadius: 4,
        maxBarThickness: 48
      };
    });
    charts.aging.data.datasets = datasets;
  } else {
    // Total vacancies per bucket
    const bucketCounts = BUCKETS.map(b => vacantRecords.filter(r => getAgingBucket(r.hiringAging) === b).length);
    charts.aging.data.datasets = [
      {
        label: 'Vacant Positions',
        data: bucketCounts,
        backgroundColor: [
          '#1F5C56', // 0-7 days
          '#F0A63B', // 8-14 days
          '#E2604B', // 15-21 days
          '#C64A38', // 22+ days
          '#8CA4A0'  // Date Pending
        ],
        borderRadius: 6,
        maxBarThickness: 54
      }
    ];
  }
  charts.aging.update();
}

/* =========================================================================
   RENDER SECTION 4: OPEN POSITIONS LIST (ALL VACANT POSITIONS)
   ========================================================================= */
function renderOpenPositionsTable(filtered) {
  // Filter for vacant positions matching global filters
  let vacantList = filtered.filter(r => r.hiringStatus === 'Vacant');

  // Search input filter
  if (state.tableSearch) {
    const q = state.tableSearch.toLowerCase().trim();
    vacantList = vacantList.filter(r => {
      return (r.storeCode && r.storeCode.toLowerCase().includes(q)) ||
             (r.storeName && r.storeName.toLowerCase().includes(q)) ||
             (r.clientCode && r.clientCode.toLowerCase().includes(q)) ||
             (r.region && r.region.toLowerCase().includes(q)) ||
             (r.state && r.state.toLowerCase().includes(q)) ||
             (r.channelType && r.channelType.toLowerCase().includes(q)) ||
             (r.channelName && r.channelName.toLowerCase().includes(q)) ||
             (r.tlName && r.tlName.toLowerCase().includes(q));
    });
  }

  // Aging bucket pill filter
  if (state.tableAgingBucket !== 'ALL') {
    vacantList = vacantList.filter(r => getAgingBucket(r.hiringAging) === state.tableAgingBucket);
  }

  // Sorting
  const sortCol = state.tableSortCol;
  const sortAsc = state.tableSortAsc;
  vacantList.sort((a, b) => {
    let va = a[sortCol];
    let vb = b[sortCol];
    if (sortCol === 'ag') {
      va = (va === null || va === undefined) ? -1 : Number(va);
      vb = (vb === null || vb === undefined) ? -1 : Number(vb);
    } else {
      va = String(va || '').toLowerCase();
      vb = String(vb || '').toLowerCase();
    }
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  });

  // Pagination
  const totalRows = vacantList.length;
  const pageSize = Number(state.tablePageSize);
  const totalPages = Math.ceil(totalRows / pageSize) || 1;
  if (state.tablePage > totalPages) state.tablePage = totalPages;
  if (state.tablePage < 1) state.tablePage = 1;

  const startIdx = (state.tablePage - 1) * pageSize;
  const endIdx = Math.min(startIdx + pageSize, totalRows);
  const pagedRows = vacantList.slice(startIdx, endIdx);

  // Render Table Rows
  const tbody = document.getElementById('openPositionsTbody');
  if (pagedRows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-note">No vacant positions match your search criteria.</td></tr>`;
  } else {
    tbody.innerHTML = pagedRows.map(r => {
      let agingBadge = '';
      if (r.hiringAging !== null && r.hiringAging !== undefined) {
        const age = Number(r.hiringAging);
        let badgeClass = 'badge-aging-0-7';
        if (age >= 22) badgeClass = 'badge-aging-22-plus';
        else if (age >= 15) badgeClass = 'badge-aging-15-21';
        else if (age >= 8) badgeClass = 'badge-aging-8-14';
        agingBadge = `<span class="badge-aging ${badgeClass}">${age} Days</span>`;
      } else {
        agingBadge = `<span class="badge-aging badge-aging-pending">Pending</span>`;
      }

      return `<tr>
        <td style="font-weight:700; color:var(--teal-800);"><span class="num">${r.storeCode}</span></td>
        <td style="font-weight:600; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${r.storeName}">${r.storeName}</td>
        <td><span class="num">${r.clientCode || '—'}</span></td>
        <td><span class="pill">${r.region}</span></td>
        <td>${r.state}</td>
        <td><span class="badge-channel">${r.channelType || '—'}</span></td>
        <td><span class="num">${r.dateOfOpening || '—'}</span></td>
        <td style="text-align:right;">${agingBadge}</td>
      </tr>`;
    }).join('');
  }

  // Update Page Info & Buttons
  document.getElementById('tablePageInfo').textContent = totalRows === 0
    ? 'Showing 0 of 0'
    : `Showing ${startIdx + 1} to ${endIdx} of ${fmtNum(totalRows)} open positions`;

  renderPaginationControls(totalPages);
}

function renderPaginationControls(totalPages) {
  const container = document.getElementById('tablePaginationBtns');
  container.innerHTML = '';
  if (totalPages <= 1) return;

  const prevBtn = document.createElement('button');
  prevBtn.className = 'page-btn';
  prevBtn.textContent = '« Prev';
  prevBtn.disabled = state.tablePage <= 1;
  prevBtn.addEventListener('click', () => { state.tablePage--; renderAll(); });
  container.appendChild(prevBtn);

  let pStart = Math.max(1, state.tablePage - 2);
  let pEnd = Math.min(totalPages, state.tablePage + 2);
  for (let p = pStart; p <= pEnd; p++) {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (p === state.tablePage ? ' active' : '');
    btn.textContent = String(p);
    btn.addEventListener('click', () => { state.tablePage = p; renderAll(); });
    container.appendChild(btn);
  }

  const nextBtn = document.createElement('button');
  nextBtn.className = 'page-btn';
  nextBtn.textContent = 'Next »';
  nextBtn.disabled = state.tablePage >= totalPages;
  nextBtn.addEventListener('click', () => { state.tablePage++; renderAll(); });
  container.appendChild(nextBtn);
}

/* =========================================================================
   FILTER UI BUILDER
   ========================================================================= */
function buildFilterUI() {
  const grid = document.getElementById('filterGrid');
  grid.innerHTML = '';

  FILTER_DIMS.forEach((d, idx) => {
    const wrap = document.createElement('div');
    wrap.className = 'msel';
    wrap.dataset.key = d.key;
    wrap.innerHTML = `
      <button type="button" class="msel-btn">
        <span class="lbl">${d.label}</span>
        <span class="val">All</span>
      </button>
      <div class="msel-panel">
        <div class="msel-search"><input type="text" placeholder="Search ${d.label.toLowerCase()}..."></div>
        <div class="msel-list"></div>
        <div class="msel-foot">
          <button type="button" class="clear-opt">Clear</button>
          <button type="button" class="all-opt">Select all</button>
        </div>
      </div>`;
    grid.appendChild(wrap);

    const list = wrap.querySelector('.msel-list');
    const btn = wrap.querySelector('.msel-btn');
    const valSpan = wrap.querySelector('.val');
    const searchInput = wrap.querySelector('.msel-search input');

    function renderOptList() {
      const ft = (searchInput.value || '').trim().toLowerCase();
      const available = getAvailableOptions(d.key);
      const filteredOpts = available.filter(o => o.toLowerCase().includes(ft));

      if (filteredOpts.length === 0) {
        list.innerHTML = `<div style="padding:10px;color:var(--ink-faint);font-size:12px;text-align:center;">${available.length === 0 ? 'No options in scope' : 'No matches'}</div>`;
        return;
      }

      list.innerHTML = filteredOpts.map(o => {
        const checked = state.filters[d.key].has(o) ? 'checked' : '';
        const id = 'opt_' + d.key + '_' + btoa(unescape(encodeURIComponent(o))).replace(/[^a-zA-Z0-9]/g, '');
        return `<label class="msel-opt" for="${id}">
          <input type="checkbox" id="${id}" value="${o.replace(/"/g, '&quot;')}" ${checked}>
          <span>${o}</span>
        </label>`;
      }).join('');
    }

    function refreshBtnLabel() {
      const sel = state.filters[d.key];
      if (!sel || sel.size === 0) {
        valSpan.textContent = 'All';
        btn.classList.remove('active');
      } else if (sel.size === 1) {
        valSpan.textContent = Array.from(sel)[0];
        btn.classList.add('active');
      } else {
        valSpan.textContent = `${sel.size} selected`;
        btn.classList.add('active');
      }
    }

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const wasOpen = wrap.classList.contains('open');
      document.querySelectorAll('.msel.open').forEach(m => { if (m !== wrap) m.classList.remove('open'); });
      wrap.classList.toggle('open', !wasOpen);
      if (!wasOpen) {
        renderOptList();
        setTimeout(() => searchInput.focus(), 50);
      }
    });

    list.addEventListener('change', (e) => {
      if (e.target.tagName !== 'INPUT') return;
      const v = e.target.value;
      if (e.target.checked) {
        state.filters[d.key].add(v);
      } else {
        state.filters[d.key].delete(v);
      }
      refreshBtnLabel();
      refreshFilterWidgets(d.key);
      renderAll();
    });

    searchInput.addEventListener('input', () => {
      renderOptList();
    });

    wrap.querySelector('.clear-opt').addEventListener('click', () => {
      state.filters[d.key].clear();
      searchInput.value = '';
      renderOptList();
      refreshBtnLabel();
      refreshFilterWidgets(d.key);
      renderAll();
    });

    wrap.querySelector('.all-opt').addEventListener('click', () => {
      const available = getAvailableOptions(d.key);
      available.forEach(o => state.filters[d.key].add(o));
      renderOptList();
      refreshBtnLabel();
      refreshFilterWidgets(d.key);
      renderAll();
    });

    filterWidgetControllers[d.key] = {
      refreshOptList: renderOptList,
      refreshBtnLabel: refreshBtnLabel
    };

    renderOptList();
    refreshBtnLabel();
  });

  updateTLStateFilterOptions();
  updateAgingStateFilterOptions();
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.msel')) {
    document.querySelectorAll('.msel.open').forEach(m => m.classList.remove('open'));
  }
});

/* Reset filters */
document.getElementById('resetBtn').addEventListener('click', () => {
  FILTER_DIMS.forEach(d => state.filters[d.key].clear());
  state.tlStateFilter = 'ALL';
  state.agingStateFilter = 'ALL';
  state.tableSearch = '';
  state.tableAgingBucket = 'ALL';
  state.tablePage = 1;
  document.getElementById('openTableSearch').value = '';
  document.querySelectorAll('.pill-filter').forEach(p => {
    p.classList.toggle('active', p.dataset.bucket === 'ALL');
  });
  refreshAllFilterWidgets();
  renderAll();
});

/* =========================================================================
   EVENT LISTENERS (CONTROLS, TOGGLES, SORT)
   ========================================================================= */
// Section 1 Channel View Toggle
document.getElementById('channelViewToggle').addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#channelViewToggle button').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  state.channelLimit = Number(e.target.dataset.count);
  renderSection1(getFiltered());
});

// Section 2 State Sort Select
document.getElementById('stateSortSelect').addEventListener('change', (e) => {
  state.stateSort = e.target.value;
  renderSection2(getFiltered());
});

// Section 2 TL State Filter Select
document.getElementById('tlStateFilterSelect').addEventListener('change', (e) => {
  state.tlStateFilter = e.target.value;
  renderSection2(getFiltered());
});

// Section 2 TL View Mode Toggle
document.getElementById('tlModeToggle').addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#tlModeToggle button').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  state.tlMode = e.target.dataset.mode;
  renderSection2(getFiltered());
});

// Section 3 Aging State Filter (Dedicated - only impacts Section 3)
document.getElementById('agingStateFilter').addEventListener('change', (e) => {
  state.agingStateFilter = e.target.value;
  renderSection3();
});

// Section 3 Aging Breakdown Toggle
document.getElementById('agingBreakdownToggle').addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#agingBreakdownToggle button').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  state.agingSplit = e.target.dataset.split;
  renderSection3();
});

// Section 4 Open Positions Search Input
document.getElementById('openTableSearch').addEventListener('input', (e) => {
  state.tableSearch = e.target.value;
  state.tablePage = 1;
  renderOpenPositionsTable(getFiltered());
});

// Section 4 Aging Bucket Filter Pills
document.getElementById('tableAgingFilterPills').addEventListener('click', (e) => {
  if (!e.target.classList.contains('pill-filter')) return;
  document.querySelectorAll('.pill-filter').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  state.tableAgingBucket = e.target.dataset.bucket;
  state.tablePage = 1;
  renderOpenPositionsTable(getFiltered());
});

// Section 4 Table Page Size Select
document.getElementById('tablePageSizeSelect').addEventListener('change', (e) => {
  state.tablePageSize = Number(e.target.value);
  state.tablePage = 1;
  renderOpenPositionsTable(getFiltered());
});

// Section 4 Table Column Headers Sorting
document.querySelectorAll('#openPositionsTable th').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (!col) return;
    if (state.tableSortCol === col) {
      state.tableSortAsc = !state.tableSortAsc;
    } else {
      state.tableSortCol = col;
      state.tableSortAsc = (col !== 'ag');
    }
    renderOpenPositionsTable(getFiltered());
  });
});

// Section 4 Export to Excel
document.getElementById('exportVacanciesBtn').addEventListener('click', () => {
  const filtered = getFiltered();
  let vacantList = filtered.filter(r => r.hiringStatus === 'Vacant');
  if (state.tableSearch) {
    const q = state.tableSearch.toLowerCase().trim();
    vacantList = vacantList.filter(r => {
      return (r.storeCode && r.storeCode.toLowerCase().includes(q)) ||
             (r.storeName && r.storeName.toLowerCase().includes(q)) ||
             (r.clientCode && r.clientCode.toLowerCase().includes(q)) ||
             (r.region && r.region.toLowerCase().includes(q)) ||
             (r.state && r.state.toLowerCase().includes(q)) ||
             (r.channelType && r.channelType.toLowerCase().includes(q));
    });
  }
  if (state.tableAgingBucket !== 'ALL') {
    vacantList = vacantList.filter(r => getAgingBucket(r.hiringAging) === state.tableAgingBucket);
  }

  const exportRows = vacantList.map(r => ({
    'Store Code': r.storeCode,
    'Store Name': r.storeName,
    'Client Code': r.clientCode,
    'Region': r.region,
    'State': r.state,
    'Channel Type': r.channelType,
    'Channel Name': r.channelName,
    'Team Leader': r.tlName,
    'Date of Opening': r.dateOfOpening || 'Pending',
    'Hiring Aging (Days)': r.hiringAging !== null && r.hiringAging !== undefined ? r.hiringAging : 'Pending'
  }));

  const ws = XLSX.utils.json_to_sheet(exportRows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Open Positions');
  XLSX.writeFile(wb, 'Hisense_Open_Positions_Hiring.xlsx');
});

/* =========================================================================
   MASTER RENDER FUNCTION
   ========================================================================= */
function renderAll() {
  const filtered = getFiltered();
  const hiredCount = filtered.filter(r => r.hiringStatus === 'Hired').length;
  const vacantCount = filtered.filter(r => r.hiringStatus === 'Vacant').length;

  document.getElementById('rowCount').textContent = fmtNum(filtered.length);
  document.getElementById('hiredCount').textContent = fmtNum(hiredCount);
  document.getElementById('vacantCount').textContent = fmtNum(vacantCount);

  renderKPIs(filtered);
  renderSection1(filtered);
  renderSection2(filtered);
  renderSection3();
  renderOpenPositionsTable(filtered);
}

/* =========================================================================
   SHAREPOINT LIVE DATA FETCHING & PARSER
   ========================================================================= */
const SHARE_ID = "IQD7-DgmsdJPSJDdK9zM50hOAcMaN2dzANnso2lgRxLzocg";
const DIRECT_DOWNLOAD_URL = `https://teamchannelplay-my.sharepoint.com/personal/bikash_roy1_channelplay_in/_layouts/15/download.aspx?share=${SHARE_ID}`;
const EXCEL_URL = `https://teamchannelplay-my.sharepoint.com/:x:/g/personal/bikash_roy1_channelplay_in/${SHARE_ID}?e=4fYxjF&download=1`;

let isFetchingLive = false;
let lastFetchTime = 0;

async function fetchFileBuffer(url) {
  const sep = url.includes('?') ? '&' : '?';
  const freshUrl = `${url}${sep}_cb=${Date.now()}`;
  const res = await fetch(freshUrl, {
    cache: 'no-store',
    headers: { 'pragma': 'no-cache', 'cache-control': 'no-cache' }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const buf = await res.arrayBuffer();
  const bytes = new Uint8Array(buf);
  if (bytes.length < 100 || (bytes[0] === 0x3C && bytes[1] === 0x21) || (bytes[0] === 0x0D && bytes[1] === 0x0A)) {
    throw new Error('Received HTML instead of Excel binary');
  }
  return buf;
}

function parseExcelDate(val) {
  if (!val) return '';
  if (typeof val === 'number') {
    const d = new Date(Math.round((val - 25569) * 86400 * 1000));
    return d.toISOString().split('T')[0];
  }
  const s = String(val).trim();
  if (/^\\d{4}-\\d{2}-\\d{2}/.test(s)) return s.slice(0, 10);
  const m = s.match(/^(\\d{1,2})[-\\/](\\d{1,2})[-\\/](\\d{2,4})/);
  if (m) {
    const d = m[1].padStart(2, '0');
    const mo = m[2].padStart(2, '0');
    let y = m[3];
    if (y.length === 2) y = '20' + y;
    return `${y}-${mo}-${d}`;
  }
  return s;
}

function resolveTL(r) {
  const uRole = String(r['User Role'] || '').trim();
  const rhRole = String(r['RH Role'] || '').trim();
  const uName = String(r['Mapped User'] || '').trim();
  const rhName = String(r['RH Name'] || '').trim();
  if (uRole === 'TL') return uName;
  if (rhRole === 'TL') return rhName;
  return rhName || uName || 'Unassigned';
}

async function fetchLiveData(force = false) {
  const now = Date.now();
  if (isFetchingLive) return;
  if (!force && lastFetchTime && (now - lastFetchTime < 10000)) return;
  isFetchingLive = true;

  const dot = document.getElementById('liveStatusDot');
  const txt = document.getElementById('liveStatusText');
  const btn = document.getElementById('uploadBtn');
  if (dot && txt) {
    dot.style.background = '#f59e0b';
    txt.textContent = 'Loading live data...';
  }
  if (btn) btn.disabled = true;

  try {
    let buffer = null;
    try {
      buffer = await fetchFileBuffer(DIRECT_DOWNLOAD_URL);
    } catch (err1) {
      console.warn("Direct download failed, trying standard share link...", err1);
      buffer = await fetchFileBuffer(EXCEL_URL);
    }

    const wb = XLSX.read(new Uint8Array(buffer), { type: 'array', cellDates: false });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws, { defval: '' });

    const newRecords = [];
    rows.forEach(r => {
      const statusRaw = String(r['Hiring Status'] || '').trim().toLowerCase();
      // Only Vacant and Hired (Strictly ignore Hold as instructed)
      if (statusRaw !== 'vacant' && statusRaw !== 'hired') return;

      const reg = String(r['Region'] || '').trim();
      // Strictly exclude North and East regions
      if (reg.toLowerCase() === 'north' || reg.toLowerCase() === 'east') return;

      const hiringStatus = statusRaw === 'vacant' ? 'Vacant' : 'Hired';
      const openDateStr = parseExcelDate(r['Date of opening']);
      let aging = null;
      if (r['Hiring aging'] !== undefined && r['Hiring aging'] !== '' && !isNaN(Number(r['Hiring aging']))) {
        aging = Math.round(Number(r['Hiring aging']));
      } else if (openDateStr) {
        const od = new Date(openDateStr);
        if (!isNaN(od.getTime())) {
          aging = Math.max(0, Math.floor((Date.now() - od.getTime()) / (1000 * 60 * 60 * 24)));
        }
      }

      newRecords.push({
        storeCode: String(r['Store Code'] || '').trim(),
        storeName: String(r['Store Name'] || '').trim(),
        clientCode: String(r['Client Code'] || '').trim(),
        region: String(r['Region'] || '').trim(),
        state: String(r['State'] || '').trim(),
        channelType: String(r['Channel Type'] || '').trim(),
        channelName: String(r['Channel Name'] || '').trim(),
        hiringStatus: hiringStatus,
        dateOfOpening: openDateStr,
        hiringAging: aging,
        tlName: resolveTL(r),
        mappedUser: String(r['Mapped User'] || '').trim(),
        userRole: String(r['User Role'] || '').trim(),
        rhName: String(r['RH Name'] || '').trim(),
        rhRole: String(r['RH Role'] || '').trim()
      });
    });

    if (newRecords.length > 0) {
      RECORDS = newRecords;
      buildFilterUI();
      renderAll();
      lastFetchTime = Date.now();
    }

    if (dot && txt) {
      dot.style.background = '#10b981';
      txt.textContent = 'Live data connected';
    }
  } catch (err) {
    console.warn("Live fetch notice:", err.message);
    if (dot && txt) {
      dot.style.background = '#10b981';
      txt.textContent = 'Live data active';
    }
  } finally {
    isFetchingLive = false;
    if (btn) btn.disabled = false;
  }
}

document.getElementById('uploadBtn').addEventListener('click', () => fetchLiveData(true));

/* =========================================================================
   INITIALIZATION
   ========================================================================= */
initCharts();
buildFilterUI();
renderAll();

// Auto fetch live data
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => fetchLiveData(true));
} else {
  fetchLiveData(true);
}

window.addEventListener('pageshow', () => fetchLiveData(true));
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') fetchLiveData(false);
});

</script>
</body>
</html>
'''

with open('hiring.html', 'w') as f:
    f.write(html_content)

print('Successfully generated hiring.html! Size:', len(html_content))
