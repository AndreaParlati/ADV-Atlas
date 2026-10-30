"""
Data Loader & Coincidence Query Module for Phase 3.
Handles hazard catalogues, Sentinel-1 STAC caches, and L3 Altimeter tracks.
"""

import json
import os
import shapely.geometry as sgeom
from shapely import wkt as swkt
from pyproj import Geod
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import config_phase3 as cfg

GEOD = Geod(ellps="WGS84")
_geom_cache = {}

CATALOGUE_COLUMNS = [
    "event_id", "datetime", "lon", "lat", "Hs_cmems", "T0_cmems",
    "flag_reason", "route_node", "n_steps", "event_start", "event_end"
]

def open_wave_dataset(year):
    """Carica il reanalysis locale delle onde CMEMS per un dato anno."""
    local = sorted(cfg.WAVE_LOCAL_DIR.glob(f"{cfg.WAVE_DATASET_ID}*_{year}-01-01-{year}-12-31.nc"))
    if not local:
        print(f"[wave] {year}: Nessun file trovato in {cfg.WAVE_LOCAL_DIR.name}/")
        return None
    return xr.open_dataset(local[0])

def interp_to_route(da, route_lons, route_lats):
    """Interpolazione bilineare sui nodi di rotta con fallback al nearest cell per terraferma."""
    pts = dict(
        longitude=xr.DataArray(route_lons, dims="node"),
        latitude=xr.DataArray(route_lats, dims="node")
    )
    return da.interp(**pts).fillna(da.sel(**pts, method="nearest")).load()

def build_hazard_catalogue_year(year, route_lons, route_lats):
    """Costruzione inline del catalogo eventi tramite proxy di altezza d'onda significativa."""
    ds = open_wave_dataset(year)
    if ds is None:
        return pd.DataFrame(columns=CATALOGUE_COLUMNS)
    
    hs = interp_to_route(ds["VHM0"], route_lons, route_lats)
    t0_var = next((v for v in ("VTPK", "VTM10", "VTM01_SW1") if v in ds), None)
    t0 = interp_to_route(ds[t0_var], route_lons, route_lats) if t0_var else hs * np.nan
    ds.close()

    baseline = hs.rolling(time=cfg.ABNORMALITY_WINDOW_STEPS, center=True, min_periods=1).mean()
    heave = (hs > cfg.HEAVE_THRESH_M).values
    abnormal = ((hs / baseline) > cfg.ABNORMALITY_IDX).values
    flag = heave | abnormal

    times = pd.to_datetime(hs["time"].values)
    step = pd.Timedelta(hours=3)
    hs_v, t0_v = hs.values, t0.values
    rows = []
    
    for j in range(len(route_lons)):
        padded = np.r_[False, flag[:, j], False]
        starts = np.flatnonzero(~padded[:-1] & padded[1:])
        ends = np.flatnonzero(padded[:-1] & ~padded[1:])
        for s, e in zip(starts, ends):
            k = s + int(np.nanargmax(hs_v[s:e, j]))
            reasons = [name for name, m in (("heave_proxy", heave), ("abnormality", abnormal)) if m[s:e, j].any()]
            rows.append(dict(
                datetime=times[k], lon=float(route_lons[j]), lat=float(route_lats[j]),
                Hs_cmems=float(hs_v[k, j]), T0_cmems=float(t0_v[k, j]),
                flag_reason="+".join(reasons), route_node=j, n_steps=int(e - s),
                event_start=times[s], event_end=times[e - 1] + step
            ))
            
    cat = pd.DataFrame(rows).sort_values(["datetime", "route_node"]).reset_index(drop=True)
    if not cat.empty:
        cat.insert(0, "event_id", [f"{year}-{i:05d}" for i in range(len(cat))])
    return cat[CATALOGUE_COLUMNS]

def load_or_build_catalogue(year_start, year_end, route_lons, route_lats):
    """Carica il catalogo della Fase 2 se presente, altrimenti lo compila inline."""
    parts = []
    for year in range(year_start, year_end + 1):
        path = cfg.DATA_DIR / f"hazard_catalogue_{year}.parquet"
        if path.exists():
            print(f"[catalogue] {year}: Caricato da {path.name}")
            parts.append(pd.read_parquet(path))
            continue
        try:
            cat = build_hazard_catalogue_year(year, route_lons, route_lats)
        except Exception as exc:
            print(f"[catalogue] {year}: Errore generazione inline: {exc}")
            continue
        if len(cat):
            cat.to_parquet(path, index=False)
        parts.append(cat)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=CATALOGUE_COLUMNS)

# ── Sentinel-1 Coincidence Queries
def load_s1_catalogue(path=cfg.S1_CACHE_PATH):
    if not path.exists():
        print(f"[sar] Attenzione: {path.name} non trovato.")
        return {}
    return json.loads(path.read_text())

def _utc_naive(value):
    ts = pd.Timestamp(value)
    return ts.tz_convert(None) if ts.tzinfo is not None else ts

def _s1_day(day, s1_catalogue):
    records, ok = [], True
    for col in cfg.SAR_COLLECTIONS:
        key = f"{col}|{day}"
        if key in s1_catalogue:
            records.extend(s1_catalogue[key])
        else:
            ok = False
    return records, ok

