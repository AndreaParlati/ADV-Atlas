"""
Motore di verifica della sicurezza idrodinamica (Seakeeping) e distanze dai ghiacci.
"""
from typing import Optional
from config import SafetyThresholds
from models import EventRecord, CandidateScenario, SafetyCheckResult, HazardType


class SafetyEngine:
    def __init__(self, thresholds: SafetyThresholds = SafetyThresholds()):
        self.thresholds = thresholds

    def evaluate_safety(self, candidate: CandidateScenario, event: EventRecord) -> SafetyCheckResult:
        """
        Calcola i moti della nave e la clearance dagli iceberg, verificando le soglie.
        In un'implementazione reale, qui si invocano le funzioni idrodinamiche di Phase 1.
        """
        # Calcolo semplificato/proxy dei moti basato sulla velocità e angolo relativo
        speed_ratio = candidate.applied_speed_kn / event.ship_speed_kn
        
        # Riducendo la velocità o deviando l'angolo si attenuano i moti
        heave_m = round(event.baseline_heave_m * (speed_ratio ** 1.5), 2)
        roll_deg = round(event.baseline_roll_deg * speed_ratio, 2)

        # Check Iceberg (Modulo A)
        ice_clearance: Optional[float] = None
        ice_safe = True
        if event.hazard_type == HazardType.ICEBERG and event.iceberg_distance_nm is not None:
            # Una deviazione incrementa la distanza dal pericolo
            ice_clearance = event.iceberg_distance_nm + abs(candidate.applied_detour_nm)
            ice_safe = ice_clearance >= self.thresholds.MIN_ICE_CLEARANCE_NM

        # Verifica complessiva delle soglie
        is_safe = (
            heave_m <= self.thresholds.MAX_HEAVE_M and
            roll_deg <= self.thresholds.MAX_ROLL_DEG and
            ice_safe
        )

        # --- CALCOLO DEI MARGINI RECUPERATI ---
        delta_heave = event.baseline_heave_m - heave_m
        delta_roll = event.baseline_roll_deg - roll_deg

        # 2. Margine recuperato (riduzione del moto + headroom di sicurezza rispetto al limite massimo)
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