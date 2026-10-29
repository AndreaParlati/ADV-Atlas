"""Modulo per la gestione di STW (Speed Through Water), JONSWAP e STAWAVE-2."""

import numpy as np

def speed_through_water(sog, current_speed, current_dir, ship_heading):
    """
    Calcola la Speed Through Water (STW) combinando SOG e correnti marine.
    """
    sog_ms = sog * 0.514444
    cur_x = current_speed * np.cos(np.radians(current_dir))
    cur_y = current_speed * np.sin(np.radians(current_dir))
    
    ship_x = sog_ms * np.cos(np.radians(ship_heading)) - cur_x
    ship_y = sog_ms * np.sin(np.radians(ship_heading)) - cur_y
    
    stw_ms = np.sqrt(ship_x**2 + ship_y**2)
    return stw_ms / 0.514444

def jonswap_spectrum(omega, hs, tp, gamma=3.3):
    """
    Genera lo spettro energetico delle onde irregolari secondo JONSWAP.
    """
    omega_p = 2.0 * np.pi / tp
    sigma = np.where(omega <= omega_p, 0.07, 0.09)
    alpha = 0.0624 / (0.230 + 0.0336 * gamma - 0.185 / (1.9 + gamma))
    
    s = np.exp(-((0.15 * omega - omega_p)**2) / (2.0 * (sigma * omega_p)**2))
    factor = alpha * (hs**2) * (omega_p**4) / (omega**5) * np.exp(-1.25 * (omega_p / omega)**4)
    return factor * (gamma**s)