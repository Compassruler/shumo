"""Question 2: conservative seven-node network, reduced by exact mirror symmetry.

Unique temperatures: [end cell, near-end cell, center cell, end plate].
All currents exposed by this module are A/cm2; cell kernels take A/m2.
The unmodified question-1 water and electrochemistry closures are in fast_cell.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.python_deps'))
import numpy as np
from numba import njit
from fast_cell import make_config, initial_state, cell_step, electro, properties, diagnostics

J0 = 0.10255839004732065
WEIGHTS = np.array([2., 2., 1.])
THERMAL = np.array([1., 1., 1., 0., 10., 1.])
# thermal: gc multiplier, gE multiplier, EP C multiplier, convection-on-EP,
# end beta, dynamic conductance flag.

@njit(cache=True)
def current(t, kind, p):
    if kind == 0:
        return p[0]
    if kind == 1:
        return min(p[0]*t, p[1])
    # arbitrary N steps: p=[j1,...,jN,t1,...,tN-1]
    n = (len(p)+1)//2
    stage = 0
    while stage < n-1 and t >= p[n+stage]-1e-10:
        stage += 1
    return p[stage]

@njit(cache=True)
def charge(t, kind, p):
    if kind == 0:
        return p[0]*t
    if kind == 1:
        tp = p[1]/p[0]
        return .5*p[0]*min(t,tp)**2 + p[1]*max(0.,t-tp)
    n = (len(p)+1)//2
    q = 0.
    left = 0.
    for k in range(n):
        right = t if k == n-1 else min(t,p[n+k])
        q += p[k]*max(0.,right-left)
        if right >= t:
            break
        left = right
    return q

@njit(cache=True)
def next_break(t, kind, p):
    if kind == 1:
        tp=p[1]/p[0]
        return tp if tp > t+1e-9 else 1e9
    if kind == 2:
        n=(len(p)+1)//2
        for k in range(n-1):
            if p[n+k]>t+1e-9:
                return p[n+k]
    return 1e9

@njit(cache=True)
def network(cfg, states, th):
    c = np.empty(4)
    r = np.empty(3)
    for k in range(3):
        cc,rr=properties(cfg,states[k])
        c[k]=cc+6066.72
        r[k]=rr if th[5]>0.5 else 0.002810469
    c[3]=39500.*th[2]
    g1=th[0]/(.5*(r[0]+r[1])+.004/95.)
    g2=th[0]/(.5*(r[1]+r[2])+.004/95.)
    ge=th[1]/(.5*r[0]+.002/95.+.005/15.)
    g=np.zeros((4,4))
    g[0,0]=g1+ge;g[0,1]=-g1;g[0,3]=-ge
    g[1,0]=-g1;g[1,1]=g1+g2;g[1,2]=-g2
    g[2,1]=-2*g2;g[2,2]=2*g2
    g[3,0]=-ge;g[3,3]=ge
    h=np.zeros(4)
    if th[3]>0.5:
        h[3]=1./(1./40.+.005/15.)
    else:
        h[0]=40.
    for k in range(4):
        g[k,k]+=h[k]
    return c,g,h,np.array([g1,g2,ge])

@njit(cache=True)
def evaluate(cfg, states, temp, j, th):
    e=np.empty((3,12));d=np.empty((3,9))
    for k in range(3):
        e[k]=electro(cfg,states[k],temp[k]+273.15,j*1e4,th[4] if k==0 else 1.)
        d[k]=diagnostics(cfg,states[k])
    return e,d

@njit(cache=True)
def advance(cfg, states, temp0, ambient, j, dt, th):
    s0,p0,w0,o0=cell_step(cfg,states[0],temp0[0]+273.15,j*1e4,dt)
    s1,p1,w1,o1=cell_step(cfg,states[1],temp0[1]+273.15,j*1e4,dt)
    s2,p2,w2,o2=cell_step(cfg,states[2],temp0[2]+273.15,j*1e4,dt)
    newstates=(s0,s1,s2)
    phase=np.array([p0,p1,p2,0.])
    c,g,h,conduct=network(cfg,newstates,th)
    a=g.copy()
    for k in range(4):
        a[k,k]+=c[k]/dt
    rhs0=c/dt*temp0+h*ambient+phase/dt
    temp=temp0.copy()
    gen=np.zeros(4)
    err=1.
    for iteration in range(30):
        for k in range(3):
            el=electro(cfg,newstates[k],temp[k]+273.15,j*1e4,th[4] if k==0 else 1.)
            gen[k]=j*1e4*(1.48-el[0])
        newtemp=np.linalg.solve(a,rhs0+gen)
        err=np.max(np.abs(newtemp-temp));temp=newtemp
        if err<1e-9:
            break
    energy=np.zeros(5)
    weight=np.array([2.,2.,1.,2.])
    energy[0]=np.dot(weight,gen)*dt
    energy[1]=np.dot(weight,phase)
    energy[2]=np.dot(weight,h*(temp-ambient))*dt
    energy[3]=np.dot(weight,c*(temp-temp0))
    energy[4]=err
    water=np.array([w0,w1,w2,o0,o1,o2])
    return newstates,temp,energy,water,conduct

SUMMARY_NAMES=['status','end_time_s','charge_C_cm2','max_current_A_cm2','min_voltage_V',
 'max_ice_bulk','max_pore_ice_saturation','min_end_temperature_C','max_temperature_spread_K',
 'energy_balance_J_m2','water_balance_kg_m2','min_gas_porosity','max_current_limiting_ratio',
 'min_kappa_S_m','max_thermal_iteration_error_K','heat_gen_J_m2','heat_phase_J_m2',
 'heat_loss_J_m2','heat_sensible_J_m2','end_voltage_V','center_temperature_C','failure_cell',
 'max_pore_ice_bulk','max_mem_ice_bulk']
STATUS={0:'success',1:'charge_exhausted',2:'voltage_limit',3:'physical_invalid',4:'time_limit'}
HISTORY_NAMES=['time_s','j_A_cm2','charge_C_cm2','T1_C','T2_C','T3_C','TEP_C']
E_NAMES=['V','Erev','eta_act','eta_ohm','eta_con','jlim_A_m2','j_over_jlim','lambda_mean','lambda_min','kappa_min','cO2','active_area']
D_NAMES=['ice_bulk','pore_ice_bulk','mem_ice_bulk','pore_ice_saturation','liquid_saturation','gas_porosity_min','inventory_min','water_kg_m2','ice_kg_m2']
for _k in (1,2,3):
    HISTORY_NAMES += [f'cell{_k}_{s}' for s in E_NAMES+D_NAMES]
HISTORY_NAMES += ['heat_gen_J_m2','heat_phase_J_m2','heat_loss_J_m2','heat_sensible_J_m2','energy_balance_J_m2','water_balance_kg_m2','g12_W_m2K','g23_W_m2K','gE_W_m2K']

@njit(cache=True)
def history_row(t,j,q,temp,e,d,energy,wb,conduct):
    row=np.empty(79)
    row[0]=t;row[1]=j;row[2]=q;row[3:7]=temp
    for k in range(3):
        row[7+21*k:19+21*k]=e[k]
        row[19+21*k:28+21*k]=d[k]
    row[70:74]=energy[:4]
    row[74]=energy[3]-energy[0]-energy[1]+energy[2]
    row[75]=wb
    row[76:79]=conduct
    return row

@njit(cache=True)
def simulate_raw(cfg, kind, p, T0, dt, tmax, th, record, stop_voltage):
    temp=np.full(4,T0)
    states=(initial_state(cfg,T0+273.15),initial_state(cfg,T0+273.15),initial_state(cfg,T0+273.15))
    t=0.;q=0.;j=current(t,kind,p)
    e,d=evaluate(cfg,states,temp,j,th)
    initial_water=np.dot(WEIGHTS,d[:,7])
    energy=np.zeros(5);water=np.zeros(6)
    c,g,h,conduct=network(cfg,states,th)
    nmax=int(tmax/dt)+len(p)+20 if record else 1
    history=np.empty((nmax,79));count=0
    if record:
        history[0]=history_row(t,j,q,temp,e,d,energy,0.,conduct);count=1
    vmax=float(np.min(e[:,0]));imax=float(np.max(d[:,0]));smax=float(np.max(d[:,3]))
    poremax=float(np.max(d[:,1]));memmax=float(np.max(d[:,2]))
    jmax=j;spread=0.;gmin=float(np.min(d[:,5]));ratio=float(np.max(e[:,6]));kmin=float(np.min(e[:,9]))
    status=4;failed=0;errmax=0.;wb=0.
    while t<tmax-1e-9:
        # Includes t=0 and right-hand limit after every current discontinuity.
        j=current(t,kind,p)
        e,d=evaluate(cfg,states,temp,j,th)
        vmax=min(vmax,float(np.min(e[:,0])))
        if np.min(e[:,0])<.30-1e-10 and stop_voltage:
            status=2;failed=int(np.argmin(e[:,0]))+1
            if record:
                history[count]=history_row(t,j,q,temp,e,d,energy,wb,conduct);count+=1
            break
        if np.min(temp[:3])>0 and np.max(d[:,0])<.99:
            status=0 if vmax>=.30-1e-10 else 2
            break
        step=min(dt,tmax-t,next_break(t,kind,p)-t)
        if charge(t+step,kind,p)>20.:
            lo=0.;hi=step
            for z in range(40):
                mid=.5*(lo+hi)
                if charge(t+mid,kind,p)>20.:hi=mid
                else:lo=mid
            step=lo
        if step<1e-10:
            status=1;break
        jm=(charge(t+step,kind,p)-charge(t,kind,p))/step
        newstates,newtemp,en,wa,conduct=advance(cfg,states,temp,T0,jm,step,th)
        # Locate success by reintegration of this single step, not extrapolation.
        if np.min(newtemp[:3])>1e-7 and np.min(temp[:3])<=1e-7:
            lo=0.;hi=step
            for z in range(22):
                mid=.5*(lo+hi)
                jmid=(charge(t+mid,kind,p)-charge(t,kind,p))/mid
                ns,nt,ne,nw,nc=advance(cfg,states,temp,T0,jmid,mid,th)
                if np.min(nt[:3])>1e-7:hi=mid
                else:lo=mid
            step=hi
            jm=(charge(t+step,kind,p)-charge(t,kind,p))/step
            newstates,newtemp,en,wa,conduct=advance(cfg,states,temp,T0,jm,step,th)
        t+=step;q=charge(t,kind,p);states=newstates;temp=newtemp
        energy+=en;water+=wa;errmax=max(errmax,en[4])
        # Left limit at switches, plus current endpoint on smooth ramps.
        jleft=current(t-1e-9,kind,p)
        e,d=evaluate(cfg,states,temp,jleft,th)
        jmax=max(jmax,jleft)
        vmax=min(vmax,float(np.min(e[:,0])))
        imax=max(imax,float(np.max(d[:,0])));smax=max(smax,float(np.max(d[:,3])))
        poremax=max(poremax,float(np.max(d[:,1])));memmax=max(memmax,float(np.max(d[:,2])))
        spread=max(spread,float(np.max(temp[:3])-np.min(temp[:3])))
        gmin=min(gmin,float(np.min(d[:,5])));ratio=max(ratio,float(np.max(e[:,6])));kmin=min(kmin,float(np.min(e[:,9])))
        wb=np.dot(WEIGHTS,d[:,7])-initial_water-np.dot(WEIGHTS,water[:3])+np.dot(WEIGHTS,water[3:])
        if record:
            history[count]=history_row(t,jleft,q,temp,e,d,energy,wb,conduct);count+=1
        if np.min(d[:,5])<-1e-10 or np.max(e[:,6])>=1 or np.min(e[:,9])<=0 or np.min(d[:,6])<-1e-8 or errmax>1e-6:
            status=3;failed=int(np.argmin(e[:,0]))+1;break
        if vmax<.30-1e-10 and stop_voltage:
            status=2;failed=int(np.argmin(e[:,0]))+1;break
        if np.min(temp[:3])>0 and np.max(d[:,0])<.99:
            status=0 if vmax>=.30-1e-10 else 2
            break
        if q>=20.-1e-9:
            status=1;break
    summary=np.array([float(status),t,q,jmax,vmax,imax,smax,np.min(temp[:3]),spread,
        energy[3]-energy[0]-energy[1]+energy[2],wb,gmin,ratio,kmin,errmax,
        energy[0],energy[1],energy[2],energy[3],e[0,0],temp[2],float(failed),poremax,memmax])
    return summary,history[:count],states,temp

def simulate(kind,p,T0=-10.,dt=.05,scale=1,tmax=600.,record=False,stop_voltage=True,thermal=None,**cell_kwargs):
    cfg=make_config(scale=scale,j0=cell_kwargs.pop('j0',J0),**cell_kwargs)
    code={'constant':0,'ramp':1,'step':2}[kind] if isinstance(kind,str) else kind
    params=np.asarray(p,dtype=float)
    if not np.all(np.isfinite(params)) or dt<=0 or tmax<=0:
        raise ValueError('Finite parameters and positive dt/tmax are required.')
    currents=params[:1] if code==0 else params[1:2] if code==1 else params[:(len(params)+1)//2]
    if np.any(currents<0) or np.any(currents>.5):
        raise ValueError('Current density must stay between 0 and 0.5 A/cm2.')
    if code==1 and (len(params)!=2 or params[0]<=0 or params[1]<=0):
        raise ValueError('Ramp requires positive slope and plateau current.')
    if code==2:
        n=(len(params)+1)//2
        if len(params)%2!=1 or np.any(np.diff(np.r_[0.,params[n:]])<=0):
            raise ValueError('Step switching times must be positive and increasing.')
    th=THERMAL.copy() if thermal is None else np.asarray(thermal,dtype=float)
    result=simulate_raw(cfg,code,params,float(T0),float(dt),float(tmax),th,record,stop_voltage)
    summary=dict(zip(SUMMARY_NAMES,map(float,result[0])))
    summary['status']=STATUS[int(summary['status'])]
    return summary,result[1],result[2],result[3]

if __name__=='__main__':
    import time,json
    for kind,p in [('constant',[.5]),('constant',[.3]),('ramp',[.01,.5]),('step',[.2,.4,.5,10,20])]:
        start=time.perf_counter()
        s,*_=simulate(kind,p,record=True)
        print(kind,p,json.dumps(s), 'runtime',time.perf_counter()-start,flush=True)
