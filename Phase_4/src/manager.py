"""
Orchestratore principale per l'esecuzione batch della Phase 4.
"""
from io_handler import IOHandler
from scenario_generator import ScenarioGenerator
from safety_engine import SafetyEngine
from cost_evaluator import CostEvaluator
from decision_engine import DecisionEngine
from models import EventRecord, ADVRecord

class Phase4Manager:
    def __init__(self, input_csv: str, output_csv: str):
        self.input_csv = input_csv
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
        """Esegue il batch su tutto il dataset di input e salva i risultati."""
        events = IOHandler.load_events_from_csv(self.input_csv)
        adv_results: List[ADVRecord] = []

        for event in events:
            result = self.process_single_event(event)
            adv_results.append(result)

        IOHandler.save_adv_results(adv_results, self.output_csv)