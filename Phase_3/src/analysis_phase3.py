"""
Analysis & Statistics Module for Phase 3 (H1, H2, H3, ADV Atlas).
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import config_phase3 as cfg

def compute_h1_statistics(merged_df, sar_results):
    """Calcola le probabilità di coincidenza globale (H1)."""
    n_events = len(merged_df)
    p_sar = float(merged_df["sar_coincident"].mean()) if n_events else np.nan
    p_alt = float(merged_df["alt_coincident"].mean()) if n_events else np.nan
    p_any = float(merged_df["any_coincident"].mean()) if n_events else np.nan

    h1_table = pd.DataFrame({
        "source": ["SAR_only", "altimeter_only", "SAR_or_altimeter"],
        "N_coincident": [
            int(merged_df["sar_coincident"].sum()),
            int(merged_df["alt_coincident"].sum()),
            int(merged_df["any_coincident"].sum())
        ],
        "N_total_events": n_events,
        "P": [p_sar, p_alt, p_any],
    })
    return h1_table

def compute_h2_spatial_bins(merged_df):
    """Analisi eterogeneità spaziale lungo i bin di longitudine (H2)."""
    df = merged_df.copy()
    df["lon_bin"] = pd.cut(df["lon"], cfg.LON_EDGES)
    by_bin = (
        df.groupby("lon_bin", observed=False)
        .agg(
            P_SAR=("sar_coincident", "mean"),
            P_alt=("alt_coincident", "mean"),
            P_combined=("any_coincident", "mean"),
            N_events=("event_id", "size")
        )
    )
    by_bin.insert(0, "lon_bin_center", [iv.mid for iv in by_bin.index])
    return by_bin.sort_values("lon_bin_center", ascending=False).reset_index(drop=True)

def analyze_h3_forecast_bias(alt_results):
    """Analisi del bias di previsione del modello CMEMS (H3)."""
    h3 = alt_results.dropna(subset=["Hs_altimeter"]).copy()
    h3["delta_Hs"] = h3["Hs_altimeter"] - h3["Hs_cmems_at_event"]
    
    mean_bias = float(h3["delta_Hs"].mean()) if len(h3) else np.nan
    median_bias = float(h3["delta_Hs"].median()) if len(h3) else np.nan
    pct_above = 100 * float((h3["delta_Hs"] > 0).mean()) if len(h3) else np.nan
    
    return h3, {
        "mean_bias": mean_bias,
        "median_bias": median_bias,
        "pct_above": pct_above,
        "n_coincident": len(h3)
    }