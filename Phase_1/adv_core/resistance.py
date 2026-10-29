"""Modulo per il calcolo della resistenza totale (Holtrop-Mennen) e resistenza al vento."""

import numpy as np

def holtrop_mennen_resistance(speed_knots, particulars):
    """
    Stima semplificata della resistenza totale in acque calme R_calm (N)
    in base ai dati geometrici della nave (particulars).
    """
    v_ms = speed_knots * 0.514444
    # Esempio di implementazione modulare basata su coefficienti di attrito e residui
    rho = 1025.0  # Densità acqua di mare (kg/m^3)
    S = particulars.get('wetted_surface', 1000.0)
    cf = 0.075 / (np.log10(max(v_ms, 0.1) * particulars.get('length', 100.0) / 1.14e-6) - 2)**2
    r_friction = 0.5 * rho * (v_ms**2) * S * cf
    
    # Componente residua stimata tramite Froude number
    fn = v_ms / np.sqrt(9.81 * particulars.get('length', 100.0))
    r_residuary = r_friction * (fn * 2.5)**4
    
    return r_friction + r_residuary

def wind_resistance(v_true, angle_true, v_ship, ship_heading, superstructure_area):
    """
    Calcola la resistenza longitudinale al vento R_wind (N) usando il vento apparente.
    """
    # Conversione vettoriale del vento apparente
    v_x_app = v_true * np.cos(np.radians(angle_true)) - v_ship * np.cos(np.radians(ship_heading))
    v_y_app = v_true * np.sin(np.radians(angle_true)) - v_ship * np.sin(np.radians(ship_heading))
    v_app = np.sqrt(v_x_app**2 + v_y_app**2)
    gamma_app = np.degrees(np.arctan2(v_y_app, v_x_app))
    
    rho_air = 1.225
    cx = 0.7 * np.cos(np.radians(gamma_app))  # กอง coefficiente aerodinamico longitudinale
    r_wind = 0.5 * rho_air * (v_app**2) * superstructure_area * cx
    return max(0.0, r_wind)