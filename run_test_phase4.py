import os
import sys
from pathlib import Path
import pandas as pd

# -----------------------------------------------------------------------------
# Configurazione del percorso sorgente (ADV-Atlas/Phase_4/src/)
# -----------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent
src_dir = project_root / "Phase_4" / "src"

# Percorso esatto verso la cartella src/
src_dir = project_root / "Phase_4" / "src"

# Aggiunta della cartella src/ direttamente al sys.path
if src_dir.exists():
    sys.path.insert(0, str(src_dir.resolve()))
    print(f"✅ Directory sorgente trovata e aggiunta al path: {src_dir.resolve()}")
else:
    print(f"❌ Errore: Il percorso {src_dir} non esiste. Verificare la struttura delle cartelle.")
    sys.exit(1)

# Importazione diretta dei moduli presenti dentro src/
try:
    from manager import Phase4Manager
    from models import HazardType
except ModuleNotFoundError as e:
    print(f"❌ Errore nell'importazione dei moduli: {e}")
    print(f"Assicurati che i file manager.py, models.py, ecc. si trovino direttamente dentro: {src_dir.resolve()}")
    sys.exit(1)


# -----------------------------------------------------------------------------
# Creazione Dati Sintetici di Prova (Aggiornati con i parametri della Phase 1)
# -----------------------------------------------------------------------------
dummy_data = [
    {
        "event_id": "TEST_WAVE_01",
        "timestamp": "2026-10-28T12:00:00Z",
        "latitude": 44.5,
        "longitude": -48.2,
        "route_leg": "Grand Banks",
        "hazard_type": HazardType.ROGUE_WAVE.value,
        # Parametri ambientali mappati per il nuovo SafetyEngine e CostEvaluator
        "hs_m": 3.0,
        "t0_s": 8.0,
        "wave_from_deg": 250.0,
        "wind_speed_ms": 20.0,
        "wind_from_deg": 240.0,
        "current_speed_ms": 0.5,
        "current_dir_to_deg": 100.0,
        # Dati satellite e nave
        "satellite_type": "Sentinel-1_IW",
        "satellite_hs": 6.2,
        "satellite_hmax": 12.5,  # Indice di anormalità critico (Hmax / Hs > 2)
        "ship_speed_kn": 16.0,
        "ship_heading_deg": 280.0,
        "baseline_foc_ton": 14.0,
        "baseline_heave_m": 4.1,   # VIOLA la soglia di sicurezza (> 3.5 m)
        "baseline_roll_deg": 6.2    # VIOLA la soglia di sicurezza (> 5.0°)
    },
    {
        "event_id": "TEST_ICE_02",
        "timestamp": "2026-10-28T16:00:00Z",
        "latitude": 46.0,
        "longitude": -47.5,
        "route_leg": "Grand Banks",
        "hazard_type": HazardType.ICEBERG.value,
        # Parametri ambientali
        "hs_m": 2.0,
        "t0_s": 7.0,
        "wave_from_deg": 220.0,
        "wind_speed_ms": 15.0,
        "wind_from_deg": 210.0,
        "current_speed_ms": 0.3,
        "current_dir_to_deg": 90.0,
        # Dati satellite e nave
        "satellite_type": "Sentinel-1_EW",
        "satellite_hs": 2.2,
        "satellite_hmax": 4.0,
        "iceberg_distance_nm": 8.0,  # VIOLA la clearance minima (< 15 NM)
        "ship_speed_kn": 16.0,
        "ship_heading_deg": 275.0,
        "baseline_foc_ton": 12.0,
        "baseline_heave_m": 2.0,
        "baseline_roll_deg": 2.5
    }
]

input_file = "dummy_input.csv"
output_file = "dummy_output.csv"


# -----------------------------------------------------------------------------
# Esecuzione del Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Salva il CSV temporaneo di test
    pd.DataFrame(dummy_data).to_csv(input_file, index=False)

    print("🚀 Avvio della simulazione di test per la Phase 4 (con motori Phase 1)...")

    # Esecuzione dell'orchestratore
    manager = Phase4Manager(input_csv=input_file, output_csv=output_file)
    manager.run()

    # Lettura e verifica dell'output
    print("\n✅ Simulazione completata con successo! Risultati del test:\n")
    df_out = pd.read_csv(output_file)
    
    columns_to_show = [
        "event_id", 
        "hazard_type", 
        "optimal_strategy", 
        "applied_speed_kn", 
        "applied_detour_nm", 
        "delta_foc_ton", 
        "heave_margin_recovered_m",
        "roll_margin_recovered_deg",
        "safety_margin_score",
        "safety_restored"
    ]
    
    # Filtra solo le colonne effettivamente presenti nel DataFrame di output
    available_cols = [col for col in columns_to_show if col in df_out.columns]
    print(df_out[available_cols].to_string(index=False))

    # Pulizia dei file CSV temporanei
    if os.path.exists(input_file):
        os.remove(input_file)
    if os.path.exists(output_file):
        os.remove(output_file)