"""
BESS Development Risk Radar — Streamlit App
Screens BESS projects by development-side risk across NYISO & ERCOT.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_permitting, load_region_risk
from scoring import apply_scores, fetch_price_volatility

# ---------------------------------------------------------------------------
# Page config  (must be the very first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BESS Dev Risk Radar",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme palette definitions
# ---------------------------------------------------------------------------
DARK_THEME = {
    "bg":       "#111111",
    "bg2":      "#1b1b1f",
    "text":     "#ffffff",
    "text_dim": "rgba(255,255,255,0.55)",
    "primary":  "#a286ec",
    "border":   "rgba(255,255,255,0.08)",
    "map_style": "carto-darkmatter",
}
LIGHT_THEME = {
    "bg":       "#f5f5f7",
    "bg2":      "#ffffff",
    "text":     "#111111",
    "text_dim": "rgba(0,0,0,0.72)",
    "primary":  "#4b3bbd",
    "border":   "rgba(0,0,0,0.10)",
    "map_style": "open-street-map",
}

# Modo-style accent palette — consistent across all charts & labels
MODO_COLORS = {
    "P":     "#fe55ba",   # pink   — Permitting
    "Q":     "#40a9ff",   # blue   — Queue
    "L":     "#f7dc2e",   # yellow — Load
    "S":     "#a286ec",   # purple — Policy
    "V":     "#36cfc9",   # teal   — Volatility
    "NYISO": "#a286ec",   # purple
    "ERCOT": "#f7dc2e",   # yellow
}

SPACER = "<div style='height:1.5rem'></div>"

# ---------------------------------------------------------------------------
# Sidebar  — theme toggle first, then ISO filter, then dimension controls
# ---------------------------------------------------------------------------
with st.sidebar:
    theme_choice = st.toggle("Light theme", value=False, key="light_theme")

    st.markdown("---")
    st.markdown("**ISO Filter**")
    iso_filter = st.radio(
        "", ["All", "NYISO", "ERCOT"],
        horizontal=True, label_visibility="collapsed", key="iso_filter",
    )

    st.markdown("---")
    st.markdown("#### Development Risk")
    st.caption("What can stop a project being built.")

    col1, col2 = st.columns([1, 2])
    with col1:
        toggle_P = st.checkbox("P — Permitting", value=True)
    with col2:
        weight_P = st.slider("", 0.5, 3.0, 1.0, 0.5, key="w_P",
                             disabled=not toggle_P, label_visibility="collapsed")
    st.caption("Moratoria, bans, local pushback.")

    col1, col2 = st.columns([1, 2])
    with col1:
        toggle_Q = st.checkbox("Q — Queue Stress", value=True)
    with col2:
        weight_Q = st.slider("", 0.5, 3.0, 1.0, 0.5, key="w_Q",
                             disabled=not toggle_Q, label_visibility="collapsed")
    st.caption("How crowded the interconnection queue is vs local demand.")

    col1, col2 = st.columns([1, 2])
    with col1:
        toggle_L = st.checkbox("L — Load Growth", value=True)
    with col2:
        weight_L = st.slider("", 0.5, 3.0, 1.0, 0.5, key="w_L",
                             disabled=not toggle_L, label_visibility="collapsed")
    st.caption("How fast electricity demand is growing, especially from data centers.")

    col1, col2 = st.columns([1, 2])
    with col1:
        toggle_S = st.checkbox("S — Policy Risk", value=True)
    with col2:
        weight_S = st.slider("", 0.5, 3.0, 1.0, 0.5, key="w_S",
                             disabled=not toggle_S, label_visibility="collapsed")
    st.caption("How much current rule changes could affect projects or revenues.")

    st.markdown("---")
    st.markdown("#### Optional Signal")
    st.caption("Price volatility: how spiky revenues are (opportunity + uncertainty).")

    col1, col2 = st.columns([1, 2])
    with col1:
        toggle_V = st.checkbox("V — Price Volatility", value=False,
                               help="Fetches live price data via gridstatus.")
    with col2:
        weight_V = st.slider("", 0.5, 3.0, 1.0, 0.5, key="w_V",
                             disabled=not toggle_V, label_visibility="collapsed")

    if toggle_V:
        st.caption("V is a market signal (revenue opportunity + uncertainty), not pure development risk.")

    st.markdown("---")
    st.caption("Scores: 1 = low risk · 2 = medium · 3 = high")
    st.caption("RiskScore = Σ (weight × score) for enabled dimensions")

# ---------------------------------------------------------------------------
# Resolve active theme
# ---------------------------------------------------------------------------
T = LIGHT_THEME if theme_choice else DARK_THEME

# ---------------------------------------------------------------------------
# CSS injection — Inter font + full theme override
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {{
        --background-color: {T['bg']};
        --secondary-background-color: {T['bg2']};
        --text-color: {T['text']};
        --primary-color: {T['primary']};
        --font: "Inter", system-ui, sans-serif;
    }}

    html, body, [class*="css"], .stApp,
    [data-testid="stAppViewContainer"] {{
        font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont,
                     "Segoe UI", sans-serif !important;
        background-color: {T['bg']} !important;
        color: {T['text']} !important;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {T['bg2']} !important;
        border-right: 1px solid {T['border']} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {T['text']} !important;
    }}

    /* Main block */
    .main .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }}

    /* Headings */
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {{
        font-weight: 600 !important;
        color: {T['text']} !important;
    }}

    /* Bordered containers */
    [data-testid="stContainer"] {{
        border-color: {T['border']} !important;
        background-color: {T['bg2']} !important;
    }}

    /* Metric boxes */
    [data-testid="metric-container"] {{
        background-color: {T['bg2']} !important;
        border: 1px solid {T['border']} !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
    }}
    [data-testid="metric-container"] label,
    [data-testid="metric-container"] [data-testid="stMetricValue"],
    [data-testid="metric-container"] [data-testid="stMetricDelta"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {{
        color: {T['text']} !important;
    }}

    /* Expander — all (default: methodology & raw permitting, top-level columns) */
    [data-testid="stExpander"] summary {{
        color: {"#000000" if theme_choice else T["text"]} !important;
        font-weight: 500;
        background-color: {"#DFDFDF" if theme_choice else "#292929"} !important;
        border-radius: 6px !important;
        padding: 0.5rem 0.75rem !important;
    }}
    /* Expander inside bordered containers (raw underlying metrics, show raw metrics) */
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stExpander"] summary,
    [data-testid="stVerticalBlockBorderWrapper"] details summary,
    [data-testid="stContainer"] [data-testid="stExpander"] summary,
    [data-testid="stContainer"] details summary {{
        background-color: {"#E2BCBC" if theme_choice else "#292929"} !important;
    }}

    /* Selectbox / dropdown — label */
    [data-testid="stSelectbox"] label,
    [data-testid="stSelectbox"] label * {{
        color: {T['text']} !important;
    }}
    /* Selectbox / dropdown — widget */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
        background-color: {"#FFFFFF" if theme_choice else T["bg2"]} !important;
        color: {"#000000" if theme_choice else T["text"]} !important;
        border-color: {T['border']} !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] svg {{
        fill: {"#000000" if theme_choice else T["text"]} !important;
    }}
    [data-baseweb="popover"] ul {{
        background-color: {"#FFFFFF" if theme_choice else T["bg2"]} !important;
    }}
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] li * {{
        background-color: {"#FFFFFF" if theme_choice else T["bg2"]} !important;
        color: {"#000000" if theme_choice else T["text"]} !important;
    }}
    [data-baseweb="popover"] li:hover {{
        background-color: {"#ffffff" if theme_choice else "rgba(255,255,255,0.08)"} !important;
    }}

    /* Tabs */
    [data-testid="stTabs"] [role="tab"] {{
        color: {T['text_dim']} !important;
        font-family: "Inter", system-ui, sans-serif !important;
    }}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
        color: {T['text']} !important;
    }}
    [data-testid="stTabs"] [role="tab"]:hover {{
        color: {T['text']} !important;
    }}

    /* Dividers */
    hr {{
        border-color: {T['border']} !important;
    }}

    /* Dataframe */
    [data-testid="stDataFrame"] {{
        background-color: {T['bg2']} !important;
    }}
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] [role="columnheader"],
    [role="columnheader"] {{
        background-color: {"#F1F1F1" if theme_choice else T["bg2"]} !important;
        color: {T['text']} !important;
    }}

    /* Caption / small text */
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {T['text_dim']} !important;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {T['bg']}; }}
    ::-webkit-scrollbar-thumb {{ background: {T['border']}; border-radius: 3px; }}

    /* About tab — expander title size */
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {{
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }}

    /* About tab — body text */
    .about-body {{
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 1.05rem;
        line-height: 1.8;
        padding: 0.75rem 0;
        color: {T['text']};
    }}
    .about-body p, .about-body li {{
        font-size: 1.05rem;
        color: {T['text']};
    }}
    .about-body li {{
        margin-bottom: 0.4rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sticky header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="
        position: sticky;
        top: 0;
        z-index: 999;
        background: linear-gradient(135deg,{T['bg2']} 0%,{T['bg']} 100%);
        border-bottom: 1px solid {T['border']};
        padding: 1.25rem 2rem;
        margin-bottom: 1rem;
        font-family: 'Inter', system-ui, sans-serif;
    ">
      <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.12em;
                  color:{T['primary']};text-transform:uppercase;margin-bottom:0.35rem;">
        Modo Energy · Take-home task
      </div>
      <div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:0.75rem;">
        <div>
          <div style="font-size:2rem;font-weight:700;color:{T['text']};margin-bottom:0.2rem;line-height:1.2;">
            BESS Development Risk Radar
          </div>
          <div style="font-size:0.95rem;color:{T['text_dim']};line-height:1.5;">
            Screen where battery projects are easiest or hardest to build —
            before you model revenues.
          </div>
        </div>
        <div style="display:flex;gap:0.4rem;flex-wrap:wrap;align-items:center;">
          <span style="background:#fe55ba;color:#fff;padding:3px 11px;border-radius:20px;
                       font-size:0.75rem;font-weight:600;">P — Permitting</span>
          <span style="background:#40a9ff;color:#fff;padding:3px 11px;border-radius:20px;
                       font-size:0.75rem;font-weight:600;">Q — Queue</span>
          <span style="background:#f7dc2e;color:#111;padding:3px 11px;border-radius:20px;
                       font-size:0.75rem;font-weight:600;">L — Load</span>
          <span style="background:#a286ec;color:#fff;padding:3px 11px;border-radius:20px;
                       font-size:0.75rem;font-weight:600;">S — Policy</span>
          <span style="background:#36cfc9;color:#111;padding:3px 11px;border-radius:20px;
                       font-size:0.75rem;font-weight:600;">V — Volatility</span>
          <span style="background:{T['border']};color:{T['text_dim']};padding:3px 11px;
                       border-radius:20px;font-size:0.72rem;">
            {iso_filter if iso_filter != 'All' else 'NYISO + ERCOT'} · v1.0
          </span>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
@st.cache_data
def get_base_data():
    df = load_region_risk()
    perm = load_permitting()
    return df, perm


df_base, df_perm = get_base_data()

# Fetch V if toggled — use session_state so fetch runs only once per session
if toggle_V:
    if "v_data" not in st.session_state:
        with st.spinner("Fetching price volatility data (14-day lookback)…"):
            try:
                st.session_state["v_data"] = fetch_price_volatility(lookback_days=14)
            except ImportError:
                st.warning(
                    "gridstatus not installed. Run `pip install gridstatus>=0.25` to enable V dimension.",
                )
                toggle_V = False
            except Exception as e:
                st.warning(f"Price data fetch failed ({e}). V dimension excluded.")
                toggle_V = False

    if toggle_V and "v_data" in st.session_state:
        df_base = df_base.merge(
            st.session_state["v_data"][["region_id", "V_volatility"]],
            on="region_id", how="left"
        )
else:
    st.session_state.pop("v_data", None)

# ---------------------------------------------------------------------------
# Apply ISO filter + compute scores
# ---------------------------------------------------------------------------
if iso_filter != "All":
    df_view = df_base[df_base["iso"] == iso_filter].copy()
else:
    df_view = df_base.copy()

df_scored = apply_scores(
    df_view,
    toggle_P=toggle_P, toggle_Q=toggle_Q, toggle_L=toggle_L, toggle_S=toggle_S,
    toggle_V=toggle_V,
    weight_P=weight_P, weight_Q=weight_Q, weight_L=weight_L, weight_S=weight_S,
    weight_V=weight_V,
)

active_cols = []
dim_labels = {
    "P_w": "P Permitting", "Q_w": "Q Queue",
    "L_w": "L Load",       "S_w": "S Policy", "V_w": "V Volatility",
}
if toggle_P: active_cols.append("P_w")
if toggle_Q: active_cols.append("Q_w")
if toggle_L: active_cols.append("L_w")
if toggle_S: active_cols.append("S_w")
if toggle_V: active_cols.append("V_w")

if not any([toggle_P, toggle_Q, toggle_L, toggle_S, toggle_V]):
    st.info("All dimensions are off. Enable at least one to see risk scores.")


tab_about, tab_dashboard = st.tabs(["About", "Dashboard"])

with tab_dashboard:
    # ---------------------------------------------------------------------------
    # Methodology / permitting expanders
    # ---------------------------------------------------------------------------
    _exp1, _exp2 = st.columns(2)
    with _exp1:
        with st.expander("Methodology & data sources"):
            st.markdown(
                """
    ### Risk Dimensions
    
    | Code | Dimension | What it captures | Score 1 | Score 2 | Score 3 |
    |------|-----------|-----------------|---------|---------|---------|
    | **P** | Permitting / Social Risk | Moratoria density + active bans | <3 restrictions, no ban | 4–7 restrictions or 1 ban | 8+ restrictions or bans |
    | **Q** | Queue Stress | Queued BESS MW ÷ zone peak load | ratio <0.15 | ratio 0.15–0.30 | ratio >0.30 |
    | **L** | Load Growth | Forecast demand growth + data center clusters | <15% forecast growth, no cluster | 15–25% or partial cluster | >25% growth + cluster |
    | **S** | Policy Uncertainty | ISC dependence (NYISO), RTC+B rollout (ERCOT) | Stable regulatory framework | One major reform in progress | Multiple reforms + market redesign |
    | **V** | Price Volatility *(optional)* | DAM/RTM price std dev + scarcity hours | Low volatility | Medium | High volatility |
    
    ### Composite Score
    ```
    RiskScore = Σ (toggle_i × weight_i × score_i)
    ```
    All toggles on, all weights = 1 → max score of 12 (P/Q/L/S only).
    
    ### Data Sources
    - **P scores**: EticaAG BESS Restrictions Database (NY: 34 entries; TX: 5 entries) + Town of Salem, NY moratorium (Oct 2025)
    - **Q scores**: NYISO Interconnection Queue XLSX (January 2026, 'ES' fuel type, active Interconnection Queue + Cluster Projects sheets); ERCOT GIS Report February 2026; ERCOT Co-located Battery Report February 2026
    - **L scores**: NYISO Power Trends 2025; ERCOT LTLF 2025 (peak load 109 GW → 139–218 GW by 2030); NYISO energy-intensive projects note (29 projects, 6,055 MW as of July 2025)
    - **S scores**: NYISO Order 2023 compliance docs; Modo Energy US Research Roundup Q3 2025; ERCOT RTC+B market design documents
    - **V scores** *(when enabled)*: Live via `gridstatus` — NYISO DAM LBMP zonal prices + ERCOT DAM SPP, 14-day lookback
    
    ### Limitations
    Directional screening tool, not a bankable model. P/L/S scores are researcher-assigned. NYISO_J scores Q=2 (0.21× ratio); all other 7 regions score Q=3. ERCOT queue saturation remains universal (1.1–5.9× peak load).
                """
            )
    
    with _exp2:
        with st.expander("Raw permitting entries (NY + TX)"):
            perm_filter_top = st.radio(
                "Filter by status", ["All", "Active", "Lifted/Expired", "Proposed"],
                horizontal=True, key="perm_filter_top",
            )
            perm_show_top = df_perm.copy()
            if perm_filter_top == "Active":
                perm_show_top = perm_show_top[perm_show_top["status"].str.lower() == "active"]
            elif perm_filter_top == "Lifted/Expired":
                perm_show_top = perm_show_top[perm_show_top["status"].str.lower().isin(["lifted", "expired"])]
            elif perm_filter_top == "Proposed":
                perm_show_top = perm_show_top[perm_show_top["status"].str.lower() == "proposed"]
            perm_th = [
                {"selector": "th", "props": [
                    ("background-color", "#F1F1F1" if theme_choice else T["bg2"]),
                    ("color", T["text"]), ("padding", "8px 12px"),
                    ("font-size", "0.85em"), ("font-weight", "600"),
                    ("text-align", "left"),
                    ("border-bottom", f"2px solid {T['border']}"),
                ]},
                {"selector": "td", "props": [
                    ("padding", "6px 12px"),
                    ("border-bottom", f"1px solid {T['border']}"),
                ]},
                {"selector": "table", "props": [
                    ("width", "100%"), ("border-collapse", "collapse"),
                    ("font-family", "Inter, system-ui, sans-serif"), ("font-size", "0.9em"),
                ]},
            ]
            perm_html = (
                perm_show_top.style
                .set_properties(**{"background-color": T["bg2"], "color": T["text"]})
                .set_table_styles(perm_th)
                .hide(axis="index")
                .to_html()
            )
            st.markdown(
                f'<div style="overflow-x:auto;max-height:400px;overflow-y:auto">{perm_html}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{len(perm_show_top)} entries shown · Source: EticaAG BESS Restrictions Database")
    
    st.markdown(SPACER, unsafe_allow_html=True)
    
    # ---------------------------------------------------------------------------
    # Row 1: ranked table (left 2/3) + metrics + bar chart (right 1/3)
    # ---------------------------------------------------------------------------
    max_possible = 12.0
    if len(df_scored) > 0 and any([toggle_P, toggle_Q, toggle_L, toggle_S, toggle_V]):
        top = df_scored.iloc[0]
        bottom = df_scored.iloc[-1]
        max_possible = sum([
            3 * weight_P * toggle_P,
            3 * weight_Q * toggle_Q,
            3 * weight_L * toggle_L,
            3 * weight_S * toggle_S,
            3 * weight_V * toggle_V,
        ])
    
    DIM_OPTIONS = {
        "P — Permitting Risk":    "P_permitting",
        "Q — Queue Stress":       "Q_queue",
        "L — Load Growth":        "L_load",
        "S — Policy Uncertainty": "S_policy",
    }
    if toggle_V and "V_volatility" in df_scored.columns:
        DIM_OPTIONS["V — Price Volatility"] = "V_volatility"
    dim_option_keys = list(DIM_OPTIONS.keys())
    nyiso_regions = df_scored[df_scored["iso"] == "NYISO"]["region_id"].tolist()
    ercot_regions = df_scored[df_scored["iso"] == "ERCOT"]["region_id"].tolist()
    
    col_main, col_bar = st.columns([2, 1], gap="large")
    
    with col_main:
        with st.container(border=True):
            st.markdown("### Step 1 — Compare regions")
            st.caption("Which regions are easiest or hardest to develop in, and what drives that risk.")
    
            display_cols = ["region_id", "region_name", "iso"]
            label_map = {"region_id": "Region ID", "region_name": "Region", "iso": "ISO"}
            if toggle_P: display_cols.append("P_permitting"); label_map["P_permitting"] = "P"
            if toggle_Q: display_cols.append("Q_queue");      label_map["Q_queue"] = "Q"
            if toggle_L: display_cols.append("L_load");       label_map["L_load"] = "L"
            if toggle_S: display_cols.append("S_policy");     label_map["S_policy"] = "S"
            if toggle_V and "V_volatility" in df_scored.columns:
                display_cols.append("V_volatility"); label_map["V_volatility"] = "V"
            display_cols.append("RiskScore"); label_map["RiskScore"] = "Risk Score"
    
            table_df = df_scored[display_cols].rename(columns=label_map)
            table_df["Risk Score"] = table_df["Risk Score"].round(2)
    
            cell_props = {"background-color": T["bg2"], "color": T["text"]}
            header_bg = "#F1F1F1" if theme_choice else T["bg2"]
            th_styles = [
                {"selector": "th", "props": [
                    ("background-color", header_bg), ("color", T["text"]),
                    ("padding", "8px 12px"), ("font-size", "0.85em"),
                    ("font-weight", "600"), ("text-align", "left"),
                    ("border-bottom", f"2px solid {T['border']}"),
                ]},
                {"selector": "td", "props": [
                    ("padding", "6px 12px"),
                    ("border-bottom", f"1px solid {T['border']}"),
                ]},
                {"selector": "table", "props": [
                    ("width", "100%"), ("border-collapse", "collapse"),
                    ("font-family", "Inter, system-ui, sans-serif"), ("font-size", "0.9em"),
                ]},
            ]
            if any([toggle_P, toggle_Q, toggle_L, toggle_S, toggle_V]):
                tbl_html = (
                    table_df.style
                    .set_properties(**cell_props)
                    .set_table_styles(th_styles)
                    .background_gradient(subset=["Risk Score"], cmap="RdYlGn_r", vmin=0, vmax=max_possible)
                    .format("{:.1f}", subset=["Risk Score"])
                    .hide(axis="index")
                    .to_html()
                )
            else:
                tbl_html = (
                    table_df.style
                    .set_properties(**cell_props)
                    .set_table_styles(th_styles)
                    .hide(axis="index")
                    .to_html()
                )
            st.markdown(
                f'<div style="overflow-x:auto;max-height:280px;overflow-y:auto">{tbl_html}</div>',
                unsafe_allow_html=True,
            )
    
            with st.expander("Raw underlying metrics"):
                raw_cols = [
                    "region_id", "queued_bess_mw", "peak_load_mw", "bess_to_peak_ratio",
                    "moratoria_count", "has_ban", "forecast_load_growth_pct", "has_dc_cluster",
                    "policy_flags",
                ]
                raw_show = [c for c in raw_cols if c in df_scored.columns]
                raw_th = [
                    {"selector": "th", "props": [
                        ("background-color", "#F1F1F1" if theme_choice else T["bg2"]),
                        ("color", T["text"]), ("padding", "8px 12px"),
                        ("font-size", "0.85em"), ("font-weight", "600"),
                        ("text-align", "left"),
                        ("border-bottom", f"2px solid {T['border']}"),
                    ]},
                    {"selector": "td", "props": [
                        ("padding", "6px 12px"),
                        ("border-bottom", f"1px solid {T['border']}"),
                    ]},
                    {"selector": "table", "props": [
                        ("width", "100%"), ("border-collapse", "collapse"),
                        ("font-family", "Inter, system-ui, sans-serif"), ("font-size", "0.9em"),
                    ]},
                ]
                raw_html = (
                    df_scored[raw_show].style
                    .set_properties(**{"background-color": T["bg2"], "color": T["text"]})
                    .set_table_styles(raw_th)
                    .hide(axis="index")
                    .to_html()
                )
                st.markdown(
                    f'<div style="overflow-x:auto;max-height:300px;overflow-y:auto">{raw_html}</div>',
                    unsafe_allow_html=True,
                )
    
        st.markdown(SPACER, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Step 2 — Explore trade-offs")
            st.caption("Choose any two risk dimensions for the axes and use bubble size for a third.")
    
            sc_col1, sc_col2, sc_col3 = st.columns(3)
            with sc_col1:
                x_label = st.selectbox("X axis", dim_option_keys, index=0)
            with sc_col2:
                y_label = st.selectbox("Y axis", dim_option_keys, index=1)
            with sc_col3:
                bubble_label = st.selectbox("Bubble size", dim_option_keys, index=2)
    
            x_col      = DIM_OPTIONS[x_label]
            y_col      = DIM_OPTIONS[y_label]
            bubble_col = DIM_OPTIONS[bubble_label]
    
            st.caption(
                f"Upper-right = high {x_label} AND high {y_label}. "
                "Bubble size reflects the third dimension. Hover for full region detail."
            )
    
            scatter_df = df_scored.copy()
            scatter_df["_bubble"] = scatter_df[bubble_col] * 15 + 5
    
            fig_scatter = px.scatter(
                scatter_df,
                x=x_col,
                y=y_col,
                size="_bubble",
                color="iso",
                hover_name="region_id",
                hover_data={
                    "region_name": True,
                    "P_permitting": True,
                    "Q_queue": True,
                    "L_load": True,
                    "S_policy": True,
                    "RiskScore": True,
                    "policy_flags": True,
                    "_bubble": False,
                },
                color_discrete_map={"NYISO": MODO_COLORS["NYISO"], "ERCOT": MODO_COLORS["ERCOT"]},
                labels={
                    x_col: f"{x_label} (1=low, 3=high)",
                    y_col: f"{y_label} (1=low, 3=high)",
                    "iso": "ISO",
                },
                size_max=55,
            )
            fig_scatter.update_layout(
                xaxis={"range": [0.5, 3.5], "dtick": 1, "showgrid": True,
                       "gridcolor": T["border"], "color": T["text"]},
                yaxis={"range": [0.5, 3.5], "dtick": 1, "showgrid": True,
                       "gridcolor": T["border"], "color": T["text"]},
                height=480,
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
                plot_bgcolor=T["bg2"],
                paper_bgcolor=T["bg2"],
                font={"color": T["text"], "family": "Inter, system-ui, sans-serif"},
                legend={"font": {"color": T["text"]}},
            )
            fig_scatter.add_annotation(
                x=3.4, y=3.4, text="Hardest to develop",
                showarrow=False, font={"color": "#d62728", "size": 11},
                xanchor="right", yanchor="top",
            )
            fig_scatter.add_annotation(
                x=0.6, y=0.6, text="Easiest to develop",
                showarrow=False, font={"color": "#2ca02c", "size": 11},
                xanchor="left", yanchor="bottom",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col_bar:
        st.divider()
        if len(df_scored) > 0 and any([toggle_P, toggle_Q, toggle_L, toggle_S, toggle_V]):
            st.metric(
                "Highest Risk",
                top["region_name"] if "region_name" in top else top["region_id"],
                f"{top['RiskScore']:.1f}",
                help="Region with the most development obstacles.",
            )
            st.metric(
                "Lowest Risk",
                bottom["region_name"] if "region_name" in bottom else bottom["region_id"],
                f"{bottom['RiskScore']:.1f}",
                help="Region with the fewest development obstacles.",
            )
            st.metric("Regions Screened", len(df_scored))
            st.metric("Max Possible Score", f"{max_possible:.1f}")
            st.divider()
    
        st.markdown("### Risk contribution by region")
    
        if not active_cols:
            st.info("Enable at least one dimension to see chart.")
        else:
            bar_df = df_scored[["region_id"] + active_cols].copy()
            bar_df = bar_df.rename(columns=dim_labels)
            bar_long = bar_df.melt(id_vars="region_id", var_name="Dimension", value_name="Score")
    
            color_map = {
                "P Permitting": MODO_COLORS["P"],
                "Q Queue":      MODO_COLORS["Q"],
                "L Load":       MODO_COLORS["L"],
                "S Policy":     MODO_COLORS["S"],
                "V Volatility": MODO_COLORS["V"],
            }
    
            fig_bar = px.bar(
                bar_long,
                x="Score",
                y="region_id",
                color="Dimension",
                orientation="h",
                barmode="stack",
                color_discrete_map=color_map,
                labels={"region_id": "Region", "Score": "Weighted Score"},
            )
            fig_bar.update_layout(
                yaxis={"categoryorder": "total ascending", "color": "#B5B5B5",
                       "tickfont": {"color": "#B5B5B5"}, "title": {"font": {"color": "#B5B5B5"}}},
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                        "font": {"color": "#B5B5B5"},
                        "title": {"font": {"color": "#B5B5B5"}}},
                margin={"l": 10, "r": 10, "t": 30, "b": 10},
                height=320,
                xaxis={"showgrid": False, "color": "#B5B5B5",
                       "tickfont": {"color": "#B5B5B5"}, "title": {"font": {"color": "#B5B5B5"}}},
                plot_bgcolor=T["bg2"],
                paper_bgcolor=T["bg2"],
                font={"color": "#B5B5B5", "family": "Inter, system-ui, sans-serif"},
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown(SPACER, unsafe_allow_html=True)
    
    # ---------------------------------------------------------------------------
    # Helper functions for region deep-dive
    # ---------------------------------------------------------------------------
    def _risk_narrative(row: pd.Series) -> list[str]:
        score_word = {1: "low", 2: "moderate", 3: "high"}
        lines = []
        p = row.get("P_permitting")
        if pd.notna(p) and int(p) > 0:
            ban_text = " including an active ban" if row.get("has_ban") else ""
            lines.append(
                f"Permitting risk is **{score_word[int(p)]}** — "
                f"{int(row.get('moratoria_count', 0))} moratoria/restrictions in zone{ban_text}."
            )
        q = row.get("Q_queue")
        if pd.notna(q) and int(q) > 0:
            lines.append(
                f"Queue stress is **{score_word[int(q)]}** — "
                f"queued BESS is {row.get('bess_to_peak_ratio', 0):.2f}x peak load."
            )
        l = row.get("L_load")
        if pd.notna(l) and int(l) > 0:
            dc = " with a data-center cluster nearby" if row.get("has_dc_cluster") else ""
            lines.append(
                f"Load growth is **{score_word[int(l)]}** — "
                f"{row.get('forecast_load_growth_pct', 0):.0f}% forecast demand growth{dc}."
            )
        s = row.get("S_policy")
        if pd.notna(s) and int(s) > 0:
            lines.append(
                f"Policy risk is **{score_word[int(s)]}** — "
                f"active reforms: {row.get('policy_flags', '—')}."
            )
        return lines
    
    
    def _driver_bar(row: pd.Series):
        moratoria = int(row.get("moratoria_count", 0))
        has_ban   = bool(row.get("has_ban", False))
        p_interp  = f"{moratoria} moratoria/bans in zone" + (" — active ban" if has_ban else "")
        ratio     = row.get("bess_to_peak_ratio", 0)
        q_interp  = f"{ratio:.2f}× queue/peak ratio"
        growth    = row.get("forecast_load_growth_pct", 0)
        dc        = row.get("has_dc_cluster", False)
        l_interp  = f"{growth:.0f}% forecast load growth" + (", DC cluster" if dc else "")
        flags     = str(row.get("policy_flags", "—"))
        s_interp  = flags
    
        dims = [
            ("P", row.get("P_permitting", 0), p_interp),
            ("Q", row.get("Q_queue",      0), q_interp),
            ("L", row.get("L_load",       0), l_interp),
            ("S", row.get("S_policy",     0), s_interp),
        ]
        # Border color = risk level; label color = Modo dimension accent
        score_border = {1: "#2ca02c", 2: "#ff7f0e", 3: "#d62728"}
    
        cols = st.columns(4)
        for i, (code, score, interp) in enumerate(dims):
            score = int(score) if pd.notna(score) else 0
            border = score_border.get(score, "#666")
            label_color = MODO_COLORS.get(code, T["primary"])
            cols[i].markdown(
                f"<div style='border-left:4px solid {border};padding:10px 14px;"
                f"background:{T['bg2']};border-radius:4px;'>"
                f"<b style='color:{label_color};font-size:1.05em;'>{code} — {score}/3</b><br>"
                f"<span style='font-size:0.82em;color:{T['text_dim']};'>{interp}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("")
    
    
    def _render_region_card(region_row: pd.Series):
        dim_cfg = [
            ("P", "P_permitting", "Permitting",     toggle_P, weight_P),
            ("Q", "Q_queue",      "Queue Stress",    toggle_Q, weight_Q),
            ("L", "L_load",       "Load Growth",     toggle_L, weight_L),
            ("S", "S_policy",     "Policy Risk",     toggle_S, weight_S),
        ]
        if toggle_V and "V_volatility" in region_row.index:
            dim_cfg.append(("V", "V_volatility", "Price Volatility", toggle_V, weight_V))
    
        active_cfg = [d for d in dim_cfg if d[3]]
        if active_cfg:
            cols = st.columns(len(active_cfg) + 1)
            for ci, (code, col, label, _tog, wt) in enumerate(active_cfg):
                val = region_row[col]
                if pd.notna(val):
                    cols[ci].metric(f"{code} — {label}", f"{val:.0f}/3", f"×{wt:.1f}w = {val*wt:.1f}pts")
            cols[len(active_cfg)].metric("Risk Score", f"{region_row['RiskScore']:.1f}")
    
        with st.expander("Show raw metrics"):
            raw_items = {
                "Queued BESS (MW)": f"{int(region_row.get('queued_bess_mw', 0)):,}" if pd.notna(region_row.get("queued_bess_mw")) else "N/A",
                "Queue/Peak ratio": f"{region_row.get('bess_to_peak_ratio', 0):.2f}x",
                "Moratoria/bans":   str(int(region_row.get("moratoria_count", 0))),
                "Load growth":      f"{region_row.get('forecast_load_growth_pct', 0):.0f}%",
                "Data center cluster": "Yes" if region_row.get("has_dc_cluster") else "No",
                "Policy flags":     str(region_row.get("policy_flags", "—")),
            }
            raw_df = pd.DataFrame(raw_items.items(), columns=["Metric", "Value"])
            header_bg = "#F1F1F1" if theme_choice else T["bg2"]
            raw_html = (
                raw_df.style
                .set_properties(**{"background-color": T["bg2"], "color": T["text"]})
                .set_table_styles([
                    {"selector": "th", "props": [
                        ("background-color", header_bg), ("color", T["text"]),
                        ("padding", "6px 12px"), ("font-size", "0.85em"),
                        ("font-weight", "600"), ("text-align", "left"),
                        ("border-bottom", f"2px solid {T['border']}"),
                    ]},
                    {"selector": "td", "props": [
                        ("padding", "5px 12px"),
                        ("border-bottom", f"1px solid {T['border']}"),
                    ]},
                    {"selector": "table", "props": [
                        ("width", "100%"), ("border-collapse", "collapse"),
                        ("font-family", "Inter, system-ui, sans-serif"), ("font-size", "0.9em"),
                    ]},
                ])
                .hide(axis="index")
                .to_html()
            )
            st.markdown(f'<div style="overflow-x:auto">{raw_html}</div>', unsafe_allow_html=True)
    
    
    def _region_card(row: pd.Series):
        """Render full region card inside a bordered container."""
        with st.container(border=True):
            st.markdown(f"**{row.get('region_name', row['region_id'])}**")
            for line in _risk_narrative(row):
                st.markdown(f"- {line}")
            st.markdown("")
            _driver_bar(row)
            _render_region_card(row)
    
    
    with st.container(border=True):
        st.markdown("### Step 3 — Drill into a region")
        st.caption("Select a region to see its full score breakdown.")
    
        s3_ny, s3_er = st.columns(2, gap="large")
        with s3_ny:
            if nyiso_regions:
                sel_nyiso = st.selectbox("NYISO Region", nyiso_regions)
                nyiso_row = df_scored[df_scored["region_id"] == sel_nyiso].iloc[0]
                _region_card(nyiso_row)
            else:
                st.info("No NYISO regions in current filter.")
    
        with s3_er:
            if ercot_regions:
                sel_ercot = st.selectbox("ERCOT Region", ercot_regions)
                ercot_row = df_scored[df_scored["region_id"] == sel_ercot].iloc[0]
                _region_card(ercot_row)
            else:
                st.info("No ERCOT regions in current filter.")
    
    st.markdown(SPACER, unsafe_allow_html=True)
    
    # ---------------------------------------------------------------------------
    # Risk vs. Revenue quadrant (visible only when V is enabled)
    # ---------------------------------------------------------------------------
    if toggle_V and "V_volatility" in df_scored.columns and df_scored["V_volatility"].notna().any():
        with st.container(border=True):
            st.subheader("Risk vs. Revenue Opportunity")
            st.caption(
                "X = composite development risk score (P/Q/L/S). "
                "Y = price volatility band (1–3), derived from recent NYISO DAM LBMP and ERCOT SPP data "
                "via gridstatus — optional dimension, fetched live. "
                "Sweet spot: low development risk + high price volatility."
            )
    
            mid_risk = df_scored["RiskScore"].median()
            mid_v    = df_scored["V_volatility"].median()
            x_max    = df_scored["RiskScore"].max() * 1.2
            y_min, y_max = 0.8, 3.3
    
            fig_rv = px.scatter(
                df_scored,
                x="RiskScore",
                y="V_volatility",
                color="iso",
                hover_name="region_id",
                text="region_id",
                hover_data={
                    "region_name": True,
                    "RiskScore": ":.1f",
                    "V_volatility": ":.2f",
                    "iso": False,
                },
                color_discrete_map={"NYISO": MODO_COLORS["NYISO"], "ERCOT": MODO_COLORS["ERCOT"]},
                labels={
                    "RiskScore": "Development Risk Score",
                    "V_volatility": "Price Volatility (1–3)",
                },
            )
            fig_rv.update_traces(textposition="top center", marker_size=12)
            fig_rv.add_vline(x=mid_risk, line_dash="dot", line_color=T["border"], line_width=1.5)
            fig_rv.add_hline(y=mid_v,    line_dash="dot", line_color=T["border"], line_width=1.5)
    
            fig_rv.add_annotation(x=mid_risk * 0.5, y=y_max * 0.97,
                                  text="High revenue upside, easier to build",
                                  showarrow=False, font={"color": "#2ca02c", "size": 11},
                                  xanchor="center")
            fig_rv.add_annotation(x=mid_risk + (x_max - mid_risk) * 0.6, y=y_max * 0.97,
                                  text="High stakes: great upside but hard to build",
                                  showarrow=False, font={"color": "#ff7f0e", "size": 11},
                                  xanchor="center")
            fig_rv.add_annotation(x=mid_risk * 0.5, y=y_min + 0.1,
                                  text="Safe but thin margins",
                                  showarrow=False, font={"color": T["text_dim"], "size": 11},
                                  xanchor="center")
            fig_rv.add_annotation(x=mid_risk + (x_max - mid_risk) * 0.6, y=y_min + 0.1,
                                  text="Avoid: hard to build and thin margins",
                                  showarrow=False, font={"color": "#d62728", "size": 11},
                                  xanchor="center")
    
            fig_rv.update_layout(
                xaxis={"range": [0, x_max], "showgrid": False, "color": T["text"]},
                yaxis={"range": [y_min, y_max],
                       "title": "Price Volatility (revenue proxy, 1–3)",
                       "showgrid": False, "color": T["text"]},
                height=440,
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
                plot_bgcolor=T["bg2"],
                paper_bgcolor=T["bg2"],
                font={"color": T["text"], "family": "Inter, system-ui, sans-serif"},
                legend={"font": {"color": T["text"]}},
            )
            st.plotly_chart(fig_rv, use_container_width=True)
    
        st.markdown(SPACER, unsafe_allow_html=True)
    
    # ---------------------------------------------------------------------------
    # Zone Reference Maps (NYISO / ERCOT only)
    # ---------------------------------------------------------------------------
    ASSETS_DIR = Path(__file__).parent.parent / "assets"
    
    # ---------------------------------------------------------------------------
    # County FIPS → ISO zone mappings
    # ---------------------------------------------------------------------------
    _NYISO_COUNTY_ZONE = {
        # Zone K — Long Island
        "36059": "NYISO_K", "36103": "NYISO_K",
        # Zone J — NYC five boroughs
        "36005": "NYISO_J", "36047": "NYISO_J", "36061": "NYISO_J",
        "36081": "NYISO_J", "36085": "NYISO_J",
        # Zone GHI — Lower Hudson Valley / Catskills
        "36027": "NYISO_GHI", "36039": "NYISO_GHI", "36071": "NYISO_GHI",
        "36079": "NYISO_GHI", "36087": "NYISO_GHI", "36105": "NYISO_GHI",
        "36111": "NYISO_GHI", "36119": "NYISO_GHI",
    }
    
    
    def _approx_centroid(geometry: dict):
        gtype = geometry.get("type", "")
        if gtype == "Polygon":
            ring = geometry["coordinates"][0]
        elif gtype == "MultiPolygon":
            ring = geometry["coordinates"][0][0]
        else:
            return 0.0, 0.0
        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        return sum(lons) / len(lons), sum(lats) / len(lats)
    
    
    def _ercot_zone_from_centroid(lon: float, lat: float) -> str:
        if lon < -100.0:
            return "ERCOT_WEST"
        if lon >= -97.0 and lat < 32.5:
            return "ERCOT_HOU"
        if lat >= 30.0:
            return "ERCOT_NORTH"
        return "ERCOT_SOUTH"
    
    
    @st.cache_data(ttl=86400, show_spinner=False)
    def _load_county_geojson() -> dict | None:
        try:
            import requests
            url = (
                "https://raw.githubusercontent.com/plotly/datasets/master/"
                "geojson-counties-fips.json"
            )
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None
    
    
    def _render_zone_map(iso: str, scored_df, max_score: float):
        counties = _load_county_geojson()
    
        if counties is None:
            if iso == "NYISO":
                st.image(str(ASSETS_DIR / "NYISO-Zones.jpg"), use_container_width=True)
            else:
                st.image(str(ASSETS_DIR / "ercot-zones.png"), use_container_width=True)
            return
    
        prefix = "36" if iso == "NYISO" else "48"
        score_lookup = scored_df.set_index("region_id")["RiskScore"].to_dict()
        name_lookup  = scored_df.set_index("region_id")["region_name"].to_dict()
    
        state_features = []
        rows = []
        for feat in counties["features"]:
            fips = feat["id"]
            if not fips.startswith(prefix):
                continue
            state_features.append(feat)
    
            if iso == "NYISO":
                zone = _NYISO_COUNTY_ZONE.get(fips, "NYISO_ABCDEF")
            else:
                lon, lat = _approx_centroid(feat["geometry"])
                zone = _ercot_zone_from_centroid(lon, lat)
    
            rows.append({
                "fips": fips,
                "region_id": zone,
                "RiskScore": score_lookup.get(zone, 0.0),
                "Zone": name_lookup.get(zone, zone),
            })
    
        if not rows:
            st.info("No county data found for this ISO.")
            return
    
        state_geojson = {"type": "FeatureCollection", "features": state_features}
        df_map = pd.DataFrame(rows)
    
        center = {"lat": 42.9, "lon": -76.0} if iso == "NYISO" else {"lat": 31.5, "lon": -99.5}
        zoom   = 5.5 if iso == "NYISO" else 4.6
    
        fig = px.choropleth_mapbox(
            df_map,
            geojson=state_geojson,
            locations="fips",
            featureidkey="id",
            color="RiskScore",
            color_continuous_scale="RdYlGn_r",
            range_color=[0, max_score],
            mapbox_style=T["map_style"],
            zoom=zoom,
            center=center,
            opacity=0.6,
            hover_name="Zone",
            hover_data={"RiskScore": ":.1f", "region_id": True, "fips": False},
            labels={"RiskScore": "Risk Score"},
            height=440,
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            paper_bgcolor=T["bg2"],
            font={"color": T["text"], "family": "Inter, system-ui, sans-serif"},
            coloraxis_colorbar={
                "title": {"text": "Risk Score", "font": {"color": T["text"]}},
                "tickfont": {"color": T["text"]},
            },
        )
        st.plotly_chart(fig, use_container_width=True)
    
    
    if iso_filter in ("NYISO", "ERCOT"):
        label = "New York (NYISO)" if iso_filter == "NYISO" else "Texas (ERCOT)"
        st.divider()
        st.subheader(f"Zone Reference Map — {label}")
        with st.spinner("Loading zone boundaries…"):
            _render_zone_map(iso_filter, df_scored, max_possible)
    
    # ---------------------------------------------------------------------------
    # Footer
    # ---------------------------------------------------------------------------
    st.divider()
    st.caption(
        "BESS Development Risk Radar · Data as of March 2026 · "
        "Built with Streamlit + Plotly · Modo Energy take-home task"
    )


with tab_about:
    with st.expander("What problem is this solving?", expanded=True):
        st.markdown(f"""<div class="about-body">
