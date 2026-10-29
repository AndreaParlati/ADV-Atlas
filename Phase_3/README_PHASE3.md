# Phase 3 — Satellite Space-Time Coincidence Analysis

Notebook: [`phase3_coincidence.ipynb`](phase3_coincidence.ipynb)


**Question:** when a hazardous sea state occurred along the Lisbon–Halifax corridor, was a
satellite looking at it? And when an altimeter was, did the CMEMS wave model get the wave height right?

| | Hypothesis | Tested in |
|---|---|---|
| **H1** | One SAR mission rarely catches a hazard event; the full set of satellites (SAR + altimeters) catches many more. | §3.4 |
| **H2** | Coverage is uneven along the route: higher near the Grand Banks (45–55°W) than in the mid-Atlantic (20–40°W). | §3.4 |
| **H3** | The CMEMS model underestimates peak significant wave height (Hs) at events a satellite observed. | §3.5 |

---

## 1. Where Phase 3 sits in the pipeline

```
download_data.ipynb ──► Wave_Reanalysis/, L3_altimetry/, data/s1_items_cache.json
phase2_hazard_timeline.ipynb ──► data/hazard_catalogue_{YEAR}.parquet
                                        │
                         phase3_coincidence.ipynb
                                        │
        data/*_coincidence_*.parquet, data/*.csv, figures/h2_*, h3_*, adv_*
```

Phase 3 **prefers local files** and only goes online for what is missing:

| Data | Local file read first | If missing |
|---|---|---|
| Hazard catalogue | `data/hazard_catalogue_{YEAR}.parquet` (Phase 2) | Built inline from the wave reanalysis (§3.1) and saved |
| Wave reanalysis (Hs `VHM0`, period `VTPK`) | `Wave_Reanalysis/cmems_mod_glo_wav_my_0.2deg_PT3H-i*_{YEAR}-01-01-{YEAR}-12-31.nc` | Streamed with `copernicusmarine` |
| Altimeter L3 Hs (1 Hz, multi-mission) | `L3_altimetry/swh_L3_alt_{YEAR}.csv` | Streamed with `copernicusmarine` (`cmems_obs-wave_glo_phy-swh_my_multi-l3_PT1S`) |
| Sentinel-1 acquisitions (time, mode, footprint — no images) | `data/s1_items_cache.json` | Missing days are requested from the CDSE STAC catalogue and added to the cache |
| SAR / altimeter results from an earlier run | `data/sar_coincidence_raw.parquet`, `data/altimeter_coincidence_raw.parquet` | Recomputed |

Local data currently available: wave reanalysis and L3 altimetry for **2010–2020**, Sentinel-1
catalogue for **2010–2020 and 2022**. The 2022 wave and altimeter files used for the test run below
are no longer in the folders, so re-running 2022 would stream them.

> **Sentinel-1 coverage by year** (from the cache): no Level-2 OCN products over the corridor in
> **2010–2014**, sparse in **2015–2016**, full from **2017**. Sentinel-1B flew from 2016 to Dec 2021, so
> **2017–2020 are two-SAR-satellite years** and 2022 is a one-satellite year (S1A only).
> In 2010–2014, `P_SAR_ONLY` is 0 by construction, not because SAR missed the events.


### Settings (Cell 1, `CONFIG` block)

