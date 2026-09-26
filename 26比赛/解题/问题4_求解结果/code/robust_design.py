"""Train on sensor/plant mismatch scenarios; validate using disjoint seeds.

Candidates reserve time for both first success and measured shutdown. Frozen controls
are evaluated on new seeds; finite tests are not a universal robustness proof.
"""
import bootstrap
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def save(rows,name):
    pd.DataFrame(rows).to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')
TRAIN=[(-1.,1.,1.2,1.2,2000),(0.,1.,1.2,1.,2001),(1.,.8,1.,.8,2002),
       (-1.,1.,1.,1.,2003),(0.,1.2,1.,1.2,2004),(1.,1.,.8,1.,2005)]
def trial(temp,p,z,dt=.05):
    shift,G,Gep,h,seed=z
    thermal=m.THERMAL.copy();thermal[0]*=G;thermal[1]*=Gep;thermal[5]*=h
    s=m.simulate(temp+shift,params=p,dt=dt,scale=2,thermal=thermal,
                 noise_T=.2,noise_V=.005,seed=seed)[0]
    return dict(seed=seed,noise_T_K=.2,noise_V_V=.005,initial_shift_K=shift,
                G_factor=G,G_EP_factor=Gep,h_factor=h,**s)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true')
    parser.add_argument('--reselect',action='store_true');parser.add_argument('--reuse-controls',action='store_true');args=parser.parse_args()
    if args.reuse_controls:
        reproduce();return
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    controls=pd.read_csv(DATA/'optimized_parameters.csv').set_index('case')
    params=[];results=[];search=[];checks=[];training=[];physical=[]
    cached_search={};cached_trials=[]
    if args.reselect:
        cached_search={(r['case'],int(r['candidate'])):r for r in pd.read_csv(DATA/'guarded_design_search.csv').to_dict('records')}
        cached_trials=pd.read_csv(DATA/'guarded_training_trials.csv').to_dict('records')
    if args.resume and (DATA/'guarded_parameters.csv').exists():
        params=pd.read_csv(DATA/'guarded_parameters.csv').to_dict('records')
        results=pd.read_csv(DATA/'guarded_results.csv').to_dict('records')
        completed={r['case'] for r in params}
        def prior(name):
            if not (DATA/name).exists():return []
            return [r for r in pd.read_csv(DATA/name).to_dict('records') if r['case'] in completed]
        search=prior('guarded_design_search.csv');checks=prior('guarded_robustness.csv')
        training=prior('guarded_training_trials.csv');physical=prior('guarded_parameter_validation.csv')
    names=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
    for _,r in initial.iterrows():
        case=r['case'];temp=r[names].to_numpy(float);original=controls.loc[case,m.PARAM_NAMES].to_numpy(float)
        if any(z['case']==case for z in params):
            print(case,'completed guarded design reused',flush=True);continue
        candidates=[original.copy()]
        if case=='case2':
            # Passive operation is a nominal lower bound, but may miss the
            # deadline under heat-transfer mismatch. Search an active reserve.
            for plan in (75.,85.,95.,105.):
                for ff in (0.,.5,1.):
                    p=m.DEFAULT.copy();p[0]=1.;p[1]=plan;p[2]=.05;p[3]=.005;p[11]=.05;p[12]=ff
                    candidates.append(p)
        if case!='case2':
            for factor in (.98,.94,.90,.84,.75):
                for target in (max(original[0],1.),max(original[0],2.),max(original[0],3.5)):
                    p=original.copy();p[1]*=factor;p[0]=target;candidates.append(p)
        survivors=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for n,p in enumerate(candidates):
                old=cached_search.get((case,n))
                if old is not None and all(abs(float(old[k])-v)<1e-8 for k,v in zip(m.PARAM_NAMES,p)):
                    nom={k:old[k] for k in list(m.SUMMARY)+['feasible','shutdown_mode','sensor_stop_margin_C']}
                    trials=[{k:v for k,v in z.items() if k not in ('case','candidate','stage')} for z in cached_trials if z['case']==case and int(z['candidate'])==n and z['stage']=='training']
                    if len(trials)!=len(TRAIN):raise RuntimeError('Incomplete cached training')
                else:
                    nom=m.simulate(temp,params=p,dt=.05,scale=2)[0]
                    trials=list(pool.map(lambda z:trial(temp,p,z),TRAIN))
                for z in trials:training.append(dict(case=case,candidate=n,stage='training',**z))
                passed=sum(z['feasible'] and z['first_success_s']<=m.Q_TIME-2. and z['stop_s']<=m.Q_TIME-2. for z in trials)
                good=nom['feasible'] and passed==len(TRAIN)
                search.append(dict(case=case,candidate=n,training_passed=passed,training_count=len(TRAIN),
                    all_training_passed=good,training_max_stop_s=max(z['stop_s'] for z in trials),
                    training_first_deadline_s=m.Q_TIME-2.,training_stop_deadline_s=m.Q_TIME-2.,**dict(zip(m.PARAM_NAMES,p)),**nom))
                if good:survivors.append((nom['E_aux_J'],p.copy(),n))
                save(search,'guarded_design_search.csv');save(training,'guarded_training_trials.csv')
                print(case,'guarded candidate',n,'E',round(nom['E_aux_J'],2),'training',passed,'/6',flush=True)
            if not survivors:raise RuntimeError('No control passes training: '+case)
            confirmed=[]
            for _,p,n in sorted(survivors,key=lambda z:z[0])[:4]:
                nom=m.simulate(temp,params=p,dt=.025,scale=2)[0]
                trials=list(pool.map(lambda z:trial(temp,p,z,.025),TRAIN))
                for z in trials:training.append(dict(case=case,candidate=n,stage='fine_confirmation',**z))
                if nom['feasible'] and all(z['feasible'] and z['first_success_s']<=m.Q_TIME-2. and z['stop_s']<=m.Q_TIME-2. for z in trials):
                    confirmed.append((nom['E_aux_J'],p.copy(),n))
            if not confirmed:raise RuntimeError('Fine training confirmation failed: '+case)
            _,p,chosen=min(confirmed,key=lambda z:z[0])
            params.append(dict(case=case,selected_training_candidate=chosen,**dict(zip(m.PARAM_NAMES,p))))
            s,h,*_=m.simulate(temp,params=p,dt=.025,scale=2,post=60,record=True)
            results.append(dict(case=case,strategy='guarded',**s))
            save(pd.DataFrame(h,columns=m.HISTORY),f'trajectory_{case}_guarded.csv')
            validation=[(shift,1.,1.,1.,seed) for shift in (-1.,0.,1.) for seed in range(6000,6010)]
            for z in pool.map(lambda z:trial(temp,p,z,.025),validation):checks.append(dict(case=case,**z))
            scenarios=[]
            for ix in range(3):
                for factor in (.8,1.2):
                    xyz=[1.,1.,1.];xyz[ix]=factor
                    scenarios.append((0.,*xyz,7000+2*ix+int(factor>1.)))
            scenarios.extend([(-1.,.8,1.2,1.2,7010),(1.,1.2,.8,.8,7011)])
            for z in pool.map(lambda z:trial(temp,p,z,.025),scenarios):physical.append(dict(case=case,**z))
        save(params,'guarded_parameters.csv');save(results,'guarded_results.csv')
        save(search,'guarded_design_search.csv');save(training,'guarded_training_trials.csv')
        save(checks,'guarded_robustness.csv');save(physical,'guarded_parameter_validation.csv')
        passed=sum(x['feasible'] for x in checks if x['case']==case)
        print(case,'guarded energy=',s['E_aux_J'],'independent validation=',passed,'/30',flush=True)
    print('Guarded design and independent validation complete',flush=True)

