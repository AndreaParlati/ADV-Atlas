# Phase 2 — Historical Hazard Timeline

Notebook: [`phase2_hazard_timeline.ipynb`](phase2_hazard_timeline.ipynb)

**Question:** when, and where along the Lisbon–Halifax corridor, was the sea state hazardous for a ship?

Phase 2 walks the CMEMS global wave reanalysis along the route every 3 hours, flags the hazardous sea states
and writes one **hazard catalogue per year**. Phase 3 ([`README_PHASE3.md`](README_PHASE3.md)) then checks
whether a satellite observed each of those events.

---

## 1. Where Phase 2 sits in the pipeline

```
download_data.ipynb ──► Wave_Reanalysis/*.nc   (Hs, peak period — required)
                        ERA5/*.nc              (10-m wind — optional)
                                │
                  phase2_hazard_timeline.ipynb   (+ ship_physics/ship_physics.py)
                                │
              data/hazard_catalogue_{YEAR}.parquet,  figures/phase2_diagnostics_{YEAR_START}.png
                                │
                     phase3_coincidence.ipynb
```

| Data | Folder / file | Variables used | Required? |
|---|---|---|---|
| CMEMS wave reanalysis, 0.2°, 3-hourly | `Wave_Reanalysis/cmems_mod_glo_wav_my_0.2deg_PT3H-i_*_{YEAR}-01-01-{YEAR}-12-31.nc` | `VHM0` (Hs), `VTPK` (peak period) | **Yes**; streamed from CMEMS if missing |
| ERA5 single levels, 0.25°, hourly | `ERA5/era5_single_levels_{YEAR}_{MM}.nc` (one per month) | `u10`, `v10` | No; `U10_era5` is NaN where missing |
| Ship physics thresholds | `ship_physics/ship_physics.py` | `HEAVE_THRESHOLD_SIG_M` etc. | No; only printed as a cross-check |

The notebook also scans `data/`, `Physics_Reanalysis/` and `L4_altimetry/` and lists what it finds, but does not
use them. The ERA5 `.nc` files are really zip archives (from the Climate Data Store), each holding one NetCDF per data
stream; the notebook reads them in place without extracting.

**Local data available now:** wave reanalysis **2010–2020** (all years); ERA5 **January 2010 – March 2012** only.

---

## 2. What you need to provide

### Credentials (only if a wave file must be streamed)
`CMEMS_USERNAME` / `CMEMS_PASSWORD` as environment variables, or in the project `.env` file (loaded automatically).
Without them, a year with no local wave file is skipped with a message.

### Settings (Cell 1, `CONFIG` block)

| Variable | Default | Meaning |
|---|---|---|
| `YEAR_START`, `YEAR_END` | `2010, 2020` | Years to process; one parquet per year |
| `N_ROUTE_PTS`, `ROUTE_LONS`, `ROUTE_LATS` | 60 points, Lisbon (−9.1°E, 38.7°N) → Halifax (−63.6°E, 44.7°N) | Waypoints where the sea state is evaluated (straight line in lon/lat, ~78 km apart) |
| `HEAVE_THRESH_M` | `3.5` | Hs above this → `flag_heave` |
| `ROGUE_HS_PROXY` | `6.0` | Hs above this → `flag_rogue` |
| `LON_BIN_EDGES` | `-65, -60, …, -5` | 5° longitude bins for the `lon_bin` column |
| `HS_CANDIDATES`, `T0_CANDIDATES`, `T0_FALLBACKS`, `WIND_U_V` | `VHM0…`, `VTPK…`, `VTM10/mwp`, `u10/v10` | Variable names searched in the files, first match wins |
| `WAVE_DATASET_ID` | `cmems_mod_glo_wav_my_0.2deg_PT3H-i` | Dataset streamed when a wave file is missing |

### How to run
- Select the `.venv` kernel and *Run All*. About 25 s per year with local files.
- The first cell pip-installs the dependencies (`copernicusmarine xarray netCDF4 h5netcdf numpy pandas scipy
  matplotlib tqdm pyarrow fastparquet python-dotenv`) into the running kernel; skip it once the environment is ready.
- Each year runs in its own `try/except`: a missing file or failed download skips that year and the rest continue.
- Re-running **overwrites** `data/hazard_catalogue_{YEAR}.parquet` for every year processed.

---

## 3. Section by section

### 2.1 Inspect downloaded data
**Does:** lists every file in the search folders, opens every `.nc` (metadata only) and records its variables,
dimensions and time range in `FOUND_FILES`. A second cell prints, per year, how many wave and ERA5 wind files exist
and warns where ERA5 is incomplete.

