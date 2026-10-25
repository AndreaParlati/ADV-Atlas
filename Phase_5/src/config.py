"""
Phase 5 - Configuration (config.py)
Parametri di calcolo, pesi per l'ADV Score e soglie operative.
"""

from pydantic import BaseModel


class ADVConfig(BaseModel):
    """
    Configurazione dei pesi e parametri operativi per la Fase 5.
    """
    # Pesi per la formula ADV Score = w_s * SafetyRestored + w_b * ForecastBiasNorm - w_f * DeltaFOCNorm
    WEIGHT_SAFETY: float = 0.50          # Peso del ripristino della sicurezza idrodinamica/iceberg
    WEIGHT_FORECAST_BIAS: float = 0.35   # Peso legato all'ampiezza dell'errore di previsione CMEMS
    WEIGHT_FUEL_PENALTY: float = 0.15    # Peso applicato al costo economico/consumi (Delta FOC)

    # Parametri di normalizzazione
    MAX_EXPECTED_BIAS_M: float = 5.0     # Valore di bias massimo atteso per normalizzazione (m)
    MAX_EXPECTED_DELTA_FOC: float = 15.0 # Penalità consumo massima attesa per normalizzazione (ton)

    # Soglia di latenza massima per definire l'azionalità in real-time (ore)
    MAX_ACTIONABLE_LATENCY_HOURS: float = 3.0

    # Nomi convenzionali per i corridoi navali
    LEG_MID_ATLANTIC: str = "Mid-Atlantic Leg"
    LEG_GRAND_BANKS: str = "Grand Banks Approach"


# Istanza predefinita di configurazione
default_config = ADVConfig()