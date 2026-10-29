"""
Motore di verifica della sicurezza idrodinamica (Seakeeping) e distanze dai ghiacci.
Aggiornato con i moduli idrodinamici e di performance di Phase 1 (adv_fuel_model).
"""
from pathlib import Path
import sys

# Aggiunge dinamicamente la cartella Phase_1 al sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
phase1_dir = root_dir / "Phase_1"
if str(phase1_dir) not in sys.path:
    sys.path.append(str(phase1_dir))

from typing import Optional
from config import SafetyThresholds
from models import EventRecord, CandidateScenario, SafetyCheckResult, HazardType
from adv_fuel_model import ShipParticulars, leg_performance, wave_relative_heading


class SafetyEngine:
    def __init__(self, thresholds: SafetyThresholds = SafetyThresholds(), ship_particulars: Optional[ShipParticulars] = None):
        self.thresholds = thresholds
        self.ship_particulars = ship_particulars or ShipParticulars()

    def evaluate_safety(self, candidate: CandidateScenario, event: EventRecord) -> SafetyCheckResult:
        """
        Calcola i moti della nave, la risposta idrodinamica e la clearance dagli iceberg,
        verificando le soglie di sicurezza e la fattibilità propulsiva di Phase 1.
        """
        # Estrazione e calcolo delle condizioni operative applicate dal candidato
        applied_speed_kn = candidate.applied_speed_kn
        applied_heading_deg = getattr(event, 'ship_heading_deg', 0.0) + getattr(candidate, 'applied_detour_deg', 0.0)
        
        # Recupero dei parametri ambientali dall'evento (con fallback a default standard)
        hs = getattr(event, 'hs_m', 3.0)
        t0 = getattr(event, 't0_s', 10.0)
        wave_from_deg = getattr(event, 'wave_from_deg', 0.0)
        wind_speed = getattr(event, 'wind_speed_ms', 10.0)
        wind_from_deg = getattr(event, 'wind_from_deg', 0.0)
        current_speed = getattr(event, 'current_speed_ms', 0.0)
        current_dir_to_deg = getattr(event, 'current_dir_to_deg', 0.0)

        # Invocazione del modello di performance e resistenza di Phase 1 (adv_fuel_model)
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

        # Calcolo dei moti basato sulla velocità e sull'influenza rigorosa d'onda di Phase 1
        speed_ratio = applied_speed_kn / event.ship_speed_kn if event.ship_speed_kn > 0 else 1.0
        mu = perf["mu_deg"]
        
        # Fattore di correzione basato sull'angolo di incidenza delle onde (head seas vs following seas)
        heading_factor = 1.0 + 0.2 * (1.0 - abs(mu - 180.0) / 180.0)

        heave_m = round(event.baseline_heave_m * (speed_ratio ** 1.5) * heading_factor, 2)
        roll_deg = round(event.baseline_roll_deg * speed_ratio * (1.0 + 0.1 * (perf["R_wave_kN"] / max(perf["R_total_kN"], 1.0))), 2)

        # Check Iceberg (Modulo A)
        ice_clearance: Optional[float] = None
        ice_safe = True
        if event.hazard_type == HazardType.ICEBERG and event.iceberg_distance_nm is not None:
            ice_clearance = event.iceberg_distance_nm + abs(candidate.applied_detour_nm)
            ice_safe = ice_clearance >= self.thresholds.MIN_ICE_CLEARANCE_NM

        # Verifica complessiva delle soglie (inclusa la fattibilità del carico motore calcolata in Phase 1)
        is_safe = (
            heave_m <= self.thresholds.MAX_HEAVE_M and
            roll_deg <= self.thresholds.MAX_ROLL_DEG and
            ice_safe and
            perf["feasible"]
        )

        # --- CALCOLO DEI MARGINI RECUPERATI ---
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