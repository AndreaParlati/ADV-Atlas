"""
Script di Test End-to-End per Phase 5 (run_test_phase5.py)
"""

import os
from Phase_5.src.manager import Phase5Manager
from Phase_5.src.config import default_config

def run_test():
    print("=== Avvio Test End-to-End Phase 5 (ADV Atlas & Operational Framing) ===")

    # Mock Input Data - Phase 3 (Satellite Coincidence)
    mock_phase3 = [
        {
            "event_id": "EVT_001",
            "route_leg": default_config.LEG_MID_ATLANTIC,
            "lat": 41.5,
            "lon": -30.2,
            "coincidence_flag": False,
            "satellite_type": None,
            "forecast_hs": 4.2,
            "satellite_hs": None,
            "forecast_bias": 0.0,
            "acquisition_latency_hours": 999.0
        },
        {
            "event_id": "EVT_002",
            "route_leg": default_config.LEG_GRAND_BANKS,
            "lat": 46.8,
            "lon": -48.1,
            "coincidence_flag": True,
            "satellite_type": "Sentinel-1 EW",
            "forecast_hs": 3.8,
            "satellite_hs": 6.5,
            "forecast_bias": 2.7,
            "acquisition_latency_hours": 1.5
        },
        {
            "event_id": "EVT_003",
            "route_leg": default_config.LEG_GRAND_BANKS,
            "lat": 47.1,
            "lon": -49.5,
            "coincidence_flag": True,
            "satellite_type": "Altimeter L3",
            "forecast_hs": 3.0,
            "satellite_hs": 5.0,
            "forecast_bias": 2.0,
            "acquisition_latency_hours": 5.0
        }
    ]

    # Mock Input Data - Phase 4 (Re-Routing Value)
    mock_phase4 = [
        {
            "event_id": "EVT_001",
            "hazard_type": "rough_seas",
            "optimal_strategy": "direct",
            "applied_speed_kn": 24.5,
            "applied_detour_nm": 0.0,
            "delta_foc_ton": 0.0,
            "safety_restored": False
        },
        {
            "event_id": "EVT_002",
            "hazard_type": "rogue_wave",
            "optimal_strategy": "detour",
            "applied_speed_kn": 20.0,
            "applied_detour_nm": 45.0,
            "delta_foc_ton": 5.2,
            "safety_restored": True
        },
        {
            "event_id": "EVT_003",
            "hazard_type": "iceberg",
            "optimal_strategy": "speed_reduction",
            "applied_speed_kn": 16.0,
            "applied_detour_nm": 0.0,
            "delta_foc_ton": 2.1,
            "safety_restored": True
        }
    ]

    # Output paths
    csv_path = "output/adv_atlas_dataset.csv"
    parquet_path = "output/adv_atlas_dataset.parquet"
    summary_path = "output/operational_summary.json"

    # Execution
    manager = Phase5Manager()
    records, summary = manager.run_pipeline(
        phase3_data=mock_phase3,
        phase4_data=mock_phase4,
        csv_output_path=csv_path,
        parquet_output_path=parquet_path,
        summary_json_path=summary_path
    )

    print(f"\n[SUCCESS] Elaborazione completata per {len(records)} eventi.")
    print(f"Dataset CSV generato in: {csv_path}")
    print(f"Dataset Parquet generato in: {parquet_path}")
    print(f"Report JSON generato in: {summary_path}\n")

    print("=== Summary Output ===")
    print(summary)

if __name__ == "__main__":
    run_test()