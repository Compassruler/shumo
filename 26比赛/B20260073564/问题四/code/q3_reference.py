"""Q3: five independent heaters, conservative full seven-node stack.

SI inside heat/mass kernels; public q in W/cm2, j in A/cm2, energy in J.
Strategy P=0: no current until th, then prescribed shifted ramp.
Strategy C=1: prescribed ramp from t=0, heater off at th.
The water/electrochemistry kernel is a frozen copy of the current Q2 kernel.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT.parent / '问题2_求解结果' / '.python_deps'
sys.path.insert(0, str(DEPS))
import numpy as np
from numba import njit
from fast_cell import make_config, initial_state, cell_step, electro, properties, diagnostics

AREA = .0025
Q_TIME = 60 + 11/.3
J0 = .10255839004732065
# g_c factor, g_E factor, end-plate capacity factor, convection on EP, beta, h factor
THERMAL = np.array([1., 1., 1., 0., 10., 1.])
SUMMARY = ['elapsed_s','charge_C_cm2','first_success_s','best_min_T_C',
 'switch_min_T_C','post_switch_min_T_C','min_voltage_V','max_ice_bulk',
 'max_end_ice_bulk','max_pore_ice_saturation','max_end_pore_ice_saturation',
 'max_pore_ice_bulk','max_mem_ice_bulk','min_porosity','max_j_jlim',
 'min_kappa_S_m','min_inventory','max_iteration_error_K','energy_residual_J',
 'water_residual_kg','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J',
 'final_min_T_C','final_max_T_C','final_left_EP_C','max_mirror_error_K',
 'ice_at_switch','post_subzero_duration_s','min_V_before_success_V']
SUMMARY += [f'post_min_T{k}_C' for k in range(1,6)]
HISTORY = ['time_s','j_A_cm2','charge_C_cm2','heater_on']
HISTORY += [f'T{k}_C' for k in range(1,6)] + ['TEL_C','TER_C']
for key in ['V','ice_bulk','pore_ice_bulk','pore_ice_saturation','mem_ice_bulk',
            'lambda_mean','j_over_jlim','gas_porosity']:
    HISTORY += [f'cell{k}_{key}' for k in range(1,6)]
HISTORY += ['E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J',
            'energy_residual_J','water_residual_kg']

@njit(cache=True)
def charge(t):
    x = max(t,0.)
    return .0025*min(x,60.)**2 + .3*max(x-60.,0.)

@njit(cache=True)
def network(cfg, states, thermal):
    c = np.empty(7); r = np.empty(5)
    for k in range(5):
        cm, rm = properties(cfg, states[k])
        c[k] = cm + (1.5 if k==0 or k==4 else 1.)*.002*1980*766
        r[k] = rm
    c[5:] = 39500*thermal[2]
    g = np.zeros((7,7))
    for k in range(4):
        z = thermal[0]/(.5*(r[k]+r[k+1])+.002/95)
        g[k,k]+=z;g[k+1,k+1]+=z;g[k,k+1]-=z;g[k+1,k]-=z
    for k, e in ((0,5),(4,6)):
        z = thermal[1]/(.5*r[k]+.002/95+.005/15)
        g[k,k]+=z;g[e,e]+=z;g[k,e]-=z;g[e,k]-=z
    h = np.zeros(7)
    if thermal[3]>.5:
        h[5:] = 1/(1/(40*thermal[5])+.005/15)
    else:
        h[0]=40*thermal[5];h[4]=40*thermal[5]
    for k in range(7):g[k,k]+=h[k]
    return c,g,h

@njit(cache=True)
def evaluate(cfg, states, temp, j, thermal):
    e=np.empty((5,12));d=np.empty((5,9))
    for k in range(5):
        e[k]=electro(cfg,states[k],temp[k]+273.15,j*1e4,
                     thermal[4] if k==0 or k==4 else 1.)
        d[k]=diagnostics(cfg,states[k])
    return e,d

@njit(cache=True)
def advance(cfg,states,temp0,j,dt,power,thermal):
    newstates = [states[k] for k in range(5)]
    phase=np.zeros(7);gen=np.zeros(7);aux=np.zeros(7);water=np.zeros(2)
    aux[:5]=power*1e4
    for k in range(5):
        sn,ph,wp,wo=cell_step(cfg,states[k],temp0[k]+273.15,j*1e4,dt)
        newstates[k]=sn;phase[k]=ph;water[0]+=wp;water[1]+=wo
    c,g,h=network(cfg,newstates,thermal)
    a=g.copy()
    for k in range(7):a[k,k]+=c[k]/dt
    rhs=c/dt*temp0+h*(-30.)+phase/dt+aux
    temp=temp0.copy();err=1.
    for it in range(30):
        for k in range(5):
            el=electro(cfg,newstates[k],temp[k]+273.15,j*1e4,
                       thermal[4] if k==0 or k==4 else 1.)
            gen[k]=j*1e4*(1.48-el[0])
        tn=np.linalg.solve(a,rhs+gen)
        err=np.max(np.abs(tn-temp));temp=tn
        if err<1e-9:break
    energy=np.array([np.sum(aux)*dt,np.sum(gen)*dt,np.sum(phase),
                     np.dot(h,temp+30)*dt,np.dot(c,temp-temp0)])*AREA
    return newstates,temp,energy,water,err

@njit(cache=True)
def row(t,j,q,on,temp,e,d,en,wb):
    z=np.empty(58)
    z[0]=t;z[1]=j;z[2]=q;z[3]=on;z[4:11]=temp
    z[11:16]=e[:,0];z[16:21]=d[:,0];z[21:26]=d[:,1]
    z[26:31]=d[:,3];z[31:36]=d[:,2];z[36:41]=e[:,7]
    z[41:46]=e[:,6];z[46:51]=d[:,5];z[51:56]=en
    z[56]=en[4]-en[0]-en[1]-en[2]+en[3];z[57]=wb
    return z

@njit(cache=True,nogil=True)
def simulate_raw(cfg,kind,power,th,dt,post,stop,record,thermal):
    # post: P loading verification length; C total horizon. No artificial warm guard.
    horizon = th+post if kind==0 else post
    temp=np.full(7,-30.)
    states=[initial_state(cfg,243.15) for k in range(5)]
    t=0.;en=np.zeros(5);water=np.zeros(2)
    e,d=evaluate(cfg,states,temp,0.,thermal)
    w0=np.sum(d[:,7]);wb=0.
    nmax=int(np.ceil(horizon/dt))+80 if record else 1
    hist=np.empty((nmax,58));count=0
    if record:hist[0]=row(0.,0.,0.,1.,temp,e,d,en,0.);count=1
    vmin=np.min(e[:,0]);imin=0.;endice=0.;sat=0.;endsat=0.;pice=0.;mice=0.
    por=np.min(d[:,5]);ratio=0.;kap=np.min(e[:,9]);inv=np.min(d[:,6]);errmax=0.
    first=-1.;best=-30.;switchtemp=-30.;postmin=1e9;iceswitch=0.;subzero=0.
    mirror=0.;vfirst=vmin;post_each=np.full(5,1e9)
    while t<horizon-1e-10:
        shift=th if kind==0 else 0.
        step=min(dt,horizon-t)
        for br in (th,shift+60.):
            if br>t+1e-9:step=min(step,br-t)
        on=t<th-1e-9
        power_on=power if on else np.zeros(5)
        jm=(charge(t+step-shift)-charge(t-shift))/step
        ns,nt,ne,nw,er=advance(cfg,states,temp,jm,step,power_on,thermal)
        # A first-hit root is located by reintegrating the last substep.
        if kind==1 and stop and np.min(temp[:5])<1e-7 and np.min(nt[:5])>=1e-7:
            lo=0.;hi=step
            for iteration in range(24):
                mid=(lo+hi)/2
                jmid=(charge(t+mid)-charge(t))/mid
                ss,tt,ee,ww,rr=advance(cfg,states,temp,jmid,mid,power_on,thermal)
                if np.min(tt[:5])>=1e-7:hi=mid
                else:lo=mid
            step=hi;jm=(charge(t+step)-charge(t))/step
            ns,nt,ne,nw,er=advance(cfg,states,temp,jm,step,power_on,thermal)
        t+=step;states=ns;temp=nt;en+=ne;water+=nw;errmax=max(errmax,er)
        j=min(.005*max(t-shift,0.),.3);q=charge(t-shift)
        e,d=evaluate(cfg,states,temp,j,thermal)
        vmin=min(vmin,np.min(e[:,0]));imin=max(imin,np.max(d[:,0]))
        endice=max(endice,d[0,0],d[4,0]);sat=max(sat,np.max(d[:,3]))
        endsat=max(endsat,d[0,3],d[4,3]);pice=max(pice,np.max(d[:,1]));mice=max(mice,np.max(d[:,2]))
        por=min(por,np.min(d[:,5]));ratio=max(ratio,np.max(e[:,6]));kap=min(kap,np.min(e[:,9]));inv=min(inv,np.min(d[:,6]))
        wb=(np.sum(d[:,7])-w0-water[0]+water[1])*AREA
        tm=np.min(temp[:5]);best=max(best,tm)
        mirror=max(mirror,abs(temp[0]-temp[4]),abs(temp[1]-temp[3]),abs(temp[5]-temp[6]))
        if abs(t-th)<1e-8:switchtemp=tm;iceswitch=np.max(d[:,0])
        if t>=th-1e-9:
            postmin=min(postmin,tm)
            post_each=np.minimum(post_each,temp[:5])
            if tm<0 and t>th+1e-9:subzero+=step
        eligible=kind==1 or t>=th-1e-9
        if first<0:
            vfirst=vmin
            if eligible and tm>=1e-7 and vmin>=.3 and imin<.99 and ratio<1 and por>=0 and kap>0 and inv>=-1e-8:
                first=t
        if record:
            hist[count]=row(t,j,q,1. if on else 0.,temp,e,d,en,wb);count+=1
        if stop and first>=0:break
        if not np.isfinite(tm) or tm>200:break
    if postmin==1e9:postmin=np.min(temp[:5])
    s=np.array([t,charge(t-(th if kind==0 else 0)),first,best,switchtemp,postmin,
      vmin,imin,endice,sat,endsat,pice,mice,por,ratio,kap,inv,errmax,
      en[4]-en[0]-en[1]-en[2]+en[3],wb,en[0],en[1],en[2],en[3],en[4],
      np.min(temp[:5]),np.max(temp[:5]),temp[5],mirror,iceswitch,subzero,vfirst,
      post_each[0],post_each[1],post_each[2],post_each[3],post_each[4]])
    return s,hist[:count],states,temp

def simulate(kind,power,th,dt=.05,scale=1,post=None,stop=False,record=False,thermal=None,**config):
    if isinstance(kind,str):kind={'P':0,'C':1}[kind]
    power=np.asarray(power,dtype=float)
    if len(power)==3:power=power[[0,1,2,1,0]]
    if len(power)!=5 or np.any(power<0) or np.any(power>1+1e-10) or th<0:
        raise ValueError('Five heater powers in [0,1] and th>=0 required')
    cfg=make_config(scale=scale,j0=J0,**config)
    if post is None:post=0. if kind==0 else Q_TIME
    a,h,states,temp=simulate_raw(cfg,kind,power,float(th),float(dt),float(post),stop,record,
                                THERMAL if thermal is None else np.asarray(thermal,float))
    s=dict(zip(SUMMARY,a.tolist()))
    s['feasible']=bool(s['first_success_s']>=0 and s['min_V_before_success_V']>=.3)
    return s,h,states,temp
