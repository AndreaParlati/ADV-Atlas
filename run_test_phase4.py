import os
import sys
from pathlib import Path
import pandas as pd

# -----------------------------------------------------------------------------
# Configurazione del percorso sorgente (ADV-Atlas/Phase 4/src/)
# -----------------------------------------------------------------------------
# Individua la cartella radice del progetto
project_root = Path(__file__).resolve().parent

# Percorso esatto verso la cartella src/
src_dir = project_root / "Phase 4" / "src"

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
# Creazione Dati Sintetici di Prova (Dummy CSV)
# -----------------------------------------------------------------------------
dummy_data = [
    {
        "event_id": "EV_WAVE_001",
        "timestamp": "2026-10-18T10:00:00Z",
        "latitude": 44.5,
        "longitude": -48.2,
        "route_leg": "Grand Banks",
        "hazard_type": HazardType.ROGUE_WAVE.value,
        "forecast_hs": 3.2,
        "forecast_tp": 8.5,
        "forecast_wave_dir": 250.0,
        "wind_speed": 22.0,
        "wind_dir": 240.0,
        "current_speed": 0.6,
        "current_dir": 110.0,
        "satellite_type": "Sentinel-1_IW",
        "satellite_hs": 6.4,
        "satellite_hmax": 12.8,
        "ship_speed_kn": 16.0,
        "ship_heading": 280.0,
        "relative_wave_heading": 150.0,
        "baseline_foc_ton": 14.2,
        "baseline_heave_m": 4.12,  # Viola la soglia (3.5 m)
        "baseline_roll_deg": 6.35   # Viola la soglia (5.0 deg)
    },
    {
        "event_id": "EV_ICE_002",
        "timestamp": "2026-10-18T14:00:00Z",
        "latitude": 46.1,
        "longitude": -47.8,
        "route_leg": "Grand Banks",
        "hazard_type": HazardType.ICEBERG.value,
        "forecast_hs": 2.5,
        "forecast_tp": 7.0,
        "forecast_wave_dir": 220.0,
        "wind_speed": 15.0,
        "wind_dir": 210.0,
        "current_speed": 0.4,
        "current_dir": 90.0,
        "satellite_type": "Sentinel-1_EW",
        "satellite_hs": 2.8,
        "satellite_hmax": 5.0,
        "iceberg_distance_nm": 8.0, # Troppo vicino! (Soglia min: 15 NM)
        "ship_speed_kn": 16.0,
        "ship_heading": 275.0,
        "relative_wave_heading": 120.0,
        "baseline_foc_ton": 12.0,
        "baseline_heave_m": 2.1,
        "baseline_roll_deg": 3.0
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

    print("🚀 Avvio della simulazione di test per la Phase 4...")

    # Esecuzione dell'orchestratore
    manager = Phase4Manager(input_csv=input_file, output_csv=output_file)
    manager.run()

    # Lettura e verifica dell'output
    print("\n✅ Simulazione completata con successo! Risultati del test:\n")
    df_out = pd.read_csv(output_file)
    
    columns_to_show = [
        "event_id", "hazard_type", "optimal_strategy", 
        "applied_speed_kn", "applied_detour_nm", 
        "delta_foc_ton", "safety_restored"
    ]
    print(df_out[columns_to_show].to_string(index=False))

    # Pulizia dei file CSV temporanei
    if os.path.exists(input_file):
        os.remove(input_file)
    if os.path.exists(output_file):
        os.remove(output_file)