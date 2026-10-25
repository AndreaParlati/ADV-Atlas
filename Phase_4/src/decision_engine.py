"""
Logica decisionale per la selezione costi-benefici e la generazione del record ADV.
"""
from typing import List, Tuple
from models import EventRecord, CandidateScenario, SafetyCheckResult, CostResult, ADVRecord


class DecisionEngine:
    @staticmethod
    def select_best_option(
        event: EventRecord,
        evaluations: List[Tuple[CandidateScenario, SafetyCheckResult, CostResult]]
    ) -> ADVRecord:
        """Filtra gli scenari sicuri e seleziona quello che minimizza il Delta FOC."""
        # 1. Filtra solo le manovre che soddisfano i vincoli di sicurezza
        safe_evals = [e for e in evaluations if e[1].is_safe]

        if safe_evals:
            # Seleziona la manovra sicura a minor consumo (min Delta FOC)
            best_cand, best_safety, best_cost = min(safe_evals, key=lambda x: x[2].delta_foc_ton)
            safety_restored = True
        else:
            # Fallback (Best-Effort): seleziona la manovra che minimizza i moti
            best_cand, best_safety, best_cost = min(evaluations, key=lambda x: x[1].heave_m + x[1].roll_deg)
            safety_restored = False

        # Calcolo dei delta rispetto alla baseline originaria
        delta_heave = round(event.baseline_heave_m - best_safety.heave_m, 2)
        delta_roll = round(event.baseline_roll_deg - best_safety.roll_deg, 2)

        return ADVRecord(
            event_id=event.event_id,
            hazard_type=event.hazard_type,
            optimal_strategy=best_cand.strategy_type,
            applied_speed_kn=best_cand.applied_speed_kn,
            applied_detour_nm=best_cand.applied_detour_nm,
            reroute_foc_ton=best_cost.foc_ton,
            delta_foc_ton=best_cost.delta_foc_ton,
            reroute_heave_m=best_safety.heave_m,
            reroute_roll_deg=best_safety.roll_deg,
            delta_heave_m=delta_heave,
            delta_roll_deg=delta_roll,
            safety_restored=safety_restored
        )