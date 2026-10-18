"""
Modulo per l'I/O: lettura e validazione del CSV di Phase 3 ed esportazione dei risultati.
"""
from typing import List
import pandas as pd
from models import EventRecord, ADVRecord

class IOHandler:
    @staticmethod
    def load_events_from_csv(file_path: str) -> List[EventRecord]:
        """Legge il CSV di Phase 3, valida i campi e restituisce una lista di EventRecord."""
        df = pd.read_csv(file_path)
        events = []
        for _, row in df.iterrows():
            # Conversione dizionario per Pydantic Validation
            event = EventRecord(**row.to_dict())
            events.append(event)
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