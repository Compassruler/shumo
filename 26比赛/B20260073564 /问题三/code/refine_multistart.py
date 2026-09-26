"""Additional physically distinct cooperative starts, including fastest full power."""
import json,time
from optimize_aux import Problem,bounds,unpack,save_csv,DATA,np,minimize

def main():
    p=Problem('C',dt=.15,scale=1)
    starts=[[1,1,1,.24,.24],[1,1,0,.40,.40],[.9,.6,.2,.55,.55],
            [.7,0,0,.96,.96],[1,1,1,.20,.9],[1,.4,.7,.35,.65]]
    best=None;solutions=[];logs=[]
    for x in starts:
        res=minimize(p.fun,np.array(x,float),method='SLSQP',bounds=bounds('C'),
           constraints={'type':'ineq','fun':p.cons},
           options={'maxiter':100,'ftol':1e-8,'eps':2e-5})
        f,g,s=p.calc(tuple(res.x))
        print('MULTISTART',x,'=>',res.x,'E',f*1000,'gmin',min(g),flush=True)
        solutions.append(dict(start=str(x),x=str(res.x),E_J=1000*f,gmin=min(g)))
        if min(g)>-1e-5 and (best is None or f<best[0]):best=(f,res.x)
    logs += p.records
    qp,th,post=unpack(best[1],'C');xx=np.r_[qp,th/100,post/100]
    for dt,scale in ((.1,2),(.025,4),(.0125,8)):
        p=Problem('C',dt=dt,scale=scale,full=True)
        res=minimize(p.fun,xx,method='SLSQP',bounds=bounds('C',True),
           constraints={'type':'ineq','fun':p.cons},
           options={'maxiter':60,'ftol':1e-8,'eps':2e-5})
        xx=res.x;f,g,s=p.calc(tuple(xx));logs+=p.records
        print('REFINE',dt,scale,xx,'E',f*1000,'g',g,flush=True)
    # Deliberately break mirror symmetry then release all five powers.
    asym=xx.copy();asym[0]=max(0,asym[0]-.03);asym[3]=max(0,asym[3]-.02)
    rr=minimize(p.fun,asym,method='SLSQP',bounds=bounds('C',True),
       constraints={'type':'ineq','fun':p.cons},options={'maxiter':45,'ftol':1e-8,'eps':2e-5})
    if min(p.cons(rr.x))>-1e-5 and p.fun(rr.x)<p.fun(xx):xx=rr.x
    f,g,s=p.calc(tuple(xx));qp,th,post=unpack(xx,'C',True)
    out=dict(mode='C',power=qp.tolist(),th_s=th,horizon_s=post,energy_J=f*1000,
             dt=.0125,scale=8,constraints=g.tolist(),summary=s)
    save_csv(DATA/'multistart_C.csv',solutions)
    save_csv(DATA/'multistart_C_evaluations.csv',logs+p.records)
    (DATA/'optimum_C_multistart.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
