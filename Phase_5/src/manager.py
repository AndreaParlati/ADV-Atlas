"""
Phase 5 - Manager (manager.py)
Orchestratore di alto livello per l'esecuzione della Phase 5.
"""

from typing import List, Dict, Any, Tuple
from .aggregator import DataAggregator
from .adv_calculator import ADVCalculator
from .operational_eval import OperationalEvaluator
from .atlas_generator import AtlasGenerator
from .config import ADVConfig, default_config


class Phase5Manager:
    """
    Manager principale per coordinare l'esecuzione della Fase 5.
    """

    def __init__(self, config: ADVConfig = default_config):
        self.config = config
        self.aggregator = DataAggregator()
        self.calculator = ADVCalculator(config=self.config)
        self.evaluator = OperationalEvaluator(config=self.config)
        self.generator = AtlasGenerator()

    def run_pipeline(
        self,
        phase3_data: List[Dict[str, Any]],
        phase4_data: List[Dict[str, Any]],
        csv_output_path: str,
        parquet_output_path: str,
        summary_json_path: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Esegue la pipeline completa di Fase 5:
        1. Data Fusion (Aggregator)
        2. Calcolo ADV Score (Calculator)
        3. Valutazione Operativa Real-time (Evaluator)
        4. Esportazione Atlas e Sintesi (Generator)
        """
        # Step 1: Data Fusion
        integrated_records = self.aggregator.aggregate(phase3_data, phase4_data)

        # Step 2: ADV Score Computation
        atlas_records = self.calculator.process_records(integrated_records)

        # Step 3: Operational Latency & Actionability Evaluation
        final_records = self.evaluator.evaluate_actionability(atlas_records)

        # Step 4: Export Datasets and Generate Summary
        self.generator.export_dataset(final_records, csv_output_path, parquet_output_path)
        summary = self.generator.generate_summary(final_records, summary_json_path)

        exported_records_dict = [r.model_dump() for r in final_records]
        return exported_records_dict, summary