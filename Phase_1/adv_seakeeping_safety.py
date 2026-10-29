"""
adv_seakeeping_safety.py
========================
Moduli estratti dalla Fase 1 (Coincidence, Hazards and Safety Model)
dedicati alla valutazione dello seakeeping, degli spettri di moto e della 
resistenza aggiuntiva in mare mosso (indispensabili per la Fase 4).
"""

import numpy as np

G = 9.81                 # [m/s2]
RHO_SW = 1025.0          # densità acqua di mare [kg/m3][cite: 22]

_trapz = getattr(np, "trapezoid", None) or np.trapz


# =============================================================================
# 1. Spettro d'onda e incontri (JONSWAP)
# =============================================================================
def jonswap(omega, Hs, T0, gamma=3.3):
    """Eq. (7): Spettro di JONSWAP S_Jz(w) [m2 s/rad]. T0 = periodo di picco."""
    w = np.maximum(np.asarray(omega, float), 1e-6)
    wp = 2 * np.pi / T0
    sigma = np.where(w < wp, 0.07, 0.09)
    J = np.exp(-((w * T0 / (2 * np.pi) - 1) ** 2) / (2 * sigma ** 2))
    A = 487.0 * Hs ** 2 / T0 ** 4
    Bc = 1949.0 / T0 ** 4
    SB = A / w ** 5 * np.exp(-Bc / w ** 4)
    return 0.658 * gamma ** J * SB


def encounter_frequency(omega, Vs, mu_deg):
    """Eq. (8): Frequenza d'incontro w_e = w - w^2 Vs cos(mu) / g."""
    return omega - omega ** 2 * Vs * np.cos(np.radians(mu_deg)) / G


def encounter_spectrum(omega, S_omega, Vs, mu_deg):
    """Eq. (10): Spettro d'incontro S(w_e) = S(w) g / |g - 2 w Vs cos(mu)|."""
    den = np.abs(G - 2 * omega * Vs * np.cos(np.radians(mu_deg)))
    with np.errstate(divide="ignore"):
        return np.where(den > 1e-9, S_omega * G / den, np.nan)


def wave_relative_heading(heading_deg, wave_from_deg):
    """mu [deg], 180 = sea al giardinetto/prua (head seas)."""
    return (np.asarray(wave_from_deg) + 180.0 - heading_deg) % 360.0


# =============================================================================
# 2. Modelli di Moto e Statistiche (Seakeeping Criteria)
# =============================================================================
def motion_spectrum(omega, S_omega, rao_fn, Vs, mu_deg, kind="linear"):
    """
    Eq. (14) (kind='linear': surge, sway, heave) o 
    Eqs. (15)-(16) (kind='angular': roll, pitch, yaw).
    """
    we = encounter_frequency(omega, Vs, mu_deg)
    rao = np.abs(rao_fn(np.abs(we), omega, Vs, mu_deg))
    if kind == "linear":
        return S_omega * rao ** 2
    S_slope = omega ** 4 / G ** 2 * S_omega
    return S_slope * rao ** 2


def motion_statistics(omega, S_motion):
    """
    Eqs. (17)-(18): m0, sigma0 = sqrt(m0); 
    valore significativo = 4 * sigma0 (come specificato in [1]).
    """
    m0 = float(_trapz(S_motion, omega))
    s0 = np.sqrt(m0)
    return {"m0": m0, "sigma0": s0, "significant": 4 * s0}


# =============================================================================
# 3. Resistenza Aggiuntiva in Onde Irregolari (STAWAVE-2)
# =============================================================================
def caw_stawave2(omega, Vs, mu_deg, ship, rho=RHO_SW):
    """
    Funzione di risposta C_aw = R_aw / zeta_0^2 [N/m2] basata su STAWAVE-2 
    (ITTC 2014, settore di prua), rastremata fuori dal settore +/-45°.
    """
    L, B = ship.L, ship.B
    Fn = max(Vs / np.sqrt(G * L), 1e-3)
    a1 = 60.3 * ship.CB ** 1.34
    a2 = 0.0072 + 0.1676 * Fn if Fn < 0.12 else Fn ** 1.5 * np.exp(-3.5 * Fn)
    wbar = np.sqrt(L / G) * ship.kyy_L ** (1 / 3) / (1.17 * Fn ** -0.143) * np.asarray(omega, float)
    b1 = np.where(wbar < 1, 11.0, -8.5)
    d1 = np.where(wbar < 1, 14.0, -14.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        shape = wbar ** b1 * np.exp(b1 / d1 * (1 - wbar ** d1))
    shape = np.nan_to_num(shape, nan=0.0, posinf=0.0)
    caw_head = 4 * rho * G * B ** 2 / L * shape * a1 * a2
    off_head = np.abs(180.0 - np.asarray(mu_deg, float) % 360.0)
    taper = np.where(off_head <= 45.0, 1.0,
                     np.where(off_head < 90.0, np.cos(np.radians(2.0 * (off_head - 45.0))) ** 2, 0.0))
    return caw_head * taper


def added_wave_resistance(Hs, T0, Vs, mu_deg, ship, caw_fn=None, omega=None, gamma=3.3):
    """Eq. (13): R_aw = 2 int_0^inf C_aw(w) S(w) dw [N]."""
    if Hs <= 0:
        return 0.0
    caw_fn = caw_fn or caw_stawave2
    w = np.linspace(0.05, 3.0, 600) if omega is None else omega
    S = jonswap(w, Hs, T0, gamma)
    return float(2 * _trapz(caw_fn(w, Vs, mu_deg, ship) * S, w))