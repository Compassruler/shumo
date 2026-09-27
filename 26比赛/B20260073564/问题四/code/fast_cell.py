"""Numba equivalent of the Q1 conservative cell model at uniform cell temperature.

This module deliberately does not advance temperature: the Q2 heat network owns it.
Electro output order is ELECTRO_NAMES; phase output order is PHASE_NAMES.
The first invocation includes Numba compilation; subsequent calls are compiled.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.python_deps'))
from typing import NamedTuple
import numpy as np
from numba import njit

F = 96485.
R = 8.314
MW = .018
TF = 273.15
WPL = 2150. * .018
RI = 920.
RL = 990.
LC = 2.5e6
LF = 333600.
YO = (.233 / .032) / (.233 / .032 + .767 / .028)
ELECTRO_NAMES = ('V_V', 'E_rev_V', 'eta_act_V', 'eta_ohm_V', 'eta_con_V',
                 'j_lim_A_m2', 'j_over_jlim', 'lambda_mean', 'lambda_min',
                 'kappa_min_S_m', 'cO2_cCL_mol_m3', 'active_area_factor')
PHASE_NAMES = ('cond', 'evap', 'dep', 'sub', 'frz', 'mlt', 'frz_pore',
               'frz_mem', 'mlt_pore', 'mlt_mem', 'adsorption_heat_J_m2')
DIAGNOSTIC_NAMES = ('ice_max_bulk', 'ice_pore_max_bulk', 'ice_mem_max_bulk',
                    's_ice_pore_max', 's_liquid_pore_max', 'gas_porosity_min',
                    'species_inventory_min', 'water_total_kg_m2', 'ice_kg_m2')


class Config(NamedTuple):
    dx: np.ndarray
    eps: np.ndarray
    permeability: np.ndarray
    cos_theta: np.ndarray
    Cdry: np.ndarray
    kdry: np.ndarray
    kg: np.ndarray
    cg: np.ndarray
    a: np.ndarray
    c: np.ndarray
    mem: np.ndarray
    acl: np.ndarray
    ccl: np.ndarray
    pore: np.ndarray
    path_dx: np.ndarray
    j0: float
    kf: float
    km: float
    kcond: float
    kevap: float
    kdep: float
    ksub: float
    lambda_nf: float
    exchange_factor: float


def make_config(scale=1, j0=.10255839004732065, kf=1., km=1., kcond=1.,
                kevap=1., kdep=1e-4, ksub=1e-4, lambda_nf=3.,
                exchange_factor=1., **kwargs):
    """Geometry/materials are exactly those in the audited Q1 model.py."""
    if kwargs:
        raise TypeError('Unexpected config arguments: ' + ', '.join(kwargs))
    if int(scale) != scale or scale < 1:
        raise ValueError('scale must be a positive integer')
    if min(kf, km, kcond, kevap, kdep, ksub) < 0:
        raise ValueError('Phase rates must be nonnegative')
    scale = int(scale)
    counts = np.array([8, 3, 6, 4, 8]) * scale
    lengths = np.array([150e-6, 3.4e-6, 12e-6, 11.3e-6, 150e-6])
    dx = np.concatenate([np.full(n, length / n) for n, length in zip(counts, lengths)])
    label = np.repeat(np.arange(5), counts)
    a = np.flatnonzero(label < 2)
    c = np.flatnonzero(label > 2)
    mem = np.flatnonzero(label == 2)
    acl = np.flatnonzero(label == 1)
    ccl = np.flatnonzero(label == 3)
    pore = np.r_[a, c]
    eps = np.select([label == 1, label == 3, label == 2], [.3916, .4207, 0.], default=.8)
    gd = (label == 0) | (label == 4)
    cl = (label == 1) | (label == 3)
    permeability = np.where(gd, 6.2e-12, 6.2e-13)
    cos_theta = np.abs(np.cos(np.deg2rad(np.where(gd, 110., 100.))))
    Cdry = np.zeros(len(dx))
    kdry = np.zeros(len(dx))
    Cdry[gd] = (1 - eps[gd]) * 185 * 545
    Cdry[cl] = (1 - eps[cl] - .3) * 970 * 240 + .3 * 2150 * 1050
    Cdry[mem] = 2150 * 1050
    kdry[gd] = (1 - eps[gd]) * .3
    kdry[cl] = (1 - eps[cl] - .3) * .27 + .3 * .24
    kdry[mem] = .24
    kg = np.where(label < 2, .1672, .02373)
    cg = np.where(label < 2, .089 * 14283, .21 * 1.43 * 919.31 + .79 * 1.35 * 1041.5)
    x = np.cumsum(dx) - dx / 2
    path_start = 150e-6 + 3.4e-6 + 12e-6 + 11.3e-6 / 2
    right = x[c] + dx[c] / 2
    left = right - dx[c]
    path_dx = np.maximum(0., right - np.maximum(left, path_start))
    return Config(dx, eps, permeability, cos_theta, Cdry, kdry, kg, cg,
                  a, c, mem, acl, ccl, pore, path_dx, float(j0), float(kf),
                  float(km), float(kcond), float(kevap), float(kdep),
                  float(ksub), float(lambda_nf), float(exchange_factor))


@njit(cache=True)
def initial_state(cfg, T_K):
    n = len(cfg.dx)
    mv = np.zeros(n)
    ml = np.zeros(n)
    mi = np.zeros(n)
    ml[cfg.mem] = WPL * 3.
    nh = cfg.eps[cfg.a] * 101325. / (R * T_K)
    no = cfg.eps[cfg.c] * YO * 101325. / (R * T_K)
    return mv, ml, mi, nh, no


@njit(cache=True)
def _psat_liquid(T):
    c = T - TF
    return 611.21 * np.exp((18.678 - c / 234.5) * c / (257.14 + c))


@njit(cache=True)
def _psat_ice(T):
    c = T - TF
    return 611.15 * np.exp((23.036 - c / 333.7) * c / (279.82 + c))


@njit(cache=True)
def _fractions(cfg, ml, mi):
    gas = cfg.eps - ml / RL - mi / RI
    gas[cfg.mem] = 0.
    return gas


@njit(cache=True)
def _face(D, dx):
    out = np.empty(len(D) - 1)
    for k in range(len(out)):
        out[k] = 1. / (dx[k] / (2 * max(D[k], 1e-30)) + dx[k+1] / (2 * max(D[k+1], 1e-30)))
    return out


@njit(cache=True)
def _transport(inventory, cap, dx, conductance, dt, source, left_g,
               left_value, right_g, right_value, adv):
    """Same conservative BE/upwind matrix as Q1; Thomas replaces solve_banded."""
    n = len(dx)
    diagonal = cap * dx
    rhs = (inventory + dt * source) * dx
    lower = np.empty(n - 1)
    upper = np.empty(n - 1)
    for k in range(n - 1):
        g = dt * conductance[k]
        vp = dt * max(adv[k], 0.)
        vm = dt * min(adv[k], 0.)
        diagonal[k] += g + vp
        diagonal[k+1] += g - vm
        upper[k] = -g + vm
        lower[k] = -g - vp
    diagonal[0] += dt * left_g
    rhs[0] += dt * left_g * left_value
    diagonal[-1] += dt * right_g
    rhs[-1] += dt * right_g * right_value
    for k in range(1, n):
        w = lower[k-1] / diagonal[k-1]
        diagonal[k] -= w * upper[k-1]
        rhs[k] -= w * rhs[k-1]
    answer = np.empty(n)
    answer[-1] = rhs[-1] / diagonal[-1]
    for k in range(n-2, -1, -1):
        answer[k] = (rhs[k] - upper[k] * answer[k+1]) / diagonal[k]
    out = dt * (left_g * (answer[0] - left_value) + right_g * (answer[-1] - right_value))
    return answer, out


@njit(cache=True)
def _mass_step(cfg, state, T, j, dt):
    mv0, ml0, mi0, nh, no = state
    mv = mv0.copy()
    ml = ml0.copy()
    mi = mi0.copy()
    n = len(ml)
    produced = MW * j / (2 * F) * dt
    ml[cfg.ccl] += produced / 11.3e-6
    amounts = np.zeros(11)
    heat_area = 0.
    for side in range(2):
        ids = cfg.a if side == 0 else cfg.c
        dx = cfg.dx[ids]
        nn = len(ids)
        dl = np.empty(nn)
        for p in range(nn):
            k = ids[p]
            sl = max(ml[k] / (RL * cfg.eps[k]), 0.)
            si = mi[k] / (RI * cfg.eps[k])
            dJ = 1.417 - 4.24 * sl + 3.789 * sl * sl
            dl[p] = (cfg.permeability[k] * sl**3 * .075 * cfg.cos_theta[k]
                     * np.sqrt(cfg.eps[k] / cfg.permeability[k]) * dJ
                     / (1.8e-3 * cfg.eps[k]) * max(1 - si, 0.)**3)
        g = np.empty(nn-1)
        for p in range(nn-1):
            g[p] = (dl[p] + dl[p+1]) / (dx[p] + dx[p+1])
        solution, _ = _transport(ml[ids], np.ones(nn), dx, g, dt,
                                 np.zeros(nn), 0., 0., 0., 0., np.zeros(nn-1))
        ml[ids] = solution
    ids = cfg.mem
    dx = cfg.dx[ids]
    lam = ml[ids] / WPL
    dm = np.maximum(1e-10 * np.exp(2416 * (1/303.15 - 1/T))
                    * (2.563 - .33*lam + .0264*lam**2 - .000671*lam**3), 1e-13)
    adv = np.full(len(ids)-1, 2.5/22 * MW*j/(F*WPL))
    solution, _ = _transport(ml[ids], np.ones(len(ids)), dx, _face(dm, dx),
                             dt, np.zeros(len(ids)), 0., 0., 0., 0., adv)
    ml[ids] = solution
    for side in range(2):
        cm = cfg.acl[-1] if side == 0 else cfg.ccl[0]
        pm = cfg.mem[0] if side == 0 else cfg.mem[-1]
        sl = max(0., ml[cm] / (RL * cfg.eps[cm]))
        lmem = ml[pm] / WPL
        q = cfg.exchange_factor * .5 * 6e-6 * WPL * sl * (14-lmem) * dt
        q = max(-ml[pm]*cfg.dx[pm], min(q, ml[cm]*cfg.dx[cm]))
        ml[pm] += q / cfg.dx[pm]
        ml[cm] -= q / cfg.dx[cm]
        eps = max(cfg.eps[cm] - ml[cm]/RL - mi[cm]/RI, 1e-12)
        activity = max(0., min(mv[cm]/eps/(MW*_psat_liquid(T)/(R*T)), 1.))
        leq = .043 + 17.81*activity - 39.85*activity**2 + 36*activity**3
        q = cfg.exchange_factor * .001 * 6e-6 * WPL * (1-min(sl, 1.)) * (leq-ml[pm]/WPL) * dt
        q = max(-ml[pm]*cfg.dx[pm], min(q, mv[cm]*cfg.dx[cm]))
        ml[pm] += q / cfg.dx[pm]
        mv[cm] -= q / cfg.dx[cm]
        heat_area += LC*q
        amounts[10] += LC*q
    gas = _fractions(cfg, ml, mi)
    out = 0.
    for side in range(2):
        ids = cfg.a if side == 0 else cfg.c
        dref = 8.69e-5 if side == 0 else 2.48e-5
        dx = cfg.dx[ids]
        eps = np.maximum(gas[ids], 1e-12)
        dv = dref * (T/298.15)**1.5 * eps**1.5
        left_g = 2*dv[0]/dx[0] if side == 0 else 0.
        right_g = 2*dv[-1]/dx[-1] if side == 1 else 0.
        cv, loss = _transport(mv[ids], eps, dx, _face(dv, dx), dt,
                             np.zeros(len(ids)), left_g, 0., right_g, 0., np.zeros(len(ids)-1))
        mv[ids] = eps*cv
        out += loss
    # Pairwise phase transfers are donor-limited, exactly matching Q1 splitting.
    gas = np.maximum(_fractions(cfg, ml, mi), 0.)
    satl_per_gas = MW*_psat_liquid(T)/(R*T)
    for k in cfg.pore:
        excess = mv[k] - gas[k]*satl_per_gas
        cond = max(excess, 0.) * (dt*cfg.kcond)/(1+dt*cfg.kcond)
        evap = min(ml[k], max(-excess, 0.) * (dt*cfg.kevap)/(1+dt*cfg.kevap))
        mv[k] += evap-cond
        ml[k] += cond-evap
        amounts[0] += cond*cfg.dx[k]
        amounts[1] += evap*cfg.dx[k]
        heat_area += LC*(cond-evap)*cfg.dx[k]
    gas = np.maximum(_fractions(cfg, ml, mi), 0.)
    sati_per_gas = MW*_psat_ice(T)/(R*T)
    for k in cfg.pore:
        excess = mv[k] - gas[k]*sati_per_gas
        dep = 0.
        sub = 0.
        if T < TF:
            dep = max(excess, 0.)*(dt*cfg.kdep)/(1+dt*cfg.kdep)
            sub = min(mi[k], max(-excess, 0.)*(dt*cfg.ksub)/(1+dt*cfg.ksub))
        mv[k] += sub-dep
        mi[k] += dep-sub
        amounts[2] += dep*cfg.dx[k]
        amounts[3] += sub*cfg.dx[k]
        heat_area += (LC+LF)*(dep-sub)*cfg.dx[k]
    af = cfg.kf * max((TF-T)/TF, 0.)
    am = cfg.km * max((T-TF)/TF, 0.)
    for k in range(n):
        freezable = ml[k] if cfg.eps[k] > 0 else max(ml[k]-WPL*cfg.lambda_nf, 0.)
        freeze = freezable*dt*af/(1+dt*af)
        melt = mi[k]*dt*am/(1+dt*am)
        ml[k] += melt-freeze
        mi[k] += freeze-melt
        heat_area += LF*(freeze-melt)*cfg.dx[k]
        amounts[4] += freeze*cfg.dx[k]
        amounts[5] += melt*cfg.dx[k]
        if cfg.eps[k] > 0:
            amounts[6] += freeze*cfg.dx[k]
            amounts[8] += melt*cfg.dx[k]
        else:
            amounts[7] += freeze*cfg.dx[k]
            amounts[9] += melt*cfg.dx[k]
    return mv, ml, mi, heat_area, produced, out, amounts


@njit(cache=True)
def _gas_step(cfg, T, ml, mi, nh, no, j, dt):
    gas = _fractions(cfg, ml, mi)
    nh_new = nh.copy()
    no_new = no.copy()
    for side in range(2):
        ids = cfg.a if side == 0 else cfg.c
        old = nh if side == 0 else no
        dref = 1.1e-4 if side == 0 else 2.2e-5
        frac = 1. if side == 0 else YO
        cl = cfg.acl if side == 0 else cfg.ccl
        nu = 2. if side == 0 else 4.
        eps = np.maximum(gas[ids], 1e-12)
        D = dref*(T/298.15)**1.5 * eps**1.5
        dx = cfg.dx[ids]
        source = np.zeros(len(ids))
        cl_length = 0.
        for k in cl:
            cl_length += cfg.dx[k]
        for p in range(len(ids)):
            if ids[p] >= cl[0] and ids[p] <= cl[-1]:
                source[p] = -j/(nu*F*cl_length)
        left_g = 2*D[0]/dx[0] if side == 0 else 0.
        right_g = 2*D[-1]/dx[-1] if side == 1 else 0.
        boundary_c = frac*101325/(R*T)
        concentration, _ = _transport(old, eps, dx, _face(D, dx), dt, source,
                                      left_g, boundary_c, right_g, boundary_c, np.zeros(len(ids)-1))
        if side == 0:
            nh_new = eps*concentration
        else:
            no_new = eps*concentration
    return nh_new, no_new


@njit(cache=True)
def cell_step_full(cfg, state, T_K, j_SI, dt):
    mv, ml, mi, phase, produced, out, amounts = _mass_step(cfg, state, T_K, j_SI, dt)
    nh, no = _gas_step(cfg, T_K, ml, mi, state[3], state[4], j_SI, dt)
    return (mv, ml, mi, nh, no), phase, produced, out, amounts


@njit(cache=True)
def cell_step(cfg, state, T_K, j_SI, dt):
    new_state, phase, produced, out, _ = cell_step_full(cfg, state, T_K, j_SI, dt)
    return new_state, phase, produced, out


@njit(cache=True)
def electro(cfg, state, T_K, j_SI, beta=1.):
    mv, ml, mi, nh, no = state
    gas = _fractions(cfg, ml, mi)
    ch = nh/np.maximum(gas[cfg.a], 1e-12)
    co = no/np.maximum(gas[cfg.c], 1e-12)
    ph = 0.
    po = 0.
    ccl = 0.
    fa = 0.
    la = np.sum(cfg.dx[cfg.acl])
    lc = np.sum(cfg.dx[cfg.ccl])
    for p in range(len(cfg.acl)):
        ph += ch[len(cfg.a)-len(cfg.acl)+p]*R*T_K*cfg.dx[cfg.acl[p]]/la
    for p in range(len(cfg.ccl)):
        k = cfg.ccl[p]
        weight = cfg.dx[k]/lc
        po += co[p]*R*T_K*weight
        ccl += co[p]*weight
        si = mi[k]/(RI*cfg.eps[k])
        fa += max(1-si, 1e-12)**3.5*weight
    erev = 1.229-.00085*(T_K-298.15)+R*T_K/(2*F)*np.log(max(ph/101325*np.sqrt(max(po/101325, 1e-15)), 1e-20))
    jzero = cfg.j0*np.exp(-67000/R*(1/T_K-1/298.15))*fa
    act = R*T_K/(.5*F)*np.arcsinh(j_SI/(2*max(jzero, 1e-25)))
    resistance = 1e-6
    lambda_min = 1e300
    lambda_mean = 0.
    kappa_min = 1e300
    lm = np.sum(cfg.dx[cfg.mem])
    for k in cfg.mem:
        lam = ml[k]/WPL
        sim = mi[k]/RI
        kap = (.5139*lam-.326)*np.exp(1268*(1/303.15-1/T_K))*(1-sim)
        resistance += cfg.dx[k]/max(kap, 1e-10)
        lambda_min = min(lambda_min, lam)
        lambda_mean += lam*cfg.dx[k]/lm
        kappa_min = min(kappa_min, kap)
    ohm = j_SI*resistance
    path_res = 0.
    for p in range(len(cfg.c)):
        k = cfg.c[p]
        do = 2.2e-5*(T_K/298.15)**1.5*max(gas[k], 1e-15)**1.5
        path_res += cfg.path_dx[p]/max(do, 1e-30)
    jlim = 4*F*ccl/max(path_res, 1e-20)
    ratio = j_SI/max(jlim, 1e-20)
    con = -beta*R*T_K/(4*F)*np.log(max(1-ratio, 1e-12))
    return np.array([erev-act-ohm-con, erev, act, ohm, con, jlim, ratio,
                     lambda_mean, lambda_min, kappa_min, ccl, fa])


@njit(cache=True)
def properties(cfg, state):
    mv, ml, mi, _, _ = state
    gas = _fractions(cfg, ml, mi)
    area_capacity = 0.
    resistance = 0.
    for k in range(len(cfg.dx)):
        if cfg.eps[k] > 0:
            C = cfg.Cdry[k]+gas[k]*cfg.cg[k]+ml[k]*4182+mi[k]*2050+mv[k]*2000
            conductivity = cfg.kdry[k]+gas[k]*cfg.kg[k]+ml[k]/RL*.6+mi[k]/RI*2.3
        else:
            C = cfg.Cdry[k]+ml[k]*4182+mi[k]*2050
            conductivity = .24+mi[k]/RI*(2.3-.24)
        area_capacity += C*cfg.dx[k]
        resistance += cfg.dx[k]/conductivity
    return area_capacity, resistance


@njit(cache=True)
def diagnostics(cfg, state):
    mv, ml, mi, nh, no = state
    gas = _fractions(cfg, ml, mi)
    total = 0.
    ice_mass = 0.
    min_species = min(np.min(mv), np.min(ml), np.min(mi), np.min(nh), np.min(no))
    for k in range(len(cfg.dx)):
        total += (mv[k]+ml[k]+mi[k])*cfg.dx[k]
        ice_mass += mi[k]*cfg.dx[k]
    return np.array([np.max(mi)/RI, np.max(mi[cfg.pore])/RI, np.max(mi[cfg.mem])/RI,
                     np.max(mi[cfg.pore]/(RI*cfg.eps[cfg.pore])),
                     np.max(ml[cfg.pore]/(RL*cfg.eps[cfg.pore])),
                     np.min(gas[cfg.pore]), min_species, total, ice_mass])
