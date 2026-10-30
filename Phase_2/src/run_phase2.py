"""
Main Execution Script for Phase 2 Pipeline.
Run this script to process all specified years and build the hazard catalogues.
"""

import pandas as pd
import config
from data_loader import (
    build_data_inventory,
    load_wave_reanalysis,
    interpolate_along_route,
    load_wind_speed,
    attach_wind,
)
from hazard_processor import apply_hazard_flags, build_catalogue, validate_catalogue

def main():
    print("Initializing Phase 2 Pipeline...")
    found_files = build_data_inventory()
    summary = []

    for year in range(config.YEAR_START, config.YEAR_END + 1):
        print(f"\n================ Processing Year {year} ================")
        try:
            wave_ds = load_wave_reanalysis(year, found_files)
            if wave_ds is None:
                continue

            route_df = interpolate_along_route(wave_ds)
            wave_ds.close()

            wind_df = load_wind_speed(year, found_files)
            route_df = attach_wind(route_df, wind_df)
            route_df = apply_hazard_flags(route_df)

            cat = build_catalogue(route_df, year)
            out_path = config.DATA_DIR / f"hazard_catalogue_{year}.parquet"
            cat.to_parquet(out_path, index=False, engine="pyarrow")
            print(f"[save] {year}: {len(cat)} hazard events exported to {out_path}")

            # Run integrity checks
            validate_catalogue(year)

            summary.append({
                "year": year,
                "n_records": len(route_df),
                "n_events": len(cat),
                "n_heave": int(cat["flag_heave"].sum()),
                "n_rogue": int(cat["flag_rogue"].sum()),
                "Hs_max": cat["Hs_cmems"].max(),
                "U10_coverage_%": 100 * cat["U10_era5"].notna().mean() if len(cat) else 0.0,
            })
        except Exception as exc:
            print(f"[ERROR] Year {year} failed with exception: {exc}")

    summary_df = pd.DataFrame(summary)
    print("\n================ Processing Summary ================")
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
    else:
        print("No years were successfully processed.")

if __name__ == "__main__":
    main()