# Phase 4 — Architettura e Dettaglio Moduli Python (`phase4_rerouting`)

Questo documento descrive la struttura software del package Python **`phase4_rerouting`**. Il package implementa la **Fase 4** della pipeline di ricerca (Re-Routing Added Value Simulation), con l'obiettivo di simulare le manovre evasive locali della nave container in risposta ai pericoli rilevati da satellite (Onde Estreme ed Iceberg) e calcolare il bilancio costi-benefici in termini di **sicurezza recuperata** e **penalità di carburante ($\Delta FOC$)**.

---

## 🏛️ Panoramica dell'Architettura Software

Il package è progettato seguendo i principi di **Modularità**, **Separazione delle Responsabilità (SRP)** e **Strong Typing** (tramite *Pydantic* e *Dataclasses*).

```
                      ┌────────────────────────┐
                      │    run_phase4.py       │ (Entry Point)
                      └───────────┬────────────┘
                                  │
                                  ▼
                      ┌────────────────────────┐
                      │      manager.py        │ (Controller / Orchestratore)
                      └───────────┬────────────┘
                                  │
      ┌───────────────────────────┼───────────────────────────┐
      │                           │                           │
      ▼                           ▼                           ▼
┌─────────────┐         ┌───────────────────┐       ┌───────────────────┐
│io_handler.py│         │scenario_gen.py    │       │   models.py       │
└─────────────┘         └─────────┬─────────┘       │   config.py       │
                                  │                 └───────────────────┘
                                  ▼
                        ┌───────────────────┐
                        │  safety_engine.py │ (Interfaccia Phase 1 - Seakeeping)
                        └─────────┬─────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │ cost_evaluator.py │ (Interfaccia Phase 1 - SFOC / Power)
                        └─────────┬─────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │decision_engine.py │ (Selezione Ottimo & ADV)
                        └───────────────────┘
```

---

## 📑 Dettaglio Modulo per Modulo

---

### 1. `config.py` — Costanti e Soglie Operative
* **Cosa fa:** Definisce in un unico punto le soglie fisiche di sicurezza e i parametri di configurazione per la generazione degli scenari.
* **Come lo fa:** Utilizza classi immutabili `@dataclass(frozen=True)` per prevenire modifiche accidentali a runtime.
* **Parametri principali:**
  * `MAX_HEAVE_M = 3.5`: Ampiezza massima ammissibile di sussulto ($m$) (Kytariolou & Themelis 2022).
  * `MAX_ROLL_DEG = 5.0`: Angolo massimo ammissibile di rollio ($^\circ$).
  * `MIN_ICE_CLEARANCE_NM = 15.0`: Distanza minima di rispetto dal limite dei ghiacci/iceberg ($NM$).
  * `SPEED_FACTORS = (0.95, 0.90, 0.85, 0.80, 0.75)`: Percentuali di riduzione velocità.
  * `DETOUR_OFFSETS_NM = (15.0, -15.0, 30.0, -30.0, ...)`: Spostamenti laterali geografici.

---

### 2. `models.py` — Modelli Dati e Tipizzazione (Pydantic)
* **Cosa fa:** Definisce la struttura formale e i vincoli di validazione per tutti i dati che scambiano i moduli.
* **Come lo fa:** Estende `pydantic.BaseModel` e `enum.Enum` per garantire che i tipi di dato (float, stringhe, booleani) siano validati automaticamente all'ingresso e durante la simulazione.
* **Classi definite:**
  * `EventRecord`: Dati d'ingresso letti dal CSV (Phase 3).
  * `CandidateScenario`: Singola variante di manovra evasiva (velocità applicata, offset deviazione).
  * `SafetyCheckResult`: Esito idrodinamico/distanza ghiacci (`heave_m`, `roll_deg`, `is_safe`).
  * `CostResult`: Esito energetico (`foc_ton`, `delta_foc_ton`, `required_power_kw`).
  * `ADVRecord`: Struttura dati finale registrata per la Phase 5.

---

### 3. `io_handler.py` — Ingestione, Validazione ed Esportazione Dati
* **Cosa fa:** Isola la logica di Input/Output da file system (CSV o Parquet).
* **Come lo fa:**
  * **Lettura (`load_events_from_csv`):** Usa `pandas` per caricare il file `.csv` della Phase 3, converte ogni riga in un dizionario e lo passa al modello `EventRecord` di Pydantic per validarne la correttezza formale.
  * **Scrittura (`save_adv_results`):** Prende la lista di oggetti `ADVRecord` prodotti dalla simulazione, li converte in `pandas.DataFrame` e li esporta in formato `.csv` o `.parquet` per la Phase 5.