| Variable | Default | Meaning |
|---|---|---|
| `YEAR_START`, `YEAR_END` | `2022, 2022` | Years to analyse. Set to `2010, 2020` to use the local data |
| `ROUTE_LONS`, `ROUTE_LATS` | 60 points Lisbon → Halifax | Route nodes (used only when the catalogue is built inline) |
| `DELTA_T_HOURS` | `3.0` | ± time window for a coincidence [h] |
| `DELTA_X_KM` | `200.0` | Distance radius for a coincidence [km] |
| `SAR_COLLECTIONS` | `sentinel-1-ocn`, `sentinel-1-ocn-wv` | Sentinel-1 collections counted as SAR coverage |
| `HEAVE_THRESH_M` | `3.5` | Inline catalogue only: Hs above this is hazardous |
| `ABNORMALITY_IDX`, `ABNORMALITY_WINDOW_STEPS` | `2.0`, `240` | Inline catalogue only: Hs above 2 × its 30-day mean is hazardous |
| `GRAND_BANKS_LON`, `MID_ATLANTIC_LON` | `(-55,-45)`, `(-40,-20)` | Segments compared in H2 |
| `LON_EDGES` | `-64, -59, …, -9` | 5° bands used for H2 and the ADV atlas |
| `REUSE_CHECKPOINTS` | `True` | Reuse `data/*_coincidence_raw.parquet` when they contain every event |
| `INSTALL_DEPS` (dependency cell) | `True` | pip-installs the requirements; set to `False` once the environment is ready |

The thresholds are cross-checked against `ship_physics/ship_physics.py`; a warning is printed if they differ.

> ⚠️ **Changed a setting or the years? Delete the old results first.** Checkpoints are reused whenever they
> contain every event ID, and the notebook does not check which settings produced them.
> - Changed `DELTA_T_HOURS`, `DELTA_X_KM` or `SAR_COLLECTIONS`, or re-ran Phase 2 → delete
>   `data/sar_coincidence_raw.parquet` and `data/altimeter_coincidence_raw.parquet`.
> - Want the inline catalogue instead of Phase 2's → delete `data/hazard_catalogue_{YEAR}.parquet`.
> - `data/s1_items_cache.json` is input, not a result: keep it. It covers the route padded by 200 km;
>   if you raise `DELTA_X_KM` above that, delete it so it is downloaded again with a larger box.

### How to run
- Run `download_data.ipynb` and `phase2_hazard_timeline.ipynb` for the same years first.
- **Remove or fix the cell right after §3.1** (`hazard_catalogue = pd.read_parquet("C:\\Users\\...\\hazard_catalogue_2022.parquet")`).
  It is a leftover inspection cell with an absolute path: it breaks on any other computer and fails
  if the 2022 file is gone. Nothing else uses it.
- In VS Code / Jupyter: select the `.venv` kernel and *Run All*.
- From the terminal:
  ```bash
  .venv/Scripts/python -m nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 \
      phase3_coincidence.ipynb --output phase3_coincidence_executed.ipynb
  ```
- Quick check with no data or network (defines every function, skips all data access):
  ```bash
  .venv/Scripts/python -m nbconvert --to script phase3_coincidence.ipynb
  .venv/Scripts/python phase3_coincidence.py --dry-run
  ```

---

## 3. Section by section

### 3.1 Hazard event catalogue
**Does:** loads the list of hazardous events to test.
1. If `data/hazard_catalogue_{YEAR}.parquet` exists (Phase 2), it is loaded as is.
2. Otherwise it is built inline: Hs is interpolated onto the 60 route nodes every 3 h; a step is
   hazardous if `Hs > 3.5 m` (*heave proxy*) **or** `Hs > 2 × 30-day running mean` (*abnormality*);
   consecutive hazardous steps at one node are **merged into one event** placed at its peak Hs.

**Input:** Phase 2 parquet, or the wave reanalysis.

**Output:** `catalogue` table (saved to `data/hazard_catalogue_{YEAR}.parquet` when built inline).
Columns used downstream: `event_id, datetime, lon, lat, Hs_cmems, flag_reason`. The printout shows the
event count and how many were triggered by each rule (`flag_reason`).

