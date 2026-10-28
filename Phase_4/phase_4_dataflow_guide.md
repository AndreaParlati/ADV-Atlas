# Phase 4 — Re-Routing Added Value Simulation: Guida ai Dati e all'Elaborazione

Questo documento descrive in modo esaustivo il funzionamento interno della **Fase 4** (Re-Routing Added Value Simulation). La Fase 4 calcola il **valore operativo reale** dell'informazione satellitare: determina la manovra locale ottimale (riduzione di velocità o deviazione spaziale) quando i dati osservati da satellite (Sentinel-1 SAR, Altimetria L3, IIP Ice Charts) rivelano un pericolo sottostimato o assente nei modelli di previsione deterministica (CMEMS / ERA5), e quantifica la relativa penalità in carburante ($\Delta FOC$).

---

## 📥 1. Dati in Input (Cosa entra nel modulo)

Il modulo della Fase 4 riceve in ingresso un file **`.csv`** (generato dalla Fase 3) contenente gli eventi di coincidenza spatio-temporale tra la rotta della nave e l'osservazione satellitare/diretta. 

Per aderire integralmente alla specifica di progetto (inclusi i canali di pericolo per **onde estreme** e **iceberg** ex Modulo A, nonché la forcing metoceanica completa ex Kytariolou & Themelis 2022), il file CSV include le seguenti 6 categorie di parametri:

### 1. Identificatori e Posizione Spazio-Temporale
* `event_id` *(String)*: Codice identificativo univoco dell'evento (es. `EV_2024_089`).
* `timestamp` *(ISO 8601 Datetime)*: Data e ora della coincidenza (es. `2024-10-15T14:30:00Z`).
* `latitude`, `longitude` *(Float)*: Coordinate geografiche della coincidenza.
* `route_leg` *(String)*: Segmento della rotta transoceanica (es. *Mid-Atlantic* o *Grand Banks Approach*).

### 2. Canale Pericolo 1: Onde Estreme e Stato del Mare (CMEMS Forecast vs Satellite)
* `forecast_hs` *(Float)*: Altezza significativa dell'onda prevista dal modello CMEMS ($m$).
* `forecast_tp` *(Float)*: Periodo di picco dell'onda previsto ($s$).
* `forecast_wave_dir` *(Float)*: Direzione di provenienza dell'onda prevista ($^\circ$).
* `satellite_type` *(String)*: Sensore satellitare (es. *Sentinel-1_IW_OSW*, *Sentinel-6_Altimeter*).
* `satellite_hs` *(Float)*: Altezza dell'onda reale misurata da satellite ($m$).
* `satellite_hmax` *(Float)*: Onda massima reale osservata o stimata tramite l'indice di anormalità ($H_{max}/H_s > 2$).
* `forecast_underestimation_ratio` *(Float)*: Rapporto di sottostima del modello rispetto all'osservazione.

### 3. Canale Pericolo 2: Iceberg e Campi di Ghiaccio (Modulo A — IIP / CIS)
* `hazard_type` *(String)*: Tipologia di pericolo prevalente (`rogue_wave`, `iceberg_field`, `combined`).
* `iceberg_hazard_flag` *(Boolean)*: Flag di presenza iceberg o superamento del "Limit of All Known Ice".
* `iceberg_distance_nm` *(Float)*: Distanza stimata tra la rotta baseline e l'iceberg / limite del ghiaccio ($NM$).
* `ice_field_density` *(Float)*: Concentrazione o densità stimata dei ghiacci nell'area.

### 4. Forzanti Metoceaniche Ambientali (ERA5 / CMEMS Ocean Physics)
* `wind_speed` *(Float)*: Velocità del vento vera ad altezza $10\text{ m}$ ($kn$ o $m/s$).
* `wind_dir` *(Float)*: Direzione di provenienza del vento vera ($^\circ$).
* `current_speed` *(Float)*: Velocità della corrente marina superficiale ($kn$).
* `current_dir` *(Float)*: Direzione verso cui fluisce la corrente ($^\circ$).

