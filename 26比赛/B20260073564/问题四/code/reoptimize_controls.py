"""Reoptimize observable feedback; deterministic multistart, full candidate log.

Auxiliary energy is the primary objective. Feasible candidates within 0.05%
of the best energy are ranked by startup time, then simultaneous temperature
spread. All chosen candidates are re-evaluated at the delivery fidelity.
"""
import bootstrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import argparse
import time
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, minimize
import control_model as m

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
IDX=[0,1,2,3,4,11]
BOUNDS=[(.4,5.),(15.,150.),(.015,.5),(.001,.08),(.1,2.),(0.,.4)]

def save(rows,name):
    pd.DataFrame(rows).to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')

def optimize(case,temp,starts,workers=4):
    trace=[];lock=Lock();start=time.perf_counter()
    # Compile each fidelity before parallel execution.
    reference=m.simulate(temp,kind='constant',dt=.1,scale=1)[0]
    Eref=max(reference['E_aux_J'],1.)
    passive=m.DEFAULT.copy();passive[[2,3,11,12]]=0.
    zero=m.simulate(temp,params=passive,dt=.025,scale=2)[0]
    if zero['feasible'] and zero['E_aux_J']==0:
        trace.append(dict(case=case,stage='zero_energy_lower_bound',evaluation_dt_s=.025,
             evaluation_scale=2,J=0.,**dict(zip(m.PARAM_NAMES,passive)),**zero))
        save(trace,f'optimization_search_{case}.csv')
        return passive,trace
    def evaluate(x,stage,dt=.1,scale=1):
        p=m.DEFAULT.copy();p[IDX]=np.clip(x,np.array(BOUNDS)[:,0],np.array(BOUNDS)[:,1])
        s=m.simulate(temp,params=p,dt=dt,scale=scale)[0]
        J=s['E_aux_J']/Eref if s['feasible'] else (10.+max(0.,-s['final_min_T_C'])/30.+s['E_aux_J']/Eref)
        record=dict(case=case,stage=stage,evaluation_dt_s=dt,evaluation_scale=scale,J=J,
                    **dict(zip(m.PARAM_NAMES,p)),**s)
        with lock:
            trace.append(record)
            if len(trace)%100==0:
                good=[r['E_aux_J'] for r in trace if r['feasible']]
                print(case,'evaluations',len(trace),'best_J_energy',min(good) if good else None,
                      'elapsed_s',round(time.perf_counter()-start,1),flush=True)
        return J
    # Search prior solutions afresh with the independent state observer.
    for p in starts:
        for factor in (.8,.9,1.,1.05):
            x=p[IDX].copy();x[1]*=factor;evaluate(x,'warm_start_recheck')
    evaluate(m.DEFAULT[IDX],'default_recheck')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for seed in (260927,42026):
            feasible=[r for r in trace if r['feasible']]
            seedp=min(feasible,key=lambda r:r['E_aux_J']) if feasible else None
            x0=np.array([seedp[m.PARAM_NAMES[i]] for i in IDX]) if seedp else m.DEFAULT[IDX]
            differential_evolution(lambda x:evaluate(x,f'DE_seed_{seed}'),BOUNDS,seed=seed,
                popsize=5,maxiter=12,tol=2e-4,polish=False,x0=x0,
                workers=pool.map,updating='deferred')
            save(trace,f'optimization_search_{case}.csv')
    feasible=sorted([r for r in trace if r['feasible']],key=lambda r:r['E_aux_J'])
    candidates=[];seen=set()
    for r in feasible:
        x=np.array([r[m.PARAM_NAMES[i]] for i in IDX]);key=tuple(np.round(x,7))
        if key not in seen:candidates.append(x);seen.add(key)
        if len(candidates)>=16:break
    if not candidates:raise RuntimeError('No coarse feasible controller '+case)
    for x in candidates:evaluate(x,'fine_rerank',.025,2)
    fine=[r for r in trace if r['feasible'] and r['evaluation_scale']==2]
    if not fine:raise RuntimeError('No fine feasible controller '+case)
    seedr=min(fine,key=lambda r:r['E_aux_J'])
    seedx=np.array([seedr[m.PARAM_NAMES[i]] for i in IDX])
    minimize(lambda x:evaluate(x,'fine_Powell',.025,2),seedx,method='Powell',bounds=BOUNDS,
             options={'maxfev':120,'xtol':.003,'ftol':1e-5})
    fine=[r for r in trace if r['feasible'] and r['evaluation_scale']==2]
    Emin=min(r['E_aux_J'] for r in fine)
    chosen=min([r for r in fine if r['E_aux_J']<=Emin*1.0005],
               key=lambda r:(r['first_success_s'],r['dTmax_K'],r['E_aux_J']))
    chosen['selected']=True
    save(trace,f'optimization_search_{case}.csv')
    print(case,'selected E',chosen['E_aux_J'],'first',chosen['first_success_s'],
          'stop',chosen['stop_s'],flush=True)
    return np.array([chosen[k] for k in m.PARAM_NAMES]),trace

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    starts={k:[] for k in initial['case']}
    for name in ('optimized_parameters.csv','guarded_parameters.csv'):
        if (DATA/name).exists():
            for _,r in pd.read_csv(DATA/name).iterrows():starts[r['case']].append(r[m.PARAM_NAMES].to_numpy(float))
    output=[];logs=[]
    cols=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
    for _,r in initial.iterrows():
        p,trace=optimize(r['case'],r[cols].to_numpy(float),starts[r['case']],args.workers)
        output.append(dict(case=r['case'],**dict(zip(m.PARAM_NAMES,p))));logs.extend(trace)
        save(output,'optimized_parameters.csv');save(logs,'optimization_search.csv')
    save([dict(parameter=m.PARAM_NAMES[i],lower=lo,upper=hi) for i,(lo,hi) in zip(IDX,BOUNDS)],
         'optimization_parameter_bounds.csv')
    print('Independent-observer controller search complete',flush=True)

if __name__=='__main__':main()
