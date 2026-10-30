"""
Script di estrazione e download dei dati satellitari e di reanalysis (CMEMS e Sentinel-1 STAC)
per la pipeline ADV-Atlas (Fase 3), ottimizzato con le API correnti.
"""

from pathlib import Path
import os
import json
import time
import copernicusmarine
from pystac_client import Client

# Configurazione percorsi e area di studio (Corridoio Lisbona -> Halifax)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Phase_3" / "data"
WAVE_DIR = BASE_DIR / "Phase_3" / "Wave_Reanalysis"
ALT_DIR = BASE_DIR / "Phase_3" / "L3_altimetry"
S1_CACHE_PATH = DATA_DIR / "s1_items_cache.json"

for d in (DATA_DIR, WAVE_DIR, ALT_DIR):
    d.mkdir(exist_ok=True, parents=True)

# Parametri geografici e temporali di riferimento
YEAR = 2022
MIN_LON, MAX_LON = -65.0, -8.0
MIN_LAT, MAX_LAT = 35.0, 48.0

def download_cmems_wave_reanalysis(year=YEAR):
    """Scarica il sottoinsieme del reanalysis delle onde CMEMS usando copernicusmarine.subset."""
    print(f"🌊 Download reanalysis onde CMEMS per l'anno {year}...")
    dataset_id = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"
    try:
        copernicusmarine.subset(
            dataset_id=dataset_id,
            minimum_longitude=MIN_LON,
            maximum_longitude=MAX_LON,
            minimum_latitude=MIN_LAT,
            maximum_latitude=MAX_LAT,
            start_datetime=f"{year}-01-01T00:00:00",
            end_datetime=f"{year}-12-31T23:59:59",
            output_directory=str(WAVE_DIR)
        )
        print("✅ Reanalysis onde scaricato con successo.")
    except Exception as e:
        print(f"❌ Errore durante il download del reanalysis CMEMS: {e}")

def download_cmems_altimetry(year=YEAR):
    """Scarica il sottoinsieme dell'altimetria L3 usando copernicusmarine.subset."""
    print(f"🛰️ Download altimetria L3 (SWH) per l'anno {year}...")
    dataset_id = "cmems_obs-wave_glo_phy-swh_my_multi-l3_PT1S"
    try:
        copernicusmarine.subset(
            dataset_id=dataset_id,
            minimum_longitude=MIN_LON,
            maximum_longitude=MAX_LON,
            minimum_latitude=MIN_LAT,
            maximum_latitude=MAX_LAT,
            start_datetime=f"{year}-01-01T00:00:00",
            end_datetime=f"{year}-12-31T23:59:59",
            output_directory=str(ALT_DIR)
        )
        print("✅ Altimetria L3 scaricata con successo.")
    except Exception as e:
        print(f"❌ Errore durante il download dell'altimetria L3: {e}")

def fetch_sentinel1_stac_cache(year=YEAR):
    """Interroga il catalogo STAC di Copernicus Data Space Ecosystem (CDSE) per Sentinel-1 mese per mese."""
    print(f"📡 Generazione cache STAC Sentinel-1 per l'anno {year} (con gestione rate limit)...")
    stac_url = "https://catalogue.dataspace.copernicus.eu/stac"
    collections = ["sentinel-1-ocn", "sentinel-1-ocn-wv"]
    
    try:
        catalog = Client.open(stac_url)
        bbox = [MIN_LON, MIN_LAT, MAX_LON, MAX_LAT]
        
        cache = {}
        for col in collections:
            print(f"   Interrogazione collezione STAC: {col} per singoli mesi...")
            for month in range(1, 13):
                start_m = f"{year}-{month:02d}-01T00:00:00Z"
                end_m = f"{year}-12-31T23:59:59Z" if month == 12 else f"{year}-{month+1:02d}-01T00:00:00Z"
                time_range = f"{start_m}/{end_m}"
                
                try:
                    search = catalog.search(
                        collections=[col],
                        bbox=bbox,
                        datetime=time_range,
                        max_items=500
                    )
                    items = list(search.items())
                    
                    for item in items:
                        date_str = item.datetime.strftime("%Y-%m-%d")
                        key = f"{col}|{date_str}"
                        if key not in cache:
                            cache[key] = []
                        
                        cache[key].append({
                            "item_id": item.id,
                            "sat_id": item.properties.get("constellation", "sentinel-1"),
                            "acq_start": item.properties.get("start_datetime", item.datetime.isoformat()),
                            "acq_end": item.properties.get("end_datetime", item.datetime.isoformat()),
                            "sensor_mode": item.properties.get("sar:instrument_mode", "IW"),
                            "orbit_direction": item.properties.get("orbit:direction", "ascending"),
                            "footprint_wkt": item.geometry.wkt if hasattr(item.geometry, "wkt") else str(item.geometry)
                        })
                    
                    # Pausa per evitare il blocco 429 (Rate Limit)
                    time.sleep(1.0)
                    
                except Exception as sub_e:
                    print(f"   ⚠️ Avviso nel mese {month} per {col}: {sub_e}")
                    time.sleep(2.0)
                    
        S1_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        S1_CACHE_PATH.write_text(json.dumps(cache, indent=2))
        print(f"✅ Cache Sentinel-1 salvata con successo in: {S1_CACHE_PATH}")
        
    except Exception as e:
        print(f"❌ Errore durante l'interrogazione STAC Sentinel-1: {e}")

if __name__ == "__main__":
    print("🚀 Avvio script di download e estrazione dati satellitari (Fase 3)...")
    download_cmems_wave_reanalysis()
    download_cmems_altimetry()
    fetch_sentinel1_stac_cache()
    print("✨ Estrazione e popolamento dati completati!")