<p>Revenue models for BESS are already sophisticated – tools like Modo's forecasts go deep on dispatch and revenues.
What's still under-exposed is <strong>development-side risk</strong>: the chance a project never reaches COD because it gets blocked
in permitting, stuck in the queue, or hit by policy changes, even when the revenue case looks great.</p>
<p>This tool asks:</p>
<blockquote style="border-left:3px solid {T['primary']};margin:1rem 0;padding:0.5rem 1rem;color:{T['text_dim']};">
  <em>Given two identical 100 MW batteries in different regions, which one is actually more likely to get built – and why?</em>
</blockquote>
<p>It turns four ingredients into simple 1–3 scores per region:</p>
<ul>
  <li><strong>P – Permitting / social risk:</strong> moratoria, bans, local pushback.</li>
  <li><strong>Q – Queue stress:</strong> how crowded the interconnection queue is vs local demand.</li>
  <li><strong>L – Load growth:</strong> how fast electricity demand is growing, especially from data centers.</li>
  <li><strong>S – Policy risk:</strong> how much active rule changes could affect projects or revenues.</li>
</ul>
<p>An optional <strong>V – price volatility</strong> layer shows where price swings create extra revenue opportunity + uncertainty,
but V is kept separate from core development risk. (When V is selected, the dashboard also surfaces a <strong>Risk vs. Revenue Opportunity</strong> scatter — letting you see which regions combine manageable development risk with high price volatility, and where those two forces pull in opposite directions.)</p>
</div>""", unsafe_allow_html=True)

    with st.expander("What I built — and what I didn't"):
        st.markdown(f"""<div class="about-body">