> **Phase 2 vs inline catalogue — not the same "event".**
> | | Phase 2 (`phase2_hazard_timeline.ipynb`) | Inline (Phase 3) |
> |---|---|---|
> | One row is | one route node × one 3-h step with Hs > 3.5 m | one storm episode at one node (merged steps) |
> | Rules | `Hs > 3.5 m` (heave), `Hs > 6 m` (rogue proxy) | `Hs > 3.5 m` or `Hs > 2 × 30-day mean` |
> | Size (order of) | ~40,000 rows per year | ~3,000 events per year |
> | Extra columns | `U10_era5`, `flag_heave`, `flag_rogue`, `lon_bin` | `route_node`, `n_steps`, `event_start`, `event_end` |
>
> With the Phase 2 file, Phase 3 runs ~13× longer and each storm is counted many times, so
> probabilities become *time-weighted* ("share of hazardous hours observed") rather than
> *event-weighted* ("share of storms observed"). Both are valid, but state which one you report.
> Phase 2's `lon_bin` is ignored: Phase 3 recomputes its own bands from `LON_EDGES`.

### 3.2 Sentinel-1 SAR coincidence
**Does:** for each event, finds Sentinel-1 Level-2 OCN products (IW/EW wide swaths and WV
vignettes) acquired within **event time ± 3 h** whose footprint intersects a **200 km circle** around the event.

**Input:** `catalogue`, `data/s1_items_cache.json`. Days not in the cache are fetched from CDSE STAC
once for the whole corridor and saved to the cache (fetching per event triggers HTTP 429 rate limits).

**Output:** `data/sar_coincidence_raw.parquet`, one row per (event, product in the time window):

| Column | Meaning |
|---|---|
| `event_id` | event tested |
| `sat_id`, `item_id` | satellite (`sentinel-1a`/`1b`) and product name |
| `acq_time`, `dt_hours` | acquisition start, and offset of the acquisition midpoint from the event [h] |
| `sensor_mode`, `orbit_direction` | IW / EW / WV, ascending / descending |
| `footprint_wkt` | product footprint polygon |
| `coincident` | `True` if the footprint touches the 200 km circle |
| `query_ok` | `False` if a catalogue day could not be fetched (the event then counts as *not* coincident) |

Events with no product in the window get one placeholder row with `coincident = False`. The printout
reports products in window, coincident footprints, events with ≥ 1 coincidence, and failed queries.

### 3.3 Altimeter coincidence
**Does:** for each event, searches 1 Hz altimeter samples within ± 3 h and 200 km (geodesic distance)
and keeps the **closest** one. `Hs_altimeter` is the median of that satellite's samples within ± 5 s
(≈ 70 km along track), to smooth 1 Hz noise. The model is then sampled at the altimeter's exact
position and time for a clean comparison.

**Input:** `catalogue`, `L3_altimetry/swh_L3_alt_{YEAR}.csv` (rows with `variable == "swh"`),
wave reanalysis (for `Hs_cmems_at_alt`).

**Output:** `data/altimeter_coincidence_raw.parquet`, one row per event (NaN columns = no match):

