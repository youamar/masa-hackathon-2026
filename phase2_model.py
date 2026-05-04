"""
Phase 2 — Correlation analysis, 2024 GHG out-of-sample backtest,
2030 baseline projection, and chart generation for the report.

Outputs:
  model_metrics.json          (consumed by app.py)
  figures/fit_<country>.png   (in-sample fit + 2024 hold-out)
  figures/projection_2030.png (baseline + stress band 2024-2030)
  figures/scatter_ghg_crop.png (correlation evidence)
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless backend (CI-safe, no display needed)
import matplotlib.pyplot as plt

FIG_DIR = Path("figures")
FIG_DIR.mkdir(exist_ok=True)

df = pd.read_csv("cleaned_wdi_data.csv")
INDICATORS = ["GHG_Emissions_MtCO2e", "Forest_Area_PctLand", "Crop_Production_Index"]
COUNTRIES = ["MYS", "IDN"]
COUNTRY_LABEL = {"MYS": "Malaysia", "IDN": "Indonesia"}
COLOR = {"MYS": "#c0392b", "IDN": "#2c3e50"}

results = {
    "correlation": {}, "validation_2024": {}, "projection_2030": {},
    "model": "Quadratic OLS on Year (numpy.polyfit deg=2)",
}

# =========================================================================
# 1. CORRELATION ANALYSIS  (per country, on overlapping non-null years)
# =========================================================================
print("=" * 70)
print("1. CORRELATION MATRIX (climate indicators vs Crop Production Index)")
print("=" * 70)
for c in COUNTRIES:
    # Drop years where any of the 3 indicators is missing -> common support
    sub = df[df["Country_Code"] == c][INDICATORS].dropna()
    corr = sub.corr()
    print(f"\n[{c}]  overlapping years used = {len(sub)}")
    print(corr.round(3).to_string())
    results["correlation"][c] = {
        "n_years": int(len(sub)),
        "matrix": corr.round(4).to_dict(),
        "ghg_vs_crop": float(corr.loc["GHG_Emissions_MtCO2e", "Crop_Production_Index"]),
        "forest_vs_crop": float(corr.loc["Forest_Area_PctLand", "Crop_Production_Index"]),
    }

# =========================================================================
# 2. BASELINE GHG MODEL  (train <=2023, validate on 2024 hold-out)
# =========================================================================
print("\n" + "=" * 70)
print("2. GHG BASELINE MODEL: train <=2023, predict 2024, validate")
print("=" * 70)

# Set up the projection-vs-fit chart now; we will draw both countries on it
fig_proj, ax_proj = plt.subplots(figsize=(8, 4.5))

for c in COUNTRIES:
    # Select GHG series for this country, drop NaN years
    sub = df[(df["Country_Code"] == c) & df["GHG_Emissions_MtCO2e"].notna()][["Year", "GHG_Emissions_MtCO2e"]]
    train = sub[sub["Year"] <= 2023]                    # strict hold-out: 2023 cut-off
    actual_2024 = float(sub.loc[sub["Year"] == 2024, "GHG_Emissions_MtCO2e"].iloc[0])

    # Fit quadratic time trend (deg=2 chosen over linear after residual diagnostics)
    coefs = np.polyfit(train["Year"], train["GHG_Emissions_MtCO2e"], deg=2)
    poly = np.poly1d(coefs)

    # Out-of-sample 2024 prediction & error metrics
    pred_2024 = float(poly(2024))
    abs_err = pred_2024 - actual_2024
    pct_err = abs_err / actual_2024 * 100
    train_pred = poly(train["Year"])
    rmse = float(np.sqrt(np.mean((train_pred - train["GHG_Emissions_MtCO2e"]) ** 2)))

    # Project 2024-2030 using the fitted polynomial
    future_years = list(range(2024, 2031))
    projection = {int(y): float(poly(y)) for y in future_years}

    print(f"\n[{c}]  train rows: {len(train)} ({int(train.Year.min())}-{int(train.Year.max())})")
    print(f"  2024 actual   : {actual_2024:,.2f} Mt CO2e")
    print(f"  2024 predicted: {pred_2024:,.2f} Mt CO2e")
    print(f"  2024 MAPE     : {abs(pct_err):.2f}%   (signed err {pct_err:+.2f}%)")
    print(f"  Train RMSE    : {rmse:,.2f} Mt CO2e")
    print(f"  2030 baseline : {projection[2030]:,.2f} Mt CO2e")

    results["validation_2024"][c] = {
        "actual": actual_2024, "predicted": pred_2024,
        "abs_error": abs_err, "pct_error": pct_err, "mape": abs(pct_err),
        "train_rmse": rmse, "train_n": int(len(train)),
    }
    results["projection_2030"][c] = {
        "baseline_path": projection,
        "baseline_2030": projection[2030],
        "poly_coefs_high_to_low": [float(x) for x in coefs],
    }

    # ---- Per-country fit chart (history + 2024 hold-out marker) ---------
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(sub["Year"], sub["GHG_Emissions_MtCO2e"], s=18, label="Actual", color=COLOR[c])
    fit_years = np.arange(int(train["Year"].min()), 2031)
    ax.plot(fit_years, poly(fit_years), color=COLOR[c], lw=1.5, label="Quadratic fit / projection")
    ax.axvline(2023.5, color="grey", ls="--", lw=0.8)
    ax.scatter([2024], [actual_2024], marker="o", s=70, edgecolor="black",
               facecolor="none", lw=1.5, label=f"2024 actual ({actual_2024:,.0f})")
    ax.scatter([2024], [pred_2024], marker="x", s=70, color="black",
               label=f"2024 predicted ({pred_2024:,.0f})")
    ax.set_title(f"{COUNTRY_LABEL[c]} — GHG Emissions: fit & 2024 hold-out (MAPE {abs(pct_err):.2f}%)")
    ax.set_xlabel("Year"); ax.set_ylabel("Mt CO2e (excl. LULUCF, AR5)")
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"fit_{c}.png", dpi=140)
    plt.close(fig)

    # ---- Add this country to the combined 2030 projection chart ---------
    ax_proj.plot(future_years, [projection[y] for y in future_years],
                 marker="o", color=COLOR[c], label=f"{COUNTRY_LABEL[c]} baseline")
    # Illustrative +20% stress band
    stressed = [projection[y] * (1 + 0.20 * (i / (len(future_years) - 1)))
                for i, y in enumerate(future_years)]
    ax_proj.fill_between(future_years, [projection[y] for y in future_years],
                         stressed, color=COLOR[c], alpha=0.15)

ax_proj.set_title("Baseline GHG Projection 2024-2030 (shaded band: +20% stress scenario)")
ax_proj.set_xlabel("Year"); ax_proj.set_ylabel("Mt CO2e")
ax_proj.legend(); ax_proj.grid(alpha=0.3)
fig_proj.tight_layout()
fig_proj.savefig(FIG_DIR / "projection_2030.png", dpi=140)
plt.close(fig_proj)

# =========================================================================
# 3. SENSITIVITY OF CROP INDEX TO GHG  (single-variable slope per country)
# =========================================================================
results["sensitivity"] = {}
fig_sc, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
for ax, c in zip(axes, COUNTRIES):
    sub = df[df["Country_Code"] == c][["GHG_Emissions_MtCO2e", "Crop_Production_Index"]].dropna()
    if len(sub) >= 5:
        slope, intercept = np.polyfit(sub["GHG_Emissions_MtCO2e"], sub["Crop_Production_Index"], 1)
        # Index points per +1% GHG, evaluated at the country mean GHG level
        pts_per_pct_ghg = float(slope * sub["GHG_Emissions_MtCO2e"].mean() / 100.0)
        results["sensitivity"][c] = {
            "slope_crop_per_MtGHG": float(slope),
            "intercept": float(intercept),
            "crop_idx_pts_per_1pct_ghg": pts_per_pct_ghg,
            "mean_ghg": float(sub["GHG_Emissions_MtCO2e"].mean()),
            "mean_crop": float(sub["Crop_Production_Index"].mean()),
        }
        # Scatter + fitted line
        ax.scatter(sub["GHG_Emissions_MtCO2e"], sub["Crop_Production_Index"],
                   s=18, color=COLOR[c])
        xs = np.linspace(sub["GHG_Emissions_MtCO2e"].min(), sub["GHG_Emissions_MtCO2e"].max(), 50)
        ax.plot(xs, slope * xs + intercept, color="black", lw=1.0)
        r = results["correlation"][c]["ghg_vs_crop"]
        ax.set_title(f"{COUNTRY_LABEL[c]}  (r = {r:+.3f})")
        ax.set_xlabel("GHG (Mt CO2e)"); ax.set_ylabel("Crop Production Index")
        ax.grid(alpha=0.3)
fig_sc.suptitle("GHG Emissions vs Crop Production Index — overlap years", y=1.02)
fig_sc.tight_layout()
fig_sc.savefig(FIG_DIR / "scatter_ghg_crop.png", dpi=140, bbox_inches="tight")
plt.close(fig_sc)

# =========================================================================
# 4. PERSIST METRICS (consumed by Streamlit dashboard)
# =========================================================================
with open("model_metrics.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved -> model_metrics.json")
print(f"Saved figures -> {FIG_DIR}/  (fit_MYS.png, fit_IDN.png, projection_2030.png, scatter_ghg_crop.png)")
