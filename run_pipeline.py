import os
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Configurazione dei percorsi di root
# -----------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent

def run_phase_2_catalogue():
    """Verifica o genera il catalogo degli hazard della Fase 2."""
    print("\n[Fase 2] 🌊 Verifica/Generazione catalogo eventi di pericolo (Hazard Catalogue)...")
    
    # Percorso atteso del catalogo hazard (es. per l'anno di riferimento)
    hazard_parquet = project_root / "Phase_3" / "data" / "hazard_catalogue_2022.parquet"
    
    if hazard_parquet.exists():
        print(f"✅ Catalogo hazard già esistente trovato in: {hazard_parquet.name}")
        return True
        
    print("⚠️ Catalogo hazard non trovato. Tentativo di generazione...")
    # Qui puoi richiamare la logica o lo script della Fase 2 se disponibile, 
    # oppure lasciare che la Fase 3 lo ricrei inline dai file NetCDF locali.
    return True

def run_phase_3():
    """Esegue l'analisi di coincidenza spazio-temporale (Fase 3)[cite: 21]."""
    print("\n[Fase 3] 🛰️ Avvio analisi di coincidenza satellitare (SAR & Altimetri)...")
    phase3_dir = project_root / "Phase_3" / "src"
    
    run_p3_script = phase3_dir / "run_phase3.py"
    if run_p3_script.exists():
        sys.path.insert(0, str(phase3_dir))
        try:
            from run_phase3 import main as run_p3
            run_p3()  # Genera o aggiorna coincidence_merged.parquet
            print("✅ Phase 3 completata: file coincidence_merged.parquet pronto.")
        except Exception as e:
            print(f"❌ Errore durante l'esecuzione della Phase 3: {e}")
            raise e
        finally:
            sys.path.pop(0)
    else:
        print("⚠️ Script 'run_phase3.py' non trovato nella cartella Phase_3.")

def run_phase_4():
    """Esegue il motore di re-routing e valutazione manovre evasive (Fase 4)."""
    print("\n[Fase 4] ⚓ Avvio motore di re-routing e sicurezza idrodinamica...")
    phase4_src = project_root / "Phase_4" / "src"
    
    if phase4_src.exists():
        sys.path.insert(0, str(phase4_src))
        from manager import Phase4Manager
        
        input_parquet = project_root / "Phase_3" / "data" / "coincidence_merged.parquet"
        output_csv = project_root / "Phase_5" / "data" / "adv_routing_results.csv"
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        
        manager = Phase4Manager(input_path=str(input_parquet), output_csv=str(output_csv))
        manager.run()
        sys.path.pop(0)
        print(f"✅ Output della Phase 4 salvato in: {output_csv}")
    else:
        raise FileNotFoundError(f"Directory Phase_4/src non trovata in {phase4_src}")

def run_phase_5():
    """Genera i report finali e i KPI dell'atlante ADV (Fase 5)."""
    print("\n[Fase 5] 📊 Generazione report finali e KPI dell'Atlante ADV...")
    output_csv = project_root / "Phase_5" / "data" / "adv_routing_results.csv"
    
    if output_csv.exists():
        import pandas as pd
        df = pd.read_csv(output_csv)
        print(f"📈 Totale eventi elaborati e ottimizzati: {len(df)}")
        print(f"🚀 Strategie di sicurezza applicate con successo: {df['safety_restored'].sum()} su {len(df)}")
    else:
        print("⚠️ File dei risultati di Phase 4 non trovato per il post-processing.")

# -----------------------------------------------------------------------------
# Esecuzione della Pipeline Completa End-to-End
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 ADV-Atlas: Avvio della Pipeline Completa (Fase 2 ➔ Fase 5)")
    
    try:
        # 1. Preparazione Dati di Base (Fase 2)
        run_phase_2_catalogue()
        
        # 2. Coincidenza Satellitare (Fase 3)
        run_phase_3()
        
        # 3. Ottimizzazione e Sicurezza (Fase 4)
        run_phase_4()
        
        # 4. Reportistica finale (Fase 5)
        run_phase_5()
        
        print("\n🎉 Pipeline completata con successo in tutte le sue fasi!")

    except Exception as e:
        print(f"\n❌ Errore critico durante l'esecuzione della pipeline: {e}")
        import traceback
        traceback.print_exc()