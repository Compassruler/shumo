"""Independent parity and conservation checks against the existing Q1 solver."""
from pathlib import Path
import sys,csv,importlib.util
from stack_model import simulate,advance,network,THERMAL
from fast_cell import make_config,initial_state,cell_step_full,electro,properties
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'inputs'/'model_q1_reference.py'
spec=importlib.util.spec_from_file_location('reference_q1',source)
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
rows=[]

def check(name,value,tol,detail=''):
    rows.append({'check':name,'measured':float(value),'tolerance':float(tol),
                 'passed':bool(value<=tol),'detail':detail})
    if value>tol:raise AssertionError((name,value,tol))

def cell_parity(scale,T0):
    cfg=make_config(scale=scale)
    model=ref.Model(bp=False,scale=scale,j0=cfg.j0)
    old=initial_state(cfg,T0)
    fast=tuple(x.copy() for x in old)
    maxstate=maxe=maxphase=maxprop=0.
    names=('V_model_V','E_rev_V','eta_act_V','eta_ohm_V','eta_con_V','j_lim_A_m2',
           'j_over_jlim','lambda_mean','lambda_min','kappa_min_S_m','cO2_cCL_mol_m3','active_area_factor')
    for n in range(240):
        T=T0+30*n/239.;j=2000.+2500*np.sin(n/70.)**2;dt=.025
        mv,ml,mi,heat,prod,out,amounts=model.mass_step(np.full(model.n,T),*old[:3],j,dt)
        nh,no,_=model.gas_step(np.full(model.n,T),ml,mi,old[3],old[4],j,dt)
        old=(mv,ml,mi,nh,no)
        fast,ph,pr,ou,amount=cell_step_full(cfg,fast,T,j,dt)
        maxstate=max(maxstate,max(np.max(np.abs(a-b)/(1+np.abs(a))) for a,b in zip(old,fast)))
        ev=model.electro(np.full(model.n,T),ml,mi,nh,no,j)
        ee=electro(cfg,fast,T,j)
        expected=np.array([ev[k] for k in names])
        maxe=max(maxe,np.max(np.abs(expected-ee)/(1+np.abs(expected))))
        maxphase=max(maxphase,abs(ph-np.dot(heat,model.dx)),abs(pr-prod),abs(ou-out))
        C,K=model.properties(mv,ml,mi)
        cp,rp=properties(cfg,fast)
        maxprop=max(maxprop,abs(cp-np.dot(C,model.dx)),abs(rp-np.sum(model.dx/K)))
    check(f'cell_state_parity_scale{scale}_T{T0}',maxstate,1e-9)
    check(f'cell_electro_parity_scale{scale}_T{T0}',maxe,1e-9)
    check(f'cell_phase_parity_scale{scale}_T{T0}',maxphase,1e-8)
    check(f'cell_properties_parity_scale{scale}_T{T0}',maxprop,1e-8)

for scale,T0 in ((1,253.15),(2,248.15)):
    cell_parity(scale,T0)

# Independent geometry inventory: N MEAs require N-1 shared + 2 terminal plates.
# Derive expectations from material data rather than reuse model BP constants.
cfg=make_config();states=tuple(initial_state(cfg,263.15) for _ in range(3))
c,g,h,conduct=network(cfg,states,THERMAL)
mea_c,mea_r=properties(cfg,states[0])
one_plate=0.002*1980.*766.
for k,nplates in enumerate((1.5,1.,1.)):
    check(f'plate_capacity_node_{k+1}_J_m2K',abs(c[k]-mea_c-nplates*one_plate),1e-9)
plate_total=float(np.dot(np.array([2.,2.,1.]),c[:3]-mea_c))
check('stack_six_plate_inventory_J_m2K',abs(plate_total-(5-1+2)*one_plate),1e-9)
expected_g=1./(mea_r+0.002/95.)
for k in (0,1):
    check(f'single_shared_plate_conductance_{k}_W_m2K',abs(conduct[k]-expected_g),1e-9)
check('terminal_full_plate_conductance_W_m2K',abs(conduct[2]-1./(.5*mea_r+.002/95.+.005/15.)),1e-9)
check('thermal_cell_pitch_m',abs(float(np.sum(cfg.dx))+(1./conduct[0]-mea_r)*95.-.0023267),1e-12)

# Independent 7-node implicit heat solve compared with the 4-node reduction.
cfg=make_config();states=tuple(initial_state(cfg,263.15) for _ in range(3))
temp=np.full(4,-10.);symmetry=0.
for z in range(200):
    ns,nt,en,wa,gg=advance(cfg,states,temp,-10.,5000./1e4,.05,THERMAL)
    c,g,h,conduct=network(cfg,ns,THERMAL)
    c7=np.array([c[3],c[0],c[1],c[2],c[1],c[0],c[3]])
    t7=np.array([temp[3],temp[0],temp[1],temp[2],temp[1],temp[0],temp[3]])
    G=np.zeros((7,7));edges=[conduct[2],conduct[0],conduct[1],conduct[1],conduct[0],conduct[2]]
    for i,v in enumerate(edges):
        G[i,i]+=v;G[i+1,i+1]+=v;G[i,i+1]-=v;G[i+1,i]-=v
    G[1,1]+=40;G[5,5]+=40
    latent=[]
    for k in range(3):
        _,ph,*_=cell_step_full(cfg,states[k],temp[k]+273.15,5000.,.05);latent.append(ph)
    phase=np.array([0.,latent[0],latent[1],latent[2],latent[1],latent[0],0.])
    rhs=c7/.05*t7+phase/.05;rhs[1]-=400.;rhs[5]-=400.
    tt=t7.copy()
    for iteration in range(30):
        gen=np.zeros(7)
        for i,k in ((1,0),(2,1),(3,2),(4,1),(5,0)):
            gen[i]=5000.*(1.48-electro(cfg,ns[k],tt[i]+273.15,5000.,10. if k==0 else 1.)[0])
        new=np.linalg.solve(G+np.diag(c7/.05),rhs+gen)
        err=np.max(abs(tt-new));tt=new
        if err<1e-9:break
    expected=np.array([nt[3],nt[0],nt[1],nt[2],nt[1],nt[0],nt[3]])
    symmetry=max(symmetry,np.max(abs(tt-expected)))
    states,temp=ns,nt
check('seven_node_vs_symmetric_reduction_K',symmetry,1e-8)

for kind,p in [('constant',[.5]),('ramp',[2.5,.5]),('step',[.2,.4,.5,5.,15.])]:
    s,h,*_=simulate(kind,p,dt=.025,scale=2,record=True)
    check(kind+'_heat_balance_J_m2',abs(s['energy_balance_J_m2']),1e-5)
    check(kind+'_water_balance_kg_m2',abs(s['water_balance_kg_m2']),1e-10)
    check(kind+'_charge_budget_violation',max(0,s['charge_C_cm2']-20.),1e-9)
    check(kind+'_current_limit_violation',max(0,s['max_current_A_cm2']-.5),1e-10)
    check(kind+'_voltage_violation',max(0,.30-s['min_voltage_V']),1e-9)

out=ROOT/'data'/'independent_verification.csv';out.parent.mkdir(exist_ok=True)
with out.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(f'{len(rows)} independent checks passed',flush=True)
