"""
Hazard Classification & Catalogue Generation.
Applies thresholds, exports Parquet catalogues, and runs schema verification.
"""

import numpy as np
import pandas as pd
import config

def apply_hazard_flags(df, heave_thresh=config.HEAVE_THRESH_M, rogue_hs_proxy=config.ROGUE_HS_PROXY):
    """Apply heave and rogue wave hazard boolean flags."""
    df = df.copy()
    df["flag_heave"] = (df["Hs"] > heave_thresh).astype(bool)
    df["flag_rogue"] = (df["Hs"] > rogue_hs_proxy).astype(bool)
    df["flag_any"] = df["flag_heave"] | df["flag_rogue"]
    return df

def build_catalogue(df, year):
    """Format flagged events to strictly match Phase 3 contract schema."""
    flagged = (
        df[df["flag_any"]]
        .sort_values(["time", "route_seg_idx"])
        .reset_index(drop=True)
        .rename(columns={"time": "datetime", "Hs": "Hs_cmems", "T0": "T0_cmems"})
    )
    flagged.insert(0, "event_id", [f"{year}_{i:05d}" for i in range(len(flagged))])
    flagged["datetime"] = pd.to_datetime(flagged["datetime"], utc=True)
    flagged["lon_bin"] = pd.cut(
        flagged["lon"],
        bins=config.LON_BIN_EDGES,
        labels=config.LON_BIN_LABELS,
        right=False,
    ).astype(str)
    
    flagged["flag_reason"] = np.where(
        flagged["flag_rogue"], "heave_proxy+rogue_proxy", "heave_proxy"
    )

    for col in ["U10_era5", "T0_cmems"]:
        if col not in flagged.columns:
            flagged[col] = np.nan

    flagged["route_seg_idx"] = flagged["route_seg_idx"].astype("int64")
    for col in ["lon", "lat", "Hs_cmems", "T0_cmems", "U10_era5"]:
        flagged[col] = flagged[col].astype("float64")

    return flagged[config.CONTRACT_COLS + config.COMPAT_COLS]

def validate_catalogue(year):
    """Validate generated Parquet catalogue file against schema contract."""
    path = config.DATA_DIR / f"hazard_catalogue_{year}.parquet"
    if not path.exists():
        print(f"Validation Error {year}: File not found at {path}")
        return False

    try:
        df = pd.read_parquet(path)
    except Exception as exc:
        print(f"Validation Error {year}: Cannot read Parquet file: {exc}")
        return False

    missing = [c for c in config.CONTRACT_COLS if c not in df.columns]
    if missing:
        print(f"Schema Error {year}: Missing columns {missing}")
        return False

    checks = [
        (df["event_id"].is_unique, "event_id unique"),
        (df["lon"].between(-70, -5).all(), "lon in [-70, -5]"),
        (df["lat"].between(30, 65).all(), "lat in [30, 65]"),
        ((df["Hs_cmems"] >= 0).all(), "Hs_cmems >= 0"),
        (isinstance(df["datetime"].dtype, pd.DatetimeTZDtype) and str(df["datetime"].dt.tz) == "UTC", "datetime tz-aware UTC"),
        (df["datetime"].dt.year.eq(year).all(), f"all events in {year}"),
        (df["flag_any"].all(), "every row flagged"),
        (df["route_seg_idx"].between(0, config.N_ROUTE_PTS - 1).all(), "route_seg_idx valid"),
        (df["lon_bin"].isin(config.LON_BIN_LABELS).all(), "lon_bin labels valid"),
    ]

    all_passed = True
    print(f"\n--- Validating {year} Catalogue ---")
    for ok, label in checks:
        status = "PASS" if ok else "FAIL"
        print(f" [{status}] {label}")
        if not ok:
            all_passed = False

    return all_passed