---

### 4. `scenario_generator.py` — Generatore Discreto di Manovre
* **Cosa fa:** Crea la griglia di opzioni di navigazione alternative (manovre evasive) disponibili per la nave nella sola finestra dell'evento.
* **Come lo fa:**
  1. Inserisce sempre lo scenario **Baseline** (prosecuzione rotta e velocità originali).
  2. Genera manovre di **Speed Reduction**: riduce la velocità originaria a passi discreti ($95\%, 90\%, \dots, 75\%$).
  3. Genera manovre di **Spatial Detour**: mantiene la velocità e applica uno scostamento geografico trasversale a tribordo ($+$) o babordo ($-$).

---

### 5. `safety_engine.py` — Valutazione Idrodinamica e Distanza Pericoli
* **Cosa fa:** Calcola la risposta dinamica della nave (moti di tenue al mare) ed eventualmente la clearance dagli iceberg, verificando il rispetto delle soglie operative e quantifica i margini di sicurezza recuperata.
* **Come lo fa:**
  1. Si interfaccia con le equazioni di *Seakeeping* della **Phase 1** per ricalcolare **Heave** e **Rollio** in base alle condizioni reali misurate da satellite ($H_{max}$) e al nuovo vettore velocità/rotta della nave.
  2. Se l'evento riguarda un pericolo iceberg (`hazard_type == 'iceberg'`), calcola la nuova distanza dal ghiaccio tenendo conto dell'offset geografico della deviazione.
  3. Valuta la condizione logica:
     $$\text{is\_safe} = (\text{Heave} \le 3.5\text{ m}) \land (\text{Roll} \le 5.0^\circ) \land (\text{Ice Clearance} \ge 15\text{ NM})$$

---

### 6. `cost_evaluator.py` — Calcolo Potenza e Penalità di Consumo ($\Delta FOC$)
* **Cosa fa:** Calcola la spesa energetica (carburante in tonnellate) necessaria per eseguire la manovra candidata e determina la differenza rispetto alla baseline.
* **Come lo fa:**
  1. Si interfaccia con il modulo propulsivo della **Phase 1**: calcola la resistenza totale $R_{tot} = R_{calm} + R_{wave} + R_{wind}$ considerando vento, corrente e onde.
  2. Stima la potenza al freno $P_B$ del motore principale (MAN B&W 8K90MC-C) e legge lo SFOC corrispondente.
  3. Integra il consumo nella finestra temporale della manovra ($FOC_{candidate}$).
  4. Calcola la penalità extra in carburante:
     $$\Delta FOC = FOC_{candidate} - FOC_{baseline}$$

---

### 7. `decision_engine.py` — Ottimizzazione e Selettore Costi-Benefici
* **Cosa fa:** Seleziona la manovra vincente tra tutte le opzioni ed elabora il bilancio finale *Added Detection Value* (ADV).
* **Come lo fa:**
  1. Filtra la lista dei candidati conservando **solo quelli per cui `is_safe == True`**.
  2. Se esistono candidati sicuri, applica il criterio di minimo e seleziona il candidato che **minimizza la penalità di carburante $\Delta FOC$**.
  3. Se nessun candidato riesce a garantire la sicurezza totale, applica una strategia *best-effort*: seleziona la manovra che riduce al minimo l'ampiezza combinata dei moti e imposta `safety_restored = False`.
  4. Calcola i margini netti recuperati ($\Delta \text{Heave}$, $\Delta \text{Roll}$) e restituisce l'oggetto `ADVRecord`.

---

### 8. `manager.py` — Controller e Orchestratore Batch
* **Cosa fa:** Rappresenta la classe "Master" che coordina l'intero flusso di lavoro dell'applicazione.
* **Come lo fa:**
  1. Viene inizializzato con i percorsi dei file d'ingresso e d'uscita.
  2. Richiama `IOHandler` per caricare gli eventi dal CSV.
  3. Cicla su ogni evento (`process_single_event`) coordinando l'esecuzione sequenziale:
     $$\text{ScenarioGenerator} \longrightarrow \text{SafetyEngine} \longrightarrow \text{CostEvaluator} \longrightarrow \text{DecisionEngine}$$
  4. Raccoglie i risultati e invoca `IOHandler` per il salvataggio su disco.
```