"""
Parametric + Forest-Conservation Climate Stress Test (MYS vs IDN).

Run:  python -m streamlit run app.py

Two-lever simulator:
  1. Stress  -> uplifts the GHG path 2024->2030 (climate downside)
  2. Strategy -> hybrid mitigation: parametric agri-cover (financial absorber)
                 + NDVI-triggered forest-conservation incentives (bends GHG path)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="R-Ignite | Parametric Climate Stress Test",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Custom CSS: STRUCTURE ONLY. No background or text-color overrides
# anywhere except the self-contained hero banner. All page colors come from
# the active Streamlit theme so light/dark both work cleanly.
st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

  /* Self-contained hero — fixed colors are safe because background is opaque */
  .hero {
    background: linear-gradient(135deg, #6b1414 0%, #a32626 60%, #d97706 100%);
    color: #ffffff; padding: 22px 28px; border-radius: 14px;
    margin-bottom: 18px; box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  }
  .hero h1 { color: #ffffff; font-size: 1.8rem; margin: 0; font-weight: 700; }
  .hero p  { color: #fde6c7; margin: 6px 0 0 0; font-size: 0.95rem; }

  /* Metric cards — structure & layout only, NO text colors so theme wins */
  div[data-testid="stMetric"] {
    background: rgba(127, 127, 127, 0.08);
    border: 1px solid rgba(127, 127, 127, 0.20);
    border-left: 4px solid #d97706;
    padding: 12px 14px;
    border-radius: 8px;
    height: 110px;
    display: flex; flex-direction: column; justify-content: center;
    gap: 4px;
    box-sizing: border-box; overflow: hidden;
  }
  div[data-testid="stMetricLabel"] {
    font-weight: 600; font-size: 0.85rem;
    line-height: 1.15; max-height: 2.4em;
    overflow: hidden;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    white-space: normal;
  }
  div[data-testid="stMetricLabel"] p {
    margin: 0; word-break: break-word; font-size: 0.85rem;
  }
  div[data-testid="stMetricValue"] {
    font-size: 1.7rem; font-weight: 700; line-height: 1.1;
    overflow: hidden; word-break: break-word;
  }
  div[data-testid="stMetricValue"] p { font-size: 1.7rem; margin: 0; }
  div[data-testid="stMetricDelta"] {
    font-size: 0.78rem; line-height: 1.1;
    overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    display: flex; flex-direction: column;
  }

  /* Force every widget label to use Streamlit's active theme text color.
     Fixes white-on-white labels when OS dark mode fights Streamlit's theme. */
  label[data-testid="stWidgetLabel"] p,
  label[data-testid="stWidgetLabel"] div,
  div[data-testid="stWidgetLabel"] p,
  div[data-testid="stMetricLabel"] p,
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
  div[data-testid="stExpander"] summary p {
    color: var(--text-color) !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🌾 Parametric Insurance & Climate Stress Test</h1>
  <p>MASA Hackathon 2026 · R-Ignite — Hybrid parametric reinsurance + forest-conservation rider for Malaysia & Indonesia</p>
</div>
""", unsafe_allow_html=True)

# --- Load artifacts ------------------------------------------------------
DATA = pd.read_csv("cleaned_wdi_data.csv")
METRICS = json.loads(Path("model_metrics.json").read_text())

# Illustrative agricultural GDP exposure (USD bn, World Bank 2022 approx).
AGRI_GDP_BN = {"MYS": 24.0, "IDN": 140.0}
DEFAULT_LOSS_PER_INDEX_POINT_PCT = 0.6
DEFAULT_PARAMETRIC_PAYOUT_EFFICIENCY = 0.85
# How much of the climate stress can be reversed by 100% conservation uptake.
# Calibrated against AFOLU's ~13-25% share of regional emissions (IPCC AR6 WGIII Ch.7).
CONSERVATION_GHG_OFFSET_AT_FULL_UPTAKE = 0.20

