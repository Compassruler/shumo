"""Joint space/time refinement for the coldest Q4 case, fixed controller."""
from pathlib import Path
import csv
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"code"))
import bootstrap  # noqa: E402,F401
import numpy as np  # noqa: E402
import control_model as m  # noqa: E402


def read(name):
    with (ROOT/"data"/name).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    initial=next(r for r in read("initial_temperature_cases.csv") if r["case"]=="case1")
    parameters=next(r for r in read("optimized_parameters.csv") if r["case"]=="case1")
    temp=np.array([float(initial[k]) for k in [f"T{i}_C" for i in range(1,6)]+["TEL_C","TER_C"]])
    p=np.array([float(parameters[k]) for k in m.PARAM_NAMES])
    rows=[]
    for scale,dt in ((4,.0125),(8,.00625),(16,.003125)):
        start=time.perf_counter()
        summary,_,_,_=m.simulate(temp,params=p,dt=dt,scale=scale,period=.2,record=False)
        row=dict(case="case1",scale=scale,dt_s=dt,period_s=.2,
                 elapsed_wall_s=time.perf_counter()-start,**summary)
        rows.append(row)
        with (ROOT/"audit"/"coupled_convergence_case1.csv").open("w",encoding="utf-8-sig",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerows(rows)
        print({k:row[k] for k in ["case","scale","dt_s","elapsed_wall_s","E_aux_J","first_success_s","stop_s","max_ice_bulk","feasible"]},flush=True)


if __name__=="__main__":main()
