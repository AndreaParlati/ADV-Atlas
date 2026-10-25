"""
Phase 5 - ADV Calculator (adv_calculator.py)
Calcolo analitico dell'ADV Score e segmentazione di rotta.
"""

from typing import List
from .models import IntegratedEventRecord, ADVAtlasRecord
from .config import ADVConfig, default_config


class ADVCalculator:
    """
    Fornisce i metodi per la formulazione matematica del valore aggiunto satellitare (ADV Score).
    """

    def __init__(self, config: ADVConfig = default_config):
        self.config = config

    def compute_adv_score(self, record: IntegratedEventRecord) -> float:
        """
        Formulazione dell'ADV Score:
        ADV = w_s * SafetyRestored + w_b * ForecastBiasNorm - w_f * DeltaFOCNorm
        Se non vi è coincidenza satellitare, l'ADV Score è 0.0.
        """
        if not record.coincidence_flag:
            return 0.0

        # Componente Sicurezza (0.0 oppure 1.0)
        safety_term = 1.0 if record.safety_restored else 0.0

        # Componente Bias di previsione normalizzato [0, 1]
        bias_norm = min(max(record.forecast_bias / self.config.MAX_EXPECTED_BIAS_M, 0.0), 1.0)

        # Componente Penalità Consumi (Delta FOC) normalizzata [0, 1]
        foc_norm = min(max(record.delta_foc_ton / self.config.MAX_EXPECTED_DELTA_FOC, 0.0), 1.0)

        # ADV Score ponderato
        score = (
            self.config.WEIGHT_SAFETY * safety_term
            + self.config.WEIGHT_FORECAST_BIAS * bias_norm
            - self.config.WEIGHT_FUEL_PENALTY * foc_norm
        )

        return round(float(max(score, 0.0)), 4)

    def process_records(self, records: List[IntegratedEventRecord]) -> List[ADVAtlasRecord]:
        """
        Calcola l'ADV score per ogni record mantenendo la struttura valida.
        Note: Le metriche di operatività verranno rifinite da OperationalEvaluator.
        """
        atlas_records = []
        for rec in records:
            score = self.compute_adv_score(rec)
            atlas_rec = ADVAtlasRecord(
                **rec.model_dump(),
                adv_score=score,
                is_actionable=False,  # default provvisorio
                operational_status="Pending"
            )
            atlas_records.append(atlas_rec)
        return atlas_records