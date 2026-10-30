"""
Definizione dei modelli dati fortemente tipizzati tramite Pydantic.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class HazardType(str, Enum):
    ROGUE_WAVE = "rogue_wave"
    ICEBERG = "iceberg"


class EventRecord(BaseModel):
    """Rappresenta la riga di input letta dal dataset unificato della Phase 3."""
    event_id: str
    timestamp: str
    latitude: float
    longitude: float
    route_leg: Optional[str] = "Grand Banks"
    hazard_type: HazardType = HazardType.ROGUE_WAVE
    
    # Meteo-marino forecast (CMEMS / Phase 3)
    forecast_hs: float
    forecast_tp: float
    forecast_wave_dir: float = 250.0
    wind_speed: float = 15.0
    wind_dir: float = 240.0
    current_speed: float = 0.3
    current_dir: float = 100.0
    
    # Campi di Coincidenza Satellitare (Fase 3)
    sar_coincident: bool = False
    alt_coincident: bool = False
    any_coincident: bool = False
    hs_altimeter: Optional[float] = None
    
    # Dati Iceberg (Modulo A)
    iceberg_distance_nm: Optional[float] = None
    
    # Baseline Nave
    ship_speed_kn: float = 16.0
    ship_heading: float = 280.0
    relative_wave_heading: float = 30.0
    baseline_foc_ton: float = 14.0
    baseline_heave_m: float = 4.1
    baseline_roll_deg: float = 6.2


class CandidateScenario(BaseModel):
    """Rappresenta una singola manovra evasiva candidata."""
    scenario_id: str
    strategy_type: str  # "Baseline", "Speed_Reduction", "Spatial_Detour"
    applied_speed_kn: float
    applied_detour_nm: float
    heading_offset_deg: float = 0.0


class SafetyCheckResult(BaseModel):
    """Risultato delle verifiche di sicurezza idrodinamica e distanze."""
    heave_m: float
    roll_deg: float
    ice_clearance_nm: Optional[float] = None
    is_safe: bool
    heave_margin_recovered_m: float = 0.0
    roll_margin_recovered_deg: float = 0.0
    ice_clearance_margin_nm: Optional[float] = None


class CostResult(BaseModel):
    """Risultato del calcolo dei consumi di carburante."""
    foc_ton: float
    delta_foc_ton: float
    required_power_kw: float


class ADVRecord(BaseModel):
    """Record finale salvato nel dataset di output per la Phase 5."""
    event_id: str
    hazard_type: HazardType
    optimal_strategy: str
    applied_speed_kn: float
    applied_detour_nm: float
    reroute_foc_ton: float
    delta_foc_ton: float
    reroute_heave_m: float
    reroute_roll_deg: float
    delta_heave_m: float
    delta_roll_deg: float
    heave_margin_recovered_m: float      
    roll_margin_recovered_deg: float     
    ice_clearance_margin_nm: Optional[float] = None
    safety_margin_score: float           # Indice normalizzato complessivo di sicurezza recuperata (0-100%)
    safety_restored: bool