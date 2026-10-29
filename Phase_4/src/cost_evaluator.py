"""
Motore per il calcolo della potenza richiesta e del consumo di carburante (FOC).
"""

from pathlib import Path
import sys

# Aggiunge dinamicamente la root al sys.path per importare adv_core
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from typing import Optional
from config import ScenarioConfig
from models import EventRecord, CandidateScenario, CostResult

# Importazione dai moduli granulari di adv_core creati in Phase 1
from phase_1.adv_core.resistance import holtrop_mennen_resistance, wind_resistance
from phase_1.adv_core.propulsion import leg_performance


class CostEvaluator:
    def __init__(self, config: ScenarioConfig = ScenarioConfig()):
        self.config = config

    def calculate_cost(self, candidate: CandidateScenario, event: EventRecord) -> CostResult:
        """
        Calcola il consumo di carburante e la potenza usando le funzioni di adv_core.
        """
        applied_speed_kn = candidate.applied_speed_kn
        ship_heading = getattr(event, 'ship_heading', 0.0)
        
        # Caratteristiche geometriche di base della nave
        particulars = {'length': 120.0, 'wetted_surface': 1400.0}

        # 1. Calcolo resistenza in acque calme (Holtrop-Mennen)
        r_calm = holtrop_mennen_resistance(applied_speed_kn, particulars)
        
        # 2. Calcolo resistenza al vento apparente
        r_wind = wind_resistance(
            v_true=getattr(event, 'wind_speed', 10.0),
            angle_true=getattr(event, 'wind_dir', 0.0),
            v_ship=applied_speed_kn,
            ship_heading=ship_heading,
            superstructure_area=150.0
        )
        
        total_resistance = r_calm + r_wind

        # 3. Calcolo prestazioni propulsive e consumo orario
        engine_params = {'total_efficiency': 0.65, 'base_sfoc': 185.0}
        perf = leg_performance(total_resistance, applied_speed_kn, engine_params)

        required_power_kw = round(perf['power_brake_kw'], 1)
        
        # Calcolo FOC sulla finestra temporale dell'evento
        foc_kg = perf['fuel_rate_kg_h'] * self.config.EVENT_WINDOW_HOURS
        distance_factor = 1.0 + (abs(candidate.applied_detour_nm) / 200.0)
        
        foc_ton = round((foc_kg / 1000.0) * distance_factor, 2)
        delta_foc_ton = round(foc_ton - event.baseline_foc_ton, 2)

        return CostResult(
            foc_ton=foc_ton,
            delta_foc_ton=delta_foc_ton,
            required_power_kw=required_power_kw
        )