"""Fixed phase references; calibrate only j0; six-channel sensitivity and kf profiles.
Run from any directory: python code/run_question1.py [--reuse] [--no-verify].
--reuse is permitted only for calibrations with the current model hash.
"""
import sys,time,argparse,hashlib,platform
from pathlib import Path
from model import Model,PHASE_NAMES,LC,LF,TF,MW,R,WPL,psat_liquid,psat_ice
from io_utils import *
from scipy.optimize import minimize_scalar
import scipy

DAT=ROOT/'data'; DAT.mkdir(exist_ok=True)
PHASE_BASE=dict(kf=1.,km=1.,kcond=1.,kevap=1.,kdep=1e-4,ksub=1e-4)
PHASE_CN=dict(kf='冻结',km='融化',kcond='凝结',kevap='蒸发',kdep='凝华',ksub='升华')
PROFILE_KF=[1e-4,1e-3,.01,.03,.1,.3,1.,3.,10.]
MODEL_HASH=hashlib.sha256((ROOT/'code/model.py').read_bytes()).hexdigest()

def simulate(d,bp,j0,kf=1.,dt=.05,scale=1,fields=False,**kwargs):
    m=Model(bp=bp,j0=j0,kf=kf,scale=scale,**kwargs)
    rows,field=m.run(d['t'],d['j'],d['T0'],dt=dt,fields=fields)
    return attach_observations(rows,d),field

def objective(rows):
    if any(not r['model_valid'] or r['ever_invalid'] for r in rows):return 1e6
    return float(np.mean([(r['V_rel_error_pct']/100)**2+(r['T_rel_error_pct']/100)**2 for r in rows]))

def fit_j0(d,bp,kf=1.,fine=False,trace=None):
    trace=[] if trace is None else trace
    def solve(logj,dt,scale,stage):
        rr,_=simulate(d,bp,10**logj,kf,dt=dt,scale=scale)
        value=objective(rr)
        trace.append(dict(evaluation=len(trace)+1,stage=stage,j0_A_m2=10**logj,kf_s_inv=kf,mean_squared_relative_objective=value,dt_s=dt,grid_scale=scale,valid_samples=sum(r['model_valid'] for r in rr)))
        return value
    grid=np.linspace(-5,3,9)
    vals=[solve(x,.05,1,'coarse_grid') for x in grid]
    k=int(np.argmin(vals));lo=grid[max(k-1,0)];hi=grid[min(k+1,len(grid)-1)]
    opt=minimize_scalar(lambda x:solve(x,.05,1,'coarse_fit'),bounds=(lo,hi),method='bounded',options={'xatol':.001})
    if fine:
        opt=minimize_scalar(lambda x:solve(x,.0125,2,'fine_fit'),bounds=(max(-5,opt.x-.18),min(3,opt.x+.18)),method='bounded',options={'xatol':.0001})
    return 10**float(opt.x),float(opt.fun),trace

def calibration(d,bp):
    j0,value,trace=fit_j0(d,bp,fine=True)
    tag='bp' if bp else 'main';write_csv(DAT/f'calibration_trace_{tag}.csv',trace)
    p=dict(j0=j0,**PHASE_BASE,kvl=1.,kvi=1e-4,objective=value,objective_normalization='mean over 176 samples',
       method='coarse log-j0 grid + bounded scalar minimization + fine-grid refinement',
       fitted_parameters=['j0'],fixed_phase_parameters=PHASE_BASE,reference_time_s=1.,
       parameter_status='attachment weights / assumed 1 s; kf/km pore extension and reverse sublimation are closures',
       training='minus20 only, 176 samples, 0-35 s',validation='minus25 held out',
       model_sha256=MODEL_HASH,fit_dt_s=.0125,fit_grid_scale=2,n_model_evaluations=len(trace),
       log10_j0_bounds=[-5,3],kf_is_fitted=False)
    json_write(DAT/f'calibration_{tag}.json',p);print('CALIBRATED',tag,p,flush=True)
    return p

