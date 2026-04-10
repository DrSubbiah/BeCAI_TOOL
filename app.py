import streamlit as st
import re
import json
import textwrap
from pathlib import Path
from parser import parse_sas_code
from metadata import extract_bcai_metadata
from generator import generate_plotly_code
from validator import build_validation_report

st.set_page_config(
    page_title="BeCAI — SAS → Plotly Converter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --ink:     #0f0e0d;
    --paper:   #f5f2ed;
    --accent:  #e84f2e;
    --gold:    #c8972a;
    --muted:   #7a776f;
    --border:  #ddd9d0;
    --b-col:   #1a3a5c;
    --c-col:   #1a5c3a;
    --a-col:   #5c1a4a;
    --i-col:   #5c3a1a;
    --card:    #ffffff;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--paper) !important;
    color: var(--ink);
}

.main { background-color: var(--paper) !important; }
.block-container { padding: 2rem 3rem !important; max-width: 1400px; }

/* Header */
.bcai-header {
    display: block;
    border-bottom: 3px solid var(--ink);
    padding-bottom: 0.75rem;
    margin-bottom: 2rem;
}
.bcai-header .bcai-sub {
    display: block;
    margin-top: 0.3rem;
}
.bcai-wordmark {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -1px;
    color: var(--ink);
    line-height: 1;
}
.bcai-wordmark span { color: var(--accent); }
.bcai-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* Pillar badges */
.pillar-b { background: var(--b-col); color: #fff; padding: 2px 8px; border-radius: 3px; font-family: 'DM Mono', monospace; font-size: 0.75rem; font-weight: 500; }
.pillar-c { background: var(--c-col); color: #fff; padding: 2px 8px; border-radius: 3px; font-family: 'DM Mono', monospace; font-size: 0.75rem; font-weight: 500; }
.pillar-a { background: var(--a-col); color: #fff; padding: 2px 8px; border-radius: 3px; font-family: 'DM Mono', monospace; font-size: 0.75rem; font-weight: 500; }
.pillar-i { background: var(--i-col); color: #fff; padding: 2px 8px; border-radius: 3px; font-family: 'DM Mono', monospace; font-size: 0.75rem; font-weight: 500; }

/* Step indicators */
.step-bar {
    display: flex;
    gap: 0;
    margin-bottom: 2.5rem;
    border: 2px solid var(--ink);
    border-radius: 4px;
    overflow: hidden;
}
.step-item {
    flex: 1;
    padding: 0.6rem 1rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    font-weight: 500;
    text-align: center;
    background: var(--paper);
    color: var(--muted);
    border-right: 2px solid var(--ink);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    transition: all 0.2s;
}
.step-item:last-child { border-right: none; }
.step-item.active {
    background: var(--ink);
    color: var(--paper);
}
.step-item.done {
    background: var(--accent);
    color: #fff;
}

/* Cards */
.meta-card {
    background: var(--card);
    border: 1.5px solid var(--border);
    border-radius: 6px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
}
.meta-card:hover { border-color: var(--ink); }

/* Score dial */
.score-block {
    text-align: center;
    padding: 2rem;
    background: var(--ink);
    color: var(--paper);
    border-radius: 8px;
}
.score-number {
    font-family: 'Syne', sans-serif;
    font-size: 4rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
}
.score-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 0.5rem;
}

/* Match icons */
.match-full    { color: #16a34a; font-weight: 600; }
.match-approx  { color: #d97706; font-weight: 600; }
.match-none    { color: #dc2626; font-weight: 600; }

/* Code area */
.stTextArea textarea {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    background: #1a1917 !important;
    color: #e8e4dc !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 4px !important;
}

/* Buttons */
.stButton button {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    background: var(--ink) !important;
    color: var(--paper) !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.15s !important;
}
.stButton button:hover { background: var(--accent) !important; }

/* Download button */
.stDownloadButton button {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
    background: transparent !important;
    color: var(--ink) !important;
    border: 1.5px solid var(--ink) !important;
    border-radius: 3px !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}
.stDownloadButton button:hover { background: var(--ink) !important; color: var(--paper) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    border-radius: 0 !important;
    color: var(--muted) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--ink) !important;
    color: var(--paper) !important;
    border-radius: 3px 3px 0 0 !important;
}

/* Dataframe */
.stDataFrame { border: 1.5px solid var(--border) !important; border-radius: 4px !important; }

/* Expander */
.streamlit-expanderHeader {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.04em !important;
    background: var(--paper) !important;
    border: 1px solid var(--border) !important;
    border-radius: 3px !important;
}

/* Metric */
[data-testid="metric-container"] {
    background: var(--card);
    border: 1.5px solid var(--border);
    border-radius: 6px;
    padding: 1rem 1.25rem;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border) !important;
    border-radius: 6px !important;
    background: var(--card) !important;
    padding: 1rem !important;
}

div[data-testid="stFileUploader"] > div { background: transparent !important; }

/* Info / success / warning boxes */
.stAlert { border-radius: 4px !important; font-family: 'DM Sans', sans-serif !important; }

/* Divider */
hr { border-color: var(--border) !important; margin: 2rem 0 !important; }

/* Sidebar hide */
[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="bcai-header">
  <div class="bcai-wordmark">Be<span>C</span>AI</div>
  <div class="bcai-sub">SAS Plot Metadata Extractor &amp; Plotly Code Generator</div>
</div>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "sas_code" not in st.session_state:
    st.session_state.sas_code = ""
if "parsed" not in st.session_state:
    st.session_state.parsed = None
if "metadata" not in st.session_state:
    st.session_state.metadata = None
if "plotly_code" not in st.session_state:
    st.session_state.plotly_code = ""
if "validation" not in st.session_state:
    st.session_state.validation = None
if "selected_proc_idx" not in st.session_state:
    st.session_state.selected_proc_idx = 0

step = st.session_state.step

# ── Step bar ────────────────────────────────────────────────────────────────────
steps = ["01 Upload SAS", "02 BCAI Metadata", "03 Plotly Code", "04 Validation"]
bar_html = '<div class="step-bar">'
for i, s in enumerate(steps, 1):
    cls = "active" if i == step else ("done" if i < step else "")
    bar_html += f'<div class="step-item {cls}">{s}</div>'
bar_html += '</div>'
st.markdown(bar_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if step == 1:
    st.markdown("### Upload your SAS program")
    st.markdown('<p style="color:var(--muted);font-size:0.9rem;">Upload the <strong>complete</strong> SAS file — DATA steps, PROC SORT, PROC MEANS, ODS statements, TITLE/FOOTNOTE, and all plot PROCs.</p>', unsafe_allow_html=True)

    uploaded = st.file_uploader("SAS file (.sas)", type=["sas", "txt"], label_visibility="collapsed")
    if uploaded:
        st.session_state.sas_code = uploaded.read().decode("utf-8", errors="replace")
        st.success(f"✓ Loaded **{uploaded.name}** — {len(st.session_state.sas_code):,} characters")

    if st.session_state.sas_code:
        with st.expander("Preview uploaded code"):
            st.code(st.session_state.sas_code[:3000] + ("\n... [truncated]" if len(st.session_state.sas_code) > 3000 else ""), language="sas")

        if st.button("Extract BCAI Metadata →"):
            with st.spinner("Parsing SAS code..."):
                parsed = parse_sas_code(st.session_state.sas_code)
                st.session_state.parsed = parsed
                st.session_state.metadata = extract_bcai_metadata(parsed)
            st.session_state.step = 2
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — BCAI METADATA
# ══════════════════════════════════════════════════════════════════════════════
elif step == 2:
    meta = st.session_state.metadata
    parsed = st.session_state.parsed

    # Proc selector if multiple
    proc_blocks = parsed.get("proc_blocks", [])
    if len(proc_blocks) > 1:
        proc_labels = [f"{i+1}. {b.get('proc_name','PROC')} — dataset: {b.get('dataset','?')}" for i, b in enumerate(proc_blocks)]
        sel = st.selectbox("Multiple plot PROCs detected — select one to generate Plotly code for:", proc_labels, index=st.session_state.selected_proc_idx)
        st.session_state.selected_proc_idx = proc_labels.index(sel)
    elif proc_blocks:
        st.info(f"**1 plot PROC detected:** `{proc_blocks[0].get('proc_name','?')}` on dataset `{proc_blocks[0].get('dataset','?')}`")

    st.markdown("---")

    # Summary metrics
    total = len(meta)
    found = sum(1 for m in meta if m["value"] not in ("", None, "not found"))
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total BCAI Items", total)
    c2.metric("Detected", found)
    c3.metric("B — Base", sum(1 for m in meta if m["pillar"] == "B" and m["value"] not in ("", None, "not found")))
    c4.metric("C — Context", sum(1 for m in meta if m["pillar"] == "C" and m["value"] not in ("", None, "not found")))
    c5.metric("A+I", sum(1 for m in meta if m["pillar"] in ("A", "I") and m["value"] not in ("", None, "not found")))

    st.markdown("---")

    # Tabbed by pillar
    tab_b, tab_c, tab_a, tab_i, tab_all = st.tabs(["B — BASE", "C — CONTEXT", "A — AESTHETICS", "I — INFORMATION", "ALL"])

    def render_pillar_table(items, pillar):
        color_map = {"B": "#1a3a5c", "C": "#1a5c3a", "A": "#5c1a4a", "I": "#5c3a1a"}
        col = color_map.get(pillar, "#333")
        rows = ""
        for m in items:
            val = m["value"] if m["value"] not in ("", None) else "<em style='color:#aaa'>—</em>"
            found_style = "color:#16a34a;font-weight:600" if m["value"] not in ("", None, "not found") else "color:#aaa"
            rows += f"""
            <tr>
              <td style="font-family:'DM Mono',monospace;font-size:0.78rem;color:{col};padding:6px 10px;white-space:nowrap;">
                <strong>{m['pillar']}</strong>
              </td>
              <td style="padding:6px 10px;font-size:0.85rem;">{m['item']}</td>
              <td style="padding:6px 10px;font-family:'DM Mono',monospace;font-size:0.8rem;{found_style}">{val}</td>
              <td style="padding:6px 10px;font-family:'DM Mono',monospace;font-size:0.75rem;color:#888;">{m.get('sas_keyword','')}</td>
            </tr>"""
        return f"""
        <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;border:1.5px solid #ddd9d0;">
          <thead>
            <tr style="background:{col};color:#fff;">
              <th style="padding:8px 10px;text-align:left;font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.08em;">PILLAR</th>
              <th style="padding:8px 10px;text-align:left;font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.08em;">METADATA ITEM</th>
              <th style="padding:8px 10px;text-align:left;font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.08em;">EXTRACTED VALUE</th>
              <th style="padding:8px 10px;text-align:left;font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.08em;">SAS KEYWORD</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    for tab, pillar in zip([tab_b, tab_c, tab_a, tab_i], ["B", "C", "A", "I"]):
        with tab:
            items = [m for m in meta if m["pillar"] == pillar]
            st.markdown(render_pillar_table(items, pillar), unsafe_allow_html=True)

    with tab_all:
        st.markdown(render_pillar_table(meta, "ALL"), unsafe_allow_html=True)

    st.markdown("---")
    col_back, col_fwd = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    with col_fwd:
        if st.button("Generate Plotly Code →"):
            with st.spinner("Generating Plotly Python code..."):
                idx = st.session_state.selected_proc_idx
                block = proc_blocks[idx] if proc_blocks else {}
                st.session_state.plotly_code = generate_plotly_code(meta, block, parsed)
            st.session_state.step = 3
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — PLOTLY CODE
# ══════════════════════════════════════════════════════════════════════════════
elif step == 3:
    st.markdown("### Generated Plotly Python Code")
    st.markdown('<p style="color:var(--muted);font-size:0.9rem;">All BCAI-extracted properties translated to equivalent Plotly API calls.</p>', unsafe_allow_html=True)

    code = st.session_state.plotly_code
    st.code(code, language="python")

    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.download_button("⬇ Download .py", data=code, file_name="bcai_plotly_chart.py", mime="text/plain")
    with col2:
        if st.button("Run Validation →"):
            with st.spinner("Building validation report..."):
                st.session_state.validation = build_validation_report(
                    st.session_state.metadata, code
                )
            st.session_state.step = 4
            st.rerun()
    with col3:
        if st.button("← Back to Metadata"):
            st.session_state.step = 2
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
elif step == 4:
    val = st.session_state.validation
    rows = val["rows"]
    score = val["score"]
    report_text = val["report_text"]

    st.markdown("### Validation Report")

    # Score
    col_score, col_stats = st.columns([1, 3])
    with col_score:
        st.markdown(f"""
        <div class="score-block">
          <div class="score-number">{score:.0f}%</div>
          <div class="score-label">Overall Match Score</div>
        </div>""", unsafe_allow_html=True)

    with col_stats:
        full = sum(1 for r in rows if r["match"] == "FULL")
        approx = sum(1 for r in rows if r["match"] == "APPROXIMATE")
        none_ = sum(1 for r in rows if r["match"] == "NOT FOUND")
        na = sum(1 for r in rows if r["match"] == "N/A")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Full Match", full)
        c2.metric("⚠️ Approximate", approx)
        c3.metric("❌ Not Found", none_)
        c4.metric("— Not Applicable", na)

    st.markdown("---")

    # Validation table
    icon_map = {"FULL": "✅", "APPROXIMATE": "⚠️", "NOT FOUND": "❌", "N/A": "—"}
    color_map = {"FULL": "#dcfce7", "APPROXIMATE": "#fef9c3", "NOT FOUND": "#fee2e2", "N/A": "#f3f4f6"}

    table_html = """
    <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;border:1.5px solid #ddd9d0;font-size:0.83rem;">
      <thead>
        <tr style="background:#0f0e0d;color:#f5f2ed;">
          <th style="padding:9px 12px;text-align:left;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:5%;">PIL</th>
          <th style="padding:9px 12px;text-align:left;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:20%;">BCAI ITEM</th>
          <th style="padding:9px 12px;text-align:left;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:20%;">SAS VALUE</th>
          <th style="padding:9px 12px;text-align:left;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:25%;">PLOTLY EQUIVALENT</th>
          <th style="padding:9px 12px;text-align:left;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:20%;">PLOTLY VALUE</th>
          <th style="padding:9px 12px;text-align:center;font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:0.08em;width:10%;">MATCH</th>
        </tr>
      </thead>
      <tbody>"""

    for r in rows:
        bg = color_map.get(r["match"], "#fff")
        icon = icon_map.get(r["match"], "—")
        pillar_colors = {"B": "#1a3a5c", "C": "#1a5c3a", "A": "#5c1a4a", "I": "#5c3a1a"}
        pc = pillar_colors.get(r["pillar"], "#333")
        table_html += f"""
        <tr style="border-bottom:1px solid #eee;background:{bg};">
          <td style="padding:7px 12px;font-family:'DM Mono',monospace;font-weight:600;color:{pc};">{r['pillar']}</td>
          <td style="padding:7px 12px;">{r['item']}</td>
          <td style="padding:7px 12px;font-family:'DM Mono',monospace;font-size:0.78rem;color:#555;">{r['sas_value'] or '—'}</td>
          <td style="padding:7px 12px;font-family:'DM Mono',monospace;font-size:0.78rem;color:#333;">{r['plotly_prop']}</td>
          <td style="padding:7px 12px;font-family:'DM Mono',monospace;font-size:0.78rem;color:#333;">{r['plotly_value'] or '—'}</td>
          <td style="padding:7px 12px;text-align:center;font-size:1rem;">{icon}</td>
        </tr>"""

    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.download_button("⬇ Download Validation Report (.txt)", data=report_text,
                           file_name="bcai_validation_report.txt", mime="text/plain")
    with col2:
        st.download_button("⬇ Download Plotly Code (.py)", data=st.session_state.plotly_code,
                           file_name="bcai_plotly_chart.py", mime="text/plain")
    with col3:
        if st.button("← Back to Plotly Code"):
            st.session_state.step = 3
            st.rerun()

    if st.button("↺ Start Over"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
