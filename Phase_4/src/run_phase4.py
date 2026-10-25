from manager import Phase4Manager

if __name__ == "__main__":
    manager = Phase4Manager(
        input_csv="data/phase3_coincidences.csv",
        output_csv="data/phase4_adv_dataset.csv"
    )
    manager.run()
    print("Simulazione Phase 4 completata con successo!")