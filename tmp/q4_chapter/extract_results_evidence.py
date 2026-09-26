from pathlib import Path
import csv
from collections import defaultdict

ROOT = Path(r'D:\shumo\26比赛\解题\问题4_求解结果')
OUT = Path(r'D:\shumo\tmp\q4_chapter\results_evidence.md')
parts = []
def read(name):
    with (ROOT/'data'/name).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    for i,r in enumerate(rows,2): r['_line'] = str(i)
    return rows
def fnum(v):
    if isinstance(v,bool): return '是' if v else '否'
    try:
        x=float(v)
        if abs(x)>0 and abs(x)<1e-4: return f'{x:.6g}'
        return f'{x:.6f}'.rstrip('0').rstrip('.')
    except (ValueError, TypeError): return str(v)
def table(rows, cols, title, source=None):
    parts.append(f'\n### {title}\n')
    if source: parts.append(f'数据源：`{source}`。line 为 CSV 物理行号（含表头）。\n')
    lines=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows: lines.append('| '+' | '.join(fnum(r.get(c,'')) for c in cols)+' |')
    parts.append('\n'.join(lines))
def say(s): parts.append(s)
def ok(r): return r.get('feasible','').lower()=='true'

say('# 第七章结果细审证据\n\n仅提取已归档 CSV、核对绘图代码，没有重算物理模型，也没有改动结果源文件。路径基准：`'+str(ROOT)+'`。本文件供论文7.4写作；数字保留工作精度，正文宜适当舍入。')
say('## 1. 16幅图的数据对应核对\n\n核对依据：`figures/figure_manifest.csv` 与 `code/plot_results.py`。全部列出的 CSV 和 PNG/SVG/PDF 文件均存在。图01的几何端板阴影还读取 precooling_layers.csv（manifest主要列数值场源）；没有由此改变温度数据。')
with (ROOT/'figures'/'figure_manifest.csv').open(encoding='utf-8-sig',newline='') as f: manifest=list(csv.DictReader(f))
figrows=[]
for r in manifest:
    files=[ROOT/'data'/x for x in r['source_csv'].split(';')]+[ROOT/'figures'/r[k] for k in ['png','svg','pdf']]
    figrows.append({'图':r['figure'],'源CSV':r['source_csv'],'文件存在':all(x.exists() for x in files),'注意':r['plot_note'].replace('\n','；')})
table(figrows,['图','源CSV','文件存在','注意'],'图源与文件存在性')
say('**图源口径提醒：**图04–06绘制的是 `trajectory_case*_guarded.csv`，虽文件名写“动态”，不是名义 dynamic。图07/09主比较为 guarded 与 constant_hold。图10启动部分是 guarded；图11下半是 case1 的名义 dynamic 单因素扰动，不能称推荐方案敏感性。图12全部是名义 dynamic 的1000–1009种子组；图13并列名义组和推荐组各自独立种子比例，不是配对实验。图14比较三种冻结策略。图15为有限候选能耗—时间关系，不是全局 Pareto 前沿证明。图16是7010物性失配＋噪声例子，冰误差图画“经电压修正的风险软测量误差”，与汇总CSV的 `observer_max_ice_error`（冰先验误差）不同。')

say('## 2. 推荐控制逐片能耗、持续时长与实际状态\n\n`code/finalize_tables.py:16–28`：功率列属于截止行时刻的前一区间；状态列属于下一积分区间。average_power 是整段0至t_off上的平均功率，不是只在通电时平均；heating_duration 是q>1e-10的区间总时长，不保证连续。停机状态5在本表0至t_off窗口持续时间为0，不代表停机未执行。')
per=[r for r in read('per_cell_heater_energy.csv') if r['strategy']=='guarded']
table(per,['_line','case','cell','energy_J','average_power_W_cm2','peak_power_W_cm2','heating_duration_s'],'逐片加热指标','data/per_cell_heater_energy.csv')
guards=read('guarded_results.csv')
share=[]
for g in guards:
    p=[r for r in per if r['case']==g['case']]
    endpoint=sum(float(r['energy_J']) for r in p if r['cell'] in ('1','5'))
    share.append({'case':g['case'],'端部两片能耗J':endpoint,'端部占比%':100*endpoint/float(g['E_aux_J'])})
