"""Modulo per il punto di lavoro dell'elica, potenza al freno (PB) e SFOC."""

def leg_performance(total_resistance, speed_knots, engine_params):
    """
    Calcola la potenza richiesta, il consumo specifico (SFOC) e le emissioni per tratta.
    """
    v_ms = speed_knots * 0.514444
    pe = total_resistance * v_ms # Resistance Power (W)
    
    # Efficienza globale stimata della linea d'asse
    eta_total = engine_params.get('total_efficiency', 0.65)
    pb_kw = (pe / eta_total) / 1000.0  # Potenza al freno in kW
    
    # Consumo specifico di carburante approssimato (g/kWh)
    sfoc = engine_params.get('base_sfoc', 185.0) 
    fuel_rate_kg_h = pb_kw * (sfoc / 1000.0)
    
    return {
        'power_brake_kw': pb_kw,
        'fuel_rate_kg_h': fuel_rate_kg_h
    }