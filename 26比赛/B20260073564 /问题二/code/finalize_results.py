"""Final high-resolution exports after the coarse multi-start optimization."""
from run_question2 import ROOT,DATA,write_csv,export_trajectory,temperature_boundary
from stack_model import simulate
import csv,json,time,math,platform,importlib.metadata
finalize_start=time.time()

def read(name):
    with (DATA/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

opt=json.loads((DATA/'optimized_parameters.json').read_text(encoding='utf-8'))
# Equal stages are the same physical control. Switching times have no effect;
# use canonical times strictly before startup instead of optimizer round-off.
if max(opt['step'][:3])-min(opt['step'][:3])<1e-8:
    opt['step']=[opt['step'][0]]*3+[8.,16.]
# Narrative/table templates describe this boundary solution; fail loudly if a
# future model revision changes it rather than silently report stale parameters.
expected={'constant':[.5],'ramp':[2.5,.5],'step':[.5,.5,.5,8.,16.]}
assert all(len(opt[k])==len(v) and max(abs(a-b) for a,b in zip(opt[k],v))<1e-8
           for k,v in expected.items()), 'Refresh strategy parameter descriptions for the new optimum'
(DATA/'optimized_parameters.json').write_text(json.dumps(opt,indent=2),encoding='utf-8')
summary=[]
for kind,p in opt.items():
    s=export_trajectory(kind,kind,p,-10.,dt=.003125,scale=8)
    summary.append({'strategy':kind,'T0_C':-10,'parameters':json.dumps(p),
                    'dt_s':.003125,'grid_scale':8,**s})
    print('final',kind,s['end_time_s'],s['max_ice_bulk'],flush=True)
write_csv('strategy_summary.csv',summary)

conv=[r for r in read('convergence.csv') if int(r['grid_scale']) not in (8,16)]
for kind,p in opt.items():
    for scale,dt in ((8,.003125),(16,.0015625)):
        s,*_=simulate(kind,p,dt=dt,scale=scale)
        conv.append({'strategy':kind,'grid_scale':scale,'dt_s':dt,**s})
write_csv('convergence.csv',conv)

boundary={};brackets=[]
for kind,p in opt.items():
    cold,warm,rows=temperature_boundary(kind,p,dt=.003125,scale=8)
    boundary[kind]={'cold_infeasible_C':cold,'warm_feasible_C':warm,'parameters':p,
                    'dt_s':.003125,'grid_scale':8}
    brackets+=rows
    print('boundary',kind,cold,warm,flush=True)
write_csv('temperature_bisection.csv',brackets)
bestkind=min(boundary,key=lambda k:boundary[k]['warm_feasible_C'])
cold=boundary[bestkind]['cold_infeasible_C'];warm=boundary[bestkind]['warm_feasible_C']
sc=export_trajectory('critical_success',bestkind,opt[bestkind],warm,dt=.003125,scale=8)
fc=export_trajectory('critical_failure',bestkind,opt[bestkind],cold,dt=.003125,scale=8)
below_T=float(math.floor(cold)-1)
below=export_trajectory('below_critical',bestkind,opt[bestkind],below_T,dt=.003125,scale=8)
boundary['critical_success']={'T0_C':warm,**sc}
boundary['critical_failure']={'T0_C':cold,**fc}
boundary['below_critical']={'T0_C':below_T,**below}
# One finest-grid pass on both sides confirms the reported practical bracket.
for T in (cold,warm):
    s,*_=simulate(bestkind,opt[bestkind],T0=T,dt=.0015625,scale=16)
    boundary[f'finest_check_{T}']={'T0_C':T,'dt_s':.0015625,'grid_scale':16,**s}
(DATA/'critical_temperature.json').write_text(json.dumps(boundary,indent=2),encoding='utf-8')
write_csv('第二小问_最低初温区间.csv',[
    {'加载策略':kind,'失败侧初温_C':boundary[kind]['cold_infeasible_C'],
     '成功侧初温_C':boundary[kind]['warm_feasible_C'],
     '区间宽度_C':boundary[kind]['warm_feasible_C']-boundary[kind]['cold_infeasible_C'],
     '口径':'固定优化曲线，已与温度逐点重新搜索对照'} for kind in opt])
write_csv('第二小问_临界与更冷工况.csv',[
    {'case':case,**boundary[case]} for case in ('critical_success','critical_failure','below_critical')])

zero=[]
for T0 in (-10.,warm,cold):
    for p in ([0.,.5,.5,.2,8.],[0.,.5,.5,8.,16.],[.5,0.,.5,8.,16.],[.5,.5,0.,8.,16.]):
        s,*_=simulate('step',p,T0=T0,dt=.05,scale=2)
        zero.append({'T0_C':T0,'parameters':json.dumps(p),**s})
write_csv('zero_current_stage_audit.csv',zero)

table=[]
names={'constant':'恒流策略','ramp':'线性升载（有限斜率搜索）','step':'三段阶梯（退化为恒流）'}
texts={'constant':'j=0.5 A/cm²','ramp':'a=2.5 A/(cm²·s), jp=0.5 A/cm², tp=0.2 s',
       'step':'j1=j2=j3=0.5 A/cm²; t1=8 s, t2=16 s（切换不改变电流）'}
for r in summary:
    k=r['strategy'];table.append({'加载策略':names[k],'最优加载参数':texts[k],
        '启动时间_s':r['end_time_s'],'累计电荷量_C_cm-2':r['charge_C_cm2'],
        '最大电流密度_A_cm-2':r['max_current_A_cm2'],'最低电压_V':r['min_voltage_V'],
        '最大冰体积分数_含膜冰':r['max_ice_bulk'],'最大多孔层冰体积分数':r['max_pore_ice_bulk'],
        '最大孔隙冰饱和度':r['max_pore_ice_saturation'],'启动结果':'成功',
        '最优性口径':'给定参数范围内搜索所得；有限斜率下界不是题给硬件约束' if k=='ramp' else '给定策略类多起点数值搜索最优，无全局证书'})
write_csv('表3_不同策略最优启动结果.csv',table)
meta=json.loads((DATA/'run_metadata.json').read_text(encoding='utf-8'))
meta.update({'main_grid_scale':8,'main_cells_per_MEA':232,'main_dt_s':.003125,
    'verification_grid_scale':16,'verification_cells_per_MEA':464,'verification_dt_s':.0015625,
    'trajectory_export_interval_s':.05,'trajectory_extra_rows':'initial/terminal/switch/extrema',
    'equal_step_canonical_switch_times_s':[8.,16.],
    'critical_temperature_tolerance_C':20/4096,
    'lower_current_search_bound_A_cm2':0.,
    'finalize_elapsed_seconds':time.time()-finalize_start,
    'python_version':platform.python_version(),'platform':platform.platform(),
    'package_versions':{name:importlib.metadata.version(name) for name in ('numpy','scipy','numba','matplotlib','openpyxl','lxml')},
    'below_critical_diagnostic_T0_C':below_T,
    'historical_search_note':'Full optimization rerun after shared-plate correction with zero lower current bounds; zero-current corners independently checked.'})
(DATA/'run_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('High-resolution results complete',flush=True)