def export_work(tag,key,d,rows,field):
    write_csv(DAT/f'{tag}_{key}.csv',rows);write_csv(DAT/f'fields_{tag}_{key}.csv',field)
    cnrows=[]
    for r in rows:
        cn={'工况初温_摄氏度':d['T0'],'时间_s':r['t_s'],'电流密度_A每m2':r['j_A_m2'],
          '实验电压_V':r['V_exp_V'],'模型电压_V':r['V_model_V'],'电压相对误差_pct':r['V_rel_error_pct'],
          '实验温度_摄氏度':r['T_exp_C'],'模型温度_摄氏度':r['T_model_C'],'温度相对误差_pct_摄氏口径':r['T_rel_error_pct'],
          '温度相对误差_pct_开尔文口径':r['T_rel_error_K_pct'],'MEA平均温度_摄氏度':r['T_MEA_C'],
          '局部最高温度_摄氏度':r['T_max_C'],'模型最大冰体积分数':r['ice_max_bulk'],
          '孔隙最大冰体积分数':r['ice_pore_max_bulk'],'膜最大冰体积分数':r['ice_mem_max_bulk'],
          '最大冰所在层':r['ice_max_layer'],'孔隙最大冰饱和度':r['s_ice_pore_max'],
          '膜平均未冻含水量_lambda':r['lambda_mean'],'活化损失_V':r['eta_act_V'],'欧姆损失_V':r['eta_ohm_V'],
          '浓差损失_V':r['eta_con_V'],'极限电流密度_A每m2':r['j_lim_A_m2'],
          '累计产水_kg每m2':r['water_produced_kg_m2'],'累计排水_kg每m2':r['water_out_kg_m2'],
          '冰库存_kg每m2':r['water_ice_kg_m2'],'冰库存与累计产水质量比':r['ice_to_produced_water_ratio'],
          '累计反应热_J每m2':r['heat_gen_J_m2'],'累计相变热_J每m2':r['heat_phase_J_m2'],
          '累计吸附等效热_J每m2':r['heat_adsorption_J_m2'],'累计散热_J每m2':r['heat_loss_J_m2'],
          '水质量守恒残差_kg每m2':r['water_balance_kg_m2'],'冰质量收支残差_kg每m2':r['ice_balance_kg_m2'],
          '离散能量守恒残差_J每m2':r['energy_balance_J_m2'],'相变潜热重建残差_J每m2':r['phase_heat_balance_J_m2'],
          '物理状态有效':r['model_valid'],'曾有内部步失效':r['ever_invalid']}
        for name,label in [('cond','凝结'),('evap','蒸发'),('dep','凝华'),('sub','升华'),('frz','冻结'),('mlt','融化')]:
            cn[f'累计{label}_kg每m2']=r[f'phase_{name}_kg_m2']
            cn[f'采样段平均{label}速率_kg每m2每s']=r[f'rate_{name}_kg_m2_s']
        cnrows.append(cn)
    label='含双极板修订' if tag=='bp' else '五层基线'
    write_csv(DAT/f'{label}_{key}_0至35秒全部采样数据.csv',cnrows)
    every5=[r for r in cnrows if np.isclose(r['时间_s']/5,round(r['时间_s']/5),atol=1e-8)]
    assert len(every5)==8;write_csv(DAT/f'{label}_{key}_每5秒结果表.csv',every5)
    return cnrows

def parameter_sources():
    rows=[]
    for param in PHASE_BASE:
        row={'kf':48,'km':48,'kcond':49,'kevap':49,'kdep':50,'ksub':50}[param]
        caveat={'kf':'膜水-冰系数扩展至孔液冻结；过冷度归一化另属闭合',
                'km':'膜水-冰系数扩展至融化；过热度归一化另属闭合',
                'ksub':'由凝华权重对称扩展；附件未独立给升华值'}.get(param,'附件权重采用1秒参考时间转成有效速率')
        rows.append(dict(parameter=param,process=PHASE_CN[param],attachment_row=row,attachment_unit='-',
            weight=PHASE_BASE[param],assumed_reference_time_s=1.,effective_rate_s_inv=PHASE_BASE[param],
            fitting_status='fixed reference, not inferred from V/T',qualification=caveat))
    write_csv(DAT/'相变参数来源与处理.csv',rows)