# ============================================================== Sidebar
st.sidebar.markdown("## ⚙️ Scenario Controls")
country = st.sidebar.selectbox(
    "🌏 Country", ["MYS", "IDN"],
    format_func=lambda c: {"MYS": "🇲🇾 Malaysia", "IDN": "🇮🇩 Indonesia"}[c])
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔥 Climate Stress")

ghg_stress_pct = st.sidebar.slider(
    "2030 GHG Emission Increase (%)", 0, 50, 20, 1)

st.sidebar.markdown("### 🛡️ Mitigation Strategy")
adoption_pct = st.sidebar.slider(
    "Parametric Insurance Adoption (%)", 0, 100, 40, 5)
conservation_pct = st.sidebar.slider(
    "Forest-Conservation Uptake (%)", 0, 100, 30, 5,
    help="NDVI-triggered parametric payouts to landowners that disincentivise "
         "deforestation. Bends the stressed GHG path downward.")

st.sidebar.markdown("### 💰 Exposure")
agri_gdp = st.sidebar.number_input(
    f"Agricultural GDP ({country}, USD bn)",
    value=AGRI_GDP_BN[country], step=1.0)

with st.sidebar.expander("Advanced Actuarial Assumptions"):
    LOSS_PER_INDEX_POINT_PCT = st.slider(
        "Loss intensity (% of agri GDP per crop-index point drop)",
        0.1, 2.0, DEFAULT_LOSS_PER_INDEX_POINT_PCT, 0.05,
        help="Translates a 1-point drop in the Crop Production Index into a "
             "% of agricultural GDP at risk.")
    PARAMETRIC_PAYOUT_EFFICIENCY = st.slider(
        "Parametric payout efficiency (% of loss covered when adopted)",
        0.0, 1.0, DEFAULT_PARAMETRIC_PAYOUT_EFFICIENCY, 0.05,
        help="Share of incurred loss that parametric triggers reimburse "
             "(net of basis risk).")

# ============================================================== Pull model
proj = {int(y): v for y, v in METRICS["projection_2030"][country]["baseline_path"].items()}
val = METRICS["validation_2024"][country]
sens = METRICS["sensitivity"][country]
corr = METRICS["correlation"][country]

# ============================================================== Build paths
years = np.array(sorted(proj.keys()))            # 2024..2030
baseline_path = np.array([proj[y] for y in years])

# Stress: linear ramp 0% -> ghg_stress_pct from 2024 to 2030
ramp = np.linspace(0, ghg_stress_pct / 100.0, len(years))
stressed_path = baseline_path * (1 + ramp)

# STRATEGY EFFECT ON THE CLIMATE INDICATOR (handbook §4.3 requirement):
# Forest-conservation uptake reduces the stress add-on. At 100% uptake, up to
# CONSERVATION_GHG_OFFSET_AT_FULL_UPTAKE of the stress is neutralised.
strategy_offset = (conservation_pct / 100.0) * CONSERVATION_GHG_OFFSET_AT_FULL_UPTAKE
strategy_path = baseline_path * (1 + ramp * (1 - strategy_offset))

# ============================================================== Loss math
ghg_pct_uplift = (strategy_path - baseline_path) / baseline_path * 100  # residual stress %
crop_drop_pts = ghg_pct_uplift * sens["crop_idx_pts_per_1pct_ghg"]
crop_damage_pts = np.abs(crop_drop_pts)  # tail-volatility framing (see report §4)

agri_gdp_musd = agri_gdp * 1000          # USD millions
loss_traditional_musd = crop_damage_pts * (LOSS_PER_INDEX_POINT_PCT / 100.0) * agri_gdp_musd
loss_mitigated_musd = loss_traditional_musd * (1 - (adoption_pct / 100.0) * PARAMETRIC_PAYOUT_EFFICIENCY)
saved_musd = loss_traditional_musd - loss_mitigated_musd

# ============================================================== KPI strip
k1, k2, k3, k4 = st.columns(4)
k1.metric("📊 2024 Model MAPE", f"{val['mape']:.2f}%",
          help="Out-of-sample error: predicted 2024 vs actual 2024")
