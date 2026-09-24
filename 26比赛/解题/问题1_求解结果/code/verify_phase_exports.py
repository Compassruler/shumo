"""Independent checks using exported data, without rerunning the simulator."""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.python_deps'))
import numpy as np
from io_utils import write_csv
DAT=ROOT/'data';tests=[]
def read(name):
    with (DAT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def check(dataset,name,observed,tol):
    tests.append(dict(dataset=dataset,check=name,observed=float(observed),tolerance=tol,passed=bool(observed<=tol)))
for tag in ['main_minus20','main_minus25','bp_minus20','bp_minus25']:
    rows=read(tag+'.csv');a=lambda c:np.array([float(r[c]) for r in rows]);t=a('t_s');dt=np.diff(t)
    check(tag,'176_samples',abs(len(rows)-176),0)
    check(tag,'sample_times',np.max(abs(t-np.arange(176)*.2)),1e-10)
    check(tag,'all_steps_valid',np.max(a('ever_invalid'))+np.max(abs(a('model_valid')-1)),0)
    for p in ['cond','evap','dep','sub','frz','mlt','frz_pore','frz_mem','mlt_pore','mlt_mem']:
        mass=a('phase_'+p+'_kg_m2');rate=a('rate_'+p+'_kg_m2_s')
        check(tag,p+'_monotonic_cumulative',max(0.,-np.diff(mass).min()),1e-15)
        check(tag,p+'_interval_rate_integral',np.max(abs(rate[1:]*dt-np.diff(mass))),1e-14)
    ice=a('phase_frz_kg_m2')-a('phase_mlt_kg_m2')+a('phase_dep_kg_m2')-a('phase_sub_kg_m2')
    check(tag,'ice_from_phase_accounting',np.max(abs(a('water_ice_kg_m2')-ice)),1e-12)
    heat=2.5e6*(a('phase_cond_kg_m2')-a('phase_evap_kg_m2'))+333600*(a('phase_frz_kg_m2')-a('phase_mlt_kg_m2'))+2833600*(a('phase_dep_kg_m2')-a('phase_sub_kg_m2'))+a('heat_adsorption_J_m2')
    check(tag,'phase_heat_from_mass',np.max(abs(a('heat_phase_J_m2')-heat)),1e-7)
    prod=.018/(2*96485)*np.cumsum(np.r_[0,.5*(a('j_A_m2')[1:]+a('j_A_m2')[:-1])*dt])
    check(tag,'faraday_production_from_inputs',np.max(abs(a('water_produced_kg_m2')-prod)),1e-12)
    check(tag,'water_inventory_closure',np.max(abs(a('water_stored_kg_m2')-a('water_initial_kg_m2')-prod+a('water_out_kg_m2'))),1e-12)
    if tag.startswith('bp'):
        check(tag,'all_samples_subfreezing',max(0.,a('T_max_C').max()),0)
        check(tag,'subfreezing_no_melting',a('phase_mlt_kg_m2')[-1],0)
for name in ['含双极板修订_两工况352行工作数据.csv','五层基线_两工况352行工作数据.csv']:
    rows=read(name);pairs={(r['工况初温_摄氏度'],r['时间_s']) for r in rows}
    check(name,'352_unique_samples',abs(len(rows)-352)+abs(len(pairs)-352),0)
for name,cols,count in [('相变敏感性全时序.csv',['model','condition','parameter','multiplier'],108),('冻结系数情景全时序.csv',['model','condition','kf_s_inv'],36)]:
    groups={}
    for row in read(name):groups.setdefault(tuple(row[c] for c in cols),[]).append(row)
    check(name,'scenario_count',abs(len(groups)-count),0)
    check(name,'176_samples_per_scenario',max(abs(len(rr)-176) for rr in groups.values()),0)
    check(name,'all_scenarios_valid',max(float(r['ever_invalid'])+abs(float(r['model_valid'])-1) for rr in groups.values() for r in rr),0)
for model in ['main','bp']:
    p=json.loads((DAT/f'calibration_{model}.json').read_text())
    check(model,'only_j0_calibrated',0 if p['fitted_parameters']==['j0'] and not p['kf_is_fitted'] else 1,0)
    check(model,'all_phase_references_fixed',max(abs(p[k]-v) for k,v in dict(kf=1,km=1,kcond=1,kevap=1,kdep=.0001,ksub=.0001).items()),0)
write_csv(DAT/'相变输出独立核验.csv',tests)
failed=[t for t in tests if not t['passed']]
print(f'{len(tests)} checks; {len(failed)} failures')
if failed:print(failed);raise SystemExit(1)
