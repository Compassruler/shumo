"""Reproducible multi-start constrained energy optimization for Q3."""
import argparse, csv, json, time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from aux_model import ROOT, np, simulate, Q_TIME
from scipy.optimize import differential_evolution, minimize

DATA=ROOT/'data'
DATA.mkdir(exist_ok=True)
def save_csv(path, records):
    if not records:return
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)

def unpack(x,mode,full=False):
    n=5 if full else 3
    p=np.array(x[:n])
    if not full:p=p[[0,1,2,1,0]]
    th=x[n]*100
    horizon=x[n+1]*100 if mode=='C' else (Q_TIME if mode=='R' else 0.)
    return p,th,horizon

class Problem:
    def __init__(self,mode,dt=.25,scale=1,full=False):
        self.mode=mode;self.dt=dt;self.scale=scale;self.full=full;self.records=[]
        self.calc=lru_cache(maxsize=400)(self._calc)
    def _calc(self,x):
        p,th,post=unpack(x,self.mode,self.full)
        s,h,st,temp=simulate('P' if self.mode in ('P','R') else 'C',p,th,
                            dt=self.dt,scale=self.scale,post=post)
        ct=s['post_switch_min_T_C'] if self.mode=='R' else s['final_min_T_C']
        individual=([s[f'post_min_T{k}_C'] for k in range(1,6)] if self.mode=='R' else temp[:5])
        g=[(tk-.001)/10 for tk in individual]
        g += [(s['min_voltage_V']-.3)*10,
           s['min_porosity'],1-s['max_j_jlim'],s['min_kappa_S_m'],
           .99-s['max_ice_bulk']]
        if self.mode=='C':g += [(post-th)/100]
        obj=25*np.sum(p)*th/1000
        self.records.append(dict(mode=self.mode,dt=self.dt,scale=self.scale,
            **{f'q{k+1}':v for k,v in enumerate(p)},th_s=th,horizon_s=post,
            E_J=obj*1000,min_T_C=ct,min_V=s['min_voltage_V'],ice=s['max_ice_bulk'],
            constraint_min=min(g)))
        return obj,np.array(g),s
    def fun(self,x):return self.calc(tuple(x))[0]
    def cons(self,x):return self.calc(tuple(x))[1]
    def penalty(self,x):
        f,g,_=self.calc(tuple(x));v=np.minimum(g,0.)
        return f+500*np.sum(v*v)+50*np.sum(-v)

def bounds(mode,full=False):
    b=[(0.,1.)]*(5 if full else 3)
    b += [(.05,2.5 if mode=='R' else 3. if mode=='P' else Q_TIME/100)]
    if mode=='C':b += [(.05,Q_TIME/100)]
    return b

def run(mode):
    t0=time.time();allrows=[];candidates=[]
    p=Problem(mode)
    # Compile once before sharing the GIL-free numerical kernel between workers.
    p.penalty(np.array([.8,.7,.5,.5,.8] if mode=='C' else [.8,.7,.5,.8]))
    for seed in (20260925,20260926):
        with ThreadPoolExecutor(max_workers=4) as pool:
            res=differential_evolution(p.penalty,bounds(mode),seed=seed,popsize=9,
                 maxiter=42,tol=.001,polish=False,workers=pool.map,updating='deferred')
        local=minimize(p.fun,res.x,method='SLSQP',bounds=bounds(mode),
             constraints={'type':'ineq','fun':p.cons},
             options={'maxiter':85,'ftol':1e-8,'eps':2e-5})
        f,g,s=p.calc(tuple(local.x))
        print(mode,'seed',seed,'x',local.x,'E',f*1000,'g',g,'ok',local.success,flush=True)
        candidates.append((f if min(g)>-1e-5 else 1e6,local.x))
    allrows += p.records
    # Distinct fast/high-power and slow/low-power basins must both be explored.
    seeds = ([1.,1.,1.,.26], [1.,.7,.1,.45]) if mode=='P' else (
       ([1.,1.,1.,.24,.24],[1.,1.,0.,.4,.4],[.9,.6,.2,.55,.55],
        [.7,0.,0.,.96,.96],[1.,1.,1.,.20,.9]) if mode=='C' else
       ([1.,1.,1.,.65],[1.,.5,0.,1.1],[.7,.2,.1,1.7]))
    for start in seeds:
        local=minimize(p.fun,np.array(start),method='SLSQP',bounds=bounds(mode),
            constraints={'type':'ineq','fun':p.cons},
            options={'maxiter':90,'ftol':1e-8,'eps':2e-5})
        f,g,s=p.calc(tuple(local.x))
        candidates.append((f if min(g)>-1e-5 else 1e6,local.x))
        print(mode,'physical_start',start,'x',local.x,'E',1000*f,'gmin',min(g),flush=True)
    x=min(candidates,key=lambda z:z[0])[1]
    # Final full five-control release, no imposed mirror symmetry.
    qp,th,post=unpack(x,mode)
    xx=np.r_[qp,th/100,post/100] if mode=='C' else np.r_[qp,th/100]
    for dt,scale in ((.10,2),(.025,4)):
        p=Problem(mode,dt=dt,scale=scale,full=True)
        local=minimize(p.fun,xx,method='SLSQP',bounds=bounds(mode,True),
              constraints={'type':'ineq','fun':p.cons},
              options={'maxiter':65,'ftol':2e-8,'eps':2e-5})
        xx=local.x
        f,g,s=p.calc(tuple(xx));allrows+=p.records
        print(mode,'refine',dt,scale,'x',xx,'E',f*1000,'g',g,'ok',local.success,flush=True)
    # Explicit asymmetric perturbation, local reoptimization in six/seven dimensions.
    pert=xx.copy();pert[0]=max(0.,pert[0]-.04);pert[1]=min(1.,pert[1]+.025)
    local=minimize(p.fun,pert,method='SLSQP',bounds=bounds(mode,True),
        constraints={'type':'ineq','fun':p.cons},options={'maxiter':45,'ftol':1e-8,'eps':2e-5})
    if min(p.cons(local.x))>=-1e-5 and p.fun(local.x)<p.fun(xx):xx=local.x
    qp,th,post=unpack(xx,mode,True)
    f,g,s=p.calc(tuple(xx))
    out=dict(mode=mode,power=qp.tolist(),th_s=th,horizon_s=post,
             energy_J=f*1000,dt=.025,scale=4,constraints=g.tolist(),summary=s,
             elapsed_wall_s=time.time()-t0)
    (DATA/f'optimum_{mode}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(DATA/f'optimization_search_{mode}.csv',allrows+p.records)
    print(json.dumps(out,ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['P','C','R']);args=ap.parse_args();run(args.mode)
