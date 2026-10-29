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
from Phase_1.adv_core.resistance import holtrop_mennen_resistance, wind_resistance
from Phase_1.adv_core.propulsion import leg_performance

# Importazione dai moduli granulari di adv_core creati in Phase 1
from phase_1.adv_core.resistance import holtrop_mennen_resistance, wind_resistance
from phase_1.adv_core.propulsion import leg_performance


class CostEvaluator:
    def __init__(self, config: ScenarioConfig = ScenarioConfig()):
        self.config = config

    def calculate_cost(self, candidate: CandidateScenario, event: EventRecord) -> CostResult:
        """
        Calcola il consumo di carburante (FOC) e la potenza utilizzando i modelli fisici di Phase 1.
        """
        # Dati geometrici di riferimento della nave
        particulars = {'length': 120.0, 'wetted_surface': 1400.0}
        
        # 1. Calcolo resistenza in acque calme (Holtrop-Mennen)
        r_calm = holtrop_mennen_resistance(candidate.applied_speed_kn, particulars)
        
        # 2. Calcolo resistenza al vento apparente
        r_wind = wind_resistance(
            v_true=event.wind_speed,
            angle_true=event.wind_dir,
            v_ship=candidate.applied_speed_kn,
            ship_heading=event.ship_heading,
            superstructure_area=150.0
        )
        
        total_resistance = r_calm + r_wind
        
        # 3. Prestazioni propulsive e consumo orario di carburante
        engine_params = {'total_efficiency': 0.65, 'base_sfoc': 185.0}
        perf = leg_performance(total_resistance, candidate.applied_speed_kn, engine_params)
        
        required_power_kw = round(perf['power_brake_kw'], 1)
        
        # Consumo totale stimato sulla finestra temporale dell'evento (es. 6 ore)
        foc_kg = perf['fuel_rate_kg_h'] * self.config.EVENT_WINDOW_HOURS
        foc_ton = round(foc_kg / 1000.0, 2)
        delta_foc_ton = round(foc_ton - event.baseline_foc_ton, 2)

        return CostResult(
            foc_ton=foc_ton,
            delta_foc_ton=delta_foc_ton,
            required_power_kw=required_power_kw
        )