"""
Phase 5 - Data Aggregator (aggregator.py)
Modulo preposto al merge e Data Fusion dei risultati di Phase 3 e Phase 4.
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np
from .models import IntegratedEventRecord


class DataAggregator:
    """
    Esegue l'integrazione relazionale tra i dati di coincidenza satellitare (Phase 3)
    e i dati di re-routing idrodinamico (Phase 4).
    """

    @staticmethod
    def aggregate(phase3_data: List[Dict[str, Any]], phase4_data: List[Dict[str, Any]]) -> List[IntegratedEventRecord]:
        """
        Effettua il merge relazionale basato su event_id e valida i record risultanti.
        """
        df_p3 = pd.DataFrame(phase3_data)
        df_p4 = pd.DataFrame(phase4_data)

        if df_p3.empty or df_p4.empty:
            return []

        # Merge relazionale su event_id
        merged_df = pd.merge(df_p3, df_p4, on="event_id", how="inner")

        integrated_records: List[IntegratedEventRecord] = []
        for _, row in merged_df.iterrows():
            record_dict = row.to_dict()
            
            # Pulisci eventuali chiavi duplicate del merge se presenti
            keys_to_clean = [k for k in record_dict.keys() if k.endswith('_x') or k.endswith('_y')]
            for k in keys_to_clean:
                clean_key = k[:-2]
                if clean_key not in record_dict or pd.isna(record_dict[clean_key]):
                    record_dict[clean_key] = record_dict[k]
                del record_dict[k]

            # Sostituisci NaN / NaT di pandas/numpy con None per compatibilità Pydantic
            cleaned_dict = {
                k: (None if pd.isna(v) or (isinstance(v, float) and np.isnan(v)) else v)
                for k, v in record_dict.items()
            }

            # Validazione ed istanziazione tramite Pydantic
            record = IntegratedEventRecord(**cleaned_dict)
            integrated_records.append(record)

        return integrated_records