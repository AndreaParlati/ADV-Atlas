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

Local data currently available: wave reanalysis, L3 altimetry and Phase 2 catalogues for **2010–2020**,
Sentinel-1 catalogue for **2010–2020 and 2022**. The results in §4 come from the 2010–2020 run.

> **Sentinel-1 coverage by year** (from the cache): no Level-2 OCN products over the corridor in
> **2010–2014**, sparse in **2015–2016**, full from **2017**. Sentinel-1B flew from 2016 to Dec 2021, so
> **2017–2020 are two-SAR-satellite years** and 2022 is a one-satellite year (S1A only).
> In 2010–2014, `P_SAR_ONLY` is 0 by construction, not because SAR missed the events.


### Settings (Cell 1, `CONFIG` block)

| Variable | Default | Meaning |
|---|---|---|
| `YEAR_START`, `YEAR_END` | `2010, 2020` | Years to analyse (all local data) |
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
- **Remove or fix the cell right after §3.1** (`hazard_catalogue = pd.read_parquet("C:\\Users\\...\\hazard_catalogue_2012.parquet")`).
  It is a leftover inspection cell with an absolute path: it breaks on any other computer. Nothing else uses it.
- A full 2010–2020 run (444k events) takes several minutes for the SAR and altimeter loops; later runs reuse the checkpoints.
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
> The 2010–2020 results in §4 use the **Phase 2** catalogue for every year. Each storm is counted once per
> waypoint and 3-h step, so probabilities are *time-weighted* ("share of hazardous waypoint-hours observed")
> rather than *event-weighted* ("share of storms observed"). Phase 2's `lon_bin` is ignored: Phase 3
> recomputes its own bands from `LON_EDGES`.

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

## 4. Results (2010–2020, Phase 2 catalogue, 444,229 events)

Each "event" is one route waypoint × one 3-hour step with Hs > 3.5 m (§3.1 box), so every P below is the
**share of hazardous waypoint-hours that a satellite observed** within ± 3 h and 200 km. Half of all events
(50 %) fall in December–February, so the results describe winter conditions above all.
Numbers marked *(derived)* were computed from `data/coincidence_merged.parquet`; the rest are printed by the notebook.

### Coverage year by year *(derived)*

| Year | N events | P(SAR) | P(altimeter) | P(either) |
|---|---|---|---|---|
| 2010 | 40,763 | 0.000 | 0.297 | 0.297 |
| 2011 | 35,942 | 0.000 | 0.343 | 0.343 |
| 2012 | 33,221 | 0.000 | 0.229 | 0.229 |
| 2013 | 45,395 | 0.000 | 0.218 | 0.218 |
| 2014 | 40,436 | 0.000 | 0.246 | 0.246 |
| 2015 | 38,678 | 0.013 | 0.262 | 0.272 |
| 2016 | 41,255 | 0.059 | 0.310 | 0.345 |
| 2017 | 37,720 | 0.144 | 0.385 | 0.475 |
| 2018 | 48,492 | 0.240 | 0.401 | 0.530 |
| 2019 | 39,764 | 0.235 | 0.382 | 0.537 |
| 2020 | 42,563 | 0.237 | 0.373 | 0.518 |

**How to read it:** before 2015 there is no Sentinel-1 product over the corridor, so P(SAR) = 0 is the absence
of the mission, not a miss. SAR coverage ramps up in 2015–2016 and is stable at ≈ 0.24 from 2018 (two satellites,
S1A + S1B). Altimeter coverage varies between 0.22 and 0.40 with the number of missions flying.
**Probability of being observed rose from about 1 in 4 (2012–2014) to about 1 in 2 (2018–2020).**
Because of this jump, the 2010–2020 averages below mix two very different periods; the **2017–2020** column is the
best picture of today's satellite system.

### H1 — Is a single mission enough? → **Supported**

| Source | P, 2010–2020 | P, 2017–2020 *(derived)* |
|---|---|---|
| One SAR mode (EW / IW / WV) | 0.020 / 0.033 / 0.039 | — |
| One altimeter mission | 0.019 (Jason-1) to 0.081 (CryoSat-2) | — |
| **Sentinel-1, all modes** | **0.089** | **0.216** |
| **All altimeters** | **0.315** | **0.386** |
| **SAR or altimeter** | **0.368** | **0.516** |
| *2022 test run, for comparison (S1A only, merged-storm catalogue)* | *SAR 0.112, alt 0.435, either 0.501* | |

Over the whole period each single SAR mode or altimeter catches at most 8 % of hazardous waypoint-hours, while the
full set catches 37 % (52 % since 2017): combining missions multiplies coverage by roughly 5–20. Sentinel-1A and 1B
contribute about equally (21,384 and 18,010 events with a coincident footprint). Eight altimeter missions appear
over the decade (CryoSat-2, Envisat, Jason-1/2/3, SARAL, Sentinel-3A/B); none of them covers more than 8 % alone.

### H2 — Is coverage higher near the Grand Banks? → **Not supported**

| Segment | P(either), 2010–2020 | N | P(either), 2017–2020 *(derived)* | N |
|---|---|---|---|---|
| Grand Banks (45–55°W) | 0.385 | 92,530 | 0.527 | 35,589 |
| Mid-Atlantic (20–40°W) | 0.371 | 196,685 | 0.522 | 73,830 |
| Corridor average | 0.368 | 444,229 | 0.516 | 168,539 |

