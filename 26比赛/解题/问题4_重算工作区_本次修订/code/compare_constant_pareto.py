"""Finite-search constant-power benchmarks and an energy/time frontier.

All comparisons use the same plant, 2 s continuous success hold, 20 C/cm2
charge horizon, and zero power after latched shutdown.  Search results are
best-found values, not certificates of global optimality.  Constant vectors
are searched symmetrically first; explicitly saved asymmetric perturbations
test the restriction without claiming a complete five-dimensional search.

Run: python code/compare_constant_pareto.py --workers 4
"""
import os
for _name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ.setdefault(_name, '1')
import bootstrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import threading
import time
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, minimize
import control_model as m

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
POWER_NAMES = [f'q{k}_W_cm2' for k in range(1, 6)]
TEMP_NAMES = [f'T{k}_C' for k in range(1, 6)] + ['TEL_C', 'TER_C']
DEADLINES = (30., 60., 90., m.Q_TIME)


def save(rows, name):
    pd.DataFrame(rows).to_csv(DATA / name, index=False, encoding='utf-8-sig',
                               float_format='%.12g')


def sym(x):
    return np.array([x[0], x[1], x[2], x[1], x[0]], dtype=float)


class Evaluator:
    def __init__(self, case, temp):
        self.case, self.temp = case, temp
        self.cache, self.rows = {}, []
        self.lock = threading.Lock()
        self.deadline = m.Q_TIME
        self.stage = 'initial'
        self.params = m.DEFAULT.copy()
        self.params[5] = 2.

    def evaluate(self, power, dt=.05, scale=1, stage=None):
        power = np.clip(np.asarray(power, float), 0., 1.)
        key = (float(dt), int(scale), *np.round(power, 11))
        with self.lock:
            cached = self.cache.get(key)
        if cached is not None:
            return cached
        summary = m.simulate(self.temp, kind='constant', power=power,
                             params=self.params, dt=dt, scale=scale)[0]
        item = dict(case=self.case, stage=stage or self.stage,
                    search_deadline_s=self.deadline, dt_s=dt, mesh_scale=scale,
                    **dict(zip(POWER_NAMES, power)), **summary)
        with self.lock:
            # Iterative optimizers can request the same point concurrently.
            if key in self.cache:
                return self.cache[key]
            item['candidate_id'] = len(self.rows)
            self.rows.append(item)
            self.cache[key] = item
        return item

    def cost(self, x):
        r = self.evaluate(sym(x))
        if r['feasible'] and r['first_success_s'] <= self.deadline + 1e-7:
            # Time only breaks machine-level ties in the primary energy target.
            return r['E_aux_J'] / 3000. + 1e-11 * r['stop_s']
        if r['feasible']:
            return 10. + (r['first_success_s'] - self.deadline) / self.deadline
        return (20. + max(0., -r['final_min_T_C']) / 30.
                + max(0., .3-r['min_voltage_V']) * 10.
                + max(0., r['max_ice_bulk']-.99) * 10.)

    def feasible_rows(self, deadline=None, fine=False):
        deadline = self.deadline if deadline is None else deadline
        return sorted((r for r in self.rows if r['feasible']
                       and r['first_success_s'] <= deadline + 1e-7
                       and ((r['mesh_scale'] == 2) if fine else True)),
                      key=lambda r: (r['E_aux_J'], r['stop_s']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--maxiter', type=int, default=15)
    parser.add_argument('--popsize', type=int, default=7)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    initial = pd.read_csv(DATA / 'initial_temperature_cases.csv')
    results, parameters, frontier, baselines, all_rows = [], [], [], [], []
    start = time.perf_counter()
    # Compile before several threads reach Numba's compilation lock together.
    warm_temp = initial.iloc[0][TEMP_NAMES].to_numpy(float)
    m.simulate(warm_temp, kind='constant', dt=.05, scale=1, horizon=.1)
    for index, row in initial.iterrows():
        case, temp = row['case'], row[TEMP_NAMES].to_numpy(float)
        ev = Evaluator(case, temp)
        for kind, power in [('zero_heater', np.zeros(5)),
                            ('inherited_constant_C', m.CONSTANT),
                            ('full_power', np.ones(5))]:
            s, h, *_ = m.simulate(temp, kind='constant', power=power,
                                 params=ev.params, dt=.025, scale=2,
                                 post=60., record=True)
            baselines.append(dict(case=case, strategy=kind,
                             **dict(zip(POWER_NAMES, power)), **s))
            save(pd.DataFrame(h, columns=m.HISTORY), f'trajectory_{case}_{kind}.csv')
            ev.evaluate(power, dt=.025, scale=2, stage='fine_baseline')
        # Seeds include both rapid high-power and slow low-power modes.
        seeds = [np.zeros(3), np.ones(3), m.CONSTANT[:3],
                 np.array([1., .2, 0.]), np.array([.5, .15, .05]),
                 np.array([.25, .08, 0.])]
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            list(pool.map(lambda x: ev.evaluate(sym(x), stage='seed'), seeds))
            for di, deadline in enumerate(DEADLINES):
                ev.deadline, ev.stage = deadline, f'DE_deadline_{deadline:.6g}'
                zero = ev.evaluate(np.zeros(5))
                if not (zero['feasible'] and zero['first_success_s'] <= deadline + 1e-7):
                    existing = ev.feasible_rows()
                    x0 = (np.array([existing[0][n] for n in POWER_NAMES[:3]])
                          if existing else np.ones(3))
                    search = differential_evolution(ev.cost, [(0., 1.)]*3,
                        seed=20260926 + 100*index + di, popsize=args.popsize,
                        maxiter=args.maxiter if di == len(DEADLINES)-1 else min(8,args.maxiter),
                        tol=1e-6, polish=False, x0=x0,
                        workers=pool.map, updating='deferred')
                    ev.stage = f'Powell_deadline_{deadline:.6g}'
                    minimize(ev.cost, search.x, method='Powell', bounds=[(0.,1.)]*3,
                             options={'maxfev':75 if di == len(DEADLINES)-1 else 45,
                                      'xtol':.001, 'ftol':1e-6})
                    # A separate asymmetric neighborhood check; every tested
                    # five-vector is logged. Symmetry is never called a proof.
                    seedrow = ev.feasible_rows()[0]
                    base = np.array([seedrow[n] for n in POWER_NAMES])
                    rng = np.random.default_rng(731 + 100*index + di)
                    perturbations = []
                    for radius in (.01, .035, .08):
                        for _ in range(4):
                            q = np.clip(base + rng.uniform(-radius, radius, 5), 0., 1.)
                            perturbations.extend([q, q[::-1]])
                    ev.stage = f'asymmetry_check_deadline_{deadline:.6g}'
                    list(pool.map(ev.evaluate, perturbations))
                # Rerank independent fine simulations, then recover any small
                # deadline crossing caused by the finer discretization.
                candidates = ev.feasible_rows()[:6]
                powers = [np.array([r[n] for n in POWER_NAMES]) for r in candidates]
                for power in powers:
                    r = ev.evaluate(power, .025, 2, f'fine_deadline_{deadline:.6g}')
                    if not r['feasible'] or r['first_success_s'] > deadline + 1e-7:
                        for bump in (.001, .003, .008):
                            adjusted = np.minimum(1., power*(1.+bump)+bump*.1)
                            rr = ev.evaluate(adjusted, .025, 2, 'fine_deadline_repair')
                            if rr['feasible'] and rr['first_success_s'] <= deadline + 1e-7:
                                break
                selected = ev.feasible_rows(fine=True)
                if not selected:
                    raise RuntimeError(f'No fine feasible candidate: {case} deadline {deadline}')
                r = selected[0]
                frontier.append(dict(case=case, deadline_s=deadline,
                    search_scope='symmetric_DE_Powell_plus_asymmetric_neighborhood',
                    optimality_claim='finite_search_best_found',
                    **{k:v for k,v in r.items() if k != 'case'}))
                print(f'{case} deadline={deadline:.6f}: E={r["E_aux_J"]:.6f} J, '
                      f'stop={r["stop_s"]:.6f}, q={[r[n] for n in POWER_NAMES]}, '
                      f'candidates={len(ev.rows)}', flush=True)
                save(all_rows + ev.rows, 'constant_optimization_search.csv')
                save(frontier, 'constant_time_frontier.csv')
        r = ev.feasible_rows(m.Q_TIME, fine=True)[0]
        power = np.array([r[n] for n in POWER_NAMES])
        s,h,*_ = m.simulate(temp, kind='constant', power=power, params=ev.params,
                             dt=.025, scale=2, post=60., record=True)
        parameters.append(dict(case=case, hold_s=2., deadline_s=m.Q_TIME,
                               **dict(zip(POWER_NAMES, power))))
        results.append(dict(case=case, strategy='constant_optimized',
                            **dict(zip(POWER_NAMES, power)), **s))
        save(pd.DataFrame(h, columns=m.HISTORY), f'trajectory_{case}_constant_optimized.csv')
        all_rows.extend(ev.rows)
        save(results, 'optimized_constant_results.csv')
        save(parameters, 'optimized_constant_parameters.csv')
        save(baselines, 'constant_baselines.csv')
        save(all_rows, 'constant_optimization_search.csv')
    # Frontier selection across the union of all evaluated candidates guarantees
    # nested-deadline consistency within the finite set actually searched.
    union = pd.DataFrame(all_rows)
    frontier = []
    for case in initial['case']:
        for deadline in DEADLINES:
            candidates = union[(union['case']==case) & union['feasible'] &
                (union['mesh_scale']==2) & (union['first_success_s']<=deadline+1e-7)]
            r = candidates.sort_values(['E_aux_J','stop_s']).iloc[0].to_dict()
            frontier.append(dict(deadline_s=deadline,
                optimality_claim='finite_search_best_found', **r))
    save(frontier, 'constant_time_frontier.csv')
    save([dict(elapsed_wall_s=time.perf_counter()-start, workers=args.workers,
               coarse_dt_s=.05, coarse_mesh_scale=1, final_dt_s=.025,
               final_mesh_scale=2, hold_s=2., deadline_s=m.Q_TIME,
               DE_maxiter=args.maxiter, DE_popsize=args.popsize,
               evaluated_unique_candidates=len(all_rows),
               target='minimum_auxiliary_energy_subject_to_common_success_hold_and_deadline',
               optimality_claim='finite_search_best_found')], 'constant_search_metadata.csv')
    print('Completed constant benchmark and time frontier.', flush=True)


if __name__ == '__main__':
    main()
