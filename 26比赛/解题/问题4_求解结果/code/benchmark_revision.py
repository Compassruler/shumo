"""Short runtime and baseline probe for the revision (no final-result writes)."""
import bootstrap
import time
import numpy as np
import pandas as pd
import control_model as m
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    initial = pd.read_csv(root/'data/initial_temperature_cases.csv')
    cols = [f'T{k}_C' for k in range(1,6)] + ['TEL_C','TER_C']
    for _, r in initial.iterrows():
        temp = r[cols].to_numpy(float)
        for q in ([0,0,0,0,0], [.2,.2,.2,.2,.2], [.4,.2,0,.2,.4], m.CONSTANT):
            start=time.perf_counter()
            s,*_=m.simulate(temp,kind='constant',power=np.asarray(q),dt=.05,scale=1)
            print(r['case'],list(q), {k: s[k] for k in ('feasible','first_success_s','stop_s','E_aux_J','min_voltage_V','max_ice_bulk')},'wall',time.perf_counter()-start,flush=True)