Per 5° band (`data/coincidence_by_lon_bin.csv`), P(either) rises **steadily from Lisbon to Halifax**: 0.30 at
9–14°W, 0.36–0.38 in the mid-Atlantic, 0.40 at 54–64°W. The trend comes from the altimeters (P_alt 0.23 → 0.35), while SAR stays at
0.07–0.11 in every band. It is consistent with altimeter ground tracks lying closer together at higher latitude, as
the route climbs from 38.7°N to 44.7°N. It is a smooth east-west trend, not a Grand Banks peak: the two Grand Banks bands (0.377 and 0.393) sit right on the trend, and in 2017–2020 the Grand Banks and
the mid-Atlantic differ by only 0.005. The lower values at the Lisbon end are robust (26,000+ events per band).

### H3 — Does the model underestimate peak Hs? → **Weakly supported**

| Metric | All matched events | Hs > 6 m events *(derived)* |
|---|---|---|
| Events with an altimeter match | 139,817 | 16,890 |
| Mean ΔHs (altimeter − model at event) | **+0.077 m** | **+0.134 m** |
| Median ΔHs | +0.067 m | +0.108 m |
| % events where the altimeter is higher | 56.5 % | 58.0 % |
| Mean ΔHs, model at the altimeter's place and time | +0.094 m | +0.181 m |
| R² / RMS difference (model vs altimeter) *(derived)* | 0.81 / 0.56 m | |

All indicators point the same way: the altimeters see slightly higher waves than the model, and the gap roughly
doubles in severe seas (Hs > 6 m), the cases that matter most for ships. The collocated control agrees in sign.
But the bias (8–18 cm) is small next to the scatter (0.56 m RMS), and it **depends strongly on the mission**: mean ΔHs
is +0.18 to +0.28 m for Jason-1/2 and SARAL, and −0.13 to −0.14 m for Sentinel-3A/B *(derived)*. Part of the
"model underestimation" is therefore a calibration difference between altimeters, not only a model error (§5).
The result also changed sign from the 2022 test (−0.003 m), which used a different catalogue and only five missions.
Median distance from event to altimeter sample: 93 km, median time offset: 1.5 h.

### ADV atlas

| Band | P(either) | Mean ΔHs [m] | ADV [m] |
|---|---|---|---|
| 9–14°W (Lisbon end) | 0.295 | +0.09 | 0.027 |
| 14–19°W | 0.312 | +0.11 | 0.034 |
| 19–44°W (5 bands) | 0.356–0.380 | +0.07 to +0.09 | 0.026–0.034 |
| 44–49°W (Grand Banks) | 0.377 | +0.05 | 0.020 |
| 49–54°W (Grand Banks) | 0.393 | +0.09 | 0.034 |
| 54–64°W (2 bands) | 0.400 | +0.07 | 0.028–0.029 |

ADV is flat along the whole corridor (0.020–0.034 m): no segment stands out where a satellite would bring
clearly more information. The Lisbon artefact of the 2022 test (0.23 m) is gone, because the Phase 2 catalogue has no
calm-sea events. Every band has a positive ΔHs, so ADV here is driven by the H3 bias.

### In one sentence
A hazardous sea state on this route had about a 1-in-3 chance of being seen by a satellite over 2010–2020, rising to
about 1-in-2 once both Sentinel-1 satellites were flying. Coverage is nearly uniform along the route, and where
altimeters did look, they found waves slightly (≈ 8 cm, ≈ 13 cm in severe seas) higher than the model.

---

## 5. Known limitations and caveats

- **Events are not independent.** One row per waypoint × 3-h step means a single storm contributes hundreds of
  rows. P values are shares of hazardous time, and the large N overstates statistical confidence; merge rows into
  storms before running significance tests.
- **Event definition.** Results from the Phase 2 catalogue (per 3-h step, used in §4) and the inline catalogue
  (per storm, used in the 2022 test) are not directly comparable; see §3.1.
- **Calm-sea events (inline catalogue only).** The "Hs > 2 × 30-day mean" rule fires when a calm sea rises from
  e.g. 0.15 to 0.35 m. It inflated the Lisbon ADV in the 2022 test; the Phase 2 catalogue used in §4 does not have it.
- **No SAR before 2015.** 2010–2014 have no Sentinel-1 OCN products, 2015–2016 very few. The 2010–2020 averages
  mix pre-SAR and SAR years; use the 2017–2020 figures for today's coverage.
- **Mission-to-mission calibration.** ΔHs ranges from about −0.14 m (Sentinel-3A/B) to +0.28 m (SARAL), so the
  pooled H3 bias depends on which missions were flying. A fair H3 test needs inter-calibrated altimeter Hs (or a
  per-mission analysis).
- **Hazard flag is an Hs stand-in**, not the ship-response flag from Phase 1 (heave + roll RAO + Hmax/Hs).
- **"Coincidence" differs by sensor:** an altimeter measures a ~7 km line under the satellite, Sentinel-1
  IW/EW image 250–400 km swaths, WV takes 20 × 20 km snapshots every 100 km. The SAR circle uses 1° ≈ 111 km,
  approximate at 40–45°N (the altimeter search uses true geodesic distance).
- **Failed catalogue days count as "no coincidence"**; the SAR cell warns how many events are affected.

## 6. Next steps
1. Remove the hard-coded-path cell after §3.1.
2. Add per-year and per-mission tables to the notebook itself (the *(derived)* numbers in §4), so they are
   regenerated on every run.
3. Merge Phase 2 rows into storm events and repeat H1–H3 per storm, with confidence intervals.
4. Test H3 per altimeter mission (or with inter-calibrated Hs) and by Hs class.
5. Replace the Hs stand-in with the full `ship_physics.py` hazard flag once Phase 1 RAOs are ready.
6. Use Sentinel-1 OCN wave products (`sentinel1_l2_*`) to compare Hs_max for case studies.
7. Pass the confirmed coincidences to the Phase 4 re-routing simulation.
