"""
Motore per il calcolo della potenza richiesta, dello SFOC e della penalità di carburante (Delta FOC).
"""
from config import ScenarioConfig
from models import EventRecord, CandidateScenario, CostResult


class CostEvaluator:
    def __init__(self, config: ScenarioConfig = ScenarioConfig()):
        self.config = config

    def calculate_cost(self, candidate: CandidateScenario, event: EventRecord) -> CostResult:
        """
        Calcola il consumo di carburante (FOC) della manovra e la differenza rispetto alla baseline.
        In un'implementazione reale, invoca le equazioni propulsive 1-18 della Phase 1.
        """
        # La potenza varia con il cubo della velocità (Legge dell'elica) + costo deviazione rotta
        speed_ratio = candidate.applied_speed_kn / event.ship_speed_kn
        distance_factor = 1.0 + (abs(candidate.applied_detour_nm) / 200.0)
        
        # Calcolo FOC sulla finestra temporale locale
        foc_ton = round(event.baseline_foc_ton * (speed_ratio ** 3) * distance_factor, 2)
        delta_foc_ton = round(foc_ton - event.baseline_foc_ton, 2)
        
        # Potenza approssimata in kW (Motore MAN B&W 8K90MC-C)
        required_power_kw = round(37000.0 * (speed_ratio ** 3), 1)

        return CostResult(
            foc_ton=foc_ton,
            delta_foc_ton=delta_foc_ton,
            required_power_kw=required_power_kw
        )