**Input:** the data folders. **Output:** `FOUND_FILES` (dictionary), the printed inventory and the coverage table.
All later cells take variable names from `FOUND_FILES`, never from documentation.

**How to read it:** check that every year shows `wave_files = 1`. `era5_wind_files < 12` means some months will
have no wind.

### 2.2 Load wave reanalysis (Hs, T0)
**Does:** `load_wave_reanalysis(year, …)` opens the local file covering the year (preferring one with a peak
period), or streams it from CMEMS. Returns `Hs` and `T0` on `time × latitude × longitude`.
If there is no peak period, T0 falls back to a mean period (`VTM10`) with a warning, or NaN.

**Input:** `FOUND_FILES`, wave file. **Output:** an xarray Dataset for one year, or `None` (year skipped).

### 2.3 Interpolate onto the route
**Does:** `interpolate_along_route(…)` bilinearly interpolates every time step onto the 60 waypoints. A waypoint whose
interpolation touches land takes the nearest grid cell; a waypoint *on* land takes the nearest **ocean** cell, and this
is printed. This happens at Halifax (waypoint 59), which uses the cell 0.1° south.

**Input:** the Dataset from 2.2. **Output:** a long table `time, route_seg_idx, lon, lat, Hs, T0`
(60 rows per time step, 175,200 rows per year).

### 2.4 Wind speed (ERA5)
**Does:** `load_wind_speed(…)` reads every monthly ERA5 file of the year, keeps the 3-hourly steps that match the wave
data, computes |U10| = √(u10² + v10²) and interpolates it onto the route. `attach_wind(…)` joins it as `U10_era5`.

**Input:** ERA5 files. **Output:** the route table with `U10_era5`.
**Fallback:** the CMEMS wave files contain no wind *speed* (`VHM0_WW` is wind-sea height), so nothing is substituted:
months without ERA5 are NaN.

### 2.5 Apply hazard flags
**Does:** `apply_hazard_flags(…)` adds
- `flag_heave = Hs > 3.5 m`, a stand-in for the significant-heave limit of the base paper (Kytariolou & Themelis 2022, Sec. 4.6);
- `flag_rogue = Hs > 6 m`, a stand-in for rogue-wave likelihood, used because the reanalysis cannot give individual
  wave heights for the paper's H_max/H_s > 2 test;
- `flag_any = flag_heave OR flag_rogue`.

A NaN Hs never raises a flag. Since 6 m > 3.5 m, every `flag_rogue` row is also a `flag_heave` row.

### 2.6 Build the catalogue and save
**Does:** for each year, runs 2.2 → 2.5, keeps the rows with `flag_any`, adds `event_id` and `lon_bin`, and saves.
`ROUTE_BY_YEAR` keeps the full (unflagged) route table of each year for the plots; `SUMMARY` holds one line per year.

**Output:** `data/hazard_catalogue_{YEAR}.parquet`. **This schema is the contract with Phase 3; do not rename columns.**

| Column | Type | Meaning |
|---|---|---|
| `event_id` | str | `"{year}_{i:05d}"`, unique within the year, ordered by time then waypoint |
| `datetime` | timestamp, UTC | time of the 3-hourly step |
| `lon`, `lat` | float | waypoint position [°E, °N] |
| `Hs_cmems` | float | significant wave height, CMEMS reanalysis [m] |
| `T0_cmems` | float | peak wave period [s] |
| `U10_era5` | float | 10-m wind speed, ERA5 [m/s]; NaN where ERA5 is missing |
| `flag_heave`, `flag_rogue`, `flag_any` | bool | the flags above (`flag_any` is always True in the file) |
| `route_seg_idx` | int | waypoint index 0 (Lisbon) … 59 (Halifax) |
| `lon_bin` | str | 5° bin `"{west}_{east}"`, e.g. `"-15_-10"` |
| `flag_reason` | str | extra column for Phase 3: `heave_proxy` or `heave_proxy+rogue_proxy` |

> **One row = one waypoint × one 3-hour step**, not one storm. A storm that sits on 10 waypoints for 2 days
> produces 10 × 16 = 160 rows. Count rows as "hazardous waypoint-hours ÷ 3", not as independent storms.

### 2.7 Validation
**Does:** re-reads each saved parquet and checks: all contract columns present, `event_id` unique, lon/lat inside
the corridor, Hs ≥ 0, `datetime` is UTC-aware and inside the year, every row flagged, valid waypoint index and bin
labels. Prints `PASS`/`FAIL` per check (never stops the notebook), the Hs range and the share of rows with wind.

