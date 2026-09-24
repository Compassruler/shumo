"""Run calibration (-20 C only), independent validation (-25 C), diagnostics, CSVs.
Usage: python code/run_question1.py [--reuse] [--no-verify]
"""
import sys,time,argparse,hashlib,platform
from pathlib import Path
from model import Model
from io_utils import *
from scipy.optimize import least_squares, minimize_scalar
import scipy

DAT=ROOT/'data'; DAT.mkdir(exist_ok=True)
def simulate(d,bp,j0,kf,dt=.05,scale=1,fields=False,**kwargs):
    m=Model(bp=bp,j0=j0,kf=kf,scale=scale,**kwargs)
    rows,field=m.run(d['t'],d['j'],d['T0'],dt=dt,fields=fields)
    return attach_observations(rows,d),field

def fit(d,bp):
    trace=[]
    def fun(x):
        j0,kf=10**x
        rows,_=simulate(d,bp,j0,kf)
        v=np.array([r['V_model_V'] for r in rows]);t=np.array([r['T_model_C'] for r in rows])
        residual=np.r_[(v-d['V'])/abs(d['V']),(t-d['T'])/abs(d['T']),np.sqrt(1e-6)*(x-np.log10([.01,1.]))]
        if not all(r['model_valid'] for r in rows) or rows[-1]['ever_invalid']:residual[:-2]+=100
        trace.append(dict(evaluation=len(trace)+1,j0_A_m2=j0,kf_s_inv=kf,objective=float(residual@residual),valid_samples=sum(r['model_valid'] for r in rows)))
        if len(trace)%15==1:print(('bp' if bp else 'main'),trace[-1],flush=True)
        return residual
    fits=[]
    for initial in ([.1,.001],[.1,.1],[.1,1.]):
        result=least_squares(fun,np.log10(initial),bounds=([-5,-4],[3,1]),diff_step=.005,ftol=3e-5,xtol=3e-5,gtol=1e-5,max_nfev=35)
        fits.append(result)
    best=min(fits,key=lambda x:x.fun@x.fun)
    tag='bp' if bp else 'main';write_csv(DAT/f'calibration_trace_{tag}.csv',trace)
    sv=np.linalg.svd(best.jac,compute_uv=False)
    return dict(j0=float(10**best.x[0]),kf=float(10**best.x[1]),km=1.,kvl=1.,kvi=.0001,
        objective=float(best.fun@best.fun),log10_parameter_bounds=[[-5,3],[-4,1]],
        log_regularization_weight=1e-6,training='minus20 only, 176 samples, 0-35 s',
        fit_dt_s=.05,status=int(best.status),message=best.message,jacobian_singular_values=sv.tolist(),
        multistart_objectives=[float(x.fun@x.fun) for x in fits],n_model_evaluations=len(trace))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reuse',action='store_true');parser.add_argument('--no-verify',action='store_true');args=parser.parse_args()
    start=time.perf_counter();data=read_data()
    input_rows=[]
    for key,d in data.items():
        for i,t in enumerate(d['t']):input_rows.append(dict(condition=key,t_s=t,I_exp_A=d['I'][i],j_A_m2=d['j'][i],V_exp_V=d['V'][i],T_exp_C=d['T'][i],implied_area_cm2=d['I'][i]/d['j'][i]*1e4,I_from_25cm2_A=d['j'][i]*.0025))
    write_csv(DAT/'原始数据与单位审计.csv',input_rows)
    audit=[]
    for key,d in data.items():
        heat=np.trapezoid(d['j']*(1.48-d['V']),d['t']);loss=np.trapezoid(80*(d['T']-d['T0']),d['t'])
        audit.append(dict(condition=key,n_samples=len(d['t']),interval_s=.2,t_start_s=0.,t_end_s=35.,
            apparent_heat_capacity_J_m2_K=(heat-loss)/(d['T'][-1]-d['T0']),reaction_heat_using_experiment_J_m2=heat,
            heat_loss_using_experiment_J_m2=loss,bipolar_plate_heat_capacity_J_m2_K=6066.72,
            implied_area_median_cm2=float(np.median(d['I']/d['j']*1e4)),given_area_cm2=25.))
    write_csv(DAT/'热容与面积诊断.csv',audit)
    calibration={};summary={};all_bp=[];all_main=[]
    for bp,tag in [(False,'main'),(True,'bp')]:
        path=DAT/f'calibration_{tag}.json'
        if args.reuse and path.exists():p=json.loads(path.read_text())
        else:p=fit(data['minus20'],bp);json_write(path,p)
        calibration[tag]=p;print('CALIBRATED',tag,p,flush=True)
        for key,d in data.items():
            rows,field=simulate(d,bp,p['j0'],p['kf'],dt=.0125,scale=2,fields=True)
            write_csv(DAT/f'{tag}_{key}.csv',rows);write_csv(DAT/f'fields_{tag}_{key}.csv',field)
            summary[f'{tag}_{key}']=metrics(rows)
            chinese=[]
            for row in rows:
                cn={'工况初温_摄氏度':d['T0'],'时间_s':row['t_s'],'电流密度_A每m2':row['j_A_m2'],
                    '实验电压_V':row['V_exp_V'],'模型电压_V':row['V_model_V'],'电压相对误差_pct':row['V_rel_error_pct'],
                    '实验温度_摄氏度':row['T_exp_C'],'模型温度_摄氏度':row['T_model_C'],'温度相对误差_pct_摄氏口径':row['T_rel_error_pct'],
                    '温度相对误差_pct_开尔文口径':row['T_rel_error_K_pct'],'模型最大冰体积分数':row['ice_max_bulk'],
                    '孔隙最大冰体积分数':row['ice_pore_max_bulk'],'膜最大冰体积分数':row['ice_mem_max_bulk'],
                    '孔隙最大冰饱和度':row['s_ice_pore_max'],'膜平均未冻含水量_lambda':row['lambda_mean'],
                    '活化损失_V':row['eta_act_V'],'欧姆损失_V':row['eta_ohm_V'],'浓差损失_V':row['eta_con_V'],
                    '极限电流密度_A每m2':row['j_lim_A_m2'],'累计产水_kg每m2':row['water_produced_kg_m2'],
                    '累计排水_kg每m2':row['water_out_kg_m2'],'累计反应热_J每m2':row['heat_gen_J_m2'],
                    '累计相变热_J每m2':row['heat_phase_J_m2'],'累计散热_J每m2':row['heat_loss_J_m2'],
                    '水质量守恒残差_kg每m2':row['water_balance_kg_m2'],'离散能量守恒残差_J每m2':row['energy_balance_J_m2'],
                    '物理状态有效':row['model_valid']}
                chinese.append(cn)
            label='含双极板修订' if bp else '五层基线'
            write_csv(DAT/f'{label}_{key}_0至35秒全部采样数据.csv',chinese)
            every5=[row for row in chinese if np.isclose(row['时间_s']/5,round(row['时间_s']/5),atol=1e-8)]
            assert len(every5)==8
            write_csv(DAT/f'{label}_{key}_每5秒结果表.csv',every5)
            (all_bp if bp else all_main).extend(chinese)
    write_csv(DAT/'含双极板修订_两工况352行工作数据.csv',all_bp)
    write_csv(DAT/'五层基线_两工况352行工作数据.csv',all_main)
    json_write(DAT/'summary.json',summary)
    if not args.no_verify:
        convergence=[]
        for bp,tag in [(False,'main'),(True,'bp')]:
            p=calibration[tag]
            for key,d in data.items():
                base,_=simulate(d,bp,p['j0'],p['kf'],dt=.0125,scale=2)
                for name,scale,dt in [('time_half',2,.00625),('grid_double',4,.0125),('grid_double_time_half',4,.00625)]:
                    rr,_=simulate(d,bp,p['j0'],p['kf'],scale=scale,dt=dt)
                    a=lambda rows,k:np.array([r[k] for r in rows])
                    entry=dict(model=tag,condition=key,check=name,grid_scale=scale,dt_s=dt)
                    for col in ['V_model_V','T_model_C','ice_max_bulk','ice_pore_max_bulk','ice_mem_max_bulk']:
                        entry['max_difference_'+col]=float(np.max(abs(a(rr,col)-a(base,col))))
                    entry['valid_samples']=sum(r['model_valid'] for r in rr);convergence.append(entry)
        write_csv(DAT/'网格与时间步收敛.csv',convergence)
        p=calibration['bp'];sens=[]
        for param,vals in [('kf',[p['kf']*.1,p['kf'],p['kf']*10]),('km',[.1,1.,10.]),('kvl',[.5,1.,2.]),('kvi',[1e-5,1e-4,1e-3]),('lambda_nf',[2.5,3.,3.5]),('exchange_factor',[.5,1.,2.])]:
            for value in vals:
                options={param:value};kf=options.pop('kf',p['kf'])
                for key,d in data.items():
                    rr,_=simulate(d,True,p['j0'],kf,dt=.025,**options);m=metrics(rr)
                    sens.append(dict(parameter=param,value=value,condition=key,V_RMSE=m['V_RMSE'],T_RMSE=m['T_RMSE'],ice_peak_bulk=m['ice_peak_bulk'],ice_pore_at35=rr[-1]['ice_pore_max_bulk'],ice_mem_at35=rr[-1]['ice_mem_max_bulk'],valid_samples=m['valid_samples']))
        write_csv(DAT/'参数与闭合敏感性.csv',sens)
        # Profile: reoptimize j0 with kf fixed. -25 C is never used for fitting.
        profiles=[];d=data['minus20']
        for kf in np.logspace(-4,1,9):
            def objective(logj):
                rr,_=simulate(d,True,10**logj,kf);m=metrics(rr)
                return float(np.mean([(r['V_rel_error_pct']/100)**2+(r['T_rel_error_pct']/100)**2 for r in rr]))
            opt=minimize_scalar(objective,bounds=(-3,1),method='bounded',options={'xatol':.015})
            rr,_=simulate(d,True,10**opt.x,kf)
            profiles.append(dict(kf_s_inv=kf,j0_reoptimized_A_m2=10**opt.x,mean_squared_relative_objective=opt.fun,ice_at35_bulk=rr[-1]['ice_max_bulk']))
        write_csv(DAT/'冻结系数剖面.csv',profiles)
        # No-freeze limit and zero-current/isothermal budget smoke checks.
        checks=[]
        zero=Model(bp=True,j0=p['j0'],kf=0.,kvi=0.,exchange_factor=0.)
        zr,_=zero.run(np.array([0.,.2,1.]),np.zeros(3),-20.,dt=.025)
        checks.append(dict(check='zero_current_no_phase_constant_temperature',observed=max(abs(x['T_model_C']+20) for x in zr),tolerance=1e-6))
        nr,_=simulate(data['minus20'],True,p['j0'],0.,kvi=0.,lambda_nf=3.)
        checks.append(dict(check='no_freezing_no_ice',observed=max(r['ice_max_bulk'] for r in nr),tolerance=1e-12))
        for item in checks:item['passed']=item['observed']<=item['tolerance']
        write_csv(DAT/'退化与守恒测试.csv',checks)
    manifest=dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
        runtime_s=time.perf_counter()-start,calibration_condition='-20 C only',validation_condition='-25 C held out',
        final_dt_s=.0125,grid_counts_MEA=[16,6,12,8,16],grid_counts_BP_each=8,
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'附件1.xlsx',SOURCE/'附件2.xlsx',ROOT.parent/'问题1_建模推导源文件.md']},
        code_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'code').glob('*.py')})
    json_write(DAT/'运行记录与来源哈希.json',manifest)
    print('DONE',manifest['runtime_s'],flush=True)
if __name__=='__main__':main()
