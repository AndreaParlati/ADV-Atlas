"""
Modulo per l'I/O: lettura e validazione dei dataset di Phase 3 (Parquet o CSV) ed esportazione.
"""
from typing import List
import pandas as pd
from models import EventRecord, ADVRecord

class IOHandler:
    @staticmethod
    def load_events_from_phase3(file_path: str) -> List[EventRecord]:
        """Legge il file di Phase 3 (Parquet o CSV), mappa i campi e restituisce EventRecord."""
        if file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
            
        events = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Mapping di compatibilità per colonne provenienti da Phase 3 (es. datetime -> timestamp, lon -> longitude)
            event_data = {
                "event_id": str(row_dict.get("event_id")),
                "timestamp": str(row_dict.get("datetime", row_dict.get("timestamp", ""))),
                "longitude": float(row_dict.get("lon", row_dict.get("longitude", 0.0))),
                "latitude": float(row_dict.get("lat", row_dict.get("latitude", 0.0))),
                "forecast_hs": float(row_dict.get("Hs_cmems", row_dict.get("forecast_hs", 3.0))),
                "forecast_tp": float(row_dict.get("T0_cmems", row_dict.get("forecast_tp", 10.0))),
                "sar_coincident": bool(row_dict.get("sar_coincident", False)),
                "alt_coincident": bool(row_dict.get("alt_coincident", False)),
                "any_coincident": bool(row_dict.get("any_coincident", False)),
                "hs_altimeter": float(row_dict["Hs_altimeter"]) if pd.notna(row_dict.get("Hs_altimeter")) else None,
                # Campi di fallback standard se non presenti nel file unificato
                "ship_speed_kn": float(row_dict.get("ship_speed_kn", 16.0)),
                "baseline_foc_ton": float(row_dict.get("baseline_foc_ton", 14.0)),
                "baseline_heave_m": float(row_dict.get("baseline_heave_m", 4.1)),
                "baseline_roll_deg": float(row_dict.get("baseline_roll_deg", 6.2)),
            }
            
            # Aggiunge eventuali altri campi presenti
            for k, v in row_dict.items():
                if k not in event_data and pd.notna(v):
                    event_data[k] = v

            events.append(EventRecord(**event_data))
        return events

    @staticmethod
    def save_adv_results(results: List[ADVRecord], output_path: str) -> None:
        """Salva il dataset finale ADV in formato CSV o Parquet."""
        data = [r.model_dump() for r in results]
        df = pd.DataFrame(data)
        
        if output_path.endswith(".parquet"):
            df.to_parquet(output_path, index=False)
        else:
            df.to_csv(output_path, index=False)