<p>What I <strong>did build</strong> in the time box:</p>
<ul>
  <li>A 1–3 scoring framework for P/Q/L/S across NYISO and ERCOT.</li>
  <li>A combined 8-region view (4 NYISO, 4 ERCOT) with toggles and weights.</li>
  <li>A ranked table, contribution bar, scatter "risk vs revenue" view, and region deep-dive cards.</li>
</ul>
<p>What I <strong>deliberately didn't build</strong>:</p>
<ul>
  <li>No dispatch engine, revenue forecast, or DSCR model – those already exist in far more depth.</li>
  <li>No attempt to optimise plant sizing or bidding strategies.</li>
</ul>
<p>Instead, I focused on:</p>
<ul>
  <li>Parsing and aggregating interconnection queues.</li>
  <li>Mapping moratoria to zones/regions.</li>
  <li>Normalising load-growth metrics from NYISO Power Trends and ERCOT LTLF/MORA.</li>
  <li>Designing a UI where you can toggle and recombine risk dimensions quickly.</li>
<p>This is a <strong>broad, shallow screening tool</strong>, not a full project model.</p>
</ul>
</div>""", unsafe_allow_html=True)

    with st.expander("How the scores are constructed"):
        st.markdown(f"""<div class="about-body">
<p>To keep the scores <strong>defensible and auditable</strong>, I follow the same pattern for each dimension:</p>
<ol>
  <li style="margin-bottom:0.75rem;">
    <strong>Start from public, named data</strong><br>
    <ul>
      <li>P: EticaAG BESS restrictions + representative ordinances, plus Modo's permitting work.</li>
      <li>Q: NYISO Interconnection Queue (Jan 2026) and ERCOT GIS / generator interconnection reports.</li>
      <li>L: NYISO Power Trends, NYISO energy-intensive projects note, ERCOT LTLF and MORA.</li>
      <li>S: NYISO Order 2023 filings and stakeholder summaries; ERCOT RTC+B and AS redesign docs; Modo's NYISO and ERCOT research.</li>
    </ul>
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Reduce to simple metrics</strong><br>
    <ul>
      <li>P = number and type of restrictions in the region.</li>
      <li>Q = (queued + installed BESS MW) / peak load.</li>
      <li>L = load-growth band + presence of data-centre clusters.</li>
      <li>S = count and materiality of active reforms affecting the storage business case.</li>
    </ul>
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Bucket into 1–3 scores with explicit rules</strong><br>
    Thresholds (e.g. Q&gt;0.30 ⇒ high queue stress) are documented in the README and tooltips.
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Expose the underlying numbers</strong><br>
    The region deep-dive shows the raw metrics (queued MW, ratios, growth %, restriction counts, policy flags)
    so you can disagree with my thresholds and rescore if you want.
  </li>
