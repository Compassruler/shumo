"""Reproducible constrained control-vector search and all question-2 exports."""
from pathlib import Path
import csv
import json
import time
import argparse
from stack_model import simulate, HISTORY_NAMES, THERMAL, PLATE_MODEL_VERSION
import numpy as np
from scipy.optimize import differential_evolution, minimize_scalar, minimize

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DATA.mkdir(exist_ok=True,parents=True)
TRACE=[]

def write_csv(name,rows,fields=None):
    rows=list(rows)
    if not rows and fields is None:return
    fields=fields or list(dict.fromkeys(key for row in rows for key in row))
    with (DATA/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def export_trajectory(name,kind,p,T0,dt=.0125,scale=2,output_interval=.05,**kwargs):
    s,h,states,temp=simulate(kind,p,T0=T0,dt=dt,scale=scale,record=True,**kwargs)
    if output_interval>dt and len(h)>2:
        # Export 20-Hz work data plus terminal, switching and extrema rows.
        # All path extrema in summary remain evaluated at EVERY internal step.
        indices=set(np.searchsorted(h[:,0],np.arange(0,h[-1,0],output_interval)).tolist())
        indices.update([0,len(h)-1])
        for k in range(3):
            indices.add(int(np.argmin(h[:,7+21*k])))
            indices.add(int(np.argmax(h[:,19+21*k])))
        indices.update((np.flatnonzero(np.diff(h[:,0])<1e-9)+1).tolist())
        if kind=='step':
            for switch in p[(len(p)+1)//2:]:
                idx=int(np.searchsorted(h[:,0],switch))
                if idx<len(h):indices.update([max(idx-1,0),idx])
        h=h[np.array(sorted(indices))]
    write_csv(f'trajectory_{name}.csv',(dict(zip(HISTORY_NAMES,r)) for r in h),HISTORY_NAMES)
    # Explicit five-cell records (mirror cells are not missing observations).
    records=[]
    for r in h:
        for k,representative in ((1,1),(2,2),(3,3),(4,2),(5,1)):
            rec={'time_s':r[0],'cell':k,'j_A_cm2':r[1],'charge_C_cm2':r[2],
                 'temperature_C':r[2+representative]}
            start=7+21*(representative-1)
            for key,val in zip(HISTORY_NAMES[start:start+21],r[start:start+21]):
                rec[key.replace(f'cell{representative}_','')]=val
            records.append(rec)
    write_csv(f'cells_{name}.csv',records)
    # Terminal one-dimensional water/ice distributions, all 5 cells.
    from fast_cell import make_config
    cfg=make_config(scale=scale)
    x=np.cumsum(cfg.dx)-cfg.dx/2
    labels=np.repeat(['aGDL','aCL','PEM','cCL','cGDL'],np.array([8,3,6,4,8])*scale)
    fields=[]
    for k,rep in ((1,0),(2,1),(3,2),(4,1),(5,0)):
        for i in range(len(x)):
            fields.append({'cell':k,'time_s':s['end_time_s'],'x_um':x[i]*1e6,'layer':labels[i],
                'temperature_C':temp[rep],'mv_kg_m3':states[rep][0][i],
                'ml_kg_m3':states[rep][1][i],'mi_kg_m3':states[rep][2][i],
                'ice_bulk':states[rep][2][i]/920})
    write_csv(f'fields_terminal_{name}.csv',fields)
    return s

def decode(kind,x):
    if kind=='constant':return [float(x[0])]
    if kind=='ramp':return [float(x[0]/x[1]),float(x[0])]
    n=(len(x)+1)//2
    return list(map(float,x[:n]))+list(np.cumsum(x[n:]))

def bounds_for(kind,n=3):
    if kind=='constant':return [(0.,.5)]
    if kind=='ramp':return [(1e-6,.5),(.2,120.)]
    return [(0.,.5)]*n+[(.2,60.)]*(n-1)

def seed_for(kind,n=3):
    if kind=='constant':return [.5]
    if kind=='ramp':return [.5,.2]
    return [.5]*n+[8.]*(n-1)

def score(s):
    if s['status']=='success':return s['end_time_s']
    return (1000+100*max(0.,-s['min_end_temperature_C'])
            +10000*max(0.,.30-s['min_voltage_V'])
            +(10000 if s['status']=='physical_invalid' else 0))

def optimize(kind,T0=-10.,seeds=(17,43),maxiter=24,popsize=6,dt=.1,scale=1,n=3,tag='main'):
    bounds=bounds_for(kind,n)
    best=[np.inf,None,None]
    def objective(x):
        p=decode(kind,x)
        s,*_=simulate(kind,p,T0=T0,dt=dt,scale=scale)
        value=score(s)
        if value<best[0]:best[:]=[value,p,s]
        TRACE.append({'tag':tag,'strategy':kind,'T0_C':T0,'dt_s':dt,'grid_scale':scale,
                      'parameters':json.dumps(p),'objective':value,**s})
        return value
    objective(seed_for(kind,n))
    if kind=='constant':
        grid=np.linspace(0.,.5,26)
        vals=[objective([v]) for v in grid]
        idx=int(np.argmin(vals))
        lo=grid[max(idx-1,0)];hi=grid[min(idx+1,len(grid)-1)]
        minimize_scalar(lambda z:objective([z]),bounds=(lo,hi),method='bounded',options={'xatol':1e-5})
    else:
        for seed in seeds:
            result=differential_evolution(objective,bounds,seed=seed,popsize=popsize,
                maxiter=maxiter,polish=False,x0=seed_for(kind,n),tol=1e-6,atol=1e-5)
            minimize(objective,result.x,method='Powell',bounds=bounds,
                     options={'maxiter':2,'maxfev':160,'xtol':.002,'ftol':1e-6})
    print(tag,T0,kind,'best',best[1],best[2]['status'],best[2]['end_time_s'],flush=True)
    return best[1],best[2]

def temperature_boundary(kind,p,dt=.0125,scale=2,thermal=None,cell_kwargs=None):
    warm=-5.;cold=-25.
    records=[]
    for _ in range(12):
        mid=.5*(cold+warm)
        s,*_=simulate(kind,p,T0=mid,dt=dt,scale=scale,thermal=thermal,**(cell_kwargs or {}))
        records.append({'strategy':kind,'T0_C':mid,'dt_s':dt,'grid_scale':scale,
                        'parameters':json.dumps(p),**s})
        if s['status']=='success':warm=mid
        else:cold=mid
    return cold,warm,records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-search',action='store_true')
    args=parser.parse_args()
    start=time.time()
    searchfile=DATA/'optimized_parameters.json'
    if args.reuse_search and searchfile.exists():
        opt=json.loads(searchfile.read_text(encoding='utf-8'))
    else:
        opt={}
        for kind in ('constant','ramp','step'):
            p,s=optimize(kind)
            opt[kind]=p
        searchfile.write_text(json.dumps(opt,indent=2),encoding='utf-8')
        write_csv('optimization_trace.csv',TRACE)
    summary=[]
    for kind,p in opt.items():
        s=export_trajectory(kind,kind,p,-10.)
        summary.append({'strategy':kind,'T0_C':-10,'parameters':json.dumps(p),
                        'dt_s':.0125,'grid_scale':2,**s})
    write_csv('strategy_summary.csv',summary)
    print('FINAL',json.dumps(summary),flush=True)
    # Refinement in time, space and both. Include scale4 to expose interface errors.
    convergence=[]
    for kind,p in opt.items():
        for scale,dt in ((1,.1),(1,.05),(1,.025),(2,.05),(2,.025),(2,.0125),(4,.0125),(4,.00625)):
            s,*_=simulate(kind,p,dt=dt,scale=scale)
            convergence.append({'strategy':kind,'grid_scale':scale,'dt_s':dt,**s})
    write_csv('convergence.csv',convergence)
    # Ramp has no supplied slew limit: test practical finite ramps toward constant limit.
    ramp_limit=[]
    for tp in (60.,30.,10.,5.,1.,.5,.2,.1,.05,.02,.01):
        s,*_=simulate('ramp',[.5/tp,.5],dt=.0125,scale=2)
        ramp_limit.append({'plateau_time_s':tp,'slope_A_cm2_s':.5/tp,**s})
    write_csv('ramp_slope_limit.csv',ramp_limit)
    # Coarse per-temperature reoptimization; failures mean no feasible point FOUND.
    temperature=[]
    for T0 in (-10.,-11.,-12.,-12.5,-12.75,-13.,-14.,-16.,-20.):
        for kind in ('constant','ramp','step'):
            if not args.reuse_search:
                p,s=optimize(kind,T0,seeds=(89,),maxiter=9,popsize=4,tag='temperature')
            else:
                p=opt[kind];s,*_=simulate(kind,p,T0=T0,dt=.1)
            fine,*_=simulate(kind,p,T0=T0,dt=.0125,scale=2)
            temperature.append({'strategy':kind,'T0_C':T0,'parameters':json.dumps(p),
                                'dt_s':.0125,'grid_scale':2,**fine})
        write_csv('temperature_search.csv',temperature)
    if TRACE:write_csv('optimization_trace.csv',TRACE)
    boundary={};brackets=[]
    for kind,p in opt.items():
        cold,warm,rows=temperature_boundary(kind,p)
        boundary[kind]={'cold_infeasible_C':cold,'warm_feasible_C':warm,'parameters':p}
        brackets+=rows
    write_csv('temperature_bisection.csv',brackets)
    bestkind=min(boundary,key=lambda k:boundary[k]['warm_feasible_C'])
    cold=boundary[bestkind]['cold_infeasible_C'];warm=boundary[bestkind]['warm_feasible_C']
    export_trajectory('critical_success',bestkind,opt[bestkind],warm)
    export_trajectory('critical_failure',bestkind,opt[bestkind],cold)
    export_trajectory('below_critical',bestkind,opt[bestkind],float(np.floor(cold)-1))
    # Fine-grid boundary confirmation, independent of the optimization grid.
    for scale,dt in ((1,.025),(2,.0125),(4,.00625)):
        cl,wa,rows=temperature_boundary(bestkind,opt[bestkind],dt=dt,scale=scale)
        boundary[f'convergence_scale{scale}']={'cold_infeasible_C':cl,'warm_feasible_C':wa,'dt_s':dt}
    # Modest closure sensitivities, no re-fitting to favorable startup outcomes.
    sensitivities=[]
    cases=[('baseline',THERMAL.copy(),{})]
    for label,idx in [('intercell_conductance',0),('endplate_coupling',1),('endplate_capacity',2)]:
        for fac in (.8,1.2):
            th=THERMAL.copy();th[idx]=fac;cases.append((f'{label}_{fac}',th,{}))
    th=THERMAL.copy();th[3]=1.;cases.append(('convection_on_endplate',th,{}))
    th=THERMAL.copy();th[4]=1.;cases.append(('end_beta_1',th,{}))
    th=THERMAL.copy();th[5]=0.;cases.append(('fixed_dry_conductance',th,{}))
    for fac in (.1,10.):cases.append((f'freezing_rate_{fac}',THERMAL.copy(),{'kf':fac}))
    for label,th,kw in cases:
        s,*_=simulate(bestkind,opt[bestkind],dt=.025,scale=2,thermal=th,**kw)
        cl,wa,_=temperature_boundary(bestkind,opt[bestkind],dt=.025,scale=2,thermal=th,cell_kwargs=kw)
        sensitivities.append({'case':label,'dt_s':.025,'grid_scale':2,'critical_cold_C':cl,'critical_warm_C':wa,**s})
    write_csv('sensitivity.csv',sensitivities)
    # Optional strategy-mesh verification: the constant control is admissible for all N.
    strategy_mesh=[]
    for n in (2,3,4):
        if n==3 or args.reuse_search:p=opt['step'] if n==3 else [.5]*n+list(np.arange(1,n)*8.)
        else:p,_=optimize('step',n=n,seeds=(137,),maxiter=9,popsize=4,tag=f'steps_{n}')
        s,*_=simulate('step',p,dt=.0125,scale=2)
        strategy_mesh.append({'segments':n,'parameters':json.dumps(p),**s})
    write_csv('strategy_mesh.csv',strategy_mesh)
    if TRACE:write_csv('optimization_trace.csv',TRACE)
    (DATA/'critical_temperature.json').write_text(json.dumps(boundary,indent=2),encoding='utf-8')
    (DATA/'run_metadata.json').write_text(json.dumps({'elapsed_seconds':time.time()-start,
        'main_grid_scale':2,'main_dt_s':.0125,'optimization_dt_s':.1,
        'ramp_plateau_time_lower_bound_s':.2,'ramp_note':'Numerical search convention, NOT supplied hardware constraint; ramp_slope_limit.csv tests its removal.',
        'optimality':'best feasible found in defined strategy classes; no global certificate',
        'minimum_temperature_scope':'fixed optimized curves, checked against per-temperature reoptimization',
        'tmax_s':600,'event_target_C':1e-7,'plate_model_version':PLATE_MODEL_VERSION,
        'plate_positions':6,'bp_thickness_m':.002,'bp_capacity_per_plate_J_m2K':3033.36,
        'bp_node_fractions_five_cells':[1.5,1.,1.,1.,1.5],
        'bp_total_capacity_J_m2K':18200.16,'cell_pitch_m':.0023267},indent=2),encoding='utf-8')
    print('BOUNDARY',json.dumps(boundary),'elapsed',time.time()-start,flush=True)

if __name__=='__main__':main()