def unit_and_input_audits(data):
    inputs=[];audit=[]
    for key,d in data.items():
        for i,t in enumerate(d['t']):inputs.append(dict(condition=key,t_s=t,I_exp_A=d['I'][i],j_A_m2=d['j'][i],V_exp_V=d['V'][i],T_exp_C=d['T'][i],implied_area_cm2=d['I'][i]/d['j'][i]*1e4,I_from_25cm2_A=d['j'][i]*.0025))
        heat=np.trapezoid(d['j']*(1.48-d['V']),d['t']);loss=np.trapezoid(80*(d['T']-d['T0']),d['t'])
        audit.append(dict(condition=key,n_samples=176,interval_s=.2,t_start_s=0.,t_end_s=35.,
            apparent_heat_capacity_J_m2_K=(heat-loss)/(d['T'][-1]-d['T0']),reaction_heat_using_experiment_J_m2=heat,
            heat_loss_using_experiment_J_m2=loss,bipolar_plate_heat_capacity_J_m2_K=6066.72,
            implied_area_median_cm2=float(np.median(d['I']/d['j']*1e4)),given_area_cm2=25.))
    write_csv(DAT/'原始数据与单位审计.csv',inputs);write_csv(DAT/'热容与面积诊断.csv',audit)

def sensitivity(data,cals):
    out=[];series=[]
    for bp,tag in [(False,'main'),(True,'bp')]:
        j0=cals[tag]['j0']
        cache={key:simulate(d,bp,j0,dt=.025,scale=2)[0] for key,d in data.items()}
        experiments=[(name,PHASE_BASE[name],factor,{name:PHASE_BASE[name]*factor},'phase_one_at_a_time') for name in PHASE_BASE for factor in [.1,1.,10.]]
        experiments += [('all_phase_rates',1.,factor,{name:value*factor for name,value in PHASE_BASE.items()},'common_phase_timescale') for factor in [.1,1.,10.]]
        experiments += [(name,base,value/base,{name:value},'structural_closure') for name,base,values in [('lambda_nf',3.,[2.5,3.,3.5]),('exchange_factor',1.,[.5,1.,2.])] for value in values]
        for name,base,factor,options,kind in experiments:
            for key,d in data.items():
                rr=cache[key] if factor==1 else simulate(d,bp,j0,dt=.025,scale=2,**options)[0]
                m=metrics(rr);b=cache[key];last=rr[-1]
                entry=dict(model=tag,condition=key,parameter=name,kind=kind,reference_value=base,multiplier=factor,value=base*factor,
                   V_RMSE=m['V_RMSE'],T_RMSE=m['T_RMSE'],mean_squared_relative_objective=objective(rr),
                   ice_peak_bulk=m['ice_peak_bulk'],ice_at35_bulk=last['ice_max_bulk'],ice_pore_at35=last['ice_pore_max_bulk'],ice_mem_at35=last['ice_mem_max_bulk'],
                   delta_ice_at35=last['ice_max_bulk']-b[-1]['ice_max_bulk'],water_ice_at35_kg_m2=last['water_ice_kg_m2'],
                   max_delta_V_V=max(abs(r['V_model_V']-s['V_model_V']) for r,s in zip(rr,b)),
                   max_delta_T_C=max(abs(r['T_model_C']-s['T_model_C']) for r,s in zip(rr,b)),
                   max_delta_ice_bulk=max(abs(r['ice_max_bulk']-s['ice_max_bulk']) for r,s in zip(rr,b)),
                   valid_samples=m['valid_samples'],ever_invalid=last['ever_invalid'],dt_s=.025,grid_scale=2)
                for phase in PHASE_NAMES:entry[f'phase_{phase}_kg_m2']=last[f'phase_{phase}_kg_m2']
                out.append(entry)
                for r in rr:series.append(dict(model=tag,condition=key,parameter=name,multiplier=factor,kind=kind,**{k:r[k] for k in ['t_s','V_model_V','T_model_C','ice_max_bulk','ice_pore_max_bulk','ice_mem_max_bulk','water_ice_kg_m2','model_valid','ever_invalid']}))
        print('SENSITIVITY',tag,'done',flush=True)
    write_csv(DAT/'参数与闭合敏感性.csv',out);write_csv(DAT/'相变敏感性全时序.csv',series)