table(share,['case','端部两片能耗J','端部占比%'],'由逐片CSV直接汇总的端部耗电占比')
states=[r for r in read('controller_state_duration.csv') if r['strategy']=='guarded']
state_rows=[]
for g in guards:
    for k in ('1','2','3','4','5'):
        ss={r['state']:r['duration_s'] for r in states if r['case']==g['case'] and r['cell']==k}
        state_rows.append({'case':g['case'],'cell':k,'状态1安全增强/s':ss.get('1',0),'状态2低温温升不足/s':ss.get('2',0),'状态3正常跟踪/s':ss.get('3',0),'状态4近目标渐缩/s':ss.get('4',0),'状态5关热/s':ss.get('5',0)})
table(state_rows,list(state_rows[0]),'状态持续时长','data/controller_state_duration.csv')
say('**可解释机制：**加热能量主要分配给端部第1、5片；中部2–4片通电时间显著短。对称结构导致两端近似对称（预冷材料取向不完全对称，勿宣称位数完全相等）。三工况推荐名义轨迹的安全增强状态1均未实际触发，风险通道是后备，不能把“频繁风险触发”当作这三条曲线节能的实证解释。状态2、3即使激活也可能经限幅得到0功率，所以状态时长不同于通电时长。')

say('## 3. 观测误差与测量确认时刻\n\n图16固定例子：seed=7010，初场整体−1 K，G×0.8、G_EP×1.2、h×1.2，测温噪声标准差0.2 K、测压0.005 V。初场扰动作为双方共同先验；没有额外检验未知端板初温偏差。观测器仍用名义物性。')
obs=read('observer_example_results.csv')
obsrows=[]
for r in obs:
    row={k:r[k] for k in ['case','first_success_s','stop_s','physical_hold_s','observer_max_temperature_error_K','observer_max_ice_error','min_voltage_V','max_ice_bulk','feasible']}
    history=read('trajectory_'+r['case']+'_observer_example.csv')
    h=[x for x in history if float(x['time_s'])<=float(r['stop_s'])+1e-8]
    row['图16五片温度误差峰K']=max(abs(float(x[f'observer_T{k}_C'])-float(x[f'T{k}_C'])) for x in h for k in range(1,6))
    row['图16端板误差峰K']=max(abs(float(x[f'observer_T{side}_C'])-float(x[f'T{side}_C'])) for x in h for side in ('EL','ER'))
    row['图16校正冰风险误差峰']=max(abs(float(x[f'cell{k}_ice_est'])-float(x[f'cell{k}_ice_bulk'])) for x in h for k in range(1,6))
    obsrows.append(row)
table(obsrows,list(obsrows[0]),'观测器与测量停机例子的汇总及图中实际误差指标','data/observer_example_results.csv + trajectory_case*_observer_example.csv')
say('`observer_max_temperature_error_K` 是包含端板的七节点热状态预测最大误差；`observer_max_ice_error` 是独立模型冰先验误差，图16风险软测量经电压创新校正后误差另列。名义完全匹配时 guarded_results 中上述观测器误差均为0，这只说明同类模型同步，不是实物估计准确性证据。首次到停机的间隔可以大于2 s，因为滤波温度须超过0.2 ℃并连续满足采样条件。')

say('## 4. 启动能量分解与停机后60 s\n\n启动账目：E_aux + E_gen + E_phase = E_loss + E_sensible；E_phase为净释热，负数表示净吸热。统计窗口到实际t_off，后验段不混入。动态较慢，反应热更大、累计电荷更大，辅助节电不等价于氢耗或全系统能耗下降。')
main=read('main_results.csv')
energy=guards+[r for r in main if r['strategy']=='constant_hold']
table(energy,['case','strategy','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','charge_at_success_C_cm2','charge_at_stop_C_cm2','energy_residual_J','max_water_residual_kg'],'推荐与固定C的能量分解','data/guarded_results.csv;data/main_results.csv')
table(energy,['case','strategy','final_min_T_C','final_max_T_C','final_left_EP_C','post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J'],'关热状态及60s后验极值','data/guarded_results.csv;data/main_results.csv')
say('**机理可据：**关热时端板仍明显低温，继续从电池吸热；完全冷却与40 min推荐策略后验最低片温降至−4.5075/−1.9099 ℃。但对应后验最低电压0.5597/0.5885 V仍高于0.30 V、最大冰量0.5010/0.2957仍低于0.99，因此本次失败的是持续暖态，不应笼统写为已发生低压或严重冰堵。三工况推荐后验均q=0，不能说仿真自动重新加热维持。')