### 5. Stato Operativo e Cinematico della Nave (Baseline Paper [1])
* `ship_speed_kn` *(Float)*: Velocità di avanzamento originaria della nave container ($kn$).
* `ship_heading` *(Float)*: Prua/rotta della nave ($^\circ$).
* `relative_wave_heading` *(Float)*: Angolo relativo tra la prua della nave e le onde ($^\circ$).
* `baseline_foc_ton` *(Float)*: Consumo stimato di carburante (FOC) per l'attraversamento della cella senza variazioni di rotta.

### 6. Indicatori di Violazione della Sicurezza (Baseline Unsafe)
* `baseline_heave_m` *(Float)*: Ampiezza del moto di sussulto (heave) calcolata in mare reale; unsafe se $> 3.5\text{ m}$.
* `baseline_roll_deg` *(Float)*: Ampiezza del moto di rollio calcolata in mare reale; unsafe se $> 5.0^\circ$.
* `iceberg_clearance_violated` *(Boolean)*: `True` se la distanza dall'iceberg è inferiore al margine minimo di sicurezza ($< 15\text{ NM}$).
* `safety_violated_flag` *(Boolean)*: `True` se almeno una delle soglie di sicurezza fisica o di clearance è stata superata.

---

## ⚙️ 2. Come vengono elaborati i dati (Il processo interno)

La Fase 4 processa ciascun evento attraverso **4 passaggi sequenziali**:

```
 ┌──────────────────────┐
 │  1. Ingestione Data  │  ---> Legge la riga dal CSV (Onde, Iceberg, Vento, Corrente, Nave)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 2. Generazione Scenari│ ---> Genera manovre locali in base al tipo di pericolo (Hazard Type)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │  3. Valutazione      │  ---> Richiama i moduli della Fase 1 (Resistenza, SFOC, Seakeeping)
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │  4. Selezione & ADV  │  ---> Trova la manovra sicura a minor consumo ed esporta le metriche
 └──────────────────────┘
```

### Passaggio 1: Generazione degli Scenari Locali (`LocalScenarioGenerator`)
A seconda del valore assunto da `hazard_type`, la Fase 4 genera una griglia discreta di candidate manovre nella sola finestra locale dell'evento ($\pm 6\text{ ore}$ o $\pm 100\text{ NM}$):
* **Per Onde Estreme (`rogue_wave`):** 
  * *Strategy 1 (Speed Reduction):* Genera step di riduzione velocità: $V_s \in [95\%, 90\%, 85\%, 80\%, 75\%] \cdot V_0$.
  * *Strategy 2 (Spatial Detour):* Mantiene la velocità e genera deviazioni trasversali con waypoint sfalsati: $d_{offset} \in [\pm 15, \pm 30, \pm 45\text{ NM}]$.
* **Per Iceberg (`iceberg_field`):** 
  * Genera primariamente deviazioni geografiche trasversali ($d_{offset} \in [+15, +30, +45, +60\text{ NM}]$) dirette lontano dalla traccia del ghiaccio, accoppiate a riduzioni prudenziali di velocità.

### Passaggio 2: Valutazione Idrodinamica e di Sicurezza (`KinematicAndSafetyEngine`)
Per ogni candidato, il motore invoca le equazioni fisiche sviluppate nella Fase 1:
1. **Resistenza Totale ($R_{tot}$):** Calcola la resistenza in acqua calma $R_{calm}(V_s, \text{corrente})$, la resistenza aggiuntiva delle onde $R_{wave}(H_s^{sat}, \omega_e)$ e la resistenza del vento $R_{wind}(V_{wind}, \text{prua})$.
2. **Moti Nave (Seakeeping):** Ricalcola le risposte di **Heave** e **Rollio** in funzione della nuova velocità e dell'angolo relativo d'incontro dell'onda.
3. **Controllo Vincoli:** Una manovra è **SICURA** se e solo se:
   $$\text{Heave} \le 3.5\text{ m}, \quad \text{Rollio} \le 5.0^\circ, \quad \text{e} \quad \text{Distanza Iceberg} \ge 15\text{ NM}$$

