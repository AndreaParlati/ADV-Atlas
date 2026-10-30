"""
Data Inventory and Loading Module.
Handles scanning local .nc/zip files, streaming from CMEMS, and route interpolation.
"""

import zipfile
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm
import config

def open_found(meta):
    """Open an inventoried NetCDF file (plain file or member inside a CDS ZIP archive)."""
    if meta["member"] is None:
        return xr.open_dataset(meta["path"], engine="netcdf4")
    return xr.open_dataset(zipfile.ZipFile(meta["path"]).open(meta["member"]), engine="h5netcdf")

def _nc_sources(path):
    """Extract list of (key, path, member) tuples from a .nc or CDS zip file."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            return [(f"{path.name}::{m}", path, m) for m in z.namelist() if m.endswith(".nc")]
    return [(path.name, path, None)]

def build_data_inventory(search_dirs=config.SEARCH_DIRS):
    """Scans search_dirs for NetCDF files and builds metadata dictionary."""
    found_files = {}
    nc_paths = sorted(p for d in search_dirs if d.exists() for p in d.glob("*.nc"))
    
    for f in tqdm(nc_paths, desc="Inventorying NetCDF files"):
        try:
            sources = _nc_sources(f)
        except Exception as exc:
            print(f"WARNING: Cannot read {f}: {exc}")
            continue
            
        for key, path, member in sources:
            meta = {"path": path, "member": member}
            try:
                ds = open_found(meta)
            except Exception as exc:
                print(f"WARNING: Cannot open {key}: {exc}")
                continue
                
            time_name = next((t for t in config.TIME_CANDIDATES if t in ds.coords), None)
            if time_name is not None:
                tv = ds.coords[time_name].values
                time_range = (str(tv[0]), str(tv[-1]))
            else:
                time_range = (None, None)
                
            found_files[key] = {
                **meta,
                "vars": list(ds.data_vars),
                "dims": dict(ds.sizes),
                "coords": list(ds.coords),
                "time_name": time_name,
                "time_range": time_range,
            }
            ds.close()
            
    return found_files

def file_years(meta):
    """Return range of calendar years covered by an inventoried file."""
    t0, t1 = meta["time_range"]
    if t0 is None:
        return range(0)
    return range(pd.Timestamp(t0).year, pd.Timestamp(t1).year + 1)

def first_var(meta, candidates):
    """Get the first variable match from candidates in file metadata."""
    return next((v for v in candidates if v in meta["vars"]), None)

def _standardise(ds):
    """Standardize coordinate names to time, latitude, and longitude."""
    rename = {}
    for std, cands in (("time", config.TIME_CANDIDATES), 
                       ("latitude", ["lat", "latitude"]),
                       ("longitude", ["lon", "longitude"])):
        for c in cands:
            if c in ds.coords and c != std and std not in ds.coords:
                rename[c] = std
                break
    return ds.rename(rename)

def load_wave_reanalysis(year, found_files):
    """Load Hs and T0 from local storage or stream via CopernicusMarine."""
    local = [(k, m) for k, m in found_files.items()
             if year in file_years(m) and first_var(m, config.HS_CANDIDATES)]
    local.sort(key=lambda km: first_var(km[1], config.T0_CANDIDATES) is None)

    ds, hs_var, t0_var = None, None, None
    for key, meta in local:
        try:
            ds = open_found(meta)
            hs_var = first_var(meta, config.HS_CANDIDATES)
            t0_var = first_var(meta, config.T0_CANDIDATES) or first_var(meta, config.T0_FALLBACKS)
            print(f"[wave] {year}: {key} (Hs={hs_var}, T0={t0_var})")
            break
        except Exception as exc:
            print(f"[wave] {year}: Could not open {key}: {exc}")
            ds = None

    if ds is None:
        if config.CMEMS_USER == "YOUR_USERNAME":
            print(f"[wave] {year}: No local file and no CMEMS credentials — skipping year.")
            return None
        print(f"[wave] {year}: Streaming {config.WAVE_DATASET_ID} from CMEMS...")
        try:
            import copernicusmarine as cm
            ds = cm.open_dataset(
                dataset_id=config.WAVE_DATASET_ID,
                variables=["VHM0", "VTPK"],
                minimum_longitude=float(config.ROUTE_LONS.min()) - 2,
                maximum_longitude=float(config.ROUTE_LONS.max()) + 2,
                minimum_latitude=float(config.ROUTE_LATS.min()) - 2,
                maximum_latitude=float(config.ROUTE_LATS.max()) + 2,
                start_datetime=f"{year}-01-01T00:00:00",
                end_datetime=f"{year}-12-31T21:00:00",
                username=config.CMEMS_USER,
                password=config.CMEMS_PASS,
            )
            hs_var, t0_var = "VHM0", "VTPK"
        except Exception as exc:
            print(f"[wave] {year}: CMEMS download failed ({exc}) — skipping year.")
            return None

    ds = _standardise(ds)
    out = ds[[hs_var]].rename({hs_var: "Hs"})
    out["T0"] = ds[t0_var] if t0_var else xr.full_like(ds[hs_var], np.nan)
    out = out.sel(time=str(year))
    
    if out.sizes.get("time", 0) == 0:
        print(f"[wave] {year}: File contains no time steps in {year} — skipping.")
        return None
    return out

def interpolate_along_route(ds, var_names=("Hs", "T0")):
    """Bilinearly interpolate dataset variables onto route waypoints."""
    present = [v for v in var_names if v in ds.data_vars]
    pts = dict(
        longitude=xr.DataArray(np.asarray(config.ROUTE_LONS, float), dims="route_seg_idx"),
        latitude=xr.DataArray(np.asarray(config.ROUTE_LATS, float), dims="route_seg_idx")
    )
    sub = ds[present].load()
    on_route = sub.interp(**pts, method="linear")
    on_route = on_route.fillna(sub.sel(**pts, method="nearest"))
    on_route = on_route.drop_vars(["longitude", "latitude"], errors="ignore")

    # Land boundary fix (nearest ocean cell fallback)
    for v in present:
        da = sub[v]
        empty = np.flatnonzero(on_route[v].isnull().all("time").values)
        if not len(empty):
            continue
        ocean = da.notnull().any("time")
        glat, glon = xr.broadcast(da["latitude"], da["longitude"])
        olat, olon = glat.values[ocean.values], glon.values[ocean.values]
        for j in empty:
            lon_j, lat_j = float(config.ROUTE_LONS[j]), float(config.ROUTE_LATS[j])
            k = np.argmin((olat - lat_j) ** 2 + ((olon - lon_j) * np.cos(np.radians(lat_j))) ** 2)
            series = da.sel(latitude=olat[k], longitude=olon[k])
            on_route[v].loc[dict(route_seg_idx=j)] = series.values

    df = on_route.to_dataframe().reset_index()
    for v in var_names:
        if v not in df.columns:
            df[v] = np.nan
    df["lon"] = np.asarray(config.ROUTE_LONS, float)[df["route_seg_idx"]]
    df["lat"] = np.asarray(config.ROUTE_LATS, float)[df["route_seg_idx"]]
    return df[["time", "route_seg_idx", "lon", "lat", *var_names]]

def load_wind_speed(year, found_files):
    """Load ERA5 u10/v10 wind speed and interpolate along route."""
    u_var, v_var = config.WIND_U_V
    files = [(k, m) for k, m in found_files.items()
             if year in file_years(m) and u_var in m["vars"] and v_var in m["vars"]]
    if not files:
        return None

    parts = []
    for key, meta in sorted(files, key=lambda km: km[1]["time_range"][0]):
        try:
            ds = _standardise(open_found(meta))
            ds = ds.sel(time=str(year))
            ds = ds.isel(time=np.flatnonzero(ds["time"].dt.hour.values % 3 == 0))
            u, v = ds[u_var], ds[v_var]
            if "number" in u.dims:
                u, v = u.isel(number=0), v.isel(number=0)
            wind = xr.Dataset({"U10": np.sqrt(u**2 + v**2)})
            parts.append(interpolate_along_route(wind, var_names=["U10"]))
            ds.close()
        except Exception as exc:
            print(f"[wind] {year}: Failed on {key}: {exc}")

    if not parts:
        return None
    wind_df = pd.concat(parts, ignore_index=True).drop_duplicates(["time", "route_seg_idx"])
    return wind_df[["time", "route_seg_idx", "U10"]]

def attach_wind(route_df, wind_df):
    """Attach U10_era5 wind speeds to the main route dataframe."""
    if wind_df is None:
        out = route_df.copy()
        out["U10_era5"] = np.nan
        return out
    out = route_df.merge(wind_df, on=["time", "route_seg_idx"], how="left")
    return out.rename(columns={"U10": "U10_era5"})