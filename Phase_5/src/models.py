"""
Phase 5 - Models (models.py)
Definizione dei modelli Pydantic per la Phase 5 dell'ADV Atlas.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class IntegratedEventRecord(BaseModel):
    """
    Rappresenta il record unificato risultante dalla Data Fusion tra Phase 3 e Phase 4.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(..., description="Identificativo univoco dell'evento")
    route_leg: str = Field(..., description="Leg di navigazione (es. Mid-Atlantic, Grand Banks Approach)")
    lat: float = Field(..., description="Latitudine del punto/segmento")
    lon: float = Field(..., description="Longitudine del punto/segmento")
    
    # Parametri da Phase 3 (Satellite & Model Coincidence)
    coincidence_flag: bool = Field(..., description="Flag di coincidenza spazio-temporale con sorvolo satellitare")
    satellite_type: Optional[str] = Field(None, description="Tipo di sensore (Sentinel-1 SAR, Altimeter L3/L4, Iceberg Radar)")
    forecast_hs: float = Field(..., description="Altezza significativa dell'onda stimata dal modello CMEMS (m)")
    satellite_hs: Optional[float] = Field(None, description="Altezza dell'onda (o Hmax equivalente) osservata da satellite (m)")
    forecast_bias: float = Field(0.0, description="Bias di sottostima del modello: max(0, satellite_hs - forecast_hs)")
    acquisition_latency_hours: float = Field(..., description="Latenza di disponibilità del dato satellitare in ore")
    
    # Parametri da Phase 4 (Hydrodynamic & Re-Routing Added Value)
    hazard_type: str = Field("rough_seas", description="Tipologia di rischio (rough_seas, rogue_wave, iceberg)")
    optimal_strategy: str = Field("direct", description="Strategia applicata in Phase 4 (direct, speed_reduction, detour)")
    applied_speed_kn: float = Field(..., description="Velocità finale applicata sul segmento (kn)")
    applied_detour_nm: float = Field(0.0, description="Miglia nautiche di deviazione rotta applicate (nm)")
    delta_foc_ton: float = Field(0.0, description="Variazione/penalità di consumo carburante in tonnellate (Delta FOC)")
    safety_restored: bool = Field(False, description="Flag che indica se le soglie di sicurezza (heave/roll/iceberg) sono state ripristinate")


class ADVAtlasRecord(IntegratedEventRecord):
    """
    Estende il record integrato con l'ADV Score calcolato e le metriche di operatività.
    """
    adv_score: float = Field(..., description="Punteggio Added Detection Value (ADV) calcolato per il segmento")
    is_actionable: bool = Field(..., description="True se la latenza satellitare consente una manovra in real-time")
    operational_status: str = Field(..., description="Classificazione operativa: 'Actionable', 'Retrospective-only', 'Blind Corridor'")