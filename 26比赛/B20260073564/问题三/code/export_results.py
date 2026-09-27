"""Fine-grid event correction, CSV trajectories, convergence and sensitivity."""
import csv,json,hashlib,shutil,time
from aux_model import ROOT,np,simulate,HISTORY,THERMAL,Q_TIME,make_config,J0
from scipy.optimize import brentq,minimize_scalar
from optimize_aux import save_csv

DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
DT=.00625;SCALE=8

def trajectory(name,h):
    np.savetxt(DATA/f'trajectory_{name}.csv',h,delimiter=',',header=','.join(HISTORY),comments='',fmt='%.12g',encoding='utf-8-sig')

def brief(kind,p,th,dt=DT,scale=SCALE,post=None,stop=False,record=False,**kw):
    return simulate(kind,p,th,dt=dt,scale=scale,post=post,stop=stop,record=record,**kw)

def main():
    # Final correction uses the active-power pattern discovered by unrestricted search.
    # It is not a presupposed control allocation: see optimization CSVs.
    ones=np.ones(5)
    tp=brentq(lambda t:brief('P',ones,t)[0]['final_min_T_C']-1e-4,24.,28.,xtol=2e-8)
    tr=brentq(lambda t:brief('P',ones,t,post=Q_TIME)[0]['post_switch_min_T_C']-.001,49.,55.,xtol=2e-7)
    curve=[]
    def cost(c):
        s,*_=brief('C',[1,1,c,1,1],60,post=60,stop=True)
        curve.append(dict(center_q_W_cm2=c,energy_J=s['E_aux_J'],startup_s=s['first_success_s']))
        return s['E_aux_J'] if s['feasible'] else 1e8
    res=minimize_scalar(cost,bounds=(.4,.85),method='bounded',options={'xatol':1e-4})
    pc=np.array([1,1,float(res.x),1,1]);sc,*_=brief('C',pc,60,post=60,stop=True)
    tc=sc['first_success_s']
    controls={'P':(ones,tp),'C':(pc,tc),'R':(ones,tr)}
    print('FINAL CONTROLS',[(k,p.tolist(),t) for k,(p,t) in controls.items()],flush=True)
    save_csv(DATA/'fine_center_power_search.csv',curve)
    rows=[];budget=[];postrows=[];converge=[]
    for strategy,(power,th) in controls.items():
        kind='C' if strategy=='C' else 'P'
        horizon=th if strategy=='C' else 0.
        # C reuses root-located ts; a 1e-7 K root tolerance satisfies strict crossing.
        s,h,states,temp=brief(kind,power,th,post=horizon,record=True)
        r=dict(strategy=strategy,**{f'q{k+1}_W_cm2':float(power[k]) for k in range(5)},
               **{f'E{k+1}_J':float(25*power[k]*th) for k in range(5)},
               th_s=th,startup_s=th,**s)
        r['result']='success' if s['feasible'] else 'failed'
        r['scope']='postload_no_subzero_extra_constraint' if strategy=='R' else 'first_success'
        rows.append(r)
        if strategy!='R':trajectory(strategy,h)
        budget.append(dict(strategy=strategy,scope='heater_interval',
          E_aux_J=s['E_aux_J'],E_gen_J=s['E_gen_J'],E_phase_J=s['E_phase_J'],
          E_loss_J=s['E_loss_J'],E_sensible_J=s['E_sensible_J'],residual_J=s['energy_residual_J']))
        # Export actual final water/ice fields, including all five cells, in SI.
        cfg=make_config(scale=SCALE,j0=J0)
        fields=[];xx=np.cumsum(cfg.dx)-cfg.dx/2
        for k,state in enumerate(states):
            for i in range(len(cfg.dx)):
                fields.append(dict(cell=k+1,x_m=xx[i],dx_m=cfg.dx[i],porosity=cfg.eps[i],
                   vapor_kg_m3=state[0][i],liquid_kg_m3=state[1][i],ice_kg_m3=state[2][i]))
        save_csv(DATA/f'final_fields_{strategy}.csv',fields)
        # First-hit parameters fixed; no resetting membrane state at heater shutdown.
        ps,ph,*_=brief(kind,power,th,post=(Q_TIME if kind=='P' else Q_TIME),record=True)
        trajectory(strategy if strategy=='R' else strategy+'_postload',ph)
        postrows.append(dict(strategy=strategy,th_s=th,**ps))
        # Numerical convergence at fixed physical controls, not reoptimized variants.
        for scale,dt in ((1,.1),(2,.05),(4,.025),(8,.025),(8,.0125),(8,.00625),(16,.00625)):
            qs,*_=brief(kind,power,th,dt=dt,scale=scale,
                       post=Q_TIME if strategy=='R' else horizon)
            converge.append(dict(strategy=strategy,scale=scale,dt_s=dt,**qs))
        print('SUMMARY',strategy,json.dumps(r,ensure_ascii=False),flush=True)
    save_csv(DATA/'summary_results.csv',rows)
    save_csv(DATA/'energy_budget.csv',budget)
    save_csv(DATA/'postload_verification.csv',postrows)
    save_csv(DATA/'convergence.csv',converge)
    # Table 4 in requested language. Quantities stay numeric except vector fields.
    table=[]
    for r in rows[:2]:
        table.append({'辅助冷启动策略':'纯预加热启动' if r['strategy']=='P' else '恒定功率协同启动',
          '加热功率密度分配_W_cm-2':json.dumps([r[f'q{k}_W_cm2'] for k in range(1,6)]),
          '加热持续时间_s':r['th_s'],
          '各片辅助加热能耗_J':json.dumps([r[f'E{k}_J'] for k in range(1,6)]),
          '总辅助加热能耗_J':r['E_aux_J'],'总启动时间_s':r['startup_s'],
          '最大冰体积分数':r['max_ice_bulk'],'最低电压_V':r['min_voltage_V'],
          '累计电荷量_C_cm-2':r['charge_C_cm2'],'启动结果':'成功' if r['feasible'] else '失败'})
    save_csv(DATA/'表4_问题三主结果.csv',table)
    # Controlled sensitivity: fixed q vector, recompute the first hit with constant heat.
    # This is NOT reoptimization; additional th changes only to recover the same target.
    sensitivities=[]
    variants=[('baseline',1.,None,None),('kf',.1,{'kf':.1},None),('kf',10.,{'kf':10.},None),
              ('gE',.8,None,(1,.8)),('gE',1.2,None,(1,1.2)),
              ('EP_capacity',.8,None,(2,.8)),('EP_capacity',1.2,None,(2,1.2)),
              ('h',.8,None,(5,.8)),('h',1.2,None,(5,1.2)),
              ('convection_on_EP',1.,None,(3,1.))]
    for param,value,kw,tchange in variants:
        therm=THERMAL.copy()
        if tchange:therm[tchange[0]]=tchange[1]
        for kind,p in [('P',ones),('C',pc)]:
            if kind=='P':
                th=brentq(lambda t:brief('P',p,t,dt=.025,scale=4,thermal=therm,**(kw or {}))[0]['final_min_T_C']-1e-4,10,90)
                ss,*_=brief('P',p,th,dt=.025,scale=4,thermal=therm,**(kw or {}))
            else:
                ss,*_=brief('C',p,Q_TIME,dt=.025,scale=4,post=Q_TIME,stop=True,thermal=therm,**(kw or {}))
            sensitivities.append(dict(strategy=kind,parameter=param,value=value,
              interpretation='fixed_power_recomputed_heating_duration',**ss))
    save_csv(DATA/'sensitivity.csv',sensitivities)
    # Source snapshots and hashes record the inherited model, not fitted Q3 data.
    inputs=ROOT/'inputs';inputs.mkdir(exist_ok=True)
    sources=[ROOT.parent/'问题3_建模推导源文件.md',ROOT.parent/'问题2_求解结果/code/stack_model.py',
             ROOT.parent/'问题2_求解结果/inputs/附件1_参数清单.csv',
             ROOT.parent/'问题2_求解结果/inputs/calibration_bp.json',
             ROOT.parent/'问题2_求解结果/inputs/题目全文提取.txt']
    hashes=[]
    for src in sources:
        dest=inputs/src.name;shutil.copy2(src,dest)
        hashes.append(dict(source=str(src.relative_to(ROOT.parent)),snapshot='inputs/'+src.name,
                           sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
    save_csv(DATA/'source_manifest.csv',hashes)
    (DATA/'final_controls.json').write_text(json.dumps({k:{'power':v[0].tolist(),'th_s':v[1]} for k,v in controls.items()},indent=2),encoding='utf-8')
    print('All final data exported',flush=True)

if __name__=='__main__':main()