def profiles(data,cals):
    entries=[];series=[];ranges=[];thresholds=[]
    for bp,tag in [(False,'main'),(True,'bp')]:
        cases=[]
        for kf in PROFILE_KF:
            j0,J,_=fit_j0(data['minus20'],bp,kf)
            for key,d in data.items():
                rr,_=simulate(d,bp,j0,kf,dt=.05,scale=1);m=metrics(rr)
                entries.append(dict(model=tag,condition=key,kf_s_inv=kf,j0_reoptimized_A_m2=j0,training_objective=J,
                   mean_squared_relative_objective=objective(rr),V_RMSE=m['V_RMSE'],T_RMSE=m['T_RMSE'],
                   ice_at35_bulk=rr[-1]['ice_max_bulk'],ice_pore_at35=rr[-1]['ice_pore_max_bulk'],ice_mem_at35=rr[-1]['ice_mem_max_bulk'],
                   water_ice_at35_kg_m2=rr[-1]['water_ice_kg_m2'],valid_samples=m['valid_samples'],ever_invalid=rr[-1]['ever_invalid']))
                for r in rr:series.append(dict(model=tag,condition=key,kf_s_inv=kf,j0_A_m2=j0,training_objective=J,**r))
                cases.append((key,kf,J,rr))
            print('PROFILE',tag,kf,j0,J,flush=True)
        best=min(x[2] for x in cases)
        for allowance in [.01,.05,.10]:
            selected=[x for x in cases if x[2]<=best*(1+allowance)]
            for key in data:
                subset=[x for x in selected if x[0]==key]
                thresholds.append(dict(model=tag,condition=key,allowed_relative_objective_increase=allowance,
                    min_training_objective=best,selected_kf_min=min(x[1] for x in subset),selected_kf_max=max(x[1] for x in subset),
                    n_scenarios=len(subset),ice_at35_min=min(x[3][-1]['ice_max_bulk'] for x in subset),ice_at35_max=max(x[3][-1]['ice_max_bulk'] for x in subset),
                    interpretation='engineering error tolerance; discrete conditional scenarios; not statistical confidence'))
                if allowance==.05:
                    for i,t in enumerate(data[key]['t']):
                        item=dict(model=tag,condition=key,t_s=t,n_scenarios=len(subset),objective_tolerance_fraction=.05)
                        for field in ['V_model_V','T_model_C','ice_max_bulk','ice_pore_max_bulk','ice_mem_max_bulk','water_ice_kg_m2']:
                            item[field+'_min']=min(x[3][i][field] for x in subset);item[field+'_max']=max(x[3][i][field] for x in subset)
                        ranges.append(item)
    write_csv(DAT/'冻结系数剖面.csv',entries);write_csv(DAT/'冻结系数情景全时序.csv',series)
    write_csv(DAT/'近优冻结情景范围_非置信区间.csv',ranges);write_csv(DAT/'近优阈值敏感性.csv',thresholds)