say('## 5. 单因素敏感性与物性失配：务必区分数据组\n\n`data/sensitivity.csv` 的48组围绕名义 dynamic 冻结参数，不是guarded；源代码 run_problem4.py:68–86。G、G_EP、h各乘0.8/1.2；T_target、K_P、K_I、ice_warn、delta_V各乘0.8/1.2。物理18组全部通过，48组共46组通过。仅T_target×0.8在case1/case3未完成测量停机，首次事件仍出现且电压、冰量未越硬阈值。负stop=-1为缺失事件哨兵。')
sens=read('sensitivity.csv')
table([r for r in sens if not ok(r)],['_line','case','parameter','factor','E_aux_J','first_success_s','stop_s','min_voltage_V','max_ice_bulk','physical_hold_s'],'名义单因素敏感性全部失败行','data/sensitivity.csv')
table([r for r in sens if r['parameter'] in ('G','G_EP','h')],['_line','case','parameter','factor','E_aux_J','first_success_s','stop_s','dTmax_K','feasible'],'名义物理参数单因素响应','data/sensitivity.csv')
say('可据数据解释：G增大促进均温，case1最大温差从G×0.8时8.052 K降至G×1.2时5.715 K。端板耦合G_EP最显著改变辅助电耗：case1从2453.251 J升至3190.957 J，case3从1465.850 J升至2017.815 J；更强端板耦合使冷端板热汇加重。h增大增加散热代价；20 min零功率分支能耗保持0，但首次成功对h变化从80.221 s延至89.736 s。K_P/K_I的±20%对名义输出影响较小；冰预警、电压预警变化无输出影响，与这些名义轨迹未触发风险增强相容，不能推断阈值永远不重要。')
pre=read('precooling_sensitivity.csv')
table([r for r in pre if float(r['cooling_min'])==20 and (float(r['conductance_factor'])==1 or float(r['h_W_m2K'])==40)],['_line','h_W_m2K','conductance_factor','mean_capacity_C','field_range_K','relative_field_range','Bi_stack'],'预冷20min代表敏感性数据','data/precooling_sensitivity.csv')
say('预冷敏感性h=20/40/80/160、BP与MEA导热倍率0.1/0.25/0.5/1/2，共40组（20/40 min）；端板本体导热不变。它采用矩阵指数解，而主初场用0.25s后向欧拉，基准均温会相差约0.002 K，不能据此误报数据冲突。绝对温差随h不必单调：h很大时整体已接近环境，剩余温差小；归一化温差与Bi增加更适合说明相对不均匀程度。这是等效参数扰动，不是测得接触热阻。')

say('## 6. 随机与联合失配验证\n\n名义组：种子1000–1009，每工况初场平移−1/0/+1 K，共30次；推荐与固定C、重优化恒功率的配对最终组：6000–6009，相同30场景。所有组温度/电压噪声标准差0.2 K/0.005 V。推荐参数冻结后检验；不是按照6000系列逐次调参。名义与推荐的比例不可作为配对因果估计。')
datasets=[('名义dynamic','robustness.csv'),('推荐guarded','guarded_robustness.csv'),('恒功率两基准','constant_robustness.csv')]
stats=[]
for label,name in datasets:
    groups=defaultdict(list)
    for r in read(name): groups[(r['case'],r.get('strategy',label))].append(r)
    for (case,strategy),rs in groups.items():
        good=[r for r in rs if ok(r)]
        stats.append({'组':label,'case':case,'strategy':strategy,'通过':f'{len(good)}/{len(rs)}','最低电压V':min(float(r['min_voltage_V']) for r in rs),'最大冰量':max(float(r['max_ice_bulk']) for r in rs),'未出现首次数':sum(float(r['first_success_s'])<0 for r in rs),'未完成停机数':sum(float(r['stop_s'])<0 for r in rs),'真实保持不足数':sum(float(r['physical_hold_completed'])<.5 for r in rs),'种子':','.join(sorted({r['seed'] for r in rs}))})
