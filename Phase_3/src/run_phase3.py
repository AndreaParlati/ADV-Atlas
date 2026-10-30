"""
Main Execution Script for Phase 3 Pipeline.
Orchestrates hazard loading, satellite queries, statistical hypotheses (H1-H3), and ADV atlas.
"""

import pandas as pd
import config_phase3 as cfg
from data_loader_phase3 import (
    load_or_build_catalogue,
    load_s1_catalogue,
    query_sentinel1_footprints,
    load_altimeter_l3,
    find_altimeter_coincidences
)
from analysis_phase3 import (
    compute_h1_statistics,
    compute_h2_spatial_bins,
    analyze_h3_forecast_bias
)
from tqdm import tqdm

def main():
    print("Inizializzazione Pipeline Fase 3 (Coincidenza Spazio-Temporale)...")
    
    # 1. Caricamento catalogo hazard
    catalogue = load_or_build_catalogue(cfg.YEAR_START, cfg.YEAR_END, cfg.ROUTE_LONS, cfg.ROUTE_LATS)
    print(f"Eventi di pericolo totali caricati: {len(catalogue)}")
    if catalogue.empty:
        print("Nessun evento disponibile. Interrompo l'esecuzione.")
        return

    # 2. Interrogazione coppe Sentinel-1
    sar_raw_path = cfg.DATA_DIR / "sar_coincidence_raw.parquet"
    if cfg.REUSE_CHECKPOINTS and sar_raw_path.exists():
        print(f"[sar] Caricamento checkpoint da {sar_raw_path.name}")
        sar_results = pd.read_parquet(sar_raw_path)
    else:
        s1_catalogue = load_s1_catalogue()
        rows = []
        for ev in tqdm(catalogue.itertuples(index=False), total=len(catalogue), desc="Query Sentinel-1"):
            try:
                rows.extend(query_sentinel1_footprints(ev.lon, ev.lat, ev.datetime, s1_catalogue, event_id=ev.event_id))
            except Exception as exc:
                rows.append(dict(event_id=ev.event_id, coincident=False, query_ok=False))
        sar_results = pd.DataFrame(rows)
        sar_results.to_parquet(sar_raw_path, index=False)

    sar_results["coincident"] = sar_results["coincident"].astype("boolean").fillna(False).astype(bool)

    # 3. Interrogazione Altimetri L3
    alt_raw_path = cfg.DATA_DIR / "altimeter_coincidence_raw.parquet"
    if cfg.REUSE_CHECKPOINTS and alt_raw_path.exists():
        print(f"[alt] Caricamento checkpoint da {alt_raw_path.name}")
        alt_results = pd.read_parquet(alt_raw_path)
    else:
        alt_ds = load_altimeter_l3(cfg.YEAR_START, cfg.YEAR_END)
        rows = []
        for ev in tqdm(catalogue.itertuples(index=False), total=len(catalogue), desc="Query Altimetri"):
            hit = find_altimeter_coincidences(ev.lon, ev.lat, ev.datetime, alt_ds)
            rows.append({"event_id": ev.event_id, "Hs_cmems_at_event": ev.Hs_cmems, **(hit or {})})
        alt_results = pd.DataFrame(rows)
        alt_results.to_parquet(alt_raw_path, index=False)

    # 4. Consolidamento e Test Ipotesi H1-H3
    sar_evt = sar_results.groupby("event_id").agg(sar_coincident=("coincident", "any")).reset_index()
    merged = catalogue.merge(sar_evt, on="event_id", how="left").merge(alt_results, on="event_id", how="left")
    merged["sar_coincident"] = merged["sar_coincident"].astype("boolean").fillna(False).astype(bool)
    merged["alt_coincident"] = merged["Hs_altimeter"].notna()
    merged["any_coincident"] = merged["sar_coincident"] | merged["alt_coincident"]
    
    merged.to_parquet(cfg.DATA_DIR / "coincidence_merged.parquet", index=False)

    print("\n--- Risultati H1: Probabilità di Coincidenza Globale ---")
    h1_table = compute_h1_statistics(merged, sar_results)
    print(h1_table.to_string(index=False))

    print("\n--- Risultati H2: Eterogeneità Spaziale per Bin di Longitudine ---")
    by_bin = compute_h2_spatial_bins(merged)
    print(by_bin[["lon_bin_center", "P_SAR", "P_alt", "P_combined", "N_events"]].to_string(index=False))

    print("\n--- Risultati H3: Bias di Previsione del Modello ---")
    _, h3_stats = analyze_h3_forecast_bias(alt_results)
    for k, v in h3_stats.items():
        print(f"  {k}: {v}")

    print(f"\nPipeline completata con successo. File salvati in: {cfg.DATA_DIR}")

if __name__ == "__main__":
    main()