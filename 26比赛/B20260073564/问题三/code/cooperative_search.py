"""Cooperative optimization with switch-aligned variables.

Use x=[q, ts/100, th/ts]. Unlike independent th,ts coordinates this preserves
the one-sided heater-on derivative on the active th=ts boundary.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from optimize_aux import Problem,save_csv,DATA,np,minimize,differential_evolution

class FractionProblem(Problem):
    def _calc(self,x):
        z=np.r_[x[:-2],x[-2]*x[-1],x[-2]]
        return super()._calc(tuple(z))

def bounds(full=False):return [(0.,1.)]*(5 if full else 3)+[(.05,29/30),(.001,1.)]

def main():
    logs=[];results=[];best=None
    p=FractionProblem('C',dt=.2)
    starts=[[1,1,1,.24,1],[1,1,0,.4,1],[.9,.6,.2,.55,1],
            [.7,0,0,29/30,1],[1,1,1,.9,.22],[1,.4,.7,.65,.54]]
    p.fun(starts[0])
    for seed in (20260927,20260928):
        with ThreadPoolExecutor(max_workers=4) as pool:
            de=differential_evolution(p.penalty,bounds(),seed=seed,popsize=8,
               maxiter=38,tol=.002,polish=False,workers=pool.map,updating='deferred')
        starts.append(de.x)
    for x in starts:
        res=minimize(p.fun,np.asarray(x),method='SLSQP',bounds=bounds(),
            constraints={'type':'ineq','fun':p.cons},options={'maxiter':65,'eps':1e-5,'ftol':1e-8})
        f,g,s=p.calc(tuple(res.x))
        print('ALIGNED',x,'=>',res.x,'E',f*1000,'gmin',min(g),flush=True)
        results.append(dict(start=str(x),x=str(res.x),energy_J=1000*f,constraint_min=min(g)))
        if min(g)>-1e-5 and (best is None or f<best[0]):best=f,res.x
    logs+=p.records
    z=best[1];xx=np.r_[np.asarray(z[:3])[[0,1,2,1,0]],z[-2:]]
    for dt,scale in ((.1,2),(.025,4),(.0125,8)):
        p=FractionProblem('C',dt=dt,scale=scale,full=True)
        res=minimize(p.fun,xx,method='SLSQP',bounds=bounds(True),
            constraints={'type':'ineq','fun':p.cons},options={'maxiter':65,'eps':1e-5,'ftol':1e-8})
        if min(p.cons(res.x))<-1e-4:
            raise RuntimeError('Infeasible refinement '+str(res.x))
        xx=res.x;f,g,s=p.calc(tuple(xx));logs+=p.records
        print('REFINE',dt,scale,xx,'E',f*1000,'gmin',min(g),flush=True)
    # Release deliberately asymmetric initial powers.
    asym=xx.copy();asym[0]=max(0,asym[0]-.03);asym[3]=max(0,asym[3]-.02)
    rr=minimize(p.fun,asym,method='SLSQP',bounds=bounds(True),
       constraints={'type':'ineq','fun':p.cons},options={'maxiter':45,'ftol':1e-8,'eps':1e-5})
    if min(p.cons(rr.x))>-1e-5 and p.fun(rr.x)<p.fun(xx):xx=rr.x
    f,g,s=p.calc(tuple(xx))
    out=dict(mode='C',power=xx[:5].tolist(),th_s=xx[-2]*xx[-1]*100,
       horizon_s=xx[-2]*100,energy_J=f*1000,dt=.0125,scale=8,
       constraints=g.tolist(),summary=s)
    save_csv(DATA/'cooperative_multistart.csv',results)
    save_csv(DATA/'cooperative_search.csv',logs+p.records)
    (DATA/'optimum_C_aligned.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