**How to read it:** the last line must say `Validation PASSED`. A `FAIL` names the year and the check.

### 2.8 Diagnostic plots (for `YEAR_START`)
`figures/phase2_diagnostics_{YEAR_START}.png`, four panels:
- **Hs at mid-route** (waypoint 30, ≈ −36.8°E): the full Hs time series with the 3.5 m (red) and 6 m (orange)
  lines. Everything above the red line ends up in the catalogue.
- **Hazard events per month:** the seasonal cycle. Expect a winter peak and a near-empty summer.
- **Hazard event locations:** flagged rows on the route, coloured by Hs. All points lie on the dashed route line
  (the catalogue is built on the waypoints only); colour shows where the strongest seas were.
- **Events per 5° bin:** the input to the per-segment analysis of Phase 3 (H2). Bins hold different numbers of
  waypoints (roughly 5–6 each, fewer at the two ends), so compare them with that in mind.

The final cells print `SUMMARY` and a Summary / Limitations text.

---

## 4. Results (2010 run)

| Metric | Value |
|---|---|
| Route-timestep records | 175,200 (60 waypoints × 2,920 steps) |
| Flagged rows (`flag_any`) | 40,763 (23.3 %) |
| of which `flag_rogue` (Hs > 6 m) | 4,002 |
| Hs range of flagged rows | 3.50 – 11.97 m |
| Rows with ERA5 wind | 100 % (median 11.8 m/s) |

**Seasonality:** December–February have 7,800–8,700 flagged rows each, July only 11. Hazardous seas on this route
are almost entirely a winter (October–March) problem.

**Along the route:** most flagged rows fall between 30°W and 50°W (5,000–5,400 per bin), fewer at the European end
(2,500 in 10–15°W) and very few in the last bin before Halifax (650 in 60–65°W). The 5–10°W bin (Lisbon) has none:
the Lisbon waypoint is near-shore and its Hs stays low.

**Meaning:** about one in four 3-hour slots at a random point of the corridor in 2010 had Hs above 3.5 m, and one
in forty above 6 m. This is an upper bound on "hazardous for the ship", because the real criterion is on the ship's
*response* (Phase 1), which is usually smaller than the sea's Hs.

---

## 5. ⚠️ Current state of `data/` — mixed catalogues

Only **2010** has been produced by this notebook. `hazard_catalogue_2011…2020.parquet` were written by Phase 3,
which builds its own catalogue when the Phase 2 file is missing. These use a **different definition** (merged storm
events, an extra "2 × 30-day mean" rule, about 3,000 rows per year instead of about 40,000) and lack the
`U10_era5`, `flag_heave`, `flag_rogue` and `lon_bin` columns.

A Phase 3 run over 2010–2020 on these files mixes the two definitions, so 2010 dominates the event count and
year-to-year comparisons are not valid. **Fix:** run this notebook for 2010–2020 (it overwrites all eleven files),
then delete `data/sar_coincidence_raw.parquet` and `data/altimeter_coincidence_raw.parquet` and re-run Phase 3.

---

## 6. Limitations

- **Hs stand-in for the ship-response flag.** `ship_physics.is_hazardous_event()` needs heave and roll RAOs from
  Phase 1. Thresholding the sea's Hs flags more situations than the ship-response criterion would.
- **`flag_rogue` is not a rogue-wave detector:** it marks severe seas where rogue waves are more likely, not
  individual waves with H_max/H_s > 2.
- **One straight-line route**, not the shortest route over the globe (great circle) and not an ensemble of routes
  that ships really sail. Storms just off the line are missed.
- **No storm merging:** see the box in §2.6.
- **ERA5 incomplete** after March 2012; `U10_era5` is NaN there.
- **Model data only:** Hs comes from a reanalysis; Phase 3 compares it with altimeters (H3).

## 7. Next steps
1. Run the notebook for 2010–2020 to replace the Phase 3-built catalogues (§5).
2. Optionally merge consecutive flagged steps per waypoint into storm events (keep the contract columns), so Phase 3
   can report "share of storms observed".
3. Finish the ERA5 download for 2012–2020.
4. Replace `flag_heave` / `flag_rogue` with `ship_physics.is_hazardous_event()` once `seakeeping_rao.py` is ready.
5. Add alternative routes (great circle, routes ships really sail) as in the project proposal.
