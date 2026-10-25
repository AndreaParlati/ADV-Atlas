# Phase 5 — Synthesis and Products (ADV Atlas & Operational Framing)

## 1. Obiettivo Generale della Fase
La Fase 5 costituisce lo stadio di sintesi finale dell'intero framework di simulazione. Il suo scopo principale è fondere e correlare i risultati quantitativi prodotti dalle fasi precedenti per generare l'Added Detection Value (ADV) Atlas lungo il corridoio navale Nord Atlantico (Lisbona–Halifax).

Nello specifico, la Fase 5 correla:
* Fase 3 (Satellite Coincidence): Frequenza di coincidenza spazio-temporale dei sorvoli satellitari (costellazione Sentinel-1 e altimetri L3/L4) ed entità della sottostima del modello di previsione deterministico CMEMS (Hs ed eventuale Hmax).
* Fase 4 (Re-Routing Added Value): Guadagno di sicurezza idrodinamica e operativa ottenuto (ripristino delle soglie limite di heave e roll, azzeramento del rischio iceberg) a fronte della penalità di consumo di carburante sostenuta (Delta FOC).

L'output primario è un dataset/mappa parametrica geolocalizzata per segmento di rotta che quantifica dove l'informazione ora-per-ora dei satelliti aggiunge valore operativo reale a un sistema di weather routing e dove, invece, esistono "corridoi ciechi" (blind corridors) strutturali dovuti alla geometria delle orbite e ai tassi di rivisitazione.

---

# 2. Dettaglio dei Moduli e Responsabilità

### 2.1 models.py
Definisce i modelli di dati tipizzati e validati tramite Pydantic che garantiscono l'integrità del flusso tra un modulo e l'altro:
* IntegratedEventRecord: Rappresenta la struttura dati combinata di un singolo evento, unendo i parametri fisici/satellitari di Phase 3 (probabilità di coincidenza, Hs modellato, Hs satellitare, bias di sottostima) con i risultati idrodinamici e strategici di Phase 4 (strategia ottimale scelta, variazione consumo Delta FOC, flag safety_restored).
* ADVAtlasRecord: Estende il record integrato aggiungendo l'ADV Score calcolato, la classificazione del segmento geografico (Mid-Atlantic Leg, Grand Banks Approach) e il flag di operatività in tempo reale (Actionable vs Retrospective-only).

### 2.2 config.py (ADVConfig)
Contiene le costanti parametriche, i pesi e le soglie di calcolo per la Fase 5:
* WEIGHT_SAFETY: Peso relativo attribuito al ripristino della sicurezza idrodinamica o alla prevenzione di collisione iceberg.
* WEIGHT_FUEL_PENALTY: Fattore di ponderazione applicato all'incremento dei consumi di carburante (Delta FOC).
* WEIGHT_FORECAST_BIAS: Peso legato all'ampiezza dell'errore di previsione del modello CMEMS.
* MAX_ACTIONABLE_LATENCY_HOURS: Soglia temporale massima di latenza del dato satellitare (es. 3 ore) entro cui l'informazione è considerata azionabile a bordo prima del passaggio della nave.

### 2.3 aggregator.py (DataAggregator)
Modulo preposto alla Data Fusion dei risultati delle fasi 3 e 4:
* Riceve in ingresso i dataset di Phase 3 (coincidenze e bias di previsione) e Phase 4 (ottimizzazione del re-routing).
* Esegue un'operazione di merge relazionale basata su event_id.
* Valida ogni record risultante tramite il modello Pydantic IntegratedEventRecord, isolando ed evidenziando eventuali disallineamenti o dati mancanti.

### 2.4 adv_calculator.py (ADVCalculator)
Implementa la formulazione matematica del valore aggiunto satellitare (Added Detection Value):
* Formulazione dell'ADV Score:
  ADV Score = w_s * SafetyRestored + w_b * ForecastBiasNorm - w_f * DeltaFOCNorm
  dove SafetyRestored indica il ripristino della sicurezza, ForecastBiasNorm esprime l'ampiezza della sottostima del modello, e DeltaFOCNorm quantifica l'impatto economico/combustibile.
* Segmentazione Geografica: Raggruppa gli eventi in base alle coordinate geografiche e al leg di navigazione (route_leg), identificando analiticamente le aree dove la probabilità di coincidenza è elevata (es. Grand Banks) rispetto alle zone a copertura rada (Mid-Atlantic blind corridor).

### 2.5 operational_eval.py (OperationalEvaluator)
Valuta il gap tra l'analisi diagnostica/retrospettiva e l'effettiva operatività real-time a bordo:
* Analizza le finestre temporali di acquisizione satellitare rispetto al piano di rotta della nave.
* Classifica ogni evento coincident come Actionable (latenza di ricezione del dato <= finestra decisionale di manovra) oppure Retrospective-only (dato acquisito ma arrivato con latenza superiore alla finestra utile di re-routing).

### 2.6 atlas_generator.py (AtlasGenerator)
Gestisce l'esportazione dei dati e la preparazione delle sintesi analitiche:
* Genera l'ADV Atlas tabellare nei formati standard .csv e .parquet.
* Calcola le metriche aggregate di corridoio: percentuale di eventi rilevati, risparmio/costo medio di carburante per tipo di rischio (onde anomale vs iceberg) e tasso di azionabilità reale.

### 2.7 manager.py (Phase5Manager)
Orchestratore di alto livello della Fase 5:
* Coordina la sequenza di esecuzioni: DataAggregator -> ADVCalculator -> OperationalEvaluator -> AtlasGenerator.
* Fornisce un'interfaccia semplice per l'esecuzione batch di tutta la sintesi finale tramite un'unica chiamata.

---

## 3. Input e Output della Fase 5

### Input Requisiti:
1. Dataset Phase 3 (phase3_coincidence_output.csv): Contiene event_id, coincidence_flag, satellite_type, forecast_hs, satellite_hs, forecast_bias.
2. Dataset Phase 4 (phase4_rerouting_output.csv): Contiene event_id, optimal_strategy, applied_speed_kn, applied_detour_nm, delta_foc_ton, safety_restored.

### Output Prodotti:
1. adv_atlas_dataset.csv / adv_atlas_dataset.parquet: Dataset integrato geolocalizzato contenente tutti i dati di rotta, parametri satellitari, strategie applicate e il punteggio adv_score calcolato.
2. operational_summary.json: Report JSON sintetico con indicatori aggregati per leg di navigazione (densità coincidenze, identificazione blind corridors, bilancio globale costo/sicurezza e tasso di azionabilità).