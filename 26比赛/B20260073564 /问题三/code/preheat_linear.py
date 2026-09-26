"""Frozen-property seven-node pure-preheat LP: an optimizer seed, not the final model.

For a constant five-heater vector q in W/cm2 and theta=T-T_amb,
  C dtheta/dt + G theta = B q, theta(0)=0,
so H(t)=[I-exp(-C^-1 G t)] G^-1 B and theta(t)=H(t)q.
At a fixed t the minimum-energy control is a five-variable linear program.
The full coupled phase/water/electrochemistry solver must validate this seed.
"""
from pathlib import Path
import csv
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'问题2_求解结果'/'.python_deps'))
import numpy as np
from scipy.linalg import expm
from scipy.optimize import linprog, minimize_scalar
from aux_model import make_config, initial_state, network, THERMAL, J0


def frozen_network():
    cfg = make_config(scale=1, j0=J0)
    states = [initial_state(cfg, 243.15) for _ in range(5)]
    cap, conduct, _ = network(cfg, states, THERMAL)
    source = np.zeros((7, 5))
    source[:5] = np.eye(5)*1.e4
    generator = conduct/cap[:, None]
    steady = np.linalg.solve(conduct, source)
    return cap, conduct, generator, steady


def solve_at(t, generator, steady, margin=1.e-6):
    response = (np.eye(7)-expm(-generator*t)) @ steady
    lp = linprog(np.ones(5), A_ub=-response[:5],
                 b_ub=np.full(5, -30.-margin), bounds=[(0., 1.)]*5,
                 method='highs')
    if not lp.success:
        return {'time_s': float(t), 'feasible': 0, 'energy_J': float('nan')}
    q = lp.x
    temps = response @ q - 30.
    row = {'time_s': float(t), 'feasible': 1, 'energy_J': float(25*t*q.sum())}
    row.update({f'q{k+1}_W_cm2': float(q[k]) for k in range(5)})
    row.update({f'T{k+1}_C': float(temps[k]) for k in range(5)})
    row.update({'TEL_C': float(temps[5]), 'TER_C': float(temps[6]),
                'max_mirror_q_difference': float(max(abs(q[0]-q[4]), abs(q[1]-q[3])))})
    return row


def main():
    cap, conduct, generator, steady = frozen_network()
    rows = [solve_at(t, generator, steady) for t in np.arange(10., 300.0001, 1.)]
    valid = [r for r in rows if r['feasible']]
    seed = min(valid, key=lambda r: r['energy_J'])
    def objective(t):
        result = solve_at(t, generator, steady)
        return result['energy_J'] if result['feasible'] else 1.e20
    refined = minimize_scalar(objective, bounds=(max(10., seed['time_s']-2),
                                                min(300., seed['time_s']+2)),
                              method='bounded', options={'xatol': 1.e-9})
    best = solve_at(refined.x, generator, steady)
    fine = [solve_at(t, generator, steady) for t in np.arange(max(10., best['time_s']-2),
                                                            best['time_s']+2.001, .05)]
    rows = sorted(rows + fine + [best], key=lambda r: r['time_s'])
    root = Path(__file__).resolve().parents[1]
    dest = root/'data'/'preheat_linear_scan.csv'
    dest.parent.mkdir(parents=True, exist_ok=True)
    fields = ['time_s', 'feasible', 'energy_J']
    fields += [f'q{k+1}_W_cm2' for k in range(5)]
    fields += [f'T{k+1}_C' for k in range(5)]
    fields += ['TEL_C', 'TER_C', 'max_mirror_q_difference']
    with dest.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'model': 'frozen-initial-properties LP seed only',
                      'heat_capacity_J_m2_K': cap.tolist(),
                      'optimum': best,
                      'nearby': [solve_at(best['time_s']+d, generator, steady)
                                 for d in [-2, -.5, -.1, 0, .1, .5, 2, 10]],
                      'csv': str(dest)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
