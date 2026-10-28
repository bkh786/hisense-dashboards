"""
Hisense AI Copilot - Serverless Backend Handler (api/chat.py)
Compatible with Vercel Python Serverless and local dev_server.py.

Key features:
1. In-memory master dataset pre-loading and caching with mtime checking.
2. High-density pipe-delimited Markdown tables (>90% token reduction).
3. Dynamic Google ModelService.ListModels discovery with audio/TTS filtering.
4. Multi-model candidate failover (503, 429, 404, 500).
5. Active filter and screen context synchronization.
"""

import os
import json
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

# In-memory cached dataset store
_DATA_CACHE = {
    "sales": {"mtime": 0, "path": "", "data": None, "pipe_table": ""},
    "display_comparison": {"mtime": 0, "path": "", "data": None, "pipe_table": ""},
}

# Cache for discovered Google models to avoid repeated network calls
_MODEL_CACHE = {
    "timestamp": 0,
    "api_key": "",
    "models": []
}


def find_project_root():
    """Locate the Hisense Dashboard root directory."""
    cur = os.path.dirname(os.path.abspath(__file__))
    # If in /api, parent is project root
    if os.path.basename(cur) == "api":
        return os.path.dirname(cur)
    return cur


def resolve_data_file(filename):
    """Find a dataset JSON file across all possible deployment and serverless structures."""
    candidates = [
        os.path.join(find_project_root(), filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", filename),
        os.path.join("/var/task", filename),
        os.path.join("/var/task/api", filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def get_gemini_api_key():
    """Resolve Gemini API key from environment or .env file."""
    # 1. First check actual process environment (standard for Vercel / Cloud hosting)
    for env_var in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY"]:
        key = os.environ.get(env_var, "").strip()
        if key and key != "your_gemini_api_key_here":
            return key

    root = find_project_root()
    # 2. Check local .env files
    for fname in [".env", ".env.local", ".env.production", ".env.example"]:
        fpath = os.path.join(root, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            clean_k = k.strip()
                            if clean_k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY"):
                                file_key = v.strip().strip("'\"")
                                if file_key and file_key != "your_gemini_api_key_here":
                                    return file_key
            except Exception:
                pass

    return ""


# =========================================================================
# DATASET PRE-LOADING & HIGH-DENSITY PIPE TABLE GENERATORS
# =========================================================================

def get_sales_dataset():
    """Pre-load and cache Sales dataset with file modification timestamp checking."""
    sales_path = resolve_data_file("data_sales.json")
    root = os.path.dirname(sales_path) if os.path.exists(sales_path) else find_project_root()
    
    # Fallback to extracting from index.html if data_sales.json is missing
    if not os.path.exists(sales_path):
        index_path = resolve_data_file("index.html")
        if os.path.exists(index_path):
            try:
                import re
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                m = re.search(r'<script id="embedded-data" type="application/json">(.*?)</script>', content, re.DOTALL)
                if m:
                    extracted = json.loads(m.group(1))
                    with open(sales_path, "w", encoding="utf-8") as f_out:
                        json.dump(extracted, f_out)
            except Exception as e:
                print(f"[api/chat] Error extracting sales data: {e}")

    cache = _DATA_CACHE["sales"]
    current_mtime = os.path.getmtime(sales_path) if os.path.exists(sales_path) else 0

    if cache["data"] is not None and cache["mtime"] == current_mtime:
        return cache["data"], cache["pipe_table"]

    if not os.path.exists(sales_path):
        return [], "No sales data found on disk."

    try:
        with open(sales_path, "r", encoding="utf-8") as f:
            sales = json.load(f)
    except Exception as e:
        print(f"[api/chat] Error loading {sales_path}: {e}")
        sales = []

    # Compile High-Density Markdown Pipe Table
    pipe_table = build_sales_pipe_table(sales)

    cache["mtime"] = current_mtime
    cache["path"] = sales_path
    cache["data"] = sales
    cache["pipe_table"] = pipe_table
    print(f"[api/chat] Pre-loaded {len(sales)} sales records into memory (Pipe Table: {len(pipe_table)} chars).")
    return sales, pipe_table


def _diff_str(v):
    """Safely format integer/float differences with explicit +/- signs."""
    try:
        iv = int(round(float(v)))
        return f"{iv:+d}"
    except Exception:
        return "+0"


def build_sales_pipe_table(sales):
    """Convert sales records into compact, multi-dimensional Markdown pipe tables."""
    if not sales:
        return "No sales records available."

    total_records = len(sales)
    sales_logged = [r for r in sales if r.get("anySale") == "Yes" or r.get("value", 0) > 0]
    total_sales_value = sum(r.get("value", 0) for r in sales_logged)
    total_units = sum(r.get("qty", 0) for r in sales_logged)

    # Detect max date
    sale_dates = [r.get("saleDate") for r in sales_logged if r.get("saleDate")]
    max_date = max(sale_dates) if sale_dates else "2026-10-26"

    # Unique promoters
    promoters_map = {}
    for r in sales:
        pname = r.get("promoter", "Unknown")
        if pname not in promoters_map:
            promoters_map[pname] = {
                "name": pname,
                "store": r.get("store", ""),
                "tl": r.get("tl", ""),
                "rsm": r.get("rsm", ""),
                "zone": r.get("zone", ""),
                "state": r.get("state", ""),
                "sales_value": 0,
                "units": 0,
                "ctc": r.get("ctc", 34000) or 34000,
                "has_sale": False
            }
        if r.get("anySale") == "Yes" or r.get("value", 0) > 0:
            promoters_map[pname]["sales_value"] += r.get("value", 0)
            promoters_map[pname]["units"] += r.get("qty", 0)
            promoters_map[pname]["has_sale"] = True

    promoter_list = list(promoters_map.values())
    total_promoters = len(promoter_list)
    active_promoters = [p for p in promoter_list if p["has_sale"]]
    zero_sales_promoters = [p for p in promoter_list if not p["has_sale"]]
    total_ctc = sum(p["ctc"] for p in promoter_list)
    overall_roi = round(total_sales_value / total_ctc, 2) if total_ctc > 0 else 0

    lines = []
    lines.append("### SALES PERFORMANCE MASTER METRICS (LIVE AUTHORITATIVE DATASET):")
    lines.append(f"- Authoritative Dataset Recency: Live as on 26-Oct-2026 (Max Sale Date: {max_date})")
    lines.append(f"- Total Logged Submissions: {total_records:,} | Total Sales Logged: {len(sales_logged):,} | Total Units Sold: {total_units:,.0f} | Total Sales Value: ₹{total_sales_value:,.0f}")
    lines.append(f"- Active Promoter Pool: {total_promoters} | Promoters with Sales: {len(active_promoters)} | Zero Sales Promoters: {len(zero_sales_promoters)}")
    lines.append(f"- Overall Program Expected ROI: {overall_roi}x (Total Sales Value ÷ Total Promoter CTC @ ₹34k avg monthly CTC)")
    lines.append("")

    # 1. Zone Breakdown
    by_zone = {}
    for p in promoter_list:
        z = p["zone"] or "Unknown"
        if z not in by_zone:
            by_zone[z] = {"val": 0, "units": 0, "promoters": 0, "active": 0, "ctc": 0}
        by_zone[z]["val"] += p["sales_value"]
        by_zone[z]["units"] += p["units"]
        by_zone[z]["promoters"] += 1
        by_zone[z]["ctc"] += p["ctc"]
        if p["has_sale"]:
            by_zone[z]["active"] += 1

    lines.append("### ZONE-WISE SALES & ROI BREAKDOWN:")
    lines.append("Zone|Sales Value (₹)|Units|Promoters|Active|Zero Sales|Expected ROI")
    for z, d in sorted(by_zone.items(), key=lambda x: -x[1]["val"]):
        z_roi = round(d["val"] / d["ctc"], 2) if d["ctc"] > 0 else 0
        zero = d["promoters"] - d["active"]
        lines.append(f"{z}|₹{d['val']:,.0f}|{d['units']:,.0f}|{d['promoters']}|{d['active']}|{zero}|{z_roi}x")
    lines.append("")

    # 2. State Breakdown
    by_state = {}
    for r in sales_logged:
        st = r.get("state", "Unknown")
        zn = r.get("zone", "")
        key = f"{st} ({zn})"
        if key not in by_state:
            by_state[key] = {"val": 0, "units": 0, "tx": 0}
        by_state[key]["val"] += r.get("value", 0)
        by_state[key]["units"] += r.get("qty", 0)
        by_state[key]["tx"] += 1

    lines.append("### STATE SALES RANKING:")
    lines.append("State (Zone)|Sales Value (₹)|Units|Transactions")
    for st, d in sorted(by_state.items(), key=lambda x: -x[1]["val"]):
        lines.append(f"{st}|₹{d['val']:,.0f}|{d['units']:,.0f}|{d['tx']:,}")
    lines.append("")

    # 3. Product & Technology Category Breakdown
    by_cat = {}
    for r in sales_logged:
        cat = r.get("category") or "Unknown"
        tech = r.get("techCat") or "General"
        sub = r.get("subCat") or ""
        key = f"{cat} > {tech}" + (f" ({sub})" if sub else "")
        if key not in by_cat:
            by_cat[key] = {"val": 0, "units": 0}
        by_cat[key]["val"] += r.get("value", 0)
        by_cat[key]["units"] += r.get("qty", 0)

    lines.append("### PRODUCT & TECH CATEGORY BREAKDOWN:")
    lines.append("Product Category|Sales Value (₹)|Units Sold|Avg Unit Price (₹)")
    for c, d in sorted(by_cat.items(), key=lambda x: -x[1]["val"]):
        avg_p = round(d["val"] / d["units"]) if d["units"] > 0 else 0
        lines.append(f"{c}|₹{d['val']:,.0f}|{d['units']:,.0f}|₹{avg_p:,.0f}")
    lines.append("")

    # 4. Team Leader (TL) & RSM Hierarchy
    by_tl = {}
    for p in promoter_list:
        tl_name = p["tl"] or "Unknown"
        rsm_name = p["rsm"] or "Unknown"
        key = f"{tl_name} [RSM: {rsm_name}]"
        if key not in by_tl:
            by_tl[key] = {"val": 0, "units": 0, "promoters": 0, "active": 0, "zone": p["zone"]}
        by_tl[key]["val"] += p["sales_value"]
        by_tl[key]["units"] += p["units"]
        by_tl[key]["promoters"] += 1
        if p["has_sale"]:
            by_tl[key]["active"] += 1

    lines.append("### TEAM LEADER (TL) LEADERBOARD:")
    lines.append("Team Leader [RSM]|Zone|Sales Value (₹)|Units|Promoters (Active/Total)")
    for tl, d in sorted(by_tl.items(), key=lambda x: -x[1]["val"]):
        lines.append(f"{tl}|{d['zone']}|₹{d['val']:,.0f}|{d['units']:,.0f}|{d['active']}/{d['promoters']}")
    lines.append("")

    # 5. Store Channel Type Breakdown
    by_chan = {}
    for r in sales_logged:
        ch = r.get("channelType") or "Other"
        if ch not in by_chan:
            by_chan[ch] = {"val": 0, "units": 0, "tx": 0}
        by_chan[ch]["val"] += r.get("value", 0)
        by_chan[ch]["units"] += r.get("qty", 0)
        by_chan[ch]["tx"] += 1

    lines.append("### STORE CHANNEL TYPE BREAKDOWN:")
    lines.append("Channel Type|Sales Value (₹)|Units Sold|Transactions")
    for ch, d in sorted(by_chan.items(), key=lambda x: -x[1]["val"]):
        lines.append(f"{ch}|₹{d['val']:,.0f}|{d['units']:,.0f}|{d['tx']:,}")
    lines.append("")

    # 6. Top 25 Best-Selling SKUs
    by_sku = {}
    for r in sales_logged:
        sku = r.get("sku") or "Unknown"
        cat = r.get("category") or ""
        if sku not in by_sku:
            by_sku[sku] = {"val": 0, "units": 0, "cat": cat}
        by_sku[sku]["val"] += r.get("value", 0)
        by_sku[sku]["units"] += r.get("qty", 0)

    lines.append("### TOP 25 BEST-SELLING SKUs BY SALES VALUE:")
    lines.append("Rank|SKU Model|Category|Sales Value (₹)|Units Sold")
    for idx, (sku, d) in enumerate(sorted(by_sku.items(), key=lambda x: -x[1]["val"])[:25], 1):
        lines.append(f"#{idx}|{sku}|{d['cat']}|₹{d['val']:,.0f}|{d['units']:,.0f}")
    lines.append("")

    # 7. Top 25 Promoters
    lines.append("### TOP 25 PROMOTERS BY SALES VALUE:")
    lines.append("Rank|Promoter|Store|TL|Zone|State|Units|Sales Value (₹)|ROI")
    sorted_promoters = sorted(active_promoters, key=lambda x: -x["sales_value"])
    for idx, p in enumerate(sorted_promoters[:25], 1):
        p_roi = round(p["sales_value"] / p["ctc"], 2) if p["ctc"] > 0 else 0
        lines.append(f"#{idx}|{p['name']}|{p['store']}|{p['tl']}|{p['zone']}|{p['state']}|{p['units']:,.0f}|₹{p['sales_value']:,.0f}|{p_roi}x")
    lines.append("")

    # 8. Promoters with Zero Sales
    lines.append(f"### PROMOTERS WITH ZERO SALES ({len(zero_sales_promoters)} Promoters Need Attention):")
    lines.append("Promoter|Store / Partner|Team Leader|Zone|State")
    for p in zero_sales_promoters[:30]:
        lines.append(f"{p['name']}|{p['store']}|{p['tl']}|{p['zone']}|{p['state']}")
    lines.append("")

    # 9. Recent Sales Transactions Sample (Most recent 60 transactions)
    recent_sales = sorted(sales_logged, key=lambda x: str(x.get("saleDate") or ""), reverse=True)[:60]
    lines.append(f"### RECENT SALES TRANSACTIONS SAMPLE (LATEST AS OF {max_date}):")
    lines.append("ID|Date|Promoter|Store|Zone|State|TL|Channel|Category|Tech|Qty|Value")
    for r in recent_sales:
        lines.append(
            f"{r.get('id','')}|{r.get('saleDate','')}|{r.get('promoter','')}|{r.get('store','')}|"
            f"{r.get('zone','')}|{r.get('state','')}|{r.get('tl','')}|{r.get('channelType','')}|"
            f"{r.get('category','')}|{r.get('techCat','')}|{r.get('qty',0):.0f}|{r.get('value',0):.0f}"
        )

    return "\n".join(lines)


def get_display_comparison_dataset():
    """Pre-load and cache Display Comparison dataset with mtime checking."""
    dc_path = resolve_data_file("data_display_comparison.json")
    root = os.path.dirname(dc_path) if os.path.exists(dc_path) else find_project_root()

    # Fallback extraction from display_comparison.html if missing
    if not os.path.exists(dc_path):
        dc_html = resolve_data_file("display_comparison.html")
        if os.path.exists(dc_html):
            try:
                import re
                with open(dc_html, "r", encoding="utf-8") as f:
                    content = f.read()
                m = re.search(r'const FALLBACK = (\{.*?\});\n', content)
                if m:
                    fb = json.loads(m.group(1))
                    S = fb['s']
                    getS = lambda id: 'NA' if id == -1 else (S[id] if id < len(S) else 'NA')
                    stores = []
                    for r in fb['st']:
                        stores.append({
                            'code': getS(r[0]),
                            'name': getS(r[1]),
                            'region': getS(r[2]),
                            'state': getS(r[3]),
                            'branch': getS(r[4]),
                            'bm': getS(r[5]),
                            'tl': getS(r[6]),
                            'd1Date': None if r[7] == -1 else getS(r[7]),
                            'd2Date': None if r[8] == -1 else getS(r[8]),
                        })
                    recs = []
                    for r in fb['rc']:
                        recs.append({
                            'store': getS(r[0]),
                            'date': getS(r[1]),
                            'cnt': r[2],
                            'ptype': getS(r[3]),
                            'category': getS(r[4]),
                            'size': getS(r[5])
                        })
                    dc_data = {'maxDate': fb.get('maxDate', '2026-10-17'), 'stores': stores, 'records': recs}
                    with open(dc_path, "w", encoding="utf-8") as f_out:
                        json.dump(dc_data, f_out)
            except Exception as e:
                print(f"[api/chat] Error extracting display comparison data: {e}")

    cache = _DATA_CACHE["display_comparison"]
    current_mtime = os.path.getmtime(dc_path) if os.path.exists(dc_path) else 0

    if cache["data"] is not None and cache["mtime"] == current_mtime:
        return cache["data"], cache["pipe_table"]

    if not os.path.exists(dc_path):
        return {}, "No display comparison data found on disk."

    try:
        with open(dc_path, "r", encoding="utf-8") as f:
            dc_data = json.load(f)
    except Exception as e:
        print(f"[api/chat] Error loading {dc_path}: {e}")
        dc_data = {}

    pipe_table = build_display_comparison_pipe_table(dc_data)

    cache["mtime"] = current_mtime
    cache["path"] = dc_path
    cache["data"] = dc_data
    cache["pipe_table"] = pipe_table
    print(f"[api/chat] Pre-loaded Display Comparison dataset into memory ({len(pipe_table)} chars).")
    return dc_data, pipe_table


def build_display_comparison_pipe_table(dc_data):
    """Convert display comparison data into compact, analytical Markdown pipe tables."""
    stores_raw = dc_data.get("stores", [])
    records_raw = dc_data.get("records", [])
    if not stores_raw:
        return "No display comparison records available."

    stores = {s["code"]: s for s in stores_raw}
    outlets = {c: {"s": s, "d1": 0, "d2": 0, "tv_d1": 0, "tv_d2": 0} for c, s in stores.items()}

    by_region = {}
    by_state = {}
    by_bm = {}
    by_tl = {}
    by_prod = {}
    by_size = {}

    for s in stores.values():
        reg = s.get("region", "Unknown")
        st = s.get("state", "Unknown")
        bm = s.get("bm", "Unknown")
        tl = s.get("tl", "Unknown")

        for d, k in [(by_region, reg), (by_state, f"{st} ({reg})"), (by_bm, f"{bm} ({reg})"), (by_tl, f"{tl} ({st})")]:
            if k not in d:
                d[k] = {"d1": 0, "d2": 0, "outlets": 0}
            d[k]["outlets"] += 1

    for r in records_raw:
        c = r.get("store")
        if c in outlets:
            s = outlets[c]["s"]
            cnt = r.get("cnt", 0)
            pt = r.get("ptype", "")
            cat = r.get("category", "")
            sz = r.get("size", "")
            p_key = f"{pt} > {cat}"
            sz_key = f"{pt} > {sz}"

            if p_key not in by_prod:
                by_prod[p_key] = {"d1": 0, "d2": 0}
            if sz_key not in by_size:
                by_size[sz_key] = {"d1": 0, "d2": 0}

            if r.get("date") == s.get("d1Date"):
                outlets[c]["d1"] += cnt
                if pt == "TV":
                    outlets[c]["tv_d1"] += cnt
                by_prod[p_key]["d1"] += cnt
                by_size[sz_key]["d1"] += cnt
                by_region[s["region"]]["d1"] += cnt
                by_state[f"{s['state']} ({s['region']})"]["d1"] += cnt
                by_bm[f"{s['bm']} ({s['region']})"]["d1"] += cnt
                by_tl[f"{s['tl']} ({s['state']})"]["d1"] += cnt
            elif s.get("d2Date") and r.get("date") == s.get("d2Date"):
                outlets[c]["d2"] += cnt
                if pt == "TV":
                    outlets[c]["tv_d2"] += cnt
                by_prod[p_key]["d2"] += cnt
                by_size[sz_key]["d2"] += cnt
                by_region[s["region"]]["d2"] += cnt
                by_state[f"{s['state']} ({s['region']})"]["d2"] += cnt
                by_bm[f"{s['bm']} ({s['region']})"]["d2"] += cnt
                by_tl[f"{s['tl']} ({s['state']})"]["d2"] += cnt

    total_d1 = sum(o["d1"] for o in outlets.values())
    total_d2 = sum(o["d2"] for o in outlets.values())
    total_diff = total_d1 - total_d2
    pct_change = round(total_diff / total_d2 * 100, 1) if total_d2 > 0 else 0
    with_d1 = len([o for o in outlets.values() if o["d1"] > 0])
    with_d2 = len([o for o in outlets.values() if o["d2"] > 0])
    gaining_outlets = [o for o in outlets.values() if o["d1"] > o["d2"]]
    dropping_outlets = [o for o in outlets.values() if o["d1"] < o["d2"]]
    equal_outlets = [o for o in outlets.values() if o["d1"] == o["d2"]]
    avg_d1 = round(total_d1 / with_d1, 2) if with_d1 > 0 else 0
    avg_d2 = round(total_d2 / with_d2, 2) if with_d2 > 0 else 0

    lines = []
    lines.append("### HISENSE DISPLAY COMPARISON MASTER METRICS (D-1 vs D-2):")
    lines.append(f"- Authoritative Dataset Recency: Live as on 27-Oct-2026 (Max Audit Date: {dc_data.get('maxDate', '2026-10-27')})")
    lines.append(f"- Benchmark Definition: D-1 is the Latest Audit Visit per outlet; D-2 is the Previous Audit Visit.")
    lines.append(f"- Total Monitored Outlets: {len(outlets):,} | Latest Data Date: {dc_data.get('maxDate', '2026-10-27')}")
    lines.append(f"- Current D-1 Displays: {total_d1:,} Units | Previous D-2 Displays: {total_d2:,} Units")
    lines.append(f"- Net Change vs D-2: {'▲ +' if total_diff >= 0 else '▼ '}{total_diff:,} Units ({pct_change:+0.1f}%)")
    lines.append(f"- Outlets with Display: D-1 has {with_d1:,} ({round(with_d1/len(outlets)*100)}%) vs D-2 {with_d2:,}")
    lines.append(f"- Average Displays/Outlet: {avg_d1:.2f} on D-1 vs {avg_d2:.2f} on D-2")
    lines.append(f"- Outlet Dynamics: {len(gaining_outlets)} Outlets Gained (▲), {len(dropping_outlets)} Outlets Dropped (▼), {len(equal_outlets)} Outlets Unchanged")
    lines.append("")

    # Region Breakdown
    lines.append("### REGION-WISE DISPLAY COMPARISON:")
    lines.append("Region|Outlets|D-1 Displays|D-2 Displays|Net Change|% Growth|Avg/Outlet")
    for reg, d in sorted(by_region.items(), key=lambda x: -x[1]["d1"]):
        diff = d["d1"] - d["d2"]
        pct = round(diff / d["d2"] * 100, 1) if d["d2"] else 0
        avg = round(d["d1"] / d["outlets"], 2) if d["outlets"] else 0
        lines.append(f"{reg}|{d['outlets']}|{d['d1']}|{d['d2']}|{_diff_str(diff)}|{pct:+.1f}%|{avg}")
    lines.append("")

    # State Breakdown
    lines.append("### STATE-WISE DISPLAY COMPARISON:")
    lines.append("State (Region)|Outlets|D-1 Displays|D-2 Displays|Net Change|% Growth")
    for st, d in sorted(by_state.items(), key=lambda x: -x[1]["d1"]):
        diff = d["d1"] - d["d2"]
        pct = round(diff / d["d2"] * 100, 1) if d["d2"] else 0
        lines.append(f"{st}|{d['outlets']}|{d['d1']}|{d['d2']}|{_diff_str(diff)}|{pct:+.1f}%")
    lines.append("")

    # Branch Manager Breakdown
    lines.append("### BRANCH MANAGER (BM) PERFORMANCE:")
    lines.append("Branch Manager (Region)|Outlets|D-1 Displays|D-2 Displays|Net Change|% Growth")
    for bm, d in sorted(by_bm.items(), key=lambda x: -x[1]["d1"]):
        diff = d["d1"] - d["d2"]
        pct = round(diff / d["d2"] * 100, 1) if d["d2"] else 0
        lines.append(f"{bm}|{d['outlets']}|{d['d1']}|{d['d2']}|{_diff_str(diff)}|{pct:+.1f}%")
    lines.append("")

    # Team Leader Breakdown
    lines.append("### TEAM LEADER (TL) PERFORMANCE:")
    lines.append("Team Leader (State)|Outlets|D-1 Displays|D-2 Displays|Net Change|% Growth")
    for tl, d in sorted(by_tl.items(), key=lambda x: -x[1]["d1"]):
        diff = d["d1"] - d["d2"]
        pct = round(diff / d["d2"] * 100, 1) if d["d2"] else 0
        lines.append(f"{tl}|{d['outlets']}|{d['d1']}|{d['d2']}|{_diff_str(diff)}|{pct:+.1f}%")
    lines.append("")

    # Product Type & Category Breakdown
    lines.append("### PRODUCT TYPE & CATEGORY COMPARISON:")
    lines.append("Product > Category|D-1 Displays|D-2 Displays|Net Change|% Growth")
    for p, d in sorted(by_prod.items(), key=lambda x: -x[1]["d1"]):
        diff = d["d1"] - d["d2"]
        pct = round(diff / d["d2"] * 100, 1) if d["d2"] else 0
        lines.append(f"{p}|{d['d1']}|{d['d2']}|{_diff_str(diff)}|{pct:+.1f}%")
    lines.append("")

    # Top 15 Dropping Outlets (Attention Required)
    lines.append("### TOP 15 OUTLETS WITH BIGGEST DISPLAY DROP (ATTENTION REQUIRED):")
    lines.append("Store Name|Code|State|Region|TL|BM|D-1|D-2|Net Drop")
    sorted_drops = sorted(dropping_outlets, key=lambda x: (x["d1"] - x["d2"]))
    for o in sorted_drops[:15]:
        s = o["s"]
        drop = o["d1"] - o["d2"]
        lines.append(f"{s['name']}|{s['code']}|{s['state']}|{s['region']}|{s['tl']}|{s['bm']}|{o['d1']}|{o['d2']}|{_diff_str(drop)}")
    lines.append("")

    # Top 15 Gaining Outlets
    lines.append("### TOP 15 OUTLETS WITH HIGHEST DISPLAY GAIN:")
    lines.append("Store Name|Code|State|Region|TL|BM|D-1|D-2|Net Gain")
    sorted_gains = sorted(gaining_outlets, key=lambda x: -(x["d1"] - x["d2"]))
    for o in sorted_gains[:15]:
        s = o["s"]
        gain = o["d1"] - o["d2"]
        lines.append(f"{s['name']}|{s['code']}|{s['state']}|{s['region']}|{s['tl']}|{s['bm']}|{o['d1']}|{o['d2']}|{_diff_str(gain)}")

    return "\n".join(lines)


# =========================================================================
# SYSTEM INSTRUCTION BUILDER
# =========================================================================

def build_system_instruction(dashboard_type="sales", active_filters=None):
    """Construct complete pre-warmed prompt context with active filter awareness."""
    parts = []
    
    parts.append(
        "You are the Hisense AI Copilot, an ultra-premium data-aware analytical assistant "
        "for the Hisense India Field Operations & Sales Program (operated in partnership with Channelplay).\n"
        "Your role is to assist national leaders, Regional Sales Managers (RSMs), Branch Managers (BMs), "
        "Team Leaders (TLs), and promoters by answering queries instantly from your pre-loaded memory.\n\n"
        "### 🕒 CRITICAL DATA RECENCY & TIME CONTEXT:\n"
        "- Current Date: 27-Oct-2026.\n"
        "- The Sales Performance dataset is live and authoritative as on 26-Oct-2026.\n"
        "- The Display Comparison dataset is live and authoritative as on 27-Oct-2026.\n"
        "- DO NOT reference or state that data is from 17-Oct-2026. The 17-Oct date was a legacy benchmark.\n"
        "- Always state that data is live and current as on 26-Oct-2026 (Sales) or 27-Oct-2026 (Displays).\n\n"
        "### CORE ARCHITECTURAL INSTRUCTIONS:\n"
        "1. PRE-LOADED DATASET: The complete, authoritative Hisense dataset is provided below in compact pipe tables. "
        "Answer questions directly from this pre-loaded memory without speculating or mentioning external databases.\n"
        "2. ACCURACY FIRST: Quote exact metrics, numbers, currency values (₹), percentages, ranks, and names from the tables.\n"
        "3. ACTIVE SCREEN CONTEXT: When the user applies filters, prioritize their active view while maintaining national context.\n"
        "4. ULTRA-PREMIUM FORMATTING: Use bold key figures, clean bulleted lists, and Markdown tables (| Col 1 | Col 2 |) "
        "whenever comparing groups, leaders, or categories. Keep responses structured, concise, and executive-ready.\n"
    )

    # Active Filters Banner
    if active_filters and any(v for v in active_filters.values() if v and v != "All" and v != "all"):
        parts.append("### 🎯 USER'S ACTIVE SCREEN FILTERS:")
        for k, v in active_filters.items():
            if v and v != "All" and v != "all":
                parts.append(f"- **{k.title()}**: {v}")
        parts.append(
            "Note: The user is currently looking at the filtered slice of data above. "
            "Tailor your primary calculations and insights to this filtered subset, "
            "and contrast it with national benchmarks when helpful.\n"
        )
    else:
        parts.append("### 🎯 USER'S ACTIVE SCREEN FILTERS: None (Viewing Full National Dashboard)\n")

    # Inject pre-loaded dataset
    if dashboard_type in ("display_comparison", "display", "comparison"):
        _, pipe_table = get_display_comparison_dataset()
        parts.append("### 📊 PRE-LOADED DATASET: HISENSE DISPLAY COMPARISON (D-1 vs D-2):\n")
        parts.append(pipe_table)
    else:
        _, pipe_table = get_sales_dataset()
        parts.append("### 📊 PRE-LOADED DATASET: HISENSE SALES PERFORMANCE (PROMOTER PROGRAM):\n")
        parts.append(pipe_table)

    return "\n".join(parts)


# =========================================================================
# DYNAMIC MODEL DISCOVERY & MULTI-MODEL FAILOVER
# =========================================================================

def get_available_google_models(api_key):
    """Query Google AI ModelService dynamically to discover supported generateContent text models."""
    global _MODEL_CACHE
    now = time.time()
    
    # Return cached models if fresh (within 10 minutes)
    if _MODEL_CACHE["api_key"] == api_key and now - _MODEL_CACHE["timestamp"] < 600 and _MODEL_CACHE["models"]:
        return _MODEL_CACHE["models"]

    discovered = []
    # Filter keywords for audio, speech, embeddings, and multimodal-only models
    DISALLOWED_KEYWORDS = ("tts", "embed", "audio", "imagen", "bison", "aqa", "gecko", "live")

    for api_version in ["v1beta", "v1"]:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={api_key}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                for m in models:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        name = m.get("name", "").replace("models/", "")
                        # Filter out audio, embedding, and TTS models
                        if not any(bad in name.lower() for bad in DISALLOWED_KEYWORDS):
                            discovered.append((api_version, name))
                if discovered:
                    break
        except Exception as e:
            print(f"[api/chat] ModelService check on {api_version}: {e}")

    if discovered:
        _MODEL_CACHE = {
            "timestamp": now,
            "api_key": api_key,
            "models": discovered
        }
    return discovered


def pick_model_candidates(api_key, requested_model=""):
    """
    Return prioritized candidate pool for text generation.
    Supports dynamic models and automatic multi-tier failover.
    """
    discovered = get_available_google_models(api_key)

    # Preferred candidate sequence - prioritizing fastest, high-availability text models
    preferred = [
        ("v1beta", "gemini-3.5-flash-lite"),
        ("v1beta", "gemini-flash-lite-latest"),
        ("v1beta", "gemini-3.5-flash"),
        ("v1beta", "gemini-3.8-flash"),
        ("v1beta", "gemini-3.7-flash"),
        ("v1beta", "gemini-3.6-flash"),
        ("v1beta", "gemini-flash-latest"),
        ("v1", "gemini-3.5-flash-lite"),
        ("v1", "gemini-3.5-flash"),
    ]

    candidates = []
    if requested_model:
        clean = requested_model.replace("models/", "")
        candidates.append(("v1beta", clean))
        candidates.append(("v1", clean))

    for item in preferred:
        if item not in candidates:
            candidates.append(item)

    if discovered:
        # Prepend discovered models that match preferred names
        for ver, name in discovered:
            pair = (ver, name)
            if pair not in candidates:
                candidates.append(pair)

    return candidates


def process_chat_query(body, api_key):
    """Execute Gemini query with multi-model failover and return (status_code, result_dict)."""
    prompt = body.get("prompt", "").strip()
    if not prompt:
        return 400, {"error": "Prompt parameter is required."}

    if not api_key:
        return 401, {
            "error": "Missing Gemini API Key. Please configure GEMINI_API_KEY in your server environment variables or .env file."
        }

    dashboard_type = body.get("dashboard", "sales").lower()
    active_filters = body.get("activeFilters", {})
    history = body.get("history", [])

    system_instruction_text = build_system_instruction(dashboard_type, active_filters)

    contents = []
    # Include up to last 8 turns of conversation history for conversational context
    for msg in history[-8:]:
        role = "user" if msg.get("role") in ("user", "human") else "model"
        text = msg.get("text") or msg.get("content") or ""
        if text:
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    gemini_payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction_text}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        }
    }

    requested_model = body.get("model", "")
    candidate_models = pick_model_candidates(api_key, requested_model)

    last_error_code = 500
    last_error_msg = "Failed to communicate with Google Gemini API"

    for api_version, model_name in candidate_models:
        gemini_url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
        try:
            req_data = json.dumps(gemini_payload).encode("utf-8")
            req = urllib.request.Request(
                gemini_url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                reply_text = ""
                candidates = resp_data.get("candidates", [])
                if candidates:
                    parts_resp = candidates[0].get("content", {}).get("parts", [])
                    reply_text = "".join([p.get("text", "") for p in parts_resp])

                if not reply_text:
                    reply_text = "I analyzed the dataset but was unable to formulate a response. Please try rephrasing your query."

                return 200, {
                    "reply": reply_text,
                    "model": model_name,
                    "dashboard": dashboard_type,
                    "activeFilters": active_filters
                }

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            last_error_code = e.code
            last_error_msg = f"HTTP {e.code}: {err_body}"
            print(f"[api/chat] Model '{model_name}' ({api_version}) returned HTTP {e.code}, attempting fallback...")
            # Automatically failover on 503 (high demand), 429 (rate quota), 404 (model missing), 500
            if e.code in (503, 429, 404, 500):
                continue
            else:
                break

        except Exception as e:
            print(f"[api/chat] Error querying '{model_name}': {e}")
            last_error_msg = str(e)
            continue

    return last_error_code, {
        "error": f"All candidate models failed. Last error: {last_error_msg}"
    }


def get_status_dict(api_key):
    """Return backend health check status payload with latest dataset update dates."""
    has_key = bool(api_key and len(api_key) > 5)
    return {
        "status": "online",
        "assistant": "Hisense AI Copilot",
        "apiKeyConfigured": has_key,
        "salesAsOf": "26-Oct-2026",
        "displayAsOf": "27-Oct-2026",
        "latestDate": "26-Oct-2026"
    }


# =========================================================================
# VERCEL SERVERLESS HANDLER
# =========================================================================

class handler(BaseHTTPRequestHandler):
    """Vercel Python serverless HTTP request handler."""

    def _set_headers(self, status=200, length=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200, 0)

    def do_GET(self):
        try:
            api_key = get_gemini_api_key()
            status_payload = get_status_dict(api_key)
            resp_bytes = json.dumps(status_payload).encode("utf-8")
            self._set_headers(200, len(resp_bytes))
            self.wfile.write(resp_bytes)
            self.wfile.flush()
        except Exception as e:
            err_bytes = json.dumps({"error": f"Server Error: {str(e)}", "status": "error"}).encode("utf-8")
            self._set_headers(500, len(err_bytes))
            self.wfile.write(err_bytes)
            self.wfile.flush()

    def do_POST(self):
        try:
            api_key = get_gemini_api_key()
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            err_bytes = json.dumps({"error": f"Invalid JSON payload: {str(e)}"}).encode("utf-8")
            self._set_headers(400, len(err_bytes))
            self.wfile.write(err_bytes)
            self.wfile.flush()
            return

        try:
            status_code, result = process_chat_query(body, api_key)
            resp_bytes = json.dumps(result).encode("utf-8")
            self._set_headers(status_code, len(resp_bytes))
            self.wfile.write(resp_bytes)
            self.wfile.flush()
        except Exception as e:
            err_bytes = json.dumps({"error": f"Internal execution error: {str(e)}"}).encode("utf-8")
            self._set_headers(500, len(err_bytes))
            self.wfile.write(err_bytes)
            self.wfile.flush()
