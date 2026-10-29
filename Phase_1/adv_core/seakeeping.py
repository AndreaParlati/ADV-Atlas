"""Modulo per il calcolo dello spettro di risposta ai moti e criteri di sicurezza."""

import numpy as np

def motion_statistics(response_operator_raos, wave_spectrum, frequencies):
    """
    Calcola momenti spettrali (m0) e valore significativo di picco (4 * sigma).
    """
    dw = np.gradient(frequencies)
    response_spectrum = (response_operator_raos**2) * wave_spectrum
    m0 = np.sum(response_spectrum * dw)
    sig_value = 4.0 * np.sqrt(max(0.0, m0))
    return {
        'variance_m0': m0,
        'significant_response': sig_value
    }