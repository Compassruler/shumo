"""Frozen-controller initialization/structure audits and finite deadline search.

All failures are exported. The 120 s horizon is an additional scenario beyond
Q4's inherited 20 C/cm2 comparison budget, never a replacement main result.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ.setdefault(key,'1')
import bootstrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import numpy as np
import pandas as pd
import control_model as m
import precooling as pc
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
COLS=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
def save(rows,name):pd.DataFrame(rows).to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')
def inputs():
 return (pd.read_csv(DATA/'initial_temperature_cases.csv'),pd.read_csv(DATA/'guarded_parameters.csv').set_index('case'),pd.read_csv(DATA/'optimized_parameters.csv').set_index('case'))
def initial_uncertainty():
 initial,guard,_=inputs();rows=[]
 profiles={'EP_colder':np.array([0,0,0,0,0,-3,-3.]),'EP_warmer':np.array([0,0,0,0,0,3,3.]),
 'cells_warmer_EP_colder':np.array([1,1,1,1,1,-1,-1.]),'cells_colder_EP_warmer':np.array([-1,-1,-1,-1,-1,1,1.]),
 'asymmetric_EP':np.array([0,0,0,0,0,-2,2.]),'asymmetric_cells':np.array([-1,-.5,0,.5,1,0,0.])}
 for _,r in initial.iterrows():
  case=r['case'];prior=r[COLS].to_numpy(float);p=guard.loc[case,m.PARAM_NAMES].to_numpy(float)
  tasks=[(strategy,name,shift,seed) for strategy in ('guarded','constant_hold') for name,shift in profiles.items() for seed in (8100,8101,8102)]
  def run(z):
   strategy,name,shift,seed=z
   s=m.simulate(prior+shift,observer_temp0=prior,kind='dynamic' if strategy=='guarded' else 'constant',params=p if strategy=='guarded' else m.DEFAULT,dt=.025,scale=2,noise_T=.2,noise_V=.005,seed=seed)[0]
   return dict(case=case,strategy=strategy,profile=name,seed=seed,**{f'initial_error_{k}_K':v for k,v in zip(COLS,shift)},**s)
  with ThreadPoolExecutor(max_workers=4) as pool:rows.extend(pool.map(run,tasks))
  save(rows,'independent_initialization_validation.csv');print('initial-prior',case,[(s,sum(x['feasible'] for x in rows if x['case']==case and x['strategy']==s)) for s in ('guarded','constant_hold')],flush=True)
def training_recheck():
 import robust_design as rd
 initial,guard,_=inputs();rows=[]
 for _,r in initial.iterrows():
  temp=r[COLS].to_numpy(float);p=guard.loc[r['case'],m.PARAM_NAMES].to_numpy(float)
  with ThreadPoolExecutor(max_workers=3) as pool:
   for z in pool.map(lambda z:rd.trial(temp,p,z,.025),rd.TRAIN):
    rows.append(dict(case=r['case'],training_reserve_passed=z['feasible'] and z['first_success_s']<=m.Q_TIME-2 and z['stop_s']<=m.Q_TIME-2,**z))
 save(rows,'guarded_training_recheck.csv')

def effective_materials():
 cfg=m.make_config(scale=2);st=m.initial_state(cfg,243.15);mv,ml,mi,_,_=st
 C=cfg.Cdry+cfg.eps*cfg.cg+ml*4182
 k=cfg.kdry+cfg.eps*cfg.kg
 mats=pc.MATERIALS.copy();counts=np.array([8,3,6,4,8])*2;start=0
 for name,n in zip(pc.MEA_ORDER,counts):
  mat=mats[name];end=start+n;cap=np.dot(C[start:end],cfg.dx[start:end]);res=np.sum(cfg.dx[start:end]/k[start:end])
  mats[name]=pc.Material(mat.thickness_m,cap/mat.thickness_m,1.,mat.thickness_m/res,mat.cells);start=end
 return mats
def structure():
 initial,guard,nom=inputs();old=pc.MATERIALS.copy();pc.MATERIALS.update(effective_materials())
 model=pc.PrecoolModel();fields=model.scan([20,40],dt=.25);pc.MATERIALS.clear();pc.MATERIALS.update(old)
 # MEA-equivalent constants in the sensitivity model are recomputed from layers.
 rows=[];initial_rows=[]
 for _,r in initial.iterrows():
  case=r['case'];prior=r[COLS].to_numpy(float)
  for label,change_cooling,change_boundary in [('baseline',False,False),('endplate_convection',False,True),('effective_precooling',True,False),('both_consistent',True,True)]:
   temp=model.node_temps(fields[float(r.cooling_min)]) if change_cooling and r.cooling_min>0 else prior.copy()
   thermal=m.THERMAL.copy();thermal[3]=float(change_boundary)
   initial_rows.append(dict(case=case,structure=label,**dict(zip(COLS,temp)),cell_range_K=np.ptp(temp[:5]),mean_cell_C=np.mean(temp[:5])))
   for strategy,params in [('guarded',guard.loc[case,m.PARAM_NAMES].to_numpy(float)),('dynamic',nom.loc[case,m.PARAM_NAMES].to_numpy(float)),('constant_hold',m.DEFAULT)]:
    s=m.simulate(temp,observer_temp0=prior,kind='constant' if strategy=='constant_hold' else 'dynamic',params=params,thermal=thermal,dt=.025,scale=2,post=60)[0]
    rows.append(dict(case=case,structure=label,strategy=strategy,controller_parameters='frozen',observer_prior='baseline_precooling',**s))
  print('structure',case,flush=True)
 frame=pd.DataFrame(rows);frame['energy_rank_feasible']=frame.where(frame.feasible).groupby(['case','structure']).E_aux_J.rank(method='min')
 save(frame,'structural_comparison.csv');save(initial_rows,'structural_initial_temperatures.csv')
 layers=[dict(layer=name,k_W_mK=mat.k_W_mK,capacity_J_m2K=mat.capacity_J_m2K) for name,mat in effective_materials().items()]
 save(layers,'consistent_precooling_materials.csv')
def deadlines():
 initial,guard,nom=inputs();rows=[];best=[]
 for _,r in initial.iterrows():
  case=r['case'];temp=r[COLS].to_numpy(float);pn=nom.loc[case,m.PARAM_NAMES].to_numpy(float);pg=guard.loc[case,m.PARAM_NAMES].to_numpy(float)
  for deadline in (60.,90.,m.Q_TIME,120.):
   candidates=[pn.copy(),pg.copy(),m.DEFAULT.copy()]
   passive=m.DEFAULT.copy();passive[[2,3,11,12]]=0.;candidates.append(passive)
   for base in (pn,pg):
    for target in (.5,1.,2.,3.5,5.):
     for factor in (.45,.65,.8,.95,1.,1.05):
      p=base.copy();p[0]=target;p[1]=deadline*factor;candidates.append(p)
   unique={tuple(np.round(p,10)):p for p in candidates};candidates=list(unique.values())
   def run(z):
    idx,p=z;s=m.simulate(temp,observer_temp0=temp,params=p,dt=.05,scale=1,horizon=deadline)[0]
    return dict(case=case,deadline_s=deadline,within_main_budget=deadline<=m.Q_TIME+1e-8,candidate=idx,stage='coarse',**dict(zip(m.PARAM_NAMES,p)),**s)
   with ThreadPoolExecutor(max_workers=4) as pool:trial=list(pool.map(run,enumerate(candidates)))
   rows.extend(trial)
   chosen=sorted([x for x in trial if x['feasible']],key=lambda x:(x['E_aux_J'],x['first_success_s']))[:4]
   fine=[]
   for x in chosen:
    p=np.array([x[k] for k in m.PARAM_NAMES]);s=m.simulate(temp,observer_temp0=temp,params=p,dt=.025,scale=2,horizon=deadline)[0]
    y=dict(case=case,deadline_s=deadline,within_main_budget=deadline<=m.Q_TIME+1e-8,candidate=x['candidate'],stage='fine',**dict(zip(m.PARAM_NAMES,p)),**s);rows.append(y);fine.append(y)
   ok=[x for x in fine if x['feasible']]
   if ok:chosen=min(ok,key=lambda x:(x['E_aux_J'],x['first_success_s']));best.append(dict(optimality_claim='finite_candidate_best_found',**chosen))
   else:best.append(dict(case=case,deadline_s=deadline,within_main_budget=deadline<=m.Q_TIME+1e-8,feasible=False,E_aux_J=np.nan,first_success_s=np.nan,stop_s=np.nan,optimality_claim='no_feasible_fine_candidate_found'))
   save(rows,'dynamic_deadline_candidates.csv');save(best,'dynamic_deadline_frontier.csv')
   print('deadline',case,deadline,'E',best[-1]['E_aux_J'],'feasible',best[-1]['feasible'],flush=True)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['initial','structure','deadlines','all'],default='all');a=parser.parse_args()
 # Compile once before concurrent solver calls.
 m.simulate(np.full(7,-30.),observer_temp0=np.full(7,-30.),horizon=.025,dt=.025,scale=2)
 if a.stage in ('initial','all'):initial_uncertainty();training_recheck()
 if a.stage in ('structure','all'):structure()
 if a.stage in ('deadlines','all'):deadlines()
if __name__=='__main__':main()
