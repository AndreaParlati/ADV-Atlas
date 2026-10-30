"""
Phase 2 Configuration Module.
Centralizes paths, thresholds, route waypoints, and candidate variable names.
"""

import os
from pathlib import Path
import numpy as np

# ── Paths (relative to the project root)
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
FIGURES_DIR = PROJECT_DIR / "figures"

DATA_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

# Search directories for local NetCDF inputs
SEARCH_DIRS = [
    DATA_DIR,
    PROJECT_DIR / "Wave_Reanalysis",
    PROJECT_DIR / "ERA5",
    PROJECT_DIR / "Physics_Reanalysis",
    PROJECT_DIR / "L4_altimetry",
]

# ── Processing Time Frame
YEAR_START = 2010
YEAR_END = 2020

# ── Route Specification: Lisbon (38.7°N, -9.1°E) → Halifax (44.7°N, -63.6°E)
N_ROUTE_PTS = 60
ROUTE_LONS = np.linspace(-9.1, -63.6, N_ROUTE_PTS)
ROUTE_LATS = np.linspace(38.7, 44.7, N_ROUTE_PTS)

# ── Hazard Thresholds
HEAVE_THRESH_M = 3.5   # Significant wave height proxy [m]
ROGUE_HS_PROXY = 6.0   # Hs threshold as rogue-wave likelihood proxy [m]

# ── Longitude Bins (5° resolution)
LON_BIN_EDGES = np.arange(-65, -4, 5)  # [-65, -60, ..., -10, -5]
LON_BIN_LABELS = [
    f"{int(LON_BIN_EDGES[i])}_{int(LON_BIN_EDGES[i + 1])}"
    for i in range(len(LON_BIN_EDGES) - 1)
]

# ── Variable Candidates
HS_CANDIDATES = ["VHM0", "hs", "swh", "significant_wave_height"]
T0_CANDIDATES = ["VTPK", "tp", "pp1d", "peak_period"]
T0_FALLBACKS = ["VTM10", "mwp"]
WIND_U_V = ("u10", "v10")
TIME_CANDIDATES = ["time", "valid_time"]

# ── CMEMS Streaming Config
WAVE_DATASET_ID = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"
CMEMS_USER = os.getenv("CMEMS_USERNAME", "YOUR_USERNAME")
CMEMS_PASS = os.getenv("CMEMS_PASSWORD", "YOUR_PASSWORD")

# ── Contract Columns
CONTRACT_COLS = [
    "event_id",
    "datetime",
    "lon",
    "lat",
    "Hs_cmems",
    "T0_cmems",
    "U10_era5",
    "flag_heave",
    "flag_rogue",
    "flag_any",
    "route_seg_idx",
    "lon_bin",
]
COMPAT_COLS = ["flag_reason"]