k2.metric("📈 Baseline 2030 GHG", f"{baseline_path[-1]:,.0f} Mt")
k3.metric("🔥 Stressed 2030 GHG", f"{stressed_path[-1]:,.0f} Mt",
          delta=f"+{ghg_stress_pct}%")
k4.metric("🌱 Strategy-Adjusted 2030", f"{strategy_path[-1]:,.0f} Mt",
          delta=f"-{(stressed_path[-1]-strategy_path[-1])/stressed_path[-1]*100:.1f}% vs stress",
          delta_color="inverse")

st.markdown("---")

# ============================================================== Charts
left, right = st.columns([3, 2])

with left:
    st.markdown("### 🌍 GHG Path: Baseline / Stressed / Strategy-Adjusted")
    ghg_df = pd.DataFrame({
        "Year": years,
        "Baseline": baseline_path,
        "Stressed": stressed_path,
        "With Strategy": strategy_path,
    }).set_index("Year")
    st.line_chart(ghg_df, color=["#2c3e50", "#c0392b", "#27ae60"])
    st.caption("💡 Forest-conservation uptake bends the stressed path downward — "
               "the strategy acts directly on the climate indicator (handbook §4.3).")

    st.markdown("### 💸 Financial Loss: Traditional vs Parametric-Mitigated")
    chart_df = pd.DataFrame({
        "Year": years,
        "Traditional Loss": loss_traditional_musd,
        "Mitigated with Parametric": loss_mitigated_musd,
        "Saved Economic Value": saved_musd,
    }).set_index("Year")
    st.area_chart(chart_df, color=["#c0392b", "#f39c12", "#27ae60"])

    cum_loss = loss_traditional_musd.sum()
    cum_saved = saved_musd.sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Cumulative Traditional Loss 2024-30", f"${cum_loss:,.0f}M")
    m2.metric("Cumulative Loss Avoided", f"${cum_saved:,.0f}M",
              delta=f"{cum_saved/cum_loss*100:.0f}% absorbed" if cum_loss > 0 else "n/a")
    m3.metric("Net Residual Loss", f"${cum_loss-cum_saved:,.0f}M")

with right:
    st.markdown("### 🔬 Model Diagnostics")
    st.info(
        f"**Country:** {country}  \n"
        f"**Train window:** 1970–2023  \n"
        f"**Model:** Quadratic OLS on Year  \n"
        f"**2024 actual:** {val['actual']:,.2f} Mt CO₂e  \n"
        f"**2024 predicted:** {val['predicted']:,.2f} Mt CO₂e  \n"
        f"**Signed error:** {val['pct_error']:+.2f}%"
    )

    st.markdown("### 🔗 Correlation Evidence")
    cc1, cc2 = st.columns(2)
    cc1.metric("GHG ↔ Crop", f"{corr['ghg_vs_crop']:+.3f}")
    cc2.metric("Forest ↔ Crop", f"{corr['forest_vs_crop']:+.3f}")
    st.caption(f"n = {corr['n_years']} overlapping years")

    st.markdown("### ⚖️ Scenario Assumptions")
    st.markdown(
        f"""
        | Parameter | Value |
        |---|---:|
        | Loss intensity (% agri-GDP / index pt) | **{LOSS_PER_INDEX_POINT_PCT:.2f}%** |
        | Parametric payout efficiency | **{PARAMETRIC_PAYOUT_EFFICIENCY:.0%}** |
        | Conservation max GHG offset @ 100% | **{CONSERVATION_GHG_OFFSET_AT_FULL_UPTAKE:.0%}** |
        | Sensitivity (idx pts / +1% GHG) | **{sens['crop_idx_pts_per_1pct_ghg']:.3f}** |
        """
    )

st.markdown("---")
with st.expander("📋 Historical WDI data used"):
    hist = DATA[DATA["Country_Code"] == country].sort_values("Year")
    st.dataframe(hist, use_container_width=True, hide_index=True)

st.caption(
    "⚠️ Disclaimer: stylised stress test for illustrative purposes. Loss intensity, "
    "payout efficiency, and conservation-offset are configurable assumptions, not "
    "Hannover Re calibrations."
)
