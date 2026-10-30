"""
Phase 3 Configuration Module.
Centralizes study area, coincidence windows, paths, and thresholds.
"""

from pathlib import Path
import numpy as np

# ── Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FIG_DIR = BASE_DIR / "figures"
WAVE_LOCAL_DIR = BASE_DIR / "Wave_Reanalysis"
ALT_LOCAL_DIR = BASE_DIR / "L3_altimetry"
S1_CACHE_PATH = DATA_DIR / "s1_items_cache.json"

for d in (DATA_DIR, FIG_DIR):
    d.mkdir(exist_ok=True, parents=True)

# ── Study Area & Route (Lisbon → Halifax)
ROUTE_LONS = np.linspace(-9.1, -63.6, 60)
ROUTE_LATS = np.linspace(38.7, 44.7, 60)

# ── Time Range & Coincidence Windows
YEAR_START, YEAR_END = 2022, 2022  # Modificare per multi-anno (es. 2010, 2020)
DELTA_T_HOURS = 3.0          # Half-window temporale [h]
DELTA_X_KM = 200.0           # Raggio spaziale di coincidenza [km]

# ── Sentinel-1 & CMEMS Specs
SAR_COLLECTIONS = ["sentinel-1-ocn", "sentinel-1-ocn-wv"]
WAVE_DATASET_ID = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"

# ── Physical & Hazard Thresholds
HEAVE_THRESH_M = 3.5
ABNORMALITY_IDX = 2.0
ABNORMALITY_WINDOW_STEPS = 240   # Finestra mobile di 30 giorni (240 x 3h)

# ── Corridor Segments & Bins (H2 & ADV)
GRAND_BANKS_LON = (-55.0, -45.0)
MID_ATLANTIC_LON = (-40.0, -20.0)
LON_EDGES = np.arange(-64.0, -8.0, 5.0)

REUSE_CHECKPOINTS = True