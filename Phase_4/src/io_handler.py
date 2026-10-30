import pandas as pd
from pathlib import Path
from models import EventRecord, HazardType, ADVRecord

class IOHandler:
    @staticmethod
    def load_events_from_phase3(file_path: str) -> list[EventRecord]:
        """Carica gli eventi di coincidenza dalla Fase 3 supportando Parquet e CSV con mappatura flessibile."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"❌ Impossibile trovare il file di input della Fase 3: {file_path}")
        
        if path.suffix.lower() == ".parquet":
            df = pd.read_parquet(path)
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            raise ValueError(f"❌ Formato file non supportato: {path.suffix}")

        events = []
        for _, row in df.iterrows():
            event = EventRecord(
                event_id=str(row.get("event_id", "UNKNOWN")),
                timestamp=str(row.get("timestamp", row.get("datetime", ""))),
                latitude=float(row.get("latitude", row.get("lat", 0.0))),
                longitude=float(row.get("longitude", row.get("lon", 0.0))),
                forecast_hs=float(row.get("forecast_hs", row.get("Hs_cmems", 0.0))),
                forecast_tp=float(row.get("forecast_tp", row.get("T0_cmems", 0.0))),
                sar_coincident=bool(row.get("sar_coincident", False)),
                alt_coincident=bool(row.get("alt_coincident", False)),
                any_coincident=bool(row.get("any_coincident", False)),
                Hs_altimeter=float(row.get("Hs_altimeter", 0.0)) if pd.notna(row.get("Hs_altimeter")) else None,
                hazard_type=HazardType(row.get("hazard_type", HazardType.ROGUE_WAVE.value)),
                ship_speed_kn=float(row.get("ship_speed_kn", 16.0)),
                baseline_foc_ton=float(row.get("baseline_foc_ton", 14.0)),
                baseline_heave_m=float(row.get("baseline_heave_m", 0.0)),
                baseline_roll_deg=float(row.get("baseline_roll_deg", 0.0))
            )
            events.append(event)
            
        return events

    @staticmethod
    def save_adv_results(adv_results: list[ADVRecord], output_path: str) -> None:
        """Salva i risultati dell'elaborazione ADV in un file CSV."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = []
        for res in adv_results:
            data.append({
                "event_id": getattr(res, "event_id", "UNKNOWN"),
                "optimal_strategy": res.optimal_strategy.value if hasattr(res.optimal_strategy, "value") else str(res.optimal_strategy),
                "applied_speed_kn": getattr(res, "applied_speed_kn", 0.0),
                "applied_detour_nm": getattr(res, "applied_detour_nm", 0.0),
                "delta_foc_ton": getattr(res, "delta_foc_ton", 0.0),
                "reroute_heave_m": getattr(res, "reroute_heave_m", 0.0),
                "reroute_roll_deg": getattr(res, "reroute_roll_deg", 0.0),
                "safety_restored": getattr(res, "safety_restored", False)
            })
        
        df = pd.DataFrame(data)
        df.to_csv(path, index=False)