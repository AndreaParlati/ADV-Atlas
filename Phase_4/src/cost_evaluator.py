"""
Motore per il calcolo della potenza richiesta, dello SFOC e della penalità di carburante (Delta FOC).
Aggiornato con i moduli idrodinamici e propulsivi di Phase 1 (adv_fuel_model).
"""

from pathlib import Path
import sys

# Aggiunge dinamicamente la cartella Phase_1 al sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
phase1_dir = root_dir / "Phase_1"
if str(phase1_dir) not in sys.path:
    sys.path.append(str(phase1_dir))

from typing import Optional
from config import ScenarioConfig
from models import EventRecord, CandidateScenario, CostResult
from adv_fuel_model import ShipParticulars, leg_performance


class CostEvaluator:
    def __init__(self, config: ScenarioConfig = ScenarioConfig(), ship_particulars: Optional[ShipParticulars] = None):
        self.config = config
        self.ship_particulars = ship_particulars or ShipParticulars()

    def calculate_cost(self, candidate: CandidateScenario, event: EventRecord) -> CostResult:
        """
        Calcola il consumo di carburante (FOC) della manovra e la differenza rispetto alla baseline,
        invocando le equazioni propulsive e idrodinamiche di Phase 1 (adv_fuel_model).
        """
        applied_speed_kn = candidate.applied_speed_kn
        applied_heading_deg = getattr(event, 'ship_heading_deg', 0.0) + getattr(candidate, 'applied_detour_deg', 0.0)
        
        # Recupero dei parametri ambientali dall'evento
        hs = getattr(event, 'hs_m', 3.0)
        t0 = getattr(event, 't0_s', 10.0)
        wave_from_deg = getattr(event, 'wave_from_deg', 0.0)
        wind_speed = getattr(event, 'wind_speed_ms', 10.0)
        wind_from_deg = getattr(event, 'wind_from_deg', 0.0)
        current_speed = getattr(event, 'current_speed_ms', 0.0)
        current_dir_to_deg = getattr(event, 'current_dir_to_deg', 0.0)

        # Invocazione del modello di performance e consumo di Phase 1
        perf = leg_performance(
            sog_kn=applied_speed_kn,
            heading_deg=applied_heading_deg,
            ship=self.ship_particulars,
            Hs=hs,
            T0=t0,
            wave_from_deg=wave_from_deg,
            wind_speed=wind_speed,
            wind_from_deg=wind_from_deg,
            current_speed=current_speed,
            current_dir_to_deg=current_dir_to_deg
        )

        speed_ratio = applied_speed_kn / event.ship_speed_kn if event.ship_speed_kn > 0 else 1.0
        distance_factor = 1.0 + (abs(candidate.applied_detour_nm) / 200.0)
        
        # Estrazione di potenza e consumo dai risultati del modello fisico (con fallback di sicurezza)
        required_power_kw = round(perf.get("power_kw", perf.get("required_power_kw", 37000.0 * (speed_ratio ** 3))), 1)
        
        base_foc = perf.get("foc_ton", event.baseline_foc_ton * (speed_ratio ** 3))
        foc_ton = round(base_foc * distance_factor, 2)
        delta_foc_ton = round(foc_ton - event.baseline_foc_ton, 2)

        return CostResult(
            foc_ton=foc_ton,
            delta_foc_ton=delta_foc_ton,
            required_power_kw=required_power_kw
        )