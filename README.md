# ADV-Atlas

## Satellite Warning Ocean ReRouting (SWORD)

> **Retrospective space-time coincidence and re-routing added value for SAR- and altimeter-detected hazardous sea states along North Atlantic shipping corridors.**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data Source: Copernicus Marine](https://img.shields.io/badge/Data-Copernicus%20Marine-005A9C)](https://marine.copernicus.eu/)
[![Data Source: CDSE](https://img.shields.io/badge/Data-Copernicus%20Data%20Space-002B49)](https://dataspace.copernicus.eu/)

---

## 📌 Executive Summary

Modern ship weather-routing tools optimize fuel consumption against safety constraints (e.g., maximum heave and roll) using deterministic forecast fields (e.g., CMEMS, ECMWF). However, these forecasts operate on grid resolutions ($\approx 3\text{h}$, degree-scale) that underrepresent or completely miss short-lived, sub-grid extreme wave events ("rogue waves").

While satellite Synthetic Aperture Radar (SAR) and multi-mission altimetry directly observe these hazardous sea states independently of numerical models, satellite acquisitions are constrained by orbital geometry and revisit patterns.

**SWORD** asks:
1. **How often** does a satellite pass coincide in space-time with a hazardous sea-state event along a North Atlantic shipping corridor that a forecast underrepresented?
2. **What operational value** (measured as *safety margin recovered* vs. *fuel penalty incurred*) does satellite-informed re-routing add to deterministic routing frameworks?

The primary objective is to compute a parametric **Added Detection Value (ADV)** atlas along the Lisbon–Halifax containership corridor.

---

## 🔬 Scientific & Methodological Framework

### Base Paper Alignment & Disciplinary Reorientation
This project builds upon the empirical routing and seakeeping framework established by **Kytariolou & Themelis (2022)** (*Journal of Navigation*), reorienting its focus toward physical oceanography (sub-grid extreme wave physics) and satellite oceanography (multi-mission sampling geometry).

### Key Hypotheses
* **H1 (Coincidence Scaling):** Space-time coincidence probability between an extreme event and a single SAR mission (Sentinel-1) is low, but increases significantly when integrating the full multi-mission open SAR/altimeter constellation.
* **H2 (Spatial Heterogeneity):** Coincidence probability is spatially non-uniform along the Lisbon–Halifax route, showing higher density near the Grand Banks / Flemish Cap approach compared to the mid-ocean leg ("blind corridor").
* **H3 (Forecast Underestimation Bias):** For coincident events, deterministic CMEMS wave forecasts significantly underestimate peak sea states ($H_s$, $H_{\max}$) compared to along-track altimetry and Sentinel-1 L2 OCN products.
* **H4 (Operational Net Value):** Re-introducing satellite-observed hazards as dynamic spatial avoidance constraints in route optimization recovers safety threshold compliance at a modest fuel cost penalty.

---

## 📊 Data Sources & Access Strategy

All datasets used in this pipeline are open-access and accessible via public APIs:

| Category | Dataset | Platform / Provider | Usage |
| :--- | :--- | :--- | :--- |
| **Wave Hazard Timeline** | `GLOBAL_MULTIYEAR_WAV_001_032` | CMEMS Marine Data Store | Multi-year $H_s$, peak period, wave direction |
| **Ocean Physics** | `GLOBAL_MULTIYEAR_PHY_001_030` | CMEMS Marine Data Store | Currents, sea surface height, temperature |
| **Atmospheric Forcing** | ERA5 Reanalysis | Copernicus Climate Data Store (CDS) | Surface wind fields ($U_{10}, V_{10}$) |
| **Independent $H_s$** | `WAVE_GLO_PHY_SWH_L3_MY_014_005` | CMEMS Marine Data Store | Along-track altimetry observational cross-check |
| **SAR Metadata** | Sentinel-1 IW/EW/WV Catalogue | Copernicus Data Space Ecosystem (CDSE) / ASF | Space-time footprint matching |
| **SAR Wave Spectra** | Sentinel-1 Level-2 OCN (OSW) | Copernicus Data Space Ecosystem | Case-study $H_{\max}$ / directional spectra validation |

---

## 🏗 Pipeline Architecture & Core Phases

```
[Phase 0: Environment & API Setup]
       │
       ▼
[Phase 1: Resistance, Fuel & Safety Model Engine] ───► (Ship Hydrodynamics & Abnormality Flag)
       │
       ▼
[Phase 2: Multi-Year Hazard Timeline Extraction] ───► (Route-Resolved Hazard Catalogue)
       │
       ▼
[Phase 3: Satellite Space-Time Coincidence Engine] ──► (Coincidence Atlas & Forecast Bias)
       │
       ▼
[Phase 4: Retrospective Re-Routing Simulator] ──────► (Fuel Penalty vs. Safety Recovered)
       │
       ▼
[Phase 5: Synthesis & ADV Atlas] ──────────────────► (Final Atlas, Package & Reports)
```

### Phase Details

* **Phase 0 — Environment & API Setup:** Verification of CDSE STAC, CMEMS Toolbox, and CDS APIs. Development environment setup.
* **Phase 1 — Fuel, Safety & Hazard Engine:** Implementation of resistance equations (calm-water, wind, wave) following Kytariolou & Themelis (2022). Seakeeping response curves (heave/roll RAOs) are generated using open strip-theory tools (e.g., SEAWAY / BEM solvers). Hazard criteria combine significant heave ($> 3.5\text{ m}$), significant roll ($> 5^\circ$), and an abnormality index ($H_{\max}/H_s > 2.0$).
* **Phase 2 — Multi-Year Hazard Event Catalogue:** Ingestion of multi-year CMEMS reanalysis data along candidate route ensembles (Lisbon–Halifax) to identify historical safety threshold breaches.
* **Phase 3 — Space-Time Coincidence Analysis:** Query of Sentinel-1 and altimetry orbital passes over cataloged hazard events given spatial-temporal thresholds $(\Delta x, \Delta t)$. Evaluation of satellite-versus-model bias.
* **Phase 4 — Retrospective Re-Routing Simulation:** Optimization re-runs over coincident hazard events with explicit satellite-informed avoidance constraints, measuring safety margin recovery versus fuel consumption penalties.
* **Phase 5 — Synthesis & Added Detection Value (ADV) Atlas:** Creation of route-resolved operational utility maps and packaging of core Python modules.

---

## 🧩 Modular Extensions

The repository features modular extension tracks that plug into the core pipeline:

```
                  ┌── Module A: Iceberg Risk Layer (Grand Banks / IIP Data)
                  ├── Module B: Full Multi-Mission Constellation Scaling
CORE PIPELINE ───┼── Module C: Hydrodynamic Seakeeping (NEMOH BEM + KCS Hull)
                  ├── Module D: Live Satellite Coincidence Dashboard
                  ├── Module E: Fleet Economics & Insurance Loss Framing
                  └── Module F: Multi-Corridor Generalization (Pacific / S. Ocean)
```

| Module | Objective | Target Component | Core Input Data |
| :--- | :--- | :--- | :--- |
| **Module A** | Iceberg hazard integration along Flemish Cap | Phase 1 & 3 | International Ice Patrol (IIP) Ice Charts |
| **Module B** | Multi-satellite constellation scaling curves | Phase 3 | CryoSat-2, SARAL, Sentinel-3/6, HY-2 |
| **Module C** | Hydrodynamic RAO computation with 3D BEM | Phase 1 | NEMOH Solver + KRISO Container Ship (KCS) |
| **Module D** | Real-time interactive demonstrator dashboard | Phase 5 | Live CDSE / CMEMS API Streams |
| **Module E** | Commercial viability & hull insurance framing | Phase 5 | Historical Marine Loss Statistics |
| **Module F** | Cross-basin validation on additional shipping lanes | Phase 2 & 3 | Extended Trans-oceanic Route Profiles |

---

## 💻 Installation & Quickstart

### Prerequisites
* Python 3.10 or higher
* Valid credentials for **Copernicus Marine Service**, **Copernicus Data Space Ecosystem**, and **ECMWF CDS**.

### Setup
```bash
# Clone the repository
git clone https://github.com/username/satellite-ocean-rerouting.git
cd satellite-ocean-rerouting

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration
Create a `.env` file in the root directory:
```env
CMEMS_USERNAME="your_cmems_username"
CMEMS_PASSWORD="your_cmems_password"
CDSE_CLIENT_ID="your_cdse_client_id"
CDSE_CLIENT_SECRET="your_cdse_client_secret"
CDS_API_KEY="your_cds_api_key"
```

---

## 🔬 Limitations & Sensitivity Notes

1. **Hydrodynamic Approximations:** Open strip-theory or parametric RAO estimates are utilized as proxies where proprietary seakeeping engines (e.g., NEWDRIFT+) are inaccessible.
2. **Historical vs. Real-Time Latency:** Archival coincidence analysis evaluates physical/geometrical overlap. Operational implementation depends on low-latency downlinking and real-time processing chains.
3. **Statistical Abnormality Index:** The $H_{\max}/H_s$ ratio serves as a statistical proxy for freak wave likelihood rather than a deterministic single-wave forecast.

---

## 📜 References & Citation

1. **Kytariolou, A., & Themelis, N. (2022).** Ship routing optimisation based on forecasted weather data and considering safety criteria. *Journal of Navigation*, 75(6), 1310–1331.
2. **Rosenthal, W., & Lehner, S. (2008).** Rogue Waves: Results of the MaxWave Project. *Journal of Offshore Mechanics and Arctic Engineering*, 130(2), 021006.
3. **Stopa, J. E., & Mouche, A. (2017).** Significant wave heights from Sentinel-1 SAR: Validation and applications. *Journal of Geophysical Research: Oceans*, 122(3), 1827–1848.
4. **Haver, S. (2004).** A possible freak wave event measured at the Draupner Jacket, January 1, 1995. *Proc. Rogue Waves 2004*, Brest, France.
5. **Babarit, A., & Delhommeau, G. (2015).** Theoretical and numerical aspects of the open source BEM solver NEMOH. *Proc. EWTEC 2015*, Nantes, France.

---