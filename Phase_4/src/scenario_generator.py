"""
Generatore discreto di manovre evasive locali (Speed Reduction & Spatial Detour).
"""
from typing import List
from config import ScenarioConfig
from models import EventRecord, CandidateScenario, HazardType


class ScenarioGenerator:
    def __init__(self, config: ScenarioConfig = ScenarioConfig()):
        self.config = config

    def generate_candidates(self, event: EventRecord) -> List[CandidateScenario]:
        """Genera lo scenario baseline e tutte le manovre candidate ammissibili."""
        candidates = []

        # 0. Scenario Baseline (Nessun intervento)
        candidates.append(
            CandidateScenario(
                scenario_id="baseline",
                strategy_type="Baseline",
                applied_speed_kn=event.ship_speed_kn,
                applied_detour_nm=0.0
            )
        )

        # 1. Strategia: Speed Reduction
        for idx, factor in enumerate(self.config.SPEED_FACTORS, 1):
            new_speed = round(event.ship_speed_kn * factor, 2)
            candidates.append(
                CandidateScenario(
                    scenario_id=f"speed_red_{idx}",
                    strategy_type="Speed_Reduction",
                    applied_speed_kn=new_speed,
                    applied_detour_nm=0.0
                )
            )

        # 2. Strategia: Spatial Detour
        for idx, offset in enumerate(self.config.DETOUR_OFFSETS_NM, 1):
            candidates.append(
                CandidateScenario(
                    scenario_id=f"detour_{idx}",
                    strategy_type="Spatial_Detour",
                    applied_speed_kn=event.ship_speed_kn,
                    applied_detour_nm=offset,
                    heading_offset_deg=5.0 if offset > 0 else -5.0
                )
            )

        return candidates