def checks(data,cals,formal):
    conv=[]
    for bp,tag in [(False,'main'),(True,'bp')]:
        for key,d in data.items():
            base=formal[tag+'_'+key]
            for name,scale,dt in [('time_half',2,.00625),('grid_double',4,.0125),('grid_double_time_half',4,.00625)]:
                rr,_=simulate(d,bp,cals[tag]['j0'],dt=dt,scale=scale)
                entry=dict(model=tag,condition=key,check=name,grid_scale=scale,dt_s=dt)
                for col in ['V_model_V','T_model_C','ice_max_bulk','ice_pore_max_bulk','ice_mem_max_bulk']:
                    delta=max(abs(x[col]-y[col]) for x,y in zip(rr,base));peak=max(abs(x[col]) for x in base)
                    entry['max_difference_'+col]=delta;entry['relative_difference_to_peak_'+col]=delta/max(peak,1e-12)
                entry.update(valid_samples=sum(r['model_valid'] for r in rr),ever_invalid=rr[-1]['ever_invalid']);conv.append(entry)
    write_csv(DAT/'网格与时间步收敛.csv',conv)
    tested=[]
    def add(name,value,tol):tested.append(dict(check=name,observed=float(value),tolerance=tol,passed=bool(value<=tol)))
    z=Model(bp=True,kf=0,kdep=0,ksub=0,exchange_factor=0)
    zr,_=z.run(np.array([0.,.2,1.]),np.zeros(3),-20,dt=.025)
    add('zero_current_constant_temperature',max(abs(r['T_model_C']+20) for r in zr),1e-6)
    rr,_=simulate(data['minus20'],True,cals['bp']['j0'],kf=0,kdep=0)
    add('no_formation_no_ice',max(r['ice_max_bulk'] for r in rr),1e-12)
    # Each independent phase channel: proper sign, nonnegative pools, paired mass and latent heat.
    expected_heat={'cond':LC,'evap':-LC,'dep':LC+LF,'sub':-(LC+LF),'frz':LF,'mlt':-LF}
    param={'cond':'kcond','evap':'kevap','dep':'kdep','sub':'ksub','frz':'kf','mlt':'km'}
    for phase in PHASE_NAMES:
        opts={k:0. for k in PHASE_BASE};opts[param[phase]]=1.
        m=Model(**opts);T=np.full(m.n,TF+(5 if phase=='mlt' else -20))
        mv=np.zeros(m.n);ml=np.zeros(m.n);mi=np.zeros(m.n);i=m.ccl[0]
        if phase in ['cond','dep']:mv[i]=.05
        elif phase in ['evap','frz']:ml[i]=20.
        else:mi[i]=20.
        v,l,ice,h,pc=m.phase_step(T,mv,ml,mi,.2)
        add(phase+'_mass_conservation',np.max(abs(v+l+ice-mv-ml-mi)),1e-11)
        add(phase+'_nonnegative',max(0.,-min(v.min(),l.min(),ice.min())),1e-12)
        add(phase+'_activated',0 if pc[phase]>0 else 1,0)
        add(phase+'_latent_heat',abs(h@m.dx-expected_heat[phase]*pc[phase]),1e-8)
    m=Model(kf=0,km=0,kcond=0,kevap=0,kdep=0,ksub=0)
    rng=np.random.default_rng(20260924);v=rng.random(m.n)*.01;l=rng.random(m.n);ice=rng.random(m.n)
    a,b,c,h,pc=m.phase_step(np.full(m.n,253.15),v,l,ice,.7)
    add('all_phase_off_identity',max(np.max(abs(a-v)),np.max(abs(b-l)),np.max(abs(c-ice)),np.max(abs(h))),1e-12)
    write_csv(DAT/'退化与守恒测试.csv',tested)
    assert all(x['passed'] for x in tested)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reuse',action='store_true');ap.add_argument('--no-verify',action='store_true');args=ap.parse_args()
    start=time.perf_counter();data=read_data();parameter_sources();unit_and_input_audits(data)
    cals={};summary={};formal={}
    for bp,tag in [(False,'main'),(True,'bp')]:
        path=DAT/f'calibration_{tag}.json'
        if args.reuse and path.exists():
            p=json.loads(path.read_text());assert p.get('model_sha256')==MODEL_HASH,'Model changed: run without --reuse.'
        else:p=calibration(data['minus20'],bp)
        cals[tag]=p;all_cn=[]
        for key,d in data.items():
            rows,field=simulate(d,bp,p['j0'],dt=.0125,scale=2,fields=True)
            assert all(r['model_valid'] and not r['ever_invalid'] for r in rows)
            formal[tag+'_'+key]=rows;summary[tag+'_'+key]=metrics(rows)
            all_cn.extend(export_work(tag,key,d,rows,field))
        label='含双极板修订' if bp else '五层基线'
        write_csv(DAT/f'{label}_两工况352行工作数据.csv',all_cn)
    json_write(DAT/'summary.json',summary)
    if not args.no_verify:
        sensitivity(data,cals);profiles(data,cals);checks(data,cals,formal)
    manifest=dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,runtime_s=time.perf_counter()-start,
       calibration_condition='-20 C only',validation_condition='-25 C held out',fitted_parameters=['j0'],phase_baseline=PHASE_BASE,reference_time_s=1.,
       final_dt_s=.0125,grid_counts_MEA=[16,6,12,8,16],grid_counts_BP_each=8,
       sensitivity_dt_s=.025,sensitivity_grid_scale=2,profile_dt_s=.05,profile_grid_scale=1,
       sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'附件1.xlsx',SOURCE/'附件2.xlsx',ROOT.parent/'问题1_建模推导源文件.md']},
       code_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'code').glob('*.py')})
    json_write(DAT/'运行记录与来源哈希.json',manifest)
    print('DONE',manifest['runtime_s'],flush=True)
if __name__=='__main__':main()
