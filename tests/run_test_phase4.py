import os
import sys
from pathlib import Path
import pandas as pd

# -----------------------------------------------------------------------------
# Configurazione dei percorsi (ADV-Atlas/Phase_4/src/)
# -----------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent
src_dir = project_root / "Phase_4" / "src"

if src_dir.exists():
    sys.path.insert(0, str(src_dir.resolve()))
    print(f"✅ Directory sorgente trovata e aggiunta al path: {src_dir.resolve()}")
else:
    print(f"❌ Errore: Il percorso {src_dir} non esiste.")
    sys.exit(1)

try:
    from manager import Phase4Manager
    from models import HazardType
except ModuleNotFoundError as e:
    print(f"❌ Errore nell'importazione dei moduli: {e}")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Creazione di un dataset di test minimale (Mock basato sul formato di Phase 3)
# -----------------------------------------------------------------------------
def create_mock_phase3_data(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mock_data = [
        {
            "event_id": "TEST_H1_01",
            "datetime": "2026-10-28T12:00:00",
            "lat": 44.5,
            "lon": -48.2,
            "Hs_cmems": 3.8,
            "T0_cmems": 9.5,
            "sar_coincident": True,
            "alt_coincident": True,
            "any_coincident": True,
            "Hs_altimeter": 4.2,  # Misura reale altimetro (Fase 3)
            "hazard_type": HazardType.ROGUE_WAVE.value,
            "ship_speed_kn": 16.0,
            "baseline_foc_ton": 14.0,
            "baseline_heave_m": 3.9,
            "baseline_roll_deg": 5.5
        }
    ]
    df = pd.DataFrame(mock_data)
    df.to_parquet(output_path, index=False)
    print(f"🧪 Dataset di test mock creato in: {output_path}")

# -----------------------------------------------------------------------------
# Esecuzione del Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    test_input_parquet = project_root / "Phase_3" / "data" / "coincidence_merged.parquet"
    test_output_csv = project_root / "test_phase4_output.csv"

    # Se il file di Phase 3 non esiste ancora, creiamo un mock di prova per testare il motore
    if not test_input_parquet.exists():
        print("⚠️ File di Phase 3 non trovato. Generazione di un file di test locale...")
        create_mock_phase3_data(test_input_parquet)

    print("\n🚀 Avvio del test di esecuzione per la Phase 4...")
    
    try:
        # Inizializza e avvia il manager puntando al file di input
        manager = Phase4Manager(input_path=str(test_input_parquet), output_csv=str(test_output_csv))
        manager.run()

        # Verifica e stampa dei risultati ottenuti
        if os.path.exists(test_output_csv):
            df_out = pd.read_csv(test_output_csv)
            print("\n✅ Test completato con successo! Anteprima dei risultati generati:\n")
            
            columns_to_show = [
                "event_id", 
                "optimal_strategy", 
                "applied_speed_kn", 
                "applied_detour_nm", 
                "delta_foc_ton", 
                "reroute_heave_m",
                "reroute_roll_deg",
                "safety_restored"
            ]
            available_cols = [c for c in columns_to_show if c in df_out.columns]
            print(df_out[available_cols].to_string(index=False))
        else:
            print("❌ Errore: Il file di output non è stato generato.")

    except Exception as e:
        print(f"❌ Errore durante l'esecuzione della simulazione: {e}")
        import traceback
        traceback.print_exc()

    # Pulizia opzionale del file di output del test
    if os.path.exists(test_output_csv):
        os.remove(test_output_csv)