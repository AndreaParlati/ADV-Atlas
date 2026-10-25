"""
Configurazioni globali e soglie di sicurezza per la Phase 4.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyThresholds:
    """Soglie limite di operabilità e sicurezza (Kytariolou & Themelis, 2022)."""
    MAX_HEAVE_M: float = 3.5          # Massimo sussulto significativo (m)
    MAX_ROLL_DEG: float = 5.0         # Massimo rollio significativo (deg)
    MIN_ICE_CLEARANCE_NM: float = 15.0 # Distanza di rispetto dal limite ghiacci (NM)


@dataclass(frozen=True)
class ScenarioConfig:
    """Parametri per la generazione discreta delle manovre evasive."""
    # Variazioni di velocità rispetto alla nominale (Speed Reduction)
    SPEED_FACTORS: tuple = (0.95, 0.90, 0.85, 0.80, 0.75)
    
    # Offsets laterali in miglia nautiche (Spatial Detour: tribordo e babordo)
    DETOUR_OFFSETS_NM: tuple = (15.0, -15.0, 30.0, -30.0, 45.0, -45.0)
    
    # Durata stimata dell'attraversamento della finestra locale dell'evento (ore)
    EVENT_WINDOW_HOURS: float = 6.0