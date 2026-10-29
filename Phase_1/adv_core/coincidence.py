"""Modulo per la validazione della coincidenza temporale tra eventi e transiti."""

def check_coincidence(event_time, transit_time, tolerance_hours=6.0, mode='baseline'):
    """
    Verifica se la coincidenza rispetta i vincoli lag-dipendenti in base alla modalità scelta.
    """
    delta_hours = abs((event_time - transit_time).total_seconds()) / 3600.0
    
    if mode == 'strict':
        limit = tolerance_hours * 0.5
    elif mode == 'relaxed':
        limit = tolerance_hours * 2.0
    else:  # baseline
        limit = tolerance_hours
        
    is_valid = delta_hours <= limit
    return {
        'is_coincident': is_valid,
        'delta_hours': delta_hours,
        'threshold_used': limit
    }