| Column | Meaning |
|---|---|
| `Hs_altimeter` | observed Hs [m] |
| `Hs_cmems_at_event` | model Hs at the event (the event's peak) [m] |
| `Hs_cmems_at_alt` | model Hs at the altimeter sample's place and time [m] |
| `dist_km`, `dt_hours` | distance and time offset of the matched sample from the event |
| `alt_platform` | mission of the closest sample |
| `platforms_in_window` | every mission with a sample inside the window (used for the H1 breakdown) |
| `alt_time`, `alt_lon`, `alt_lat` | where and when the matched sample is |

### 3.4 Coincidence statistics — H1 and H2
**Does:** merges catalogue + SAR + altimeter results per event and computes
**P = events with a coincidence / all events**.

**Input:** outputs of §3.1–3.3.

**Output:**
- `h1_table` — P for SAR alone, altimeters alone, SAR *or* altimeter (`P_SAR_ONLY`, `P_ALT_ONLY`, `P_SAR_OR_ALT`).
- `h1_breakdown` — P for each SAR mode and each altimeter mission on its own.
- `data/coincidence_by_lon_bin.csv` — per 5° band, Lisbon → Halifax: `lon_bin_center, P_SAR, P_alt, P_combined, N_events`.
- `P_GRAND_BANKS`, `P_MID_ATLANTIC` — P(either) in the two H2 segments.
- `data/coincidence_merged.parquet` — one row per event with every flag (`sar_coincident`, `alt_coincident`, `any_coincident`) and the altimeter match.
- `figures/h2_coincidence_by_segment.png` — bar per band (orange = Grand Banks bands, dashed line = corridor mean, `n=` events per band).

**How to read it:**
- **H1 is supported** when each single source (one SAR mode, one altimeter) sits well below `P_SAR_OR_ALT`.
  The gap is the gain from combining missions.
- **H2 is supported** when `P_GRAND_BANKS` is clearly above `P_MID_ATLANTIC` and the orange bars stand above
  the dashed line. Ignore bands with small `n`: one or two events change their P by a lot.
- P is a share between 0 and 1: 0.5 means half of the hazardous events had at least one satellite observation in the window.

### 3.5 Forecast bias — H3
**Does:** for every altimeter-coincident event, ΔHs = `Hs_altimeter − Hs_cmems_at_event`.

**Input:** `altimeter_coincidence_raw.parquet`.

**Output:** printed `MEAN_BIAS_M`, `MEDIAN_BIAS_M`, `PCT_ALT_ABOVE` (% events where the altimeter is higher),
`MEAN_BIAS_COLOC_M` (same, but model sampled at the altimeter: the cleaner control), and
`figures/h3_forecast_bias.png`:
- *left:* model vs altimeter scatter. Points above the y = x line mean the altimeter saw higher waves than the model. R² shows how well they agree.
- *right:* histogram of ΔHs. Orange line = mean, dotted line = 0.

**How to read it:** **H3 is supported** if the mean/median ΔHs is clearly positive, `PCT_ALT_ABOVE` > 50 %, and
`MEAN_BIAS_COLOC_M` agrees in sign. Built-in bias: events are chosen *because* the model shows high Hs, and the
altimeter can be 200 km / 3 h away from that peak, so the event-based ΔHs leans **negative**. When the two
numbers disagree, trust `MEAN_BIAS_COLOC_M` more.

### 3.6 Preliminary Added Detection Value (ADV) atlas
**Does:** per 5° band, **ADV = P_combined × |mean ΔHs in the band|**, in metres. High where a satellite is both
likely to be overhead *and* likely to show something the model missed. Bands with no altimeter match get ΔHs = 0.

**Input:** `merged` and `by_bin` from §3.4–3.5.

**Output:** `data/adv_by_lon_bin.csv` (`lon_bin_center, P_combined, mean_delta_Hs, ADV, N_events`),
`figures/adv_atlas_preliminary.png` (ADV line on top, event count per band below, Grand Banks shaded),
a markdown table, and a **Recap** of every headline number.

**How to read it:** the ADV value is the "expected correction a satellite would bring" per event in that band.
Compare bands, not absolute values, and always look at `N_events` and the sign of `mean_delta_Hs` next to it.
ADV uses |ΔHs|, so a band where the model over-predicts scores as high as one where it under-predicts.

---

## 4. Results (2022 test run, inline catalogue, 3,037 events)

These are the latest executed results. They come from the **inline** catalogue (§3.1, merged events) and
one Sentinel-1 satellite. A 2010–2020 run with the Phase 2 catalogue will give different numbers (see §3.1 box).

### H1 — Is a single mission enough? → **Supported**

| Source | P(coincidence) |
|---|---|
| One SAR mode (EW / WV / IW) | 0.025 / 0.031 / 0.064 |
| One altimeter mission | 0.074 (Jason-3) to 0.124 (Sentinel-3B) |
| **Sentinel-1, all modes** | **0.112** |
| **All altimeters** | **0.435** |
| **SAR or altimeter** | **0.501** |

With one satellite, a hazard event is observed about 1 time in 10. With every mission combined, about half
the time. All 2022 SAR coverage is Sentinel-1A. Altimeters contribute most of the coverage because there are
five of them (CryoSat-2, Jason-3, SARAL, Sentinel-3A/B), even though each only sees a thin line.

### H2 — Is coverage higher near the Grand Banks? → **Not supported in 2022**

| Segment | P(either) | N events |
|---|---|---|
| Grand Banks (45–55°W) | 0.526 | 643 |
| Mid-Atlantic (20–40°W) | 0.516 | 1,063 |
| Corridor average | 0.501 | 3,037 |

Coverage is fairly even between 15°W and 64°W (0.47–0.58 per band). The 49–54°W band is highest (0.58) but
44–49°W is below average (0.48), so the Grand Banks as a whole is no different from the mid-Atlantic. The clear
outlier is the **Lisbon end** (9–14°W) at 0.38, partly due to calm-sea events (§5). More years are needed before
calling H2 rejected.

### H3 — Does the model underestimate peak Hs? → **Not supported in 2022**

| Metric | Value |
|---|---|
| Events with an altimeter match | 1,322 |
| Mean ΔHs (altimeter − model at event) | −0.003 m |
| Median ΔHs | −0.048 m |
| % events where the altimeter is higher | 45.6 % |
| Mean ΔHs, model at the altimeter's place and time | +0.093 m |
| R² (model vs altimeter) | 0.85 |

Model and altimeters agree closely, with no systematic underestimation of event peaks. The collocated
comparison shows a small positive bias (+9 cm), a weak hint in the H3 direction, much smaller than the scatter.

### ADV atlas
Highest at the **Lisbon end** (0.23 m), then the **49–54°W Grand Banks band** (0.11 m); mostly below 0.07 m
elsewhere. The Lisbon value is **an artefact, not a finding** (next section).

---

## 5. Known limitations and caveats

- **Calm-sea events (inline catalogue only).** The "Hs > 2 × 30-day mean" rule also fires when a calm sea
  rises from e.g. 0.15 to 0.35 m. These events, mostly near Lisbon, are the cluster at Hs_model ≈ 0.3 m in the
  H3 scatter and inflate the Lisbon ADV. The Phase 2 catalogue does not have this problem (it only uses Hs thresholds).
- **Event definition.** Results from the Phase 2 catalogue (per 3-h step) and the inline catalogue (per storm)
  are not directly comparable; see §3.1.
- **No SAR before 2015.** 2010–2014 have no Sentinel-1 OCN products, 2015–2016 very few. Compare H1 across
  years only from 2017 on, or report SAR-era and pre-SAR years separately.
- **Hazard flag is an Hs stand-in**, not the ship-response flag from Phase 1 (heave + roll RAO + Hmax/Hs).
- **"Coincidence" differs by sensor:** an altimeter measures a ~7 km line under the satellite, Sentinel-1
  IW/EW image 250–400 km swaths, WV takes 20 × 20 km snapshots every 100 km. The SAR circle uses 1° ≈ 111 km,
  approximate at 40–45°N (the altimeter search uses true geodesic distance).
- **Failed catalogue days count as "no coincidence"**; the SAR cell warns how many events are affected.

## 6. Next steps
1. Remove the hard-coded-path cell after §3.1.
2. Decide which event definition to report (per step, or merge Phase 2 rows into storms), then run
   `YEAR_START, YEAR_END = 2010, 2020` after deleting the old `*_coincidence_raw.parquet` checkpoints.
3. Replace the Hs stand-in with the full `ship_physics.py` hazard flag once Phase 1 RAOs are ready.
4. Use Sentinel-1 OCN wave products (`sentinel1_l2_*`) to compare Hs_max for case studies.
5. Pass the confirmed coincidences to the Phase 4 re-routing simulation.