def reproduce():
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    controls=pd.read_csv(DATA/'guarded_parameters.csv').set_index('case')
    names=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C'];rows=[];noise=[];physical=[]
    for _,r in initial.iterrows():
        case=r['case'];temp=r[names].to_numpy(float);p=controls.loc[case,m.PARAM_NAMES].to_numpy(float)
        s,h,*_=m.simulate(temp,params=p,dt=.025,scale=2,post=60.,record=True)
        rows.append(dict(case=case,strategy='guarded',**s))
        save(pd.DataFrame(h,columns=m.HISTORY),f'trajectory_{case}_guarded.csv')
        scenarios=[(shift,1.,1.,1.,seed) for shift in (-1.,0.,1.) for seed in range(6000,6010)]
        extra=[]
        for ix in range(3):
            for factor in (.8,1.2):
                xyz=[1.,1.,1.];xyz[ix]=factor
                extra.append((0.,*xyz,7000+2*ix+int(factor>1.)))
        extra.extend([(-1.,.8,1.2,1.2,7010),(1.,1.2,.8,.8,7011)])
        with ThreadPoolExecutor(max_workers=4) as pool:
            noise.extend(dict(case=case,**z) for z in pool.map(lambda z:trial(temp,p,z,.025),scenarios))
            physical.extend(dict(case=case,**z) for z in pool.map(lambda z:trial(temp,p,z,.025),extra))
        print(case,'frozen guarded controls reproduced',flush=True)
    save(rows,'guarded_results.csv');save(noise,'guarded_robustness.csv');save(physical,'guarded_parameter_validation.csv')
if __name__=='__main__':main()
