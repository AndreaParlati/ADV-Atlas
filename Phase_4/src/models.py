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
    """Rappresenta la riga di input letta dal CSV generato dalla Phase 3."""
    event_id: str
    timestamp: str
    latitude: float
    longitude: float
    route_leg: str
    hazard_type: HazardType = HazardType.ROGUE_WAVE
    
    # Meteo-marino forecast (CMEMS)
    forecast_hs: float
    forecast_tp: float
    forecast_wave_dir: float
    wind_speed: float
    wind_dir: float
    current_speed: float
    current_dir: float
    
    # Rilevamento Satellite (Observed)
    satellite_type: str
    satellite_hs: float
    satellite_hmax: float
    
    # Dati Iceberg (Modulo A)
    iceberg_distance_nm: Optional[float] = None
    
    # Baseline Nave
    ship_speed_kn: float
    ship_heading: float
    relative_wave_heading: float
    baseline_foc_ton: float
    baseline_heave_m: float
    baseline_roll_deg: float


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