"""
Phase 5 - Atlas Generator (atlas_generator.py)
Esportazione del dataset ADV Atlas (CSV/Parquet) e generazione delle metriche di sintesi JSON.
"""

import os
import json
from typing import List, Dict, Any
import pandas as pd
from .models import ADVAtlasRecord


class AtlasGenerator:
    """
    Genera gli output finali della Fase 5: il dataset ADV Atlas ed il report sintetico.
    """

    @staticmethod
    def export_dataset(records: List[ADVAtlasRecord], csv_path: str, parquet_path: str) -> None:
        """
        Esporta il dataset completo nei formati tabellari standard .csv e .parquet.
        """
        dicts = [r.model_dump() for r in records]
        df = pd.DataFrame(dicts)

        # Creazione cartelle se non esistenti
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)

        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)

    @staticmethod
    def generate_summary(records: List[ADVAtlasRecord], summary_json_path: str) -> Dict[str, Any]:
        """
        Calcola le metriche aggregate di corridoio e genera il report JSON sintetico.
        """
        dicts = [r.model_dump() for r in records]
        df = pd.DataFrame(dicts)

        if df.empty:
            summary = {}
        else:
            total_events = len(df)
            coincident_events = int(df["coincidence_flag"].sum())
            actionable_events = int(df["is_actionable"].sum())
            
            # Aggregazione per leg di navigazione
            leg_summary = {}
            for leg_name, group in df.groupby("route_leg"):
                leg_total = len(group)
                leg_coincidents = int(group["coincidence_flag"].sum())
                leg_actionable = int(group["is_actionable"].sum())
                
                leg_summary[leg_name] = {
                    "total_events": leg_total,
                    "coincidence_rate": round(leg_coincidents / leg_total if leg_total > 0 else 0.0, 4),
                    "actionable_rate": round(leg_actionable / leg_total if leg_total > 0 else 0.0, 4),
                    "mean_adv_score": round(float(group["adv_score"].mean()), 4),
                    "mean_delta_foc_ton": round(float(group["delta_foc_ton"].mean()), 4),
                    "blind_corridor_flag": bool((leg_coincidents / leg_total) < 0.2 if leg_total > 0 else True)
                }

            summary = {
                "global_metrics": {
                    "total_events_analyzed": total_events,
                    "coincidence_rate_global": round(coincident_events / total_events if total_events > 0 else 0.0, 4),
                    "actionable_rate_global": round(actionable_events / total_events if total_events > 0 else 0.0, 4),
                    "mean_adv_score_global": round(float(df["adv_score"].mean()), 4),
                    "total_delta_foc_ton": round(float(df["delta_foc_ton"].sum()), 2),
                    "safety_restored_count": int(df["safety_restored"].sum())
                },
                "legs_breakdown": leg_summary
            }

        # Salvataggio file JSON
        os.makedirs(os.path.dirname(summary_json_path), exist_ok=True)
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=4, ensure_ascii=False)

        return summary