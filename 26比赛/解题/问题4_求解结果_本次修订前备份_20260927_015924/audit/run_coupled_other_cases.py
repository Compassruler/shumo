"""Read-only model audit: jointly refine spatial and temporal meshes for cases 2/3."""
from pathlib import Path
import csv
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
import bootstrap
import control_model as model

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return {row['case']: row for row in csv.DictReader(stream)}

initial = rows(ROOT / 'data' / 'initial_temperature_cases.csv')
parameters = rows(ROOT / 'data' / 'optimized_parameters.csv')
target = ROOT / 'audit' / 'coupled_convergence_other_cases.csv'
completed = []
for scale, dt in [(4, .0125), (8, .00625), (16, .003125)]:
    for case in ['case2', 'case3']:
        temp = [float(initial[case][key]) for key in
                ['T1_C', 'T2_C', 'T3_C', 'T4_C', 'T5_C', 'TEL_C', 'TER_C']]
        params = [float(parameters[case][key]) for key in model.PARAM_NAMES]
        print(f'START {case} scale={scale} dt={dt}', flush=True)
        started = time.perf_counter()
        summary, _, _, _ = model.simulate(temp, params=params, scale=scale,
                                         dt=dt, period=.2, post=0., record=False)
        row = dict(case=case, scale=scale, dt_s=dt, period_s=.2,
                   elapsed_wall_s=time.perf_counter() - started, **summary)
        completed.append(row)
        with target.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerows(completed)
        print(f'DONE {case} scale={scale} E={row["E_aux_J"]:.12g} '
              f'ts={row["first_success_s"]:.12g} stop={row["stop_s"]:.12g} '
              f'maxice={row["max_ice_bulk"]:.12g} feasible={row["feasible"]} '
              f'wall={row["elapsed_wall_s"]:.3f}', flush=True)
