"""A separate margin-reserving alternative; preserves nominal optimization results.

Select among an explicit small grid using six training disturbances. Validate
the selected candidate on thirty new seed/initial-temperature combinations.
Finite tests are evidence, not a universal robustness proof.
"""
import bootstrap
from pathlib import Path
import numpy as np
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def save(rows,name):pd.DataFrame(rows).to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')
def main():
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    controls=pd.read_csv(DATA/'optimized_parameters.csv').set_index('case')
    params=[];results=[];search=[];checks=[]
    names=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
    for _,r in initial.iterrows():
        case=r['case'];temp=r[names].to_numpy(float);original=controls.loc[case,m.PARAM_NAMES].to_numpy(float)
        candidates=[original.copy()]
        if case!='case2':
            for factor in (.98,.95,.9,.85):
                for target in (max(original[0],1.),max(original[0],2.),max(original[0],3.)):
                    p=original.copy();p[1]*=factor;p[0]=target;candidates.append(p)
        best=None
        for n,p in enumerate(candidates):
            nom=m.simulate(temp,params=p,dt=.05,scale=2)[0]
            good=nom['feasible'];maxstop=nom['stop_s'];trained=0
            for shift in (-1.,1.):
                for seed in (2000,2001,2002):
                    s=m.simulate(temp+shift,params=p,dt=.05,scale=2,noise_T=.2,noise_V=.005,seed=seed)[0]
                    good=good and s['feasible'];maxstop=max(maxstop,s['stop_s']);trained+=int(s['feasible'])
            search.append(dict(case=case,candidate=n,training_passed=trained,training_count=6,
                               all_training_passed=good,training_max_stop_s=maxstop,**dict(zip(m.PARAM_NAMES,p)),**nom))
            if good and (best is None or nom['E_aux_J']<best[0]):best=(nom['E_aux_J'],p.copy())
        if best is None:raise RuntimeError(f'No guarded candidate passes training in {case}')
        p=best[1];params.append(dict(case=case,**dict(zip(m.PARAM_NAMES,p))))
        s,h,*_=m.simulate(temp,params=p,dt=.025,scale=2,post=60,record=True)
        results.append(dict(case=case,strategy='guarded',**s))
        save(pd.DataFrame(h,columns=m.HISTORY),f'trajectory_{case}_guarded.csv')
        for shift in (-1.,0.,1.):
            for seed in range(3000,3010):
                s=m.simulate(temp+shift,params=p,dt=.025,scale=2,noise_T=.2,noise_V=.005,seed=seed)[0]
                checks.append(dict(case=case,seed=seed,noise_T_K=.2,noise_V_V=.005,initial_shift_K=shift,**s))
        save(params,'guarded_parameters.csv');save(results,'guarded_results.csv')
        save(search,'guarded_design_search.csv');save(checks,'guarded_robustness.csv')
        passed=sum(x['feasible'] for x in checks if x['case']==case)
        print(case,'guarded E=',best[0],'validation=',passed,'/30',flush=True)
    print('Guarded alternatives completed',flush=True)
if __name__=='__main__':main()
