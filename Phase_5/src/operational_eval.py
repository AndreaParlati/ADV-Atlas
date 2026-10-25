"""
Phase 5 - Operational Evaluator (operational_eval.py)
Valutazione della latenza temporale e classificazione di operatività.
"""

from typing import List
from .models import ADVAtlasRecord
from .config import ADVConfig, default_config


class OperationalEvaluator:
    """
    Valuta la latenza di acquisizione satellitare per distinguere informazioni
    azionabili in tempo reale a bordo da analisi puramente diagnostiche/retrospettive.
    """

    def __init__(self, config: ADVConfig = default_config):
        self.config = config

    def evaluate_actionability(self, records: List[ADVAtlasRecord]) -> List[ADVAtlasRecord]:
        """
        Applica i criteri di latenza e coincidenza per classificare lo stato operativo del segmento.
        """
        for record in records:
            if not record.coincidence_flag:
                record.is_actionable = False
                record.operational_status = "Blind Corridor"
            else:
                if record.acquisition_latency_hours <= self.config.MAX_ACTIONABLE_LATENCY_HOURS:
                    record.is_actionable = True
                    record.operational_status = "Actionable"
                else:
                    record.is_actionable = False
                    record.operational_status = "Retrospective-only"
        return records