"""
Orchestratore principale per l'esecuzione batch della Phase 4 (integrato con i dati di Phase 3).
"""
from typing import List
from io_handler import IOHandler
from scenario_generator import ScenarioGenerator
from safety_engine import SafetyEngine
from cost_evaluator import CostEvaluator
from decision_engine import DecisionEngine
from models import EventRecord, ADVRecord

class Phase4Manager:
    def __init__(self, input_path: str = "../Phase_3/data/coincidence_merged.parquet", output_csv: str = "phase4_routing_output.csv"):
        self.input_path = input_path
        self.output_csv = output_csv
        
        # Inizializzazione dei sottomoduli
        self.scenario_gen = ScenarioGenerator()
        self.safety_eng = SafetyEngine()
        self.cost_eval = CostEvaluator()

    def process_single_event(self, event: EventRecord) -> ADVRecord:
        """Esegue la simulazione completa per un singolo evento."""
        # 1. Generazione candidati
        candidates = self.scenario_gen.generate_candidates(event)
        
        # 2. Valutazione di sicurezza e costo per ciascun candidato
        evaluations = []
        for cand in candidates:
            safety_res = self.safety_eng.evaluate_safety(cand, event)
            cost_res = self.cost_eval.calculate_cost(cand, event)
            evaluations.append((cand, safety_res, cost_res))
            
        # 3. Selezione decisionale dell'ottimo
        return DecisionEngine.select_best_option(event, evaluations)

    def run(self) -> None:
        """Esegue il batch caricando il dataset reale della Phase 3 e salva i risultati."""
        print(f"📥 Caricamento eventi reali da Phase 3: {self.input_path}")
        events = IOHandler.load_events_from_phase3(self.input_path)
        adv_results: List[ADVRecord] = []

        for event in events:
            result = self.process_single_event(event)
            adv_results.append(result)

        IOHandler.save_adv_results(adv_results, self.output_csv)
        print(f"✅ Elaborazione completata. Risultati salvati in: {self.output_csv}")