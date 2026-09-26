"""Q4 conservative seven-node plant and sampled per-cell feedback controller.

Public units: seconds, Celsius, W/cm2 and A/cm2. Internal heat fluxes are SI.
Plant inherited from Q3; full finite-volume water/ice/electrochemical submodel.
No controller action occurs after latched shutdown. Samples of q describe the
interval ENDING at each output row, so sum(q*dt*25) is the exact heater energy.
"""
import bootstrap
import numpy as np
from numba import njit
from fast_cell import make_config, initial_state, cell_step, electro, properties, diagnostics

AREA=.0025
Q_TIME=60+11/.3
J0=.10255839004732065
THERMAL=np.array([1.,1.,1.,0.,10.,1.])
CONSTANT=np.array([1.,1.,.6245115587719579,1.,1.])
PARAM_NAMES=['T_target_C','t_plan_s','K_P','K_I','taper_K','hold_s',
             'q_boost_min','ice_warn','delta_V','risk_warn','L_obs','rate_gain','ff_factor']
DEFAULT=np.array([1.,60.,.15,.015,1.,2.,.6,.8,.1,.7,.02,.1,1.])

@njit(cache=True)
def charge(t):
    t=max(t,0.)
    return .0025*min(t,60.)**2+.3*max(t-60.,0.)

@njit(cache=True)
def network(cfg,states,thermal):
    c=np.empty(7); r=np.empty(5)
    for k in range(5):
        cm,rm=properties(cfg,states[k])
        c[k]=cm+(1.5 if k==0 or k==4 else 1.)*.002*1980*766
        r[k]=rm
    c[5:]=39500*thermal[2]
    g=np.zeros((7,7))
    for k in range(4):
        z=thermal[0]/(.5*(r[k]+r[k+1])+.002/95)
        g[k,k]+=z;g[k+1,k+1]+=z;g[k,k+1]-=z;g[k+1,k]-=z
    for k,e in ((0,5),(4,6)):
        z=thermal[1]/(.5*r[k]+.002/95+.005/15)
        g[k,k]+=z;g[e,e]+=z;g[k,e]-=z;g[e,k]-=z
    h=np.zeros(7)
    if thermal[3]>.5:
        h[5:]=1/(1/(40*thermal[5])+.005/15)
    else:
        h[0]=40*thermal[5];h[4]=40*thermal[5]
    for k in range(7):g[k,k]+=h[k]
    return c,g,h

@njit(cache=True)
def evaluate(cfg,states,temp,j,thermal):
    e=np.empty((5,12));d=np.empty((5,9))
    for k in range(5):
        e[k]=electro(cfg,states[k],temp[k]+273.15,j*1e4,thermal[4] if k==0 or k==4 else 1.)
        d[k]=diagnostics(cfg,states[k])
    return e,d

@njit(cache=True)
def advance(cfg,states,temp0,j,dt,power,thermal):
    ns=[states[k] for k in range(5)]
    phase=np.zeros(7);gen=np.zeros(7);aux=np.zeros(7);water=np.zeros(2)
    aux[:5]=power*1e4
    for k in range(5):
        sn,ph,wp,wo=cell_step(cfg,states[k],temp0[k]+273.15,j*1e4,dt)
        ns[k]=sn;phase[k]=ph;water[0]+=wp;water[1]+=wo
    c,g,h=network(cfg,ns,thermal)
    a=g.copy()
    for k in range(7):a[k,k]+=c[k]/dt
    rhs=c/dt*temp0+h*(-30.)+phase/dt+aux
    temp=temp0.copy();err=1.
    for iteration in range(30):
        for k in range(5):
            el=electro(cfg,ns[k],temp[k]+273.15,j*1e4,thermal[4] if k==0 or k==4 else 1.)
            gen[k]=j*1e4*(1.48-el[0])
        tn=np.linalg.solve(a,rhs+gen)
        err=np.max(np.abs(tn-temp));temp=tn
        if err<1e-9:break
    energy=np.array([np.sum(aux)*dt,np.sum(gen)*dt,np.sum(phase),
        np.dot(h,temp+30)*dt,np.dot(c,temp-temp0)])*AREA
    return ns,temp,energy,water,err