### Passaggio 3: Valutazione dei ConsumiEnergetici (`CostBenefitEvaluator`)
Per le manovre risultate conformi ai vincoli:
1. Calcola la richiesta di potenza al motore principale (MAN B&W 8K90MC-C) e il consumo totale di carburante ($FOC_{candidate}$) in tonnellate tramite la mappa SFOC.
2. Calcola la penalità di consumo:
   $$\Delta FOC = FOC_{candidate} - FOC_{baseline}$$
3. Calcola il margine di sicurezza recuperato ($\Delta \text{Heave}$, $\Delta \text{Roll}$, $\Delta \text{Ice_Clearance}$).

### Passaggio 4: Selezione della Manovra Ottimale
Tra tutte le opzioni sicure, il sistema **seleziona il candidato che minimizza la penalità di carburante $\Delta FOC$**.

---

## 📤 3. Dati in Output (Cosa restituisce il modulo)

Il risultato finale della simulazione viene esportato nel dataset **`Phase4_ADV_Dataset`** (`.csv` / `.parquet`), strutturato con i seguenti campi per ogni evento:

| Nome Campo | Tipo | Descrizione |
| :--- | :--- | :--- |
| `event_id` | *String* | Identificativo dell'evento coincidente. |
| `hazard_type` | *String* | Tipologia di pericolo gestita (`rogue_wave`, `iceberg_field`, `combined`). |
| `optimal_strategy` | *String* | Manovra selezionata (`Speed_Reduction`, `Spatial_Detour`, `Combined_Speed_Detour`). |
| `applied_speed_kn` | *Float* | Nuova velocità operativa applicata ($kn$). |
| `applied_detour_nm` | *Float* | Offset geografico trasversale applicato ($NM$). |
| `reroute_foc_ton` | *Float* | Consumo totale di carburante della manovra ri-ottimizzata ($t$). |
| `delta_foc_ton` | *Float* | **Penalità di carburante ($\Delta FOC$):** Spesa extra in carburante ($t$). |
| `reroute_heave_m` | *Float* | Nuovo ampiezza di sussulto (heave) ($m$). |
| `reroute_roll_deg` | *Float* | Nuovo ampiezza di rollio ($^\circ$). |
| `iceberg_clearance_m` | *Float* | Nuova distanza minima dall'iceberg o limite del ghiaccio ($NM$). |
| `delta_heave_m` | *Float* | Riduzione del moto di sussulto rispetto alla baseline ($m$). |
| `delta_roll_deg` | *Float* | Riduzione del moto di rollio rispetto alla baseline ($^\circ$). |
| `heave_margin_recovered_m` | *Float*	| Margine di sussulto recuperato (riduzione del moto + headroom di sicurezza). |
| `roll_margin_recovered_deg` |	*Float*	| Margine di rollio recuperato rispetto alla soglia limite. |
| `ice_clearance_margin_nm` |	*Float* | (Optional)	Margine di distanza extra guadagnato dal limite dei ghiacci (NM). |
| `safety_margin_score` |	*Float*	| Indice sintetico normalizzato (0–100%) del recupero complessivo di sicurezza. |
| `safety_restored` | *Boolean* | `True` se tutti i parametri di sicurezza fisica/clearance sono stati ripristinati. |

---

## 🎯 4. Connessione con la Fase 5 (ADV Atlas)

Le metriche di output della Fase 4 alimenteranno la **Fase 5**, consentendo di:
1. Mappare lungo il corridoio Atlantico le regioni ad **Alto ADV** (massimo recupero di sicurezza con minima spesa $\Delta FOC$) sia per eventi di mareggiata sia per l'avvicinamento al Grand Banks esposto agli iceberg.
2. Identificare i **Corridoi Ciechi** (*blind corridors*), dovuti a buchi di rivisitazione satellitare o ad aree in cui le deviazioni richieste comportano una penalità di carburante insostenibile.
```

Ho generato il file `Phase4_DataFlow_Guide.md` aggiornato. Il documento ora integra tutte le specifiche di progetto, comprese le forzanti meteoceaniche complete (vento e correnti) e il secondo canale di pericolo (iceberg e campi di ghiaccio del Modulo A).