def query_sentinel1_footprints(event_lon, event_lat, event_time, s1_catalogue, event_id=None):
    t = _utc_naive(event_time)
    t_start, t_end = t - pd.Timedelta(hours=cfg.DELTA_T_HOURS), t + pd.Timedelta(hours=cfg.DELTA_T_HOURS)
    dlat = cfg.DELTA_X_KM / 111.0
    dlon = cfg.DELTA_X_KM / (111.0 * np.cos(np.radians(event_lat)))
    bbox = sgeom.box(event_lon - dlon, event_lat - dlat, event_lon + dlon, event_lat + dlat)
    buffer = sgeom.Point(event_lon, event_lat).buffer(cfg.DELTA_X_KM / 111.0)

    records, query_ok = [], True
    for day in pd.date_range(t_start.normalize(), t_end.normalize(), freq="D"):
        recs, ok = _s1_day(day.strftime("%Y-%m-%d"), s1_catalogue)
        records.extend(recs)
        query_ok &= ok

    out, seen = [], set()
    for r in records:
        if r["item_id"] in seen:
            continue
        seen.add(r["item_id"])
        a0, a1 = _utc_naive(r["acq_start"]), _utc_naive(r["acq_end"])
        if a1 < t_start or a0 > t_end:
            continue
        geom = _geom_cache.get(r["item_id"])
        if geom is None:
            geom = _geom_cache[r["item_id"]] = swkt.loads(r["footprint_wkt"])
        if not geom.intersects(bbox):
            continue
        out.append(dict(
            event_id=event_id, sat_id=r["sat_id"], item_id=r["item_id"], acq_time=a0,
            dt_hours=((a0 + (a1 - a0) / 2) - t) / pd.Timedelta(hours=1),
            sensor_mode=r["sensor_mode"], orbit_direction=r["orbit_direction"],
            footprint_wkt=r["footprint_wkt"], coincident=bool(geom.intersects(buffer)),
            query_ok=query_ok
        ))
    if not out:
        out.append(dict(event_id=event_id, coincident=False, query_ok=query_ok))
    return out

# ── Altimeter L3 Queries
def load_altimeter_l3(year_start, year_end):
    parts = []
    for year in range(year_start, year_end + 1):
        local = cfg.ALT_LOCAL_DIR / f"swh_L3_alt_{year}.csv"
        if not local.exists():
            continue
        df = pd.read_csv(local, usecols=["variable", "platform_id", "time", "longitude", "latitude", "value"])
        df = df[df["variable"] == "swh"]
        parts.append(pd.DataFrame({
            "time": pd.to_datetime(df["time"], utc=True).dt.tz_convert(None),
            "longitude": df["longitude"], "latitude": df["latitude"],
            "VAVH": df["value"], "platform": df["platform_id"]
        }))
    if not parts:
        return xr.Dataset({"VAVH": ("obs", np.array([], float)), "platform": ("obs", np.array([], object))},
                          coords={"time": ("obs", np.array([], "datetime64[ns]")),
                                  "latitude": ("obs", np.array([], float)),
                                  "longitude": ("obs", np.array([], float))})
    df = pd.concat(parts, ignore_index=True).dropna(subset=["VAVH"])
    df = df[df["longitude"].between(-70.0, -5.0) & df["latitude"].between(30.0, 65.0)].sort_values("time").reset_index(drop=True)
    return xr.Dataset(
        {"VAVH": ("obs", df["VAVH"].to_numpy(float)), "platform": ("obs", df["platform"].astype(str).to_numpy(object))},
        coords={"time": ("obs", df["time"].to_numpy("datetime64[ns]")),
                "latitude": ("obs", df["latitude"].to_numpy(float)),
                "longitude": ("obs", df["longitude"].to_numpy(float))}
    )

def find_altimeter_coincidences(event_lon, event_lat, event_time, alt_ds):
    times = alt_ds["time"].values
    t = np.datetime64(_utc_naive(event_time), "ns")
    dt = np.timedelta64(int(cfg.DELTA_T_HOURS * 3600), "s")
    i0 = np.searchsorted(times, t - dt, side="right")
    i1 = np.searchsorted(times, t + dt, side="left")
    if i1 <= i0:
        return None
    lon = alt_ds["longitude"].values[i0:i1]
    lat = alt_ds["latitude"].values[i0:i1]
    n = i1 - i0
    _, _, dist_m = GEOD.inv(np.full(n, event_lon), np.full(n, event_lat), lon, lat)
    dist_km = dist_m / 1000.0
    inside = dist_km < cfg.DELTA_X_KM
    if not inside.any():
        return None
    k = int(np.argmin(np.where(inside, dist_km, np.inf)))
    platform = alt_ds["platform"].values[i0:i1]
    vavh = alt_ds["VAVH"].values[i0:i1]
    t_k = times[i0 + k]
    near = (platform == platform[k]) & (np.abs(times[i0:i1] - t_k) <= np.timedelta64(5, "s"))
    return dict(
        dist_km=float(dist_km[k]), dt_hours=float((t_k - t) / np.timedelta64(1, "h")),
        Hs_altimeter=float(np.nanmedian(vavh[near])), alt_platform=str(platform[k]),
        platforms_in_window=",".join(sorted(set(platform[inside]))),
        alt_time=pd.Timestamp(t_k), alt_lon=float(lon[k]), alt_lat=float(lat[k])
    )