table(stats,list(stats[0]),'三类策略噪声与初温组的事件/安全统计')
say('物性联合最终组每工况8次：G/G_EP/h之一±20%、初场不偏移的6次（seed7000–7005），以及(−1 K,G×0.8,G_EP×1.2,h×1.2,7010)和(+1 K,G×1.2,G_EP×0.8,h×0.8,7011)。推荐24/24、固定C24/24，重优化恒功率case1=8/8、case2=7/8、case3=3/8。重优化恒功率仅做名义优化，不能将这些失败说成恒功率类经过稳健整定后的能力上限。')
phys=read('constant_parameter_validation.csv')
table([r for r in phys if not ok(r)],['_line','case','strategy','seed','initial_shift_K','G_factor','G_EP_factor','h_factor','first_success_s','stop_s','physical_hold_s','min_voltage_V','max_ice_bulk','feasible'],'重优化恒功率在配对物性失配组的全部失败行','data/constant_parameter_validation.csv')
pil=read('guarded_pilot_robustness.csv')+read('guarded_pilot_parameter_validation.csv')
table([r for r in pil if not ok(r)],['case','seed','initial_shift_K','G_factor','G_EP_factor','h_factor','first_success_s','stop_s','min_voltage_V','max_ice_bulk'],'开发期guarded_pilot失败保留','data/guarded_pilot_robustness.csv;data/guarded_pilot_parameter_validation.csv')
say('开发版88/90通过，失败主要暴露首次成功有裕度仍不足以保证测量保持及时完成。因此最终训练要求首次与测量停机均不晚于94.6667 s。不要将开发期pilot 3000/5000系列失败混入冻结后6000/7000系列最终验证率。有限试验不构成高斯无界噪声下任意扰动保证。')

say('## 7. 守恒、收敛与图10解读\n\n守恒只证明离散账目一致，独立参考、步长网格、真实约束和观测检验提供不同证据，不能用极小残差代替所有准确性验证。')
table(read('precooling_validation.csv'),['test','observed','tolerance','unit','passed','note'],'11项预冷验证','data/precooling_validation.csv')
conv=read('precooling_convergence.csv')
table([r for r in conv if float(r['cooling_min'])==20],['study','scale','control_volumes','dt_s','max_field_error_K','max_node_error_K','reference'],'预冷20min收敛代表数据','data/precooling_convergence.csv')
joint=read('coupled_convergence.csv')
table(joint,['case','dt_s','scale','period_s','E_aux_J','first_success_s','stop_s','max_ice_bulk','min_voltage_V','feasible'],'推荐冻结参数联合加密','data/coupled_convergence.csv')
deltas=[]
for case in ('case1','case2','case3'):
    rs=sorted([r for r in joint if r['case']==case],key=lambda r:float(r['scale']))
    a,b=rs[0],rs[-1]
    deltas.append({'case':case,'能耗相对变化%':100*(float(b['E_aux_J'])/float(a['E_aux_J'])-1),'冰峰相对变化%':100*(float(b['max_ice_bulk'])/float(a['max_ice_bulk'])-1),'首次时间差s':float(b['first_success_s'])-float(a['first_success_s'])})
table(deltas,list(deltas[0]),'正式58控制体/0.025s至232控制体/0.00625s的CSV算术比较')
gc=read('guarded_convergence.csv')
table([r for r in gc if float(r['scale'])==2 and float(r['dt_s'])==.025],['case','period_s','E_aux_J','first_success_s','stop_s','max_ice_bulk','feasible'],'控制采样周期变化','data/guarded_convergence.csv')
say('联合加密能耗仅约−0.05%，首次事件时间变化很小；冰峰相对仍变化约2.09%–3.37%，固定时间步空间加密时变化更明显。可称“宏观能耗与时间结果稳定，局部冰量对离散仍较敏感”，不能称完全网格无关。采样周期0.1/0.2/0.4 s全部成功，但采样决定停机时刻与保持窗口，不是纯数值积分误差，须独立说明。')

say('## 8. 正文分配建议\n\n7.4初场可用图01–03择重；轨迹图04–06配端部能耗占比和状态时长；综合比较用图07、14或15；预冷扫描图08；关热后可借轨迹阴影和图13；稳健性用图11–13并明确nominal/guarded标签，观测器图16作为独立失配例证；守恒图09，收敛图10。不要为覆盖16图而重复相同主结果，也不要把所有附加CSV大表放入论文正文。')
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
print(f'Wrote {OUT}; {len(parts)} blocks; {OUT.stat().st_size} bytes')
