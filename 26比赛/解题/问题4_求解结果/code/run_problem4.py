"""Reproduce Q4: FVM precooling, offline controller tuning, scan, validation, CSV.

python code/run_problem4.py [--reuse-controls] [--skip-precool]
Optimization is deterministic (fixed seeds). All evaluated candidates are saved.
"""
import bootstrap
from pathlib import Path
import argparse,csv,time,hashlib,platform,sys
import numpy as np
import pandas as pd

import control_model as m

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
IDX=[0,1,2,3,4,11]
BOUNDS=[(.2,4.),(5.,190.),(.025,.65),(.0005,.07),(.1,2.),(0.,.4)]

def save(rows,name):
    df=pd.DataFrame(rows);df.to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')

def simulate_case(temp,params,**kwargs):return m.simulate(temp,params=params,**kwargs)

def optimize_case(case,temp,previous=None):
    from reoptimize_controls import optimize
    starts=[] if previous is None else [previous]
    return optimize(case,temp,starts)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-controls',action='store_true')
    parser.add_argument('--skip-precool',action='store_true');parser.add_argument('--resume-search',action='store_true');args=parser.parse_args()
    DATA.mkdir(exist_ok=True)
    if not args.skip_precool:
        from precooling import export_precooling
        export_precooling(ROOT)
    init=pd.read_csv(DATA/'initial_temperature_cases.csv')
    names=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
    cases={r['case']:r[names].to_numpy(float) for _,r in init.iterrows()}
    if args.reuse_controls:
        old=pd.read_csv(DATA/'optimized_parameters.csv')
        controls={r['case']:r[m.PARAM_NAMES].to_numpy(float) for _,r in old.iterrows()}
    else:
        controls={};all_trace=[]
        previous={}
        if args.resume_search and (DATA/'optimized_parameters.csv').exists():
            old=pd.read_csv(DATA/'optimized_parameters.csv')
            previous={r['case']:r[m.PARAM_NAMES].to_numpy(float) for _,r in old.iterrows()}
        for case,temp in cases.items():
            controls[case],trace=optimize_case(case,temp,previous.get(case));all_trace.extend(trace)
            save([dict(case=k,**dict(zip(m.PARAM_NAMES,p))) for k,p in controls.items()],'optimized_parameters.csv')
        save(all_trace,'optimization_search.csv')
    mainrows=[];convergence=[];sensitivity=[];robustness=[]
    for case,temp in cases.items():
        for strategy in ('dynamic','constant_hold','constant_first'):
            p=controls[case].copy() if strategy=='dynamic' else m.DEFAULT.copy()
            if strategy=='constant_first':p[5]=0.
            s,h,states,final=m.simulate(temp,kind='dynamic' if strategy=='dynamic' else 'constant',
                         params=p,dt=.025,scale=2,post=60.,record=True)
            mainrows.append(dict(case=case,strategy=strategy,**s))
            save(hframe(h),f'trajectory_{case}_{strategy}.csv')
            cfg=m.make_config(scale=2,j0=m.J0);fields=[]
            for k,state in enumerate(states):
                x=np.cumsum(cfg.dx)-cfg.dx/2
                for n in range(len(x)):
                    fields.append(dict(cell=k+1,x_um=x[n]*1e6,time_s=s['elapsed_s'],T_C=final[k],
                         vapor_kg_m3=state[0][n],liquid_kg_m3=state[1][n],ice_kg_m3=state[2][n],ice_bulk=state[2][n]/920))
            save(fields,f'final_fields_{case}_{strategy}.csv')
            print(case,strategy,{k:s[k] for k in ['feasible','E_aux_J','first_success_s','stop_s','post_min_T_C']},flush=True)
        for dt,scale,period in ((.1,1,.2),(.05,1,.2),(.025,1,.2),(.025,2,.2),(.0125,2,.2),(.025,4,.2),(.025,2,.1)):
            s=m.simulate(temp,params=controls[case],dt=dt,scale=scale,period=period)[0]
            convergence.append(dict(case=case,dt_s=dt,scale=scale,period_s=period,**s))
        for parameter,index in [('G',0),('G_EP',1),('h',5)]:
            for factor in (.8,1.2):
                thermal=m.THERMAL.copy();thermal[index]*=factor
                s=m.simulate(temp,params=controls[case],thermal=thermal,dt=.025,scale=2)[0]
                sensitivity.append(dict(case=case,parameter=parameter,factor=factor,**s))
        for parameter,index in [('T_target',0),('K_P',2),('K_I',3),('ice_warn',7),('delta_V',8)]:
            for factor in (.8,1.2):
                p=controls[case].copy();p[index]*=factor
                s=m.simulate(temp,params=p,dt=.025,scale=2)[0]
                sensitivity.append(dict(case=case,parameter=parameter,factor=factor,**s))
        # Fixed-gain stress tests. Independent random seeds, no retuning.
        for shift in (-1.,0.,1.):
            for seed in range(10):
                s=m.simulate(temp+shift,params=controls[case],dt=.025,scale=2,
                       noise_T=.2,noise_V=.005,seed=1000+seed)[0]
                robustness.append(dict(case=case,seed=1000+seed,noise_T_K=.2,noise_V_V=.005,initial_shift_K=shift,**s))
    save(mainrows,'main_results.csv');save(convergence,'startup_convergence.csv')
    save(sensitivity,'sensitivity.csv');save(robustness,'robustness.csv')
    scan=[]
    for _,r in pd.read_csv(DATA/'precooling_nodes.csv').iterrows():
        temp=r[names].to_numpy(float);p=m.DEFAULT.copy();p[5]=0.
        s,h,*_=m.simulate(temp,kind='constant',params=p,dt=.025,scale=2,record=True)
        scan.append(dict(cooling_min=r['cooling_min'],mean_capacity_C=r['mean_capacity_C'],**s))
        save(hframe(h),f'trajectory_scan_{int(r["cooling_min"]):03d}min.csv')
    save(scan,'constant_scan.csv')
    manifest=[]
    for sub in ('code','inputs'):
        for path in sorted((ROOT/sub).glob('*')):
            if path.is_file():manifest.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    save(manifest,'source_manifest.csv')
    save([dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,solver_dt=.025,
          mesh_scale=2,controller_period=.2,charge_budget=20.,horizon_s=m.Q_TIME)],'run_environment.csv')
    print('COMPLETE: numerical datasets written',flush=True)

def hframe(h):return pd.DataFrame(h,columns=m.HISTORY)
if __name__=='__main__':main()

