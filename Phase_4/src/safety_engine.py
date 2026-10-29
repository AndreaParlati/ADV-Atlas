"""
Motore di verifica della sicurezza idrodinamica (Seakeeping) e distanze dai ghiacci
integrato con i moduli oceanografici e di seakeeping della Phase 1 (adv_core).
"""
from typing import Optional
import numpy as np
from config import SafetyThresholds
from models import EventRecord, CandidateScenario, SafetyCheckResult, HazardType
from Phase_1.adv_core.oceanography import speed_through_water, jonswap_spectrum
from Phase_1.adv_core.seakeeping import motion_statistics


class SafetyEngine:
    def __init__(self, thresholds: SafetyThresholds = SafetyThresholds()):
        self.thresholds = thresholds

    def evaluate_safety(self, candidate: CandidateScenario, event: EventRecord) -> SafetyCheckResult:
        """
        Calcola i moti effettivi della nave basandosi su spettri d'onda JONSWAP e RAO.
        """
        # 1. Calcolo Speed Through Water (STW) effettivo rispetto alle correnti
        stw_knots = speed_through_water(
            sog=candidate.applied_speed_kn,
            current_speed=event.current_speed,
            current_dir=event.current_dir,
            ship_heading=event.ship_heading
        )
        
        # 2. Generazione spettro energetico JONSWAP
        frequencies = np.linspace(0.1, 2.0, 50)
        wave_spec = jonswap_spectrum(frequencies, hs=event.forecast_hs, tp=event.forecast_tp)
        
        # 3. Valutazione statistica dei moti (Heave e Roll tramite RAO di risposta)
        heave_rao = np.ones_like(frequencies) * 0.4
        roll_rao = np.ones_like(frequencies) * 1.2
        
        heave_stats = motion_statistics(heave_rao, wave_spec, frequencies)
        roll_stats = motion_statistics(roll_rao, wave_spec, frequencies)
        
        speed_ratio = stw_knots / max(event.ship_speed_kn, 0.1)
        heave_m = round(heave_stats['significant_response'] * (speed_ratio ** 0.8), 2)
        roll_deg = round(roll_stats['significant_response'] * speed_ratio, 2)

        # 4. Verifica Clearance Iceberg (Modulo A)
        ice_clearance: Optional[float] = None
        ice_safe = True
        if event.hazard_type == HazardType.ICEBERG and event.iceberg_distance_nm is not None:
            ice_clearance = event.iceberg_distance_nm + abs(candidate.applied_detour_nm)
            ice_safe = ice_clearance >= self.thresholds.MIN_ICE_CLEARANCE_NM

        # 5. Verifica complessiva delle soglie limite
        is_safe = (
            heave_m <= self.thresholds.MAX_HEAVE_M and
            roll_deg <= self.thresholds.MAX_ROLL_DEG and
            ice_safe
        )

        return SafetyCheckResult(
            heave_m=heave_m,
            roll_deg=roll_deg,
            ice_clearance_nm=ice_clearance,
            is_safe=is_safe
        )