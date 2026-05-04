"""
Phase 1 ETL — World Bank WDI wide-format -> clean year-indexed table.

Input  : WB_WDI_WIDEF.csv  (SDMX wide format, ~1,500 indicators x 217 economies x 65 years)
Output : cleaned_wdi_data.csv  (Country x Year x 3 indicator columns)

The three indicators chosen are the macro drivers our parametric reinsurance
thesis relies on: total GHG emissions (the climate driver), forest area
(natural-capital buffer / LULUCF proxy), and the crop production index
(operational outcome variable a parametric product would protect).
"""
import pandas as pd

SRC = "WB_WDI_WIDEF.csv"
OUT = "cleaned_wdi_data.csv"

# Indicator codes are SDMX-style (underscore), NOT the dotted WDI API codes
# the handbook references. Mapping verified by grepping the indicator
# dictionary inside WB_WDI_WIDEF.csv.
INDICATORS = {
    "WB_WDI_EN_GHG_ALL_MT_CE_AR5": "GHG_Emissions_MtCO2e",   # Total GHG excl. LULUCF, Mt CO2e (AR5)
    "WB_WDI_AG_LND_FRST_ZS":       "Forest_Area_PctLand",    # Forest area, % of land
    "WB_WDI_AG_PRD_CROP_XD":       "Crop_Production_Index",  # Crop prod. index (2014-16 = 100)
}
COUNTRIES = ["MYS", "IDN"]  # Malaysia & Indonesia — focus markets for the SEA thesis

# --- Load raw wide CSV ---------------------------------------------------
df = pd.read_csv(SRC, low_memory=False)

# --- Filter to focus countries + chosen indicators -----------------------
df = df[df["REF_AREA"].isin(COUNTRIES) & df["INDICATOR"].isin(INDICATORS)]

# --- Wide -> long: year columns are the numeric ones (1960..2025) --------
year_cols = [c for c in df.columns if c.isdigit()]
long = df.melt(
    id_vars=["REF_AREA", "REF_AREA_LABEL", "INDICATOR"],
    value_vars=year_cols, var_name="Year", value_name="Value",
)
long["Year"] = long["Year"].astype(int)
long["Value"] = pd.to_numeric(long["Value"], errors="coerce")  # blank -> NaN
long["Indicator"] = long["INDICATOR"].map(INDICATORS)          # rename to readable form

# --- Long -> tidy wide: one row per (Country, Year), 3 indicator columns -
wide = long.pivot_table(
    index=["REF_AREA", "REF_AREA_LABEL", "Year"],
    columns="Indicator", values="Value", aggfunc="first",
).reset_index().rename(columns={"REF_AREA": "Country_Code", "REF_AREA_LABEL": "Country"})
wide.columns.name = None
wide = wide.sort_values(["Country_Code", "Year"]).reset_index(drop=True)

# --- Persist + sanity print ----------------------------------------------
wide.to_csv(OUT, index=False)
print(f"Saved {OUT}: {wide.shape[0]} rows, {wide.shape[1]} cols")
print("\nFirst 5 rows:")
print(wide.head().to_string(index=False))
print("\nNon-null counts per indicator (per country):")
print(wide.groupby("Country_Code")[list(INDICATORS.values())].count())
print("\nMost recent rows with any data:")
print(wide.dropna(subset=list(INDICATORS.values()), how="all").groupby("Country_Code").tail(3).to_string(index=False))