</ol>
<p>Judgement plays the biggest role in <strong>P</strong> and <strong>S</strong>, and the tool uses single snapshots for <strong>Q</strong> and <strong>L</strong>;
those limitations are called out explicitly so it's clear where subjectivity enters.</p>
</div>""", unsafe_allow_html=True)

    with st.expander("How different stakeholders can use it"):
        st.markdown(f"""<div class="about-body">
<ul>
  <li style="margin-bottom:0.75rem;">
    <strong>Developers</strong> – use P and Q to screen where it's realistically possible to originate projects and get them through interconnection.
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Asset owners / lenders</strong> – use P/Q/L/S together to decide how hard to haircut pipeline MW in each region before plugging revenues into DSCR models.
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Traders / optimisers</strong> – combine core risk scores with V (price volatility) to see where capacity might <em>not</em> show up as quickly as the queue suggests, preserving spreads, or where oversupply risk is highest.
  </li>
  <li style="margin-bottom:0.75rem;">
    <strong>Utilities / ISOs</strong> – focus on L and Q to identify regions where demand growth and queue saturation collide, creating adequacy and planning challenges.
  </li>
</ul>
<p>The same map of P/Q/L/S tells a different story depending on your seat – the interface surfaces those views explicitly.</p>
</div>""", unsafe_allow_html=True)
