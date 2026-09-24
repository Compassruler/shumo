"""Conservative one-dimensional, three-phase cold-start model.
Only prescribed current is accepted: observed voltage/temperature never enter here.
See reports/算法模型与实现说明.md for explicit closures and MD corrections.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.python_deps'))
import numpy as np
from scipy.linalg import solve_banded

F=96485.; R=8.314; MW=.018; TF=273.15; WPL=2150*.018; RI=920.; RL=990.
LC=2.5e6; LF=333600.; YO=(.233/.032)/(.233/.032+.767/.028)

def psat(T):
    c=np.asarray(T)-TF
    return np.where(c>=0,611.21*np.exp((18.678-c/234.5)*c/(257.14+c)),
                    611.15*np.exp((23.036-c/333.7)*c/(279.82+c)))

def transport(u, cap, dx, conductance, dt, source=None, left=None, right=None, adv=None):
    """BE: d(cap*u)/dt = divergence(g*grad u)+source; all faces conservative.
    u is OLD concentration/inventory; cap is new capacity. Input RHS is inventory.
    Returns new concentration and signed outward integrated boundary amount.
    adv: positive upwind face velocity. Zero boundary flux unless specified.
    """
    n=len(dx); a=np.zeros((3,n)); a[1]=cap*dx
    rhs=u*dx
    if source is not None: rhs=rhs+dt*source*dx
    g=dt*np.asarray(conductance)
    a[1,:-1]+=g; a[1,1:]+=g; a[0,1:]-=g; a[2,:-1]-=g
    if adv is not None:
        vp=dt*np.maximum(adv,0); vm=dt*np.minimum(adv,0)
        a[1,:-1]+=vp; a[2,:-1]-=vp; a[1,1:]-=vm; a[0,1:]+=vm
    if left is not None:
        a[1,0]+=dt*left[0]; rhs[0]+=dt*left[0]*left[1]
    if right is not None:
        a[1,-1]+=dt*right[0]; rhs[-1]+=dt*right[0]*right[1]
    v=solve_banded((1,1),a,rhs,check_finite=False)
    out=0.
    if left is not None:out+=dt*left[0]*(v[0]-left[1])
    if right is not None:out+=dt*right[0]*(v[-1]-right[1])
    return v,out

class Model:
    def __init__(self, bp=False, scale=1, j0=.1, kf=1., km=1., kvl=1., kvi=1e-4,
                 lambda_nf=3., exchange_factor=1.):
        self.bp=bp; self.j0=j0; self.kf=kf; self.km=km; self.kvl=kvl; self.kvi=kvi
        self.lambda_nf=lambda_nf; self.exchange_factor=exchange_factor
        names=['aGDL','aCL','PEM','cCL','cGDL']; lengths=[150e-6,3.4e-6,12e-6,11.3e-6,150e-6]
        counts=[8,3,6,4,8]
        self.dx=np.concatenate([np.full(n*scale,l/(n*scale)) for n,l in zip(counts,lengths)])
        self.label=np.concatenate([np.repeat(name,n*scale) for name,n in zip(names,counts)])
        self.x=np.cumsum(self.dx)-self.dx/2; self.n=len(self.dx); self.L=self.dx.sum()
        self.a=np.flatnonzero(np.isin(self.label,['aGDL','aCL'])); self.c=np.flatnonzero(np.isin(self.label,['cCL','cGDL']))
        self.mem=np.flatnonzero(self.label=='PEM'); self.acl=np.flatnonzero(self.label=='aCL'); self.ccl=np.flatnonzero(self.label=='cCL')
        self.pore=np.r_[self.a,self.c]
        self.eps=np.select([self.label=='aCL',self.label=='cCL',self.label=='PEM'],[.3916,.4207,0.],default=.8)
        self.K=np.where(np.isin(self.label,['aGDL','cGDL']),6.2e-12,6.2e-13)
        self.theta=np.where(np.isin(self.label,['aGDL','cGDL']),110.,100.)
        self.Cdry=np.zeros(self.n); self.kdry=np.zeros(self.n)
        gd=np.isin(self.label,['aGDL','cGDL']); cl=np.isin(self.label,['aCL','cCL'])
        self.Cdry[gd]=(1-self.eps[gd])*185*545
        self.Cdry[cl]=(1-self.eps[cl]-.3)*970*240+.3*2150*1050
        self.Cdry[self.mem]=2150*1050
        self.kdry[gd]=(1-self.eps[gd])*.3
        self.kdry[cl]=(1-self.eps[cl]-.3)*.27+.3*.24
        self.kdry[self.mem]=.24
        if bp:
            self.offset=4*scale
            self.dxT=np.r_[np.full(self.offset,.002/self.offset),self.dx,np.full(self.offset,.002/self.offset)]
            self.labelsT=np.r_[np.repeat('aBP',self.offset),self.label,np.repeat('cBP',self.offset)]
        else:self.offset=0; self.dxT=self.dx.copy(); self.labelsT=self.label.copy()
        self.nT=len(self.dxT); self.idx=np.arange(self.n)+self.offset
        self.xT=np.cumsum(self.dxT)-self.dxT/2-(.002 if bp else 0.)
        path_start=150e-6+3.4e-6+12e-6+11.3e-6/2
        right=self.x[self.c]+self.dx[self.c]/2
        left=right-self.dx[self.c]
        self.path_dx=np.maximum(0,right-np.maximum(left,path_start))

    def face(self,D,idx=None):
        dx=self.dx if idx is None else self.dx[idx]
        return 1/(dx[:-1]/(2*np.maximum(D[:-1],1e-30))+dx[1:]/(2*np.maximum(D[1:],1e-30)))

    def fractions(self,ml,mi):
        gas=self.eps-ml/RL-mi/RI; gas[self.mem]=0
        return gas

    def properties(self,mv,ml,mi):
        gas=self.fractions(ml,mi)
        kg=np.where(np.isin(self.label,['aGDL','aCL']),.1672,.02373)
        cg=np.where(np.isin(self.label,['aGDL','aCL']),.089*14283,.21*1.43*919.31+.79*1.35*1041.5)
        C=self.Cdry+gas*cg+ml*4182+mi*2050+mv*2000
        k=self.kdry+gas*kg+ml/RL*.6+mi/RI*2.3
        C[self.mem]=self.Cdry[self.mem]+ml[self.mem]*4182+mi[self.mem]*2050
        k[self.mem]=.24+mi[self.mem]/RI*(2.3-.24)
        CT=np.full(self.nT,1980*766.); KT=np.full(self.nT,95.)
        CT[self.idx]=C; KT[self.idx]=k
        return CT,KT

    def electro(self,T,ml,mi,nh,no,j):
        temp=T[self.idx]; gas=self.fractions(ml,mi)
        ch=nh/np.maximum(gas[self.a],1e-12); co=no/np.maximum(gas[self.c],1e-12)
        ph=np.average(ch[-len(self.acl):]*R*temp[self.acl],weights=self.dx[self.acl])
        po=np.average(co[:len(self.ccl)]*R*temp[self.ccl],weights=self.dx[self.ccl])
        tc=np.average(temp[self.ccl],weights=self.dx[self.ccl])
        si=mi[self.ccl]/(RI*self.eps[self.ccl]); fa=np.average(np.maximum(1-si,1e-12)**3.5,weights=self.dx[self.ccl])
        erev=1.229-.00085*(tc-298.15)+R*tc/(2*F)*np.log(max(ph/101325*np.sqrt(max(po/101325,1e-15)),1e-20))
        jzero=self.j0*np.exp(-67000/R*(1/tc-1/298.15))*fa
        act=R*tc/(.5*F)*np.arcsinh(j/(2*max(jzero,1e-25)))
        lam=ml[self.mem]/WPL; sim=mi[self.mem]/RI
        kap=(.5139*lam-.326)*np.exp(1268*(1/303.15-1/temp[self.mem]))*(1-sim)
        ohm=j*(np.sum(self.dx[self.mem]/np.maximum(kap,1e-10))+1e-6)
        do=2.2e-5*(temp[self.c]/298.15)**1.5*np.maximum(gas[self.c],1e-15)**1.5
        path_res=np.sum(self.path_dx/np.maximum(do,1e-30))
        ccl=np.average(co[:len(self.ccl)],weights=self.dx[self.ccl])
        jlim=4*F*ccl/max(path_res,1e-20)
        ratio=j/max(jlim,1e-20)
        con=-R*tc/(4*F)*np.log(max(1-ratio,1e-12))
        return dict(V_model_V=erev-act-ohm-con,E_rev_V=erev,eta_act_V=act,eta_ohm_V=ohm,eta_con_V=con,
                    j_lim_A_m2=jlim,j_over_jlim=ratio,lambda_mean=np.average(lam,weights=self.dx[self.mem]),
                    lambda_min=lam.min(),kappa_min_S_m=kap.min(),cO2_cCL_mol_m3=ccl,
                    active_area_factor=fa)

    def mass_step(self,T,mv0,ml0,mi0,j,dt):
        temp=T[self.idx]; mv=mv0.copy();ml=ml0.copy();mi=mi0.copy(); heat=np.zeros(self.n)
        produced=MW*j/(2*F)*dt; ml[self.ccl]+=produced/11.3e-6
        # Darcy-derived effective diffusion, frozen mobility; nonnegative implicit solve.
        gas=self.fractions(ml0,mi0)
        for ids in (self.a,self.c):
            sl=np.maximum(ml[ids]/(RL*self.eps[ids]),0)
            si=mi[ids]/(RI*self.eps[ids]); dJ=1.417-4.24*sl+3.789*sl**2
            dl=self.K[ids]*(sl**3)*(.075*np.abs(np.cos(np.deg2rad(self.theta[ids])))*np.sqrt(self.eps[ids]/self.K[ids]))*dJ/(1.8e-3*self.eps[ids]) * np.maximum(1-si,0)**3
            # Arithmetic face mobility avoids an impermeable interface at a dry cell.
            g=.5*(dl[:-1]+dl[1:])/(.5*(self.dx[ids][:-1]+self.dx[ids][1:]))
            ml[ids],_=transport(ml[ids],np.ones(len(ids)),self.dx[ids],g,dt)
        # Membrane water diffusion + conservative upwind electro-osmotic transport.
        ids=self.mem; lam=ml[ids]/WPL
        dm=1e-10*np.exp(2416*(1/303.15-1/temp[ids]))*(2.563-.33*lam+.0264*lam**2-.000671*lam**3)
        adv=np.full(len(ids)-1,2.5/22*MW*j/(F*WPL))
        ml[ids],_=transport(ml[ids],np.ones(len(ids)),self.dx[ids],self.face(np.maximum(dm,1e-13),ids),dt,adv=adv)
        # Equal/opposite membrane-CL interface transfers. Capacity length is Lmem/2,
        # independent of mesh; pool limits only prevent consuming unavailable water.
        for cm,pm in ((self.acl[-1],self.mem[0]),(self.ccl[0],self.mem[-1])):
            sl=max(0.,ml[cm]/(RL*self.eps[cm])); lmem=ml[pm]/WPL
            q=self.exchange_factor*.5*6e-6*WPL*sl*(14.-lmem)*dt
            q=np.clip(q,-ml[pm]*self.dx[pm],ml[cm]*self.dx[cm])
            ml[pm]+=q/self.dx[pm];ml[cm]-=q/self.dx[cm]
            e=max(self.eps[cm]-ml[cm]/RL-mi[cm]/RI,1e-12)
            activity=np.clip(mv[cm]/e/(MW*psat(temp[cm])/(R*temp[cm])),0,1)
            leq=.043+17.81*activity-39.85*activity**2+36.*activity**3
            q=self.exchange_factor*.001*6e-6*WPL*(1-min(sl,1))*(leq-ml[pm]/WPL)*dt
            q=np.clip(q,-ml[pm]*self.dx[pm],mv[cm]*self.dx[cm])
            ml[pm]+=q/self.dx[pm];mv[cm]-=q/self.dx[cm]
            # Reference enthalpy: adsorption is treated as vapor -> bound liquid.
            heat[pm]+=LC*q/self.dx[pm]
        gas=self.fractions(ml,mi); out=0.
        for ids,dref,isleft in ((self.a,8.69e-5,True),(self.c,2.48e-5,False)):
            eps=np.maximum(gas[ids],1e-12)
            dv=dref*(temp[ids]/298.15)**1.5*eps**1.5
            b=(2*dv[0 if isleft else -1]/self.dx[ids][0 if isleft else -1],0.)
            cv,loss=transport(mv[ids],eps,self.dx[ids],self.face(dv,ids),dt,left=b if isleft else None,right=None if isleft else b)
            mv[ids]=eps*cv;out+=loss
        # Local finite-rate phase changes; actual transfers are used for heat & mass.
        sat=np.maximum(gas,0)*MW*psat(temp)/(R*temp); ids=self.pore
        excess=np.maximum(mv[ids]-sat[ids],0)
        kd=self.kvi*(temp[ids]<TF); kt=self.kvl+kd
        total=excess*(dt*kt)/(1+dt*kt)
        cond=total*self.kvl/kt; dep=total*kd/kt
        mv[ids]-=total;ml[ids]+=cond;mi[ids]+=dep;heat[ids]+=LC*cond+(LC+LF)*dep
        evap=np.minimum(ml[ids],np.maximum(sat[ids]-mv[ids],0)*dt*self.kvl/(1+dt*self.kvl))
        mv[ids]+=evap;ml[ids]-=evap;heat[ids]-=LC*evap
        freezable=ml.copy();freezable[self.mem]=np.maximum(ml[self.mem]-WPL*self.lambda_nf,0)
        kf=self.kf*np.maximum((TF-temp)/TF,0);km=self.km*np.maximum((temp-TF)/TF,0)
        freeze=freezable*dt*kf/(1+dt*kf); melt=mi*dt*km/(1+dt*km)
        ml+=melt-freeze;mi+=freeze-melt;heat+=LF*(freeze-melt)
        return mv,ml,mi,heat,produced,out

    def gas_step(self,T,ml,mi,nh,no,j,dt):
        temp=T[self.idx];gas=self.fractions(ml,mi); outs=[]; inventories=[]
        for ids,nold,dref,frac,cl,nu,left in ((self.a,nh,1.1e-4,1.,self.acl,2,True),(self.c,no,2.2e-5,YO,self.ccl,4,False)):
            eps=np.maximum(gas[ids],1e-12);D=dref*(temp[ids]/298.15)**1.5*eps**1.5
            src=np.zeros(len(ids));mask=np.isin(ids,cl);src[mask]=-j/(nu*F*np.sum(self.dx[cl]))
            bidx=0 if left else -1;b=(2*D[bidx]/self.dx[ids][bidx],frac*101325/(R*temp[ids][bidx]))
            c,out=transport(nold,eps,self.dx[ids],self.face(D,ids),dt,source=src,left=b if left else None,right=None if left else b)
            inventories.append(eps*c);outs.append(out)
        return *inventories,outs

    def thermal_step(self,T0,mv,ml,mi,nh,no,j,phase,dt,ambient):
        C,k=self.properties(mv,ml,mi)
        g=1/(self.dxT[:-1]/(2*k[:-1])+self.dxT[1:]/(2*k[1:]))
        gl=1/(1/40+self.dxT[0]/(2*k[0]));gr=1/(1/40+self.dxT[-1]/(2*k[-1]))
        T=T0.copy();qphase=np.zeros(self.nT);qphase[self.idx]=phase/dt
        for iteration in range(30):
            e=self.electro(T,ml,mi,nh,no,j);qgen=j*(1.48-e['V_model_V'])
            source=qphase.copy();source[self.idx]+=qgen/self.L
            new,loss=transport(C*T0,C,self.dxT,g,dt,source,left=(gl,ambient),right=(gr,ambient))
            err=np.max(np.abs(new-T));T=new
            if err<1e-7:break
        if err>=1e-6:raise RuntimeError(f'Thermal iteration did not converge: {err}')
        sensible=float(np.dot(C*(T-T0),self.dxT))
        return T,qgen*dt,float(np.dot(phase,self.dx)),loss,sensible,iteration+1

    def run(self,t_samples,current,T0_C,dt=.025,fields=False):
        ts=np.asarray(t_samples);current=np.asarray(current)
        T=np.full(self.nT,T0_C+TF);mv=np.zeros(self.n);ml=np.zeros(self.n);mi=np.zeros(self.n)
        ml[self.mem]=WPL*3
        nh=self.eps[self.a]*101325/(R*(T0_C+TF));no=self.eps[self.c]*YO*101325/(R*(T0_C+TF))
        initial=float(np.dot(mv+ml+mi,self.dx));sumprod=sumout=qgen=qphase=qloss=sensible=0.
        h0=np.dot(nh,self.dx[self.a]);o0=np.dot(no,self.dx[self.c]);hout=oout=hcons=ocons=0.
        rows=[]; fieldrows=[];t=0.;max_it=0;ever_invalid=False;min_gas=np.inf;min_kappa=np.inf;max_ratio=0.
        def record(tt,j):
            e=self.electro(T,ml,mi,nh,no,j);ice=mi/RI; gas=self.fractions(ml,mi)
            row=dict(t_s=float(tt),j_A_m2=j,T_model_C=float(np.dot(T,self.dxT)/self.dxT.sum()-TF),
                T_MEA_C=float(np.dot(T[self.idx],self.dx)/self.L-TF),T_min_C=T.min()-TF,T_max_C=T.max()-TF,
                ice_max_bulk=ice.max(),ice_pore_max_bulk=ice[self.pore].max(),ice_mem_max_bulk=ice[self.mem].max(),
                s_ice_pore_max=np.max(ice[self.pore]/self.eps[self.pore]),
                s_liquid_pore_max=np.max(ml[self.pore]/RL/self.eps[self.pore]),gas_porosity_min=gas[self.pore].min(),
                ice_max_x_um=float(self.x[np.argmax(ice)]*1e6),ice_max_layer=self.label[np.argmax(ice)],
                water_produced_kg_m2=sumprod,water_stored_kg_m2=float(np.dot(mv+ml+mi,self.dx)),water_initial_kg_m2=initial,
                water_vapor_kg_m2=float(np.dot(mv,self.dx)),water_liquid_pore_kg_m2=float(np.dot(ml[self.pore],self.dx[self.pore])),
                water_unfrozen_mem_kg_m2=float(np.dot(ml[self.mem],self.dx[self.mem])),water_ice_kg_m2=float(np.dot(mi,self.dx)),
                water_out_kg_m2=sumout,water_balance_kg_m2=float(np.dot(mv+ml+mi,self.dx))-initial-sumprod+sumout,
                heat_gen_J_m2=qgen,heat_phase_J_m2=qphase,heat_loss_J_m2=qloss,heat_sensible_integral_J_m2=sensible,
                energy_balance_J_m2=sensible-qgen-qphase+qloss,
                H2_balance_mol_m2=float(np.dot(nh,self.dx[self.a]))-h0+hout+hcons,
                O2_balance_mol_m2=float(np.dot(no,self.dx[self.c]))-o0+oout+ocons,
                model_valid=int(gas[self.pore].min()>=-1e-10 and e['j_over_jlim']<1 and e['kappa_min_S_m']>0 and min(nh.min(),no.min(),mv.min(),ml.min(),mi.min())>=-1e-8),
                thermal_iterations_max=max_it,ever_invalid=int(ever_invalid),min_gas_porosity_all_steps=min_gas if np.isfinite(min_gas) else gas[self.pore].min(),min_kappa_all_steps=min_kappa if np.isfinite(min_kappa) else e['kappa_min_S_m'],max_j_over_jlim_all_steps=max_ratio,**e)
            rows.append(row)
            if fields:
                for k in range(self.nT):
                    local=k-self.offset
                    inside=0<=local<self.n
                    fieldrows.append(dict(t_s=float(tt),x_um=self.xT[k]*1e6,dx_um=self.dxT[k]*1e6,layer=self.labelsT[k],T_C=T[k]-TF,lambda_unfrozen=(ml[local]/WPL if inside and self.label[local]=='PEM' else 0.),
                        mv_kg_m3=mv[local] if inside else 0.,ml_kg_m3=ml[local] if inside else 0.,mi_kg_m3=mi[local] if inside else 0.,
                        ice_bulk=ice[local] if inside else 0.,gas_porosity=gas[local] if inside else 0.))
        record(ts[0],current[0])
        for target in ts[1:]:
            steps=int(np.ceil((target-t)/dt-1e-8));h=(target-t)/steps
            for _ in range(steps):
                j=float(np.interp(t+h/2,ts,current))
                mv,ml,mi,ph,prod,out=self.mass_step(T,mv,ml,mi,j,h)
                nh,no,gasout=self.gas_step(T,ml,mi,nh,no,j,h)
                T,qg,qp,ql,ss,nit=self.thermal_step(T,mv,ml,mi,nh,no,j,ph,h,T0_C+TF)
                ee=self.electro(T,ml,mi,nh,no,j);gg=self.fractions(ml,mi)[self.pore].min()
                min_gas=min(min_gas,gg);min_kappa=min(min_kappa,ee['kappa_min_S_m']);max_ratio=max(max_ratio,ee['j_over_jlim'])
                ever_invalid=ever_invalid or gg < -1e-10 or ee['kappa_min_S_m'] <= 0 or ee['j_over_jlim'] >= 1 or min(nh.min(),no.min(),mv.min(),ml.min(),mi.min()) < -1e-8
                sumprod+=prod;sumout+=out;qgen+=qg;qphase+=qp;qloss+=ql;sensible+=ss;max_it=max(max_it,nit)
                hout+=gasout[0];oout+=gasout[1];hcons+=h*j/(2*F);ocons+=h*j/(4*F)
                t+=h
            t=float(target);record(t,float(np.interp(t,ts,current)))
        return rows,fieldrows