HISTORY=['time_s','j_A_cm2','charge_C_cm2','stopped']
HISTORY += [f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']
for name in ['q_W_cm2','V_V','ice_bulk','pore_ice_bulk','mem_ice_bulk','pore_ice_saturation',
             'lambda','j_over_jlim','gas_porosity','state','risk','rT_K_s','rV_V_s','ice_est']:
    HISTORY += [f'cell{k}_{name}' for k in range(1,6)]
HISTORY += ['E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg']
HISTORY += ['water_inventory_kg','water_produced_kg','water_out_kg']
SUMMARY=['first_success_s','stop_s','elapsed_s','E_aux_J','E_gen_J','E_phase_J','E_loss_J',
 'E_sensible_J','energy_residual_J','water_residual_kg','min_voltage_V','max_ice_bulk',
 'dTmax_K','final_min_T_C','final_max_T_C','final_left_EP_C','min_gas_porosity',
 'max_j_over_jlim','min_kappa_S_m','min_inventory','max_iteration_error_K',
 'max_power_W_cm2','charge_at_success_C_cm2','post_min_T_C','post_min_voltage_V','post_max_ice_bulk',
 'post_energy_J','first_success_energy_J','max_water_residual_kg']

@njit(cache=True)
def row(t,temp,e,d,q,en,wb,stopped,cs,water):
    out=np.zeros(91)
    out[:4]=np.array([t,min(.005*t,.3),charge(t),1. if stopped else 0.])
    out[4:11]=temp;out[11:16]=q;out[16:21]=e[:,0]
    out[21:26]=d[:,0];out[26:31]=d[:,1];out[31:36]=d[:,2];out[36:41]=d[:,3]
    out[41:46]=e[:,7];out[46:51]=e[:,6];out[51:56]=d[:,5]
    for k in range(5):
        out[56+k]=cs[k,4];out[61+k]=cs[k,5];out[66+k]=cs[k,2]
        out[71+k]=cs[k,3];out[76+k]=cs[k,6]
    out[81:86]=en
    out[86]=en[4]-en[0]-en[1]-en[2]+en[3];out[87]=wb
    out[88]=np.sum(d[:,7])*AREA;out[89:91]=water*AREA
    return out

@njit(cache=True)
def valid(temp,e,d):
    return (np.min(temp[:5])>1e-7 and np.min(e[:,0])>=.3 and np.max(d[:,0])<.99
      and np.max(e[:,6])<1 and np.min(d[:,5])>=0 and np.min(e[:,9])>0 and np.min(d[:,6])>=-1e-8)

@njit(cache=True)
def control(t,period,temp0,temp,e,d,states,cfg,p,thermal,cs,integral,measure_noise):
    c,g,h=network(cfg,states,thermal)
    q=np.zeros(5)
    beta=np.exp(-period/.15);br=np.exp(-period/.20)
    losses=g@temp-h*(-30.)
    for k in range(5):
        T=temp[k]+measure_noise[k,0];V=e[k,0]+measure_noise[k,1]
        oldT=cs[k,0];oldV=cs[k,1]
        Tf=beta*oldT+(1-beta)*T;Vf=beta*oldV+(1-beta)*V
        rT=br*cs[k,2]+(1-br)*(Tf-oldT)/period
        rV=br*cs[k,3]+(1-br)*(Vf-oldV)/period
        # No-ice voltage channel uses estimated water/gas states and measured T.
        st=states[k]
        clean=(st[0],st[1],np.zeros_like(st[2]),st[3],st[4])
        vclear=electro(cfg,clean,T+273.15,min(.005*t,.3)*1e4,thermal[4] if k in (0,4) else 1.)[0]
        ie=max(0.,min(1.,d[k,0]+p[10]*max(0.,vclear-V)/.1))
        low=max(0.,-Tf/30.)
        required=max(0.,(p[0]-Tf)/max(p[1]-t,1.))
        deficit=max(0.,(required-rT)/(required+.01))
        drop=max(0.,-rV)/.1
        risk=.4*ie/.99+.4*max(0.,(.3+p[8]-Vf)/p[8])+.2*min(drop,1.)
        danger=ie>p[7] or Vf<.3+p[8] or (rV<-.1 and Vf<.6) or risk>p[9]
        slope=(p[0]-temp0[k])/p[1] if t<p[1] else 0.
        ref=temp0[k]+(p[0]-temp0[k])*min(t/p[1],1.)
        error=ref-Tf
        # Net heat feedforward: sensible trajectory + network losses - reaction heat.
        ff=p[12]*(c[k]*slope+losses[k]-min(.005*t,.3)*1e4*(1.48-e[k,0]))/1e4
        gain=p[2]*(.6+.4*min(1.,max(0.,-Tf/30.)))
        trial=integral[k]+p[3]*error*period
        raw=ff+gain*error+trial+p[11]*min(deficit,2.)*min(low,1.)
        if (raw<=1 or error<0) and (raw>=0 or error>0):integral[k]=max(-2.,min(2.,trial))
        nominal=ff+gain*error+integral[k]+p[11]*min(deficit,2.)*min(low,1.)
        state=2. if deficit>.1 else 3.
        taper=1.
        if Tf>0 and ie<.5 and rV>-.05:
            taper=max(0.,min(1.,(p[0]-Tf)/p[4]));state=4.
        output=max(0.,min(1.,nominal))*taper
        # Safety has highest priority and is never multiplied by the taper.
        if danger:
            boost=p[6]+(1-p[6])*max(0.,min(1.,(risk-p[9])/(1-p[9])))
            output=max(output,boost);state=1.
        q[k]=max(0.,min(1.,output))
        cs[k,:]=np.array([Tf,Vf,rT,rV,state,risk,ie])
    return q

@njit(cache=True,nogil=True)
def simulate_raw(cfg,temp0,kind,p,power,dt,period,horizon,post,record,thermal,noise):
    temp=temp0.copy();states=[initial_state(cfg,temp[k]+273.15) for k in range(5)]
    e,d=evaluate(cfg,states,temp,0.,thermal)
    en=np.zeros(5);water=np.zeros(2);w0=np.sum(d[:,7]);wb=0.;maxwb=0.
    cs=np.zeros((5,7));cs[:,0]=temp[:5];cs[:,1]=e[:,0]
    integral=np.zeros(5);q=np.zeros(5);t=0.;first=-1.;stop=-1.;holding=-1.
    # Initially warm cases require no cold-start heating or artificial first step.
    stopped=valid(temp,e,d)
    if stopped:first=0.;stop=0.
    nmax=int(np.ceil((horizon+post)/dt))+500 if record else 1
    hist=np.empty((nmax,91));count=0
    if record:hist[count]=row(t,temp,e,d,q,en,wb,stopped,cs,water);count+=1
    vmin=np.min(e[:,0]);imax=np.max(d[:,0]);spread=np.max(temp[:5])-np.min(temp[:5])
    por=np.min(d[:,5]);ratio=0.;kap=np.min(e[:,9]);inv=np.min(d[:,6]);errmax=0.;qmax=0.
    postmin=np.min(temp[:5]);postv=vmin;posti=imax;fenergy=0.;stopenergy=0.;stop_en=en.copy();stop_wb=0.
    stop_temp=temp.copy();ctrl_index=0;next_control=0.
    while t<(stop+post if stopped else horizon)-1e-9:
        if stopped:
            q[:]=0.;cs[:,4]=5.
        elif t>=next_control-1e-9:
            if kind==0:q=power.copy()
            else:
                q=control(t,period,temp0,temp,e,d,states,cfg,p,thermal,cs,integral,noise[min(ctrl_index,len(noise)-1)])
            ctrl_index+=1;next_control=ctrl_index*period
        end=stop+post if stopped else horizon
        step=min(dt,end-t)
        if not stopped:step=min(step,next_control-t)
        if 60.>t+1e-9:step=min(step,60.-t)
        if holding>=0 and not stopped and holding+p[5]>t+1e-9:step=min(step,holding+p[5]-t)
        jm=(charge(t+step)-charge(t))/step
        ns,nt,ne,nw,er=advance(cfg,states,temp,jm,step,q,thermal)
        # Locate the first warm crossing by reintegration of the last substep.
        if first<0 and np.min(temp[:5])<=1e-7 and np.min(nt[:5])>1e-7:
            lo=0.;hi=step
            for _ in range(22):
                mid=.5*(lo+hi);jm2=(charge(t+mid)-charge(t))/mid
                ss,tt,ee,ww,rr=advance(cfg,states,temp,jm2,mid,q,thermal)
                if np.min(tt[:5])>1e-7:hi=mid
                else:lo=mid
            step=hi;jm=(charge(t+step)-charge(t))/step
            ns,nt,ne,nw,er=advance(cfg,states,temp,jm,step,q,thermal)
        t+=step;temp=nt;states=ns;en+=ne;water+=nw;errmax=max(errmax,er)
        e,d=evaluate(cfg,states,temp,min(.005*t,.3),thermal)
        wb=(np.sum(d[:,7])-w0-water[0]+water[1])*AREA;maxwb=max(maxwb,abs(wb))
        if not stopped:
            vmin=min(vmin,np.min(e[:,0]));imax=max(imax,np.max(d[:,0]));qmax=max(qmax,np.max(q))
            spread=max(spread,np.max(temp[:5])-np.min(temp[:5]))
            por=min(por,np.min(d[:,5]));ratio=max(ratio,np.max(e[:,6]))
            kap=min(kap,np.min(e[:,9]));inv=min(inv,np.min(d[:,6]))
            ok=valid(temp,e,d) and vmin>=.3 and imax<.99 and ratio<1 and inv>=-1e-8 and por>=0 and kap>0
            if ok:
                if first<0:first=t;fenergy=en[0]
                if holding<0:holding=t
                if t-holding>=p[5]-1e-8:
                    stopped=True;stop=t;stop_en=en.copy();stop_wb=wb;stop_temp=temp.copy();stopenergy=en[0]
                    postmin=np.min(temp[:5]);postv=np.min(e[:,0]);posti=np.max(d[:,0])
            else:holding=-1.
        else:
            postmin=min(postmin,np.min(temp[:5]));postv=min(postv,np.min(e[:,0]));posti=max(posti,np.max(d[:,0]))
        if record:hist[count]=row(t,temp,e,d,q,en,wb,stopped,cs,water);count+=1
        if not np.isfinite(np.min(temp)) or np.max(temp)>200 or vmin<.3 or imax>=.99 or inv<-1e-8:break
    if stop<0:stop_en=en.copy();stop_temp=temp.copy();stop_wb=wb;stopenergy=en[0]
    residual=stop_en[4]-stop_en[0]-stop_en[1]-stop_en[2]+stop_en[3]
    summary=np.array([first,stop,t,stop_en[0],stop_en[1],stop_en[2],stop_en[3],stop_en[4],
      residual,stop_wb,vmin,imax,spread,np.min(stop_temp[:5]),np.max(stop_temp[:5]),stop_temp[5],
      por,ratio,kap,inv,errmax,qmax,charge(first) if first>=0 else -1.,postmin,postv,posti,
      en[0]-stopenergy,fenergy,maxwb])
    return summary,hist[:count],states,temp

def simulate(temp0,kind='dynamic',params=None,power=CONSTANT,dt=.05,period=.2,scale=1,
             horizon=Q_TIME,post=0.,record=False,thermal=None,noise_T=0.,noise_V=0.,seed=42,**config):
    temp0=np.asarray(temp0,float);p=DEFAULT.copy() if params is None else np.asarray(params,float).copy()
    power=np.asarray(power,float)
    if temp0.shape!=(7,) or p.shape!=(13,) or power.shape!=(5,):raise ValueError('Invalid vector shape')
    if kind not in ('constant','dynamic'):raise ValueError('Unknown strategy')
    if dt<=0 or period<dt or p[1]<=0 or p[4]<=0 or p[5]<0 or np.any(power<0) or np.any(power>1):raise ValueError('Invalid controls')
    if p[8]<=0 or not 0<=p[9]<1 or not 0<=p[6]<=1 or not 0<p[7]<.99 or np.any(p[2:4]<0):raise ValueError('Invalid gains or safety thresholds')
    if not np.all(np.isfinite(temp0)) or not np.all(np.isfinite(p)):raise ValueError('Nonfinite input')
    cfg=make_config(scale=scale,j0=J0,**config)
    rng=np.random.default_rng(seed);noise=rng.normal(size=(int(horizon/period)+10,5,2))
    noise[:,:,0]*=noise_T;noise[:,:,1]*=noise_V
    s,h,states,temp=simulate_raw(cfg,temp0,0 if kind=='constant' else 1,p,power,float(dt),float(period),
           float(horizon),float(post),record,THERMAL if thermal is None else np.asarray(thermal,float),noise)
    result=dict(zip(SUMMARY,s.tolist()))
    result['feasible']=bool(result['stop_s']>=0 and result['stop_s']<=horizon+1e-7
       and result['min_voltage_V']>=.3 and result['max_ice_bulk']<.99 and result['max_j_over_jlim']<1
       and result['min_inventory']>=-1e-8 and result['min_gas_porosity']>=0 and result['min_kappa_S_m']>0
       and result['max_iteration_error_K']<1e-6)
    return result,h,states,temp
