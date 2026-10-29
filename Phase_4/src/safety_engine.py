"""
Motore di verifica della sicurezza idrodinamica (Seakeeping) e distanze dai ghiacci
"""

from pathlib import Path
import sys

# Aggiunge dinamicamente la cartella adv_core al sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
adv_core_dir = root_dir / "Phase_1" / "adv_core"
if str(adv_core_dir) not in sys.path:
    sys.path.append(str(adv_core_dir))

from typing import Optional
import numpy as np
from config import SafetyThresholds
from models import EventRecord, CandidateScenario, SafetyCheckResult, HazardType

# Importazione dai moduli granulari di adv_core
from oceanography import speed_through_water, jonswap_spectrum
from seakeeping import motion_statistics


class SafetyEngine:
    def __init__(self, thresholds: SafetyThresholds = SafetyThresholds()):
        self.thresholds = thresholds

    def evaluate_safety(self, candidate: CandidateScenario, event: EventRecord) -> SafetyCheckResult:
        """
        Valuta i moti della nave utilizzando STW, spettri d'onda JONSWAP e statistiche spettrali.
        """
        applied_speed_kn = candidate.applied_speed_kn
        ship_heading = getattr(event, 'ship_heading', 0.0)

        # 1. Calcolo Speed Through Water (STW) rispetto alle correnti
        stw_knots = speed_through_water(
            sog=applied_speed_kn,
            current_speed=getattr(event, 'current_speed', 0.0),
            current_dir=getattr(event, 'current_dir', 0.0),
            ship_heading=ship_heading
        )

        # 2. Generazione spettro energetico JONSWAP
        hs = getattr(event, 'forecast_hs', 3.0)
        tp = getattr(event, 'forecast_tp', 10.0)
        frequencies = np.linspace(0.1, 2.0, 50)
        wave_spec = jonswap_spectrum(frequencies, hs=hs, tp=tp)

        # 3. Statistiche dei moti (Heave e Roll tramite RAO)
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

        # 5. Verifica complessiva delle soglie
        is_safe = (
            heave_m <= self.thresholds.MAX_HEAVE_M and
            roll_deg <= self.thresholds.MAX_ROLL_DEG and
            ice_safe
        )

        # Calcolo dei margini recuperati
        delta_heave = event.baseline_heave_m - heave_m
        delta_roll = event.baseline_roll_deg - roll_deg

        heave_margin_rec = round(delta_heave + max(0.0, self.thresholds.MAX_HEAVE_M - heave_m), 2)
        roll_margin_rec = round(delta_roll + max(0.0, self.thresholds.MAX_ROLL_DEG - roll_deg), 2)
        
        ice_margin_rec = None
        if ice_clearance is not None and event.iceberg_distance_nm is not None:
            ice_margin_rec = round(ice_clearance - event.iceberg_distance_nm, 2)

        return SafetyCheckResult(
            heave_m=heave_m,
            roll_deg=roll_deg,
            ice_clearance_nm=ice_clearance,
            is_safe=is_safe,
            heave_margin_recovered_m=heave_margin_rec,
            roll_margin_recovered_deg=roll_margin_rec,
            ice_clearance_margin_nm=ice_margin_rec
        )