"""Build the detailed Chinese Q4 report directly from saved numeric CSVs.

Produces UTF-8 Markdown and a standalone HTML view with complete result tables.
No result is copied from the model derivation or the previous Q4 submission.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.python_deps'))
import numpy as np
import pandas as pd

CASES={'case1':'工况1：完全冷却','case2':'工况2：预冷20 min','case3':'工况3：预冷40 min'}
STRATEGIES={'dynamic':'动态反馈＋2 s保持','constant_hold':'恒功率＋2 s保持','constant_first':'恒功率首次过零（Q3口径）','guarded':'留裕度备选＋2 s保持'}
NAMES={'case':'工况','strategy':'策略','cooling_min':'预冷/min','feasible':'可行',
 'first_success_s':'首次达标/s','stop_s':'关热时刻/s','elapsed_s':'仿真总时长/s',
 'E_aux_J':'辅助电能/J','E_gen_J':'反应产热/J','E_phase_J':'相变净释热/J',
 'E_loss_J':'环境散热/J','E_sensible_J':'离散显热增量/J',
 'energy_residual_J':'能量残差/J','water_residual_kg':'终点水量残差/kg',
 'min_voltage_V':'最低电压/V','max_ice_bulk':'最大冰体积分数','dTmax_K':'最大五片温差/K',
 'final_min_T_C':'关热最低片温/℃','final_max_T_C':'关热最高片温/℃',
 'final_left_EP_C':'关热左端板/℃','min_gas_porosity':'最小气相孔隙率',
 'max_j_over_jlim':'最大j/jlim','min_kappa_S_m':'最小质子电导/S·m⁻¹',
 'min_inventory':'最小库存（内核单位）','max_iteration_error_K':'最大Picard误差/K',
 'max_power_W_cm2':'峰值单片功率/W·cm⁻²','charge_at_success_C_cm2':'首次达标累计电荷/C·cm⁻²',
 'post_min_T_C':'关热后最低片温/℃','post_min_voltage_V':'关热后最低电压/V',
 'post_max_ice_bulk':'关热后最大冰体积分数','post_energy_J':'关热后辅助电能/J',
 'first_success_energy_J':'首次达标辅助电能/J','max_water_residual_kg':'最大水量残差绝对值/kg',
 'mean_capacity_C':'热容加权均温/℃','mean_length_C':'厚度加权均温/℃',
 'mean_seven_nodes_C':'七节点算术均温/℃','field_min_C':'全场最低温/℃',
 'field_max_C':'全场最高温/℃','field_range_K':'全场温差/K','cell_range_K':'五片初始温差/K',
 'center_minus_left_EP_K':'中片−左端板/K','surface_left_C':'左外表面/℃','surface_right_C':'右外表面/℃',
 'relative_field_range':'全场温差/剩余均温','Bi_stack':'堆级Bi',
 'TEL_C':'左端板均温/℃','TER_C':'右端板均温/℃',
 'T_target_C':'目标温度/℃','t_plan_s':'规划时间/s','K_P':'比例增益','K_I':'积分增益',
 'taper_K':'渐缩带/K','hold_s':'保持/s','q_boost_min':'安全增强起值/W·cm⁻²',
 'ice_warn':'冰量预警','delta_V':'电压预警带/V','risk_warn':'综合风险阈值',
 'L_obs':'电压校正增益','rate_gain':'温升不足补偿增益','ff_factor':'前馈倍率',
 'dt_s':'数值步长/s','scale':'网格倍率','period_s':'控制周期/s','parameter':'扰动参数','factor':'倍率',
 'seed':'随机种子','noise_T_K':'温度噪声标准差/K','noise_V_V':'电压噪声标准差/V',
 'initial_shift_K':'初场平移/K','study':'检验类型','control_volumes':'控制体数',
 'max_field_error_K':'最大温度场误差/K','max_node_error_K':'最大节点投影误差/K',
 'reference':'独立参考','h_W_m2K':'h/W·m⁻²·K⁻¹','conductance_factor':'导热倍率',
 'G_eff_W_m2K':'等效G/W·m⁻²·K⁻¹','note':'说明','test':'检验项目','observed':'观测量',
 'tolerance':'容差','unit':'单位','passed':'通过','energy_released_J':'内能减少/J',
 'convective_loss_J':'端面对流累计散热/J','residual_J':'残差/J','relative_residual':'相对残差',
 'node':'节点','capacity_J_m2K':'单位面积热容/J·m⁻²·K⁻¹','capacity_J_K':'节点总热容/J·K⁻¹',
 'mode':'模态','eigenvalue_per_s':'特征值/s⁻¹','time_constant_s':'时间常数/s',
 'max_initial_modal_amplitude_K':'当前初场最大激发幅值/K'}
NAMES.update({f'T{k}_C':f'电池{k}均温/℃' for k in range(1,6)})


def load(name,root=ROOT,required=True):
    path=root/'data'/name
    if not path.exists():
        if required:raise FileNotFoundError(path)
        return None
    return pd.read_csv(path,encoding='utf-8-sig')


def fmt(value):
    if pd.isna(value):return '—'
    if isinstance(value,(bool,np.bool_)):return '是' if value else '否'
    if isinstance(value,str):return CASES.get(value,STRATEGIES.get(value,value))
    if isinstance(value,(int,np.integer)):return str(value)
    v=float(value)
    if v==0:return '0'
    if abs(v)<1e-4 or abs(v)>=1e7:return f'{v:.5e}'
    if abs(v)<1:return f'{v:.6f}'.rstrip('0').rstrip('.')
    return f'{v:.5f}'.rstrip('0').rstrip('.')


class Report:
    def __init__(self):self.md=[];self.html=[]
    def heading(self,text,level=2):
        self.md.append('#'*level+' '+text+'\n')
        self.html.append(f'<h{level}>{escape(text)}</h{level}>')
    def p(self,text):
        self.md.append(text+'\n')
        self.html.append('<p>'+escape(text).replace('\n','<br>')+'</p>')
    def formula(self,text):
        self.md.append('```text\n'+text+'\n```\n')
        self.html.append('<pre class="formula">'+escape(text)+'</pre>')
    def table(self,title,df,columns=None,source=None):
        self.heading(title,3)
        if columns is not None:df=df[[c for c in columns if c in df.columns]]
        if df.empty:
            self.p('本表无数据。');return
        headers=[NAMES.get(c,c) for c in df.columns]
        rows=[[fmt(v) for v in row] for row in df.itertuples(index=False,name=None)]
        safe=lambda s:s.replace('|','\\|').replace('\n',' ')
        lines=['| '+' | '.join(map(safe,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']
        lines+=['| '+' | '.join(map(safe,row))+' |' for row in rows]
        self.md.append('\n'.join(lines)+'\n')
        table='<table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'
        table+=''.join('<tr>'+''.join('<td>'+escape(x)+'</td>' for x in row)+'</tr>' for row in rows)
        self.html.append('<div class="table-wrap">'+table+'</tbody></table></div>')
        if source:
            sources=[s.strip() for s in source.split(' + ')]
            mdlinks='、'.join(f'[{s}](data/{s})' for s in sources)
            htmllinks='、'.join(f'<a href="data/{escape(s)}">{escape(s)}</a>' for s in sources)
            self.md.append(f'数据源：{mdlinks}；共 {len(df)} 行，CSV保留工作精度。\n')
            self.html.append(f'<p class="caption">数据源：{htmllinks}；共 {len(df)} 行，CSV保留工作精度。</p>')
    def image(self,name,caption):
        self.md.append(f'![{caption}](figures/{name}.png)\n\n{caption}。矢量版：[SVG](figures/{name}.svg)。\n')
        self.html.append(f'<figure><img src="figures/{name}.png" alt="{escape(caption)}"><figcaption>{escape(caption)}。<a href="figures/{name}.svg">SVG矢量版</a></figcaption></figure>')
    def link(self,name,href):
        self.md.append(f'[{name}]({href})\n')
        self.html.append(f'<p><a href="{escape(href)}">{escape(name)}</a></p>')
    def write(self,root):
        (root/'问题四_完整求解报告.md').write_text('\n'.join(self.md),encoding='utf-8-sig')
        css='''body{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#213445;background:#f2f5f7;margin:0;line-height:1.85}main{max-width:1320px;margin:0 auto;padding:42px 5vw;background:white}h1{font-size:30px;color:#123e5c;line-height:1.4;border-bottom:3px solid #187393;padding-bottom:18px}h2{font-size:23px;margin-top:46px;color:#174e6d}h3{font-size:17px;margin-top:28px}p{margin:12px 0}a{color:#12628d}.table-wrap{overflow-x:auto;margin:18px 0;border:1px solid #d6e0e7;border-radius:5px}table{border-collapse:collapse;min-width:100%;font-size:12px;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #dce3e9;padding:8px 11px;white-space:nowrap;text-align:right}th{background:#e6eff5;color:#164365;font-weight:600}td:first-child,th:first-child{text-align:left}tr:nth-child(even){background:#f7fafc}.caption,figcaption{font-size:12px;color:#586d7a}figure{margin:24px 0}img{display:block;width:100%;height:auto;border:1px solid #e0e5e9}pre{font-family:Consolas,"Microsoft YaHei",monospace;font-size:13px;line-height:1.7;white-space:pre-wrap;background:#f2f6f8;border-left:4px solid #297a9a;padding:16px;overflow-x:auto}.lead{background:#eaf4f8;padding:20px;border-radius:6px}@media print{body{background:white}main{max-width:none;padding:0}h2{break-after:avoid}figure{break-inside:avoid}.table-wrap{overflow:visible}table{font-size:8px}td,th{white-space:normal;padding:4px}a{color:inherit}}'''
        html='<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>问题四完整求解报告</title><style>'+css+'</style></head><body><main>'+''.join(self.html)+'</main></body></html>'
        (root/'问题四_完整求解报告.html').write_text(html,encoding='utf-8')


STRATEGIES.update({'dynamic':'名义能耗优选动态','guarded':'推荐留裕度动态',
                  'optimized_constant':'同工况重优化恒功率','constant_optimized':'同工况重优化恒功率',
                  'zero_heat':'零辅助加热','zero_heater':'零辅助加热',
                  'inherited_constant_C':'固定问题三C','full_power':'全片满功率'})
NAMES.update({'stop_temperature_margin_K':'测量关热温度裕度/K',
 'max_observer_ice_error':'冰软测量最大绝对误差','max_observer_T_error_K':'观测温度最大误差/K',
 'max_observer_ice_error_bulk':'冰先验最大绝对误差','observer_initial_shift_K':'观测器初温偏差/K',
 'physical_first_within_budget':'真实首次达标在预算内','measurement_stop_completed':'测量保持完成',
 'physical_hold_s':'真实连续达标时长/s','measured_hold_s':'测量连续达标时长/s',
 'stop_truth_valid':'测量停机时真实状态有效','false_stop':'测量误停',
 'first_deadline_s':'首次达标期限/s','first_time_limit_s':'首次达标期限/s',
 'q1_W_cm2':'电池1功率/W·cm⁻²','q2_W_cm2':'电池2功率/W·cm⁻²',
 'q3_W_cm2':'电池3功率/W·cm⁻²','q4_W_cm2':'电池4功率/W·cm⁻²',
 'q5_W_cm2':'电池5功率/W·cm⁻²','candidate':'候选编号','stage':'搜索阶段',
 'training_passed':'训练通过数','training_count':'训练总数','all_training_passed':'训练全通过',
 'training_max_stop_s':'训练最大关热/s','seed':'随机种子'})
NAMES.update({'first_min_voltage_V':'首次窗口最低电压/V','first_max_ice_bulk':'首次窗口最大冰量',
 'first_dTmax_K':'首次窗口最大温差/K','charge_at_stop_C_cm2':'关热累计电荷/C·cm⁻²',
 'physical_hold_completed':'真实状态连续保持完成','observer_max_temperature_error_K':'观测器最大温度误差/K',
 'observer_max_ice_error':'观测冰先验最大误差','post_max_iteration_error_K':'后验段最大迭代误差/K',
 'startup_window_end_s':'启动仿真窗口终点/s','shutdown_mode':'停机口径',
 'sensor_stop_margin_C':'滤波测温裕度/℃','deadline_s':'首次真实成功期限/s'})


def good(df):
    return df['feasible'].astype(str).str.lower().isin(['true','1'])


def optional_table(r,root,name,title,columns=None):
    df=load(name,root,False)
    if df is not None:r.table(title,df,columns,name)
    return df


def image_if(r,root,name,caption):
    if (root/'figures'/(name+'.png')).exists():r.image(name,caption)


def search_stats(df):
    rows=[]
    group=[c for c in ('case','stage') if c in df]
    for keys,g in df.groupby(group,sort=False):
        if not isinstance(keys,tuple):keys=(keys,)
        row=dict(zip(group,keys));ok=good(g) if 'feasible' in g else pd.Series(True,index=g.index)
        row.update({'候选数':len(g),'可行候选数':int(ok.sum())})
        for key in ('J','E_aux_J','first_success_s','stop_s'):
            if key in g:row['最低可行'+NAMES.get(key,key)]=g.loc[ok,key].min() if ok.any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def robust_stats(df):
    rows=[]
    for case,g in df.groupby('case',sort=False):
        ok=good(g);success=g.loc[ok]
        row={'case':case,'试验数':len(g),'可行数':int(ok.sum()),'经验通过率/%':100*ok.mean(),
             '成功样本平均能耗/J':success.E_aux_J.mean(),'成功样本能耗标准差/J':success.E_aux_J.std(),
             '成功样本最小能耗/J':success.E_aux_J.min(),'成功样本最大能耗/J':success.E_aux_J.max(),
             '全部样本最低电压/V':g.min_voltage_V.min(),'全部样本最大冰量':g.max_ice_bulk.max()}
        for key in ('noise_T_K','noise_V_V','initial_shift_K','G_factor','G_EP_factor','h_factor','observer_initial_shift_K'):
            if key in g:row[key+'实际取值']=','.join(fmt(x) for x in sorted(g[key].dropna().unique()))
        rows.append(row)
    return pd.DataFrame(rows)


def build(root=ROOT):
    main=load('main_results.csv',root);guard=load('guarded_results.csv',root)
    initial=load('initial_temperature_cases.csv',root);scan=load('constant_scan.csv',root)
    nominal=main[main.strategy=='dynamic'].copy();fixed=main[main.strategy=='constant_hold'].copy()
    allrows=pd.concat([guard,main],ignore_index=True)
    recommended=pd.concat([guard,fixed],ignore_index=True)
    noise=load('robustness.csv',root);gnoise=load('guarded_robustness.csv',root)
    opt=load('optimized_constant_results.csv',root,False)
    if opt is not None:allrows=pd.concat([allrows,opt],ignore_index=True)
    all_sources='guarded_results.csv + main_results.csv'+(' + optimized_constant_results.csv' if opt is not None else '')
    r=Report();r.heading('问题四：动态辅助加热控制与预冷过程——修订后的完整数值求解',1)
    r.p('本报告由本目录本轮重算的CSV自动生成。推荐结果为留温度与时间裕度的动态反馈方案；名义能耗优选、问题三固定恒功率、同工况重优化恒功率及失败候选分别保留。先报告可复核结果，再解释模型、求解过程和适用范围。全部结论只在已给物理模型、加载曲线、有限搜索及有限扰动试验范围内成立。')
    r.heading('1. 结果概览与比较口径')
    comparison=[]
    for case in CASES:
        a=guard[guard['case']==case].iloc[0];b=fixed[fixed['case']==case].iloc[0]
        ng=gnoise[gnoise['case']==case];saving=100*(b.E_aux_J-a.E_aux_J)/b.E_aux_J if b.E_aux_J else np.nan
        comparison.append(dict(case=case,推荐动态能耗_J=a.E_aux_J,固定恒功率能耗_J=b.E_aux_J,
          相对固定C节能率_pct=saving,动态首次达标_s=a.first_success_s,动态关热_s=a.stop_s,
          动态可行=bool(good(pd.DataFrame([a])).iloc[0]),独立验证通过=int(good(ng).sum()),独立验证总数=len(ng)))
        direction='下降' if saving>=0 else '增加'
        r.p(f'{CASES[case]}：推荐动态辅助电能{a.E_aux_J:.3f} J；真实状态首次达标{a.first_success_s:.5f} s；传感反馈确认并关热{a.stop_s:.5f} s。固定问题三功率按相同测量停机规则耗电{b.E_aux_J:.3f} J，推荐动态能耗{direction}{abs(saving):.3f}%。推荐策略本工况独立扰动通过{int(good(ng).sum())}/{len(ng)}次；名义可行性为{fmt(bool(good(pd.DataFrame([a])).iloc[0]))}。')
    r.table('表1 推荐策略数值概览',pd.DataFrame(comparison))
    r.p(f'名义能耗优选方案在原噪声/初场试验组通过{int(good(noise).sum())}/{len(noise)}次；推荐方案在独立种子组通过{int(good(gnoise).sum())}/{len(gnoise)}次。不同种子组比例不是严格配对试验或数学鲁棒性证明。失败试验全部保留；失败时消耗的电能不能作为成功节能样本计算成功组均值。')
    postbad=guard[(guard.post_min_T_C<=0)|(guard.post_min_voltage_V<.3)|(guard.post_max_ice_bulk>=.99)]
    if len(postbad):
        r.p('关热后持续运行检验仍有限制：'+ '、'.join(CASES[c] for c in postbad['case'])+'至少有一项持续暖态/电压/冰量标准未满足。本文的启动成功指规定的首次达标与测量保持过程完成，不能改写为关热后长期保持暖态。后验段不重新加热，完整最低温度与约束极值单独列示。')
    else:r.p('本次推荐策略在已仿真的关热后观察窗内，温度、电压、冰量持续状态均满足表中阈值。该结论仅覆盖保存的有限观察窗。')
    zeros=guard[(guard.E_aux_J.abs()<1e-10)&good(guard)]
    if len(zeros):r.p('推荐策略中'+ '、'.join(CASES[c] for c in zeros['case'])+'实现零辅助电能并通过名义约束；由于电能非负，这些工况达到主能耗目标的非负下界。该事实不证明其他工况、加权目标或带更多工程约束时的全局最优。')
    if opt is not None and len(opt[opt.E_aux_J.abs()<1e-10]):
        r.p('重新优化的恒功率类同样包含零功率。当该基准也达到0 J时，应理解为此工况在模型内可利用反应热自启动，不能把相对原固定C的100%辅助节电全部归因于动态反馈优势。')
    r.p('节约量仅指辅助电热丝电能。较慢启动会利用更多电化学反应热，并改变累计加载电荷；不能把辅助电能下降百分比直接解释为氢耗、净输出电能或全系统总能耗下降百分比。')

    r.heading('2. 输入、模型修正及物理假设')
    inventory=root/'inputs'/'parameter_inventory.csv'
    if inventory.exists():r.table('输入参数与来源',pd.read_csv(inventory,encoding='utf-8-sig'))
    r.p('预冷初态25 ℃，环境−30 ℃，两端真实外表面换热系数40 W/(m²·K)。结构为2块端板、6块共享双极板和5组MEA，每组MEA显式包含阳极GDL、阳极CL、膜、阴极CL和阴极GDL。两端电池分摊1.5块BP，中间电池分摊1块；端板保留独立节点，电熱丝面积每片25 cm²。')
    fixes=pd.DataFrame([
      ['外法向边界','左端 kTₓ=h(T−Tₐ)，右端 −kTₓ=h(T−Tₐ)','修正源文档(4.3)符号'],
      ['半网格对流热阻','g_b=(1/h+Δx/(2k))⁻¹','控制体中心不等于真实外表面'],
      ['BP共享与初温映射','按实际半片几何分配，热容加权投影','不重复计数且映射守恒'],
      ['安全增强','先渐缩，再取max(q渐缩,q安全)，最后限幅','渐缩不能清零安全增强'],
      ['停机锁存','测量条件连续成立后停机，之后q恒为0','避免成功后重新加热'],
      ['真实事件与测量停机','真实首次事件仅用于评价；停机由采样观测决定','明确可实施的反馈信息范围'],
      ['能耗窗口','分别保存首次真实达标和实际关热电能','共同测量保持策略才可直接比较'],
      ['时间预算','首次真实成功受预算约束，实际关热允许额外保持时间','不把2 s保持误算入首次成功预算'],
      ['零时刻判据','初态已满足首次条件则t_s=0、E_first=0','修复10 min扫描的虚假加热'],
      ['有限优化与扰动','保存搜索域、候选、失败率和关热后状态','不宣称未经证明的全局最优或硬安全保证']
    ],columns=['项目','实现','修正原因'])
    r.table('表2 关键逻辑修正',fixes)
    caps=load('precooling_node_capacities.csv',root)
    r.p(f'预冷名义整堆单位面积热容由附件原值求得{caps.capacity_J_m2K.sum():.7f} J/(m²·K)。启动内核采用孔隙、气体、离聚物及膜含水量修正的有效热物性；两阶段热容近似并非完全相同。启动初态由预冷温度映射得到，不将两套近似混称为同一绝对焓模型。预冷散热位于端板外表面；主启动沿用问题三端电池对流热网络，这一建模近似也保留说明。')
    r.p('启动统一电流为j(t)=min(0.005t,0.3) A/cm²。水相、气体传输、电压和产热继承问题三校准内核；启动前自由液水与冰为0，膜保留λ=3的结合水。吹扫不意味着质子传导所需膜含水量也置零。题给阈值与材料值、前序校准参数、为计算引入的搜索边界在输入清单中区分。')

    r.heading('3. 预冷方程、完整温度场与初始条件')
    r.formula('C_i dT_i/dτ = g_(i−1/2)(T_(i−1)−T_i)+g_(i+1/2)(T_(i+1)−T_i)\nC_i=(ρc_p)_iΔx_i；g_(i+1/2)=[Δx_i/(2k_i)+Δx_(i+1)/(2k_(i+1))]⁻¹\n两端增加g_b(T_amb−T_i)，g_b=(1/h+Δx/(2k))⁻¹\nu=T−T_amb；(C/Δτ+L)u^(m+1)=(C/Δτ)u^m\nT_node = Σ_(CV属于node) C_i T_i / Σ_(CV属于node) C_i')
    layers=load('precooling_layers.csv',root);pre=load('precooling_nodes.csv',root)
    r.p(f'模型包含{len(layers)}个材料区、{int(layers.control_volumes.sum())}个控制体，总厚度{layers.thickness_m.sum()*1000:.7f} mm。后向欧拉正式步长0.25 s，要求时刻精确落点。空间场所有控制体温度在precooling_fields.csv保存，包含位置、宽度、物性和节点归属；热容加权、厚度加权、七节点算术平均分别保存。')
    r.table('表3 三工况七节点初温与全场极值',initial,
      ['case','cooling_min','TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C','mean_capacity_C','field_range_K','cell_range_K'],'initial_temperature_cases.csv')
    r.table('三种均温与空间梯度定义',initial,
      ['case','mean_capacity_C','mean_length_C','mean_seven_nodes_C','field_min_C','field_max_C','center_minus_left_EP_K','surface_left_C','surface_right_C','Bi_stack'],'initial_temperature_cases.csv')
    r.table('10–100 min全部预冷节点结果',pre,
      ['cooling_min','TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C','mean_capacity_C','field_range_K','cell_range_K'],'precooling_nodes.csv')
    modes=load('precooling_slow_modes.csv',root)
    r.p(f'慢模态时间常数为{modes.iloc[0].time_constant_s:.6f} s（{modes.iloc[0].time_constant_s/60:.6f} min）；它与C_tot/(2h)的集总近似接近但不完全相同。半堆热阻包含端板、3块BP和2.5组MEA，基准Bi={pre.iloc[0].Bi_stack:.8f}。温差必须按实际统计口径报告，不能将五片节点温差代替含表面的全场温差。')
    r.table('预冷慢模态与初态激发幅值',modes,source='precooling_slow_modes.csv')
    r.table('映射后的节点热容',caps,source='precooling_node_capacities.csv')
    for name,cap in [('图01_预冷温度场族','全场温度与局部梯度'),('图02_预冷均温与温差','三种温差定义与随预冷时间的变化'),('图03_三工况初始温度','三工况初场；各图独立纵轴')]:image_if(r,root,name,cap)

    r.heading('4. 启动被控对象、观测器、状态机与终止事件')
    r.formula('C_k(X)dT_k/dt = Σ_l G_kl(T_l−T_k)−h_k(T_k−T_amb)+q_gen,k+q_phase,k+10⁴q_k\nq_gen,k=10⁴j(t)(1.48−V_k)；q_k以W/cm²计\nV_k=E_rev−η_act−η_ohm−η_con\nE_aux(t)=25Σ_k∫_0^t q_k(s)ds；0≤q_k≤1 W/cm²\n路径约束：min V≥0.30 V，max_(k,x) ε_ice<0.99\n附加诊断：j/j_lim<1，气相孔隙率≥0，质子电导>0，库存非负（数值容差内）')
    r.p('每片水相/气体状态采用有限体积离散，热网络包含五片均温与两个端板温度。每步推进质量与相变后，通过Picard迭代求解后向欧拉热方程及温度依赖电压；正式步长0.025 s、每片58个基础传输控制体、控制采样周期0.2 s。质量、能量、物理约束与非线性迭代误差随时间导出。首次温度跨零事件通过子步重积分及二分定位，而非仅取较晚采样时刻。')
    r.p('观测器使用独立副本状态，由电流输入、已施加功率及温度/电压采样推进；控制律不直接读取被控对象的真实冰、水、气体库存或真实端板温度。温度和电压经低通滤波并计算滤波速率；独立水相先验与其预测电压减去实测电压的有符号残差组合，冰量估计限幅到[0,1]。真实温度和真实冰量仅用于数值评估与估计误差检查，不作为隐藏的控制输入。观测器仍基于相同类型的物理模型，其模型误差覆盖范围以实际扰动试验为准。')
    r.formula('T_ref,k = T0,k+(T_target−T0,k)min(t/t_plan,1)\ne_k=T_ref,k−T_filtered,k\nq_nom,k = q_ff,k + K_P,eff e_k + I_k + 温升不足补偿\nI_k增量=K_I e_k Δt_c；积分限幅并作饱和方向抗积分饱和\nq_ff,k依据独立观测模型的热容、导热、端板状态及反应热计算\n低风险近目标时先渐缩q_nom；低压、冰量或电压下降风险触发时\nq_k = clip(max(q_tapered,k,q_boost,k),0,1)\n关热锁存后所有q_k永久置零')
    states=pd.DataFrame([[1,'低压或结冰风险','安全增强优先'],[2,'低温且升温不足','前馈+PI+温升补偿'],[3,'正常跟踪','调节名义功率'],[4,'接近目标且风险低','渐缩加热'],[5,'测量保持完成','关热锁存']],columns=['状态码','判定','动作'])
    r.table('控制状态机',states)
    margins=','.join(fmt(x) for x in sorted(guard['sensor_stop_margin_C'].dropna().unique())) if 'sensor_stop_margin_C' in guard else '见停机配置'
    r.p(f'真实首次成功t_first由五片真实均温均超过数值零阈值、当时状态和历史路径约束满足来评价。测量停机独立地检查每次采样的滤波温度裕度、滤波电压及观测冰量，连续满足2 s后才关热；本次实际温度裕度为{margins} ℃，保持计时在条件失效时清零。由采样确定的停机时刻可以晚于真实首次成功2 s以上，这一差异通过表格和图16显示。零时刻已达标的首次事件直接记t_first=0；已温暖初场无需冷启动干预的分支允许初态直接结束。')
    r.p('沿用问题三累计电荷20 C/cm²的比较预算得到真实首次成功期限96.6667 s（前60 s加载9 C/cm²，随后0.3 A/cm²加载剩余11 C/cm²）。本轮只将该期限用于首次真实成功；测量保持及实际关热允许延伸到相应保持窗口内。该预算是本次继承比较的边界，不能冒充问题四另外给出的题设条件。')
    r.p('主策略能耗、最低电压、最大冰量和最大同刻五片温差均统计到实际关热；first_success_energy_J单独表示首次真实成功窗口。constant_first保留问题三理想首次成功口径。关热后继续加载60 s，q严格锁存为0，后验段的极值与能量单独保存，不混入启动主窗口。测量误停和实际首次达标超时均应判为不可行，不能只看测得温度宣布仿真成功。')

    r.heading('5. 优化范围、候选覆盖与推荐策略选择')
    r.p('采用参数化闭环控制律进行有限搜索。常规六维参数为目标温度、规划时间、比例增益、积分增益、渐缩带和温升补偿增益；先做零名义辅助分支检查，再做差分进化候选搜索、正式精度复算与局部整定。安全阈值、采样、停机条件对比较策略保持同一口径。所有阶段、候选参数和可行性保存在搜索CSV中，不能把未成功或仅粗精度成功候选计作最终优选。')
    optional_table(r,root,'optimization_parameter_bounds.csv','本轮动态优化参数边界')
    r.formula('主目标：min E_aux（满足共同物理约束、真实首次期限与测量保持）\n可行候选归一化评分J=E_aux/E_ref；不可行候选使用较高罚值\n正式精度候选中先找E_min；在E≤1.0005E_min的0.05%近最优带内\n依次按首次真实成功时间、最大同刻温差和辅助电能排序\n独立零名义功率分支：K_P=K_I=rate_gain=ff_factor=0，保留风险后备\n推荐方案另要求在保存的扰动训练集内全部通过，再依能耗选取\n有限候选搜索不提供连续控制函数空间的全局极小证明')
    r.p('本轮以辅助电能为首要目标；0.05%近最优带用于避免工作精度级别能耗差压倒明显的时间差。规划时间t_plan是参考轨迹参数，可以超过实际首次成功期限。动态搜索使用两个固定随机种子，多起点复核后粗精度差分进化，再将优选候选以正式精度重排并局部整定；各次评估精度与阶段在候选CSV中记录。恒功率固定C沿用问题三分配[1,1,0.6245115587719579,1,1] W/cm²；新增同工况恒功率再优化用于区分“优于固定旧分配”与“优于重新整定的恒功率”。')
    optional_table(r,root,'optimized_parameters.csv','名义能耗优选的全部控制参数')
    optional_table(r,root,'guarded_parameters.csv','推荐留裕度方案的全部控制参数')
    search=load('optimization_search.csv',root,False)
    if search is not None:r.table('名义搜索各阶段覆盖数量与可行目标值',search_stats(search),source='optimization_search.csv')
    design=optional_table(r,root,'guarded_design_search.csv','推荐方案全部候选与训练筛选',
      ['case','candidate','T_target_C','t_plan_s','training_passed','training_count','all_training_passed','training_max_stop_s','training_first_deadline_s','training_stop_deadline_s','feasible','E_aux_J','first_success_s','stop_s','min_voltage_V','max_ice_bulk'])
    if design is not None:r.p(f'推荐候选训练记录共{len(design)}行；实际训练次数、通过次数与最坏停机时间逐候选列示。选择使用的训练随机种子与推荐策略独立验证种子分离；独立验证结果不反向用于同一验证集的逐次参数挑选。')
    r.p('裕度训练联合施加初温平移、片间导热、端板导热与对流偏差，并包含温度/电压采样噪声；最终规则要求真实首次成功和测量确认停机均不晚于94.6667 s。实际停机相对98.6667 s最终评价窗口留出4 s裕度。粗训练存活候选在正式步长下再确认，最终从正式确认通过的候选选择名义辅助能耗最低者。所有训练扰动与正式确认行如下表，独立验证另列。')
    optional_table(r,root,'guarded_training_trials.csv','全部训练扰动及正式精度确认',
      ['case','candidate','stage','seed','initial_shift_K','G_factor','G_EP_factor','h_factor','noise_T_K','noise_V_V','feasible','E_aux_J','first_success_s','stop_s','physical_hold_completed','observer_max_temperature_error_K','observer_max_ice_error'])
    optional_table(r,root,'optimized_constant_parameters.csv','同工况重优化恒功率参数')
    optional_table(r,root,'constant_search_metadata.csv','恒功率再优化的范围、精度与总候选数')
    r.p('恒功率再优化先在对称三维功率域[0,1]³搜索[q端,q次端,q中,q次端,q端]，再检查保存的非对称五维邻域扰动。每个期限下进行差分进化和有界局部搜索，候选以正式精度复算；有限非对称邻域检查不能证明全五维域的全局最优。最终期限前沿从所有已评正式精度候选的并集中重新选择，保证更宽期限不会因候选集缩小而虚假增耗。')
    for fname in ('constant_optimization_search.csv','optimized_constant_search.csv'):
        csearch=load(fname,root,False)
        if csearch is not None:r.table('恒功率再优化搜索覆盖',search_stats(csearch),source=fname)

    r.heading('6. 第(1)问：推荐策略主表及全部比较结果')
    maincols=['case','strategy','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk','max_power_W_cm2']
    r.table('表4 题目要求的推荐动态与问题三固定C对比',recommended,maincols,'guarded_results.csv + main_results.csv')
    r.table('名义能耗优选及问题三两种统计窗口',main,maincols,'main_results.csv')
    if opt is not None:
        r.table('同工况重优化恒功率完整结果',opt,maincols+['first_success_energy_J','final_min_T_C','post_min_T_C','post_energy_J'],'optimized_constant_results.csv')
        diffs=[]
        for case in CASES:
            a=guard[guard['case']==case].iloc[0];c=opt[opt['case']==case]
            if not len(c):continue
            b=c.iloc[0]
            diffs.append({'case':case,'推荐动态能耗/J':a.E_aux_J,'重优化恒功率能耗/J':b.E_aux_J,
              '动态减恒功率/J':a.E_aux_J-b.E_aux_J,'动态减恒功率关热时间/s':a.stop_s-b.stop_s,
              '推荐动态可行':bool(good(pd.DataFrame([a])).iloc[0]),'恒功率可行':bool(good(pd.DataFrame([b])).iloc[0])})
        r.table('重优化恒功率与推荐动态的实际差值',pd.DataFrame(diffs))
        r.p('推荐动态与重新优化恒功率的能耗差以本表为准，不预设动态必然更低。理论上任意时间函数控制类包含恒功率控制，但本次参数化反馈类与有限算法搜索可能没有包含或找到全部恒功率最优行为，因此不能据有限搜索结果反推连续最优控制的结构。')
    optional_table(r,root,'constant_baselines.csv','零辅助加热、固定C及满功率的完整基线')
    frontier=optional_table(r,root,'constant_time_frontier.csv','全部恒功率能耗—时间限制候选')
    r.p('能耗—时间图为已求候选的可行前沿或截止时间约束下的有限解集，未经连续域完备搜索不得称全局Pareto前沿。不可行点保留在CSV中；图中叉号只表示失败候选，不代表成功启动。')
    for name,cap in [('图07_三工况主指标比较','推荐动态与固定C采用共同测量保持规则'),('图14_重优化恒功率与推荐动态','同工况恒功率再优化与推荐动态比较'),('图15_能耗时间候选前沿','已计算候选的能耗—时间取舍')]:image_if(r,root,name,cap)
    for i,case in enumerate(CASES,4):image_if(r,root,f'图{i:02d}_{case}_动态控制轨迹',CASES[case]+'推荐动态的五路功率、温度、电压和冰量；阴影为关热后观察')
    r.table('两种能耗窗口、关热状态与累计加载量',allrows,
      ['case','strategy','first_success_s','first_success_energy_J','charge_at_success_C_cm2','first_min_voltage_V','first_max_ice_bulk','first_dTmax_K','stop_s','E_aux_J','charge_at_stop_C_cm2','final_min_T_C','final_max_T_C','final_left_EP_C','elapsed_s'],'guarded_results.csv + main_results.csv')
    extra=[c for c in allrows if any(key in c for key in ('observer','measured','physical_hold','truth','false_stop','margin','deadline'))]
    if extra:r.table('观测误差与测量停机诊断',allrows,['case','strategy','feasible']+extra,'guarded_results.csv + main_results.csv')
    image_if(r,root,'图16_观测器误差与测量停机','观测状态误差、温度测量与真实首次事件/测量停机时刻')
    r.table('关热后60 s独立状态检查',allrows,
      ['case','strategy','post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J'],'guarded_results.csv + main_results.csv')
    optional_table(r,root,'per_cell_heater_energy.csv','每片辅助电能、功率与加热时长')
    optional_table(r,root,'controller_state_duration.csv','逐片控制状态累计时长')

    r.heading('7. 第(2)问：10–100 min固定恒功率启动的完整扫描')
    r.p(f'对10、15、…、100 min共{len(scan)}个预冷初场，固定问题三功率和相同电流加载逐一计算；采用理想首次真实达标口径，保持时间为0。全部轨迹保存为trajectory_scan_XXXmin.csv。已满足初始判据时，首次启动时间和辅助电能均为0；这不等于任意后续负载下的长期可用性证明。')
    r.table('19点全部启动主结果',scan,
      ['cooling_min','mean_capacity_C','feasible','E_aux_J','first_success_s','dTmax_K','min_voltage_V','max_ice_bulk','final_min_T_C','final_max_T_C'],'constant_scan.csv')
    r.table('19点能量与物理诊断',scan,
      ['cooling_min','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg','min_gas_porosity','max_j_over_jlim','min_kappa_S_m','max_iteration_error_K'],'constant_scan.csv')
    r.p(f'离散扫描可行数为{int(good(scan).sum())}/{len(scan)}。'+('没有发现失败网格点，不输出未识别的临界冷却时间。' if good(scan).all() else '失败点见可行性列；未专门二分的临界时间不应报告为连续精确阈值。'))
    r.p('初始温差与启动中温差是不同指标：较长预冷使初温趋于环境且绝对空间梯度减小；启动中的端板热汇、散热、产热与局部融冰会重新形成不均匀。完整场和过程结果应联合解释。')
    image_if(r,root,'图08_预冷时间扫描','全部19点恒功率扫描结果')

    r.heading('8. 能量、水量、独立检验与数值收敛')
    r.formula('预冷残差=AΣ_i C_i[T_i(0)−T_i(τ)]−AΣ_m Δτ_m g_b[u_L^(m+1)+u_R^(m+1)]\n启动离散能量残差=E_sensible−E_aux−E_gen−E_phase+E_loss\n水量残差=A(最终库存−初始库存−累计生成+累计边界流出)\nE_sensible逐步累计Σ C(X_new)ΔT；不是变热容时简单的端点CT之差')
    r.p('预冷对流累计采用与后向欧拉一致的端点积分；相变净释热冻结为正、融化为负。近机器精度的离散残差证明数值账目闭合，不证明所有热物理近似都无误差。另用矩阵指数、绝热极限、非均匀绝热守恒、最大值原理、网格与时间步加密提供独立证据。')
    r.table('全部策略启动能量与水量收支',allrows,
      ['case','strategy','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg','max_water_residual_kg'],all_sources)
    r.table('全部策略物理可行性诊断',allrows,
      ['case','strategy','min_gas_porosity','max_j_over_jlim','min_kappa_S_m','min_inventory','max_iteration_error_K'],all_sources)
    image_if(r,root,'图09_能量收支与累积能耗','推荐动态与固定C的能量闭合及动态累计辅助电能')
    included={'guarded_parameter_validation.csv'}
    for fname,title in [('precooling_energy_balance.csv','全部预冷能量守恒'),('precooling_validation.csv','预冷验证'),('precooling_convergence.csv','预冷时间与空间收敛'),('startup_convergence.csv','名义固定控制参数的启动收敛'),('guarded_convergence.csv','推荐控制参数的步长、网格和采样周期变化'),('coupled_convergence.csv','推荐策略的空间与时间联合加密')]:
        optional_table(r,root,fname,title);included.add(fname)
    r.p('启动加密保持控制参数固定，从而把离散误差与重新优化效果分开。局部冰峰值可能比总能耗对水相网格与顺序分裂更敏感；应依据上表实际变化评价，不因所有值均低于0.99就宣称局部峰值已经网格无关。表中显示的小数位是工作精度，不能直接解释为实物预测精度。')
    image_if(r,root,'图10_网格步长与控制周期检验','预冷独立参考和启动离散参数变化')
    for path in sorted((root/'data').glob('*.csv')):
        if path.name in included:continue
        if any(s in path.stem.lower() for s in ('validation','verification','audit','unit_test','check')):
            df=load(path.name,root)
            if len(df)<1000:r.table('补充独立检验：'+path.stem,df,source=path.name)

    r.heading('9. 物理扰动、测量噪声与独立验证')
    pilot=load('guarded_pilot_robustness.csv',root,False)
    pilot_physical=load('guarded_pilot_parameter_validation.csv',root,False)
    if pilot is not None:
        r.p(f'开发阶段的第一版留裕度方案在种子3000–3009组通过{int(good(pilot).sum())}/{len(pilot)}次，其失败数据保存在guarded_pilot_*.csv。依据这些开发反馈，最终规则要求训练场景的实际停机确认也不晚于94.6667 s，避免只对首次过零保留裕度。最终参数冻结后改用6000–6009组噪声和7000系列物性失配样例复核，未依据这些最终样本再次调参。')
        r.table('首轮开发验证失败记录（保留）',pilot[~good(pilot)],['case','seed','initial_shift_K','first_success_s','stop_s','E_aux_J','feasible'],'guarded_pilot_robustness.csv')
        if pilot_physical is not None:r.table('首轮开发物性失配失败记录（保留）',pilot_physical[~good(pilot_physical)],source='guarded_pilot_parameter_validation.csv')
    r.p('预冷灵敏度改变端面换热与BP/MEA等效导热，端板本体导热不变；这是参数化模型分析，不是已经测量得到的接触热阻。绝对温差同时受整体剩余温差影响，因此与归一化梯度分别报告。启动物理与控制参数扰动固定控制增益，并按实际CSV列示的倍率计算。')
    optional_table(r,root,'precooling_sensitivity.csv','全部预冷传热参数组合',
      ['cooling_min','h_W_m2K','conductance_factor','G_eff_W_m2K','mean_capacity_C','field_range_K','cell_range_K','relative_field_range','Bi_stack'])
    optional_table(r,root,'sensitivity.csv','全部启动物理与控制参数扰动',
      ['case','parameter','factor','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk','final_min_T_C'])
    image_if(r,root,'图11_物理参数与控制器敏感性','预冷与启动单因素扰动')
    r.p('温度、电压噪声进入真实采样链与保持判定；独立模型观测器根据自身状态和采样更新。不同初场试验把给定预冷初场作为共同先验，不另外模拟未知端板初温偏差；物性失配时观测器仍固定名义模型。高斯噪声无界，有限随机试验只能支持已测分布与幅值内的经验表现。即使全部通过，也不等于任意扰动下的鲁棒安全或无限时域稳定。')
    optional_table(r,root,'observer_example_results.csv','独立观测器噪声及物性失配示例汇总')
    robustcols=['case','seed','noise_T_K','noise_V_V','initial_shift_K','observer_initial_shift_K','G_factor','G_EP_factor','h_factor','feasible','E_aux_J','first_success_s','stop_s','final_min_T_C','dTmax_K','min_voltage_V','max_ice_bulk']
    r.table('名义能耗优选：全部扰动试验',noise,robustcols,'robustness.csv')
    r.table('名义试验统计（成功能耗与全部安全极值分开）',robust_stats(noise))
    r.table('推荐留裕度策略：全部独立扰动验证',gnoise,robustcols,'guarded_robustness.csv')
    r.table('推荐独立验证统计',robust_stats(gnoise))
    physical=optional_table(r,root,'guarded_parameter_validation.csv','推荐方案独立物理失配与噪声联合验证',robustcols)
    if physical is not None:
        r.table('推荐物理失配验证统计',robust_stats(physical))
        r.p(f'与推荐策略90次名义物性噪声验证分开，独立物理失配组共{len(physical)}次，通过{int(good(physical).sum())}次。观测器仍使用名义物性，真实对象按G、G_EP和h倍率扰动，因而可检查控制器在这些参数失配方向的表现。')
    paired=load('constant_robustness.csv',root,False)
    paired_phys=load('constant_parameter_validation.csv',root,False)
    if paired is not None:
        r.table('相同随机种子下两种恒功率基准的完整验证',paired,['strategy']+robustcols,'constant_robustness.csv')
        for label,g in paired.groupby('strategy'):
            r.table(STRATEGIES.get(label,label)+'：同种子验证统计',robust_stats(g))
    if paired_phys is not None:
        r.table('两种恒功率基准的相同物理失配场景',paired_phys,['strategy']+robustcols,'constant_parameter_validation.csv')
        for label,g in paired_phys.groupby('strategy'):
            r.table(STRATEGIES.get(label,label)+'：物理失配统计',robust_stats(g))
        r.p('推荐动态和两种恒功率基准采用相同初场、噪声种子与物理参数倍率。这样可以区分名义辅助能耗优势与经验鲁棒表现；重新优化恒功率仍是名义优化，不能冒称已经做过鲁棒参数再优化。')
    r.p('stop_s为负的行表示该次仿真没有完成规定停机，而非负的物理时间；first_success_s为负表示未发现首次真实达标。失败原因应综合首次期限、测量保持、误停、路径电压/冰量及物理可行性判断。图中的失败标志与原始负哨兵值不会被替换成成功时间。')
    for name,cap in [('图12_测量噪声与初场扰动','名义策略全部试验；叉号为不可行'),('图13_名义与留裕度备选','名义与推荐策略的能耗、时间、独立试验与关热后限制')]:image_if(r,root,name,cap)
    r.p('若应用要求关热后所有片持续高于0 ℃，应把后验最小温度或更长持续运行窗纳入新的约束并重新优化。本文保留现有任务的启动口径，同时明确输出后续降温风险；不通过关热后隐藏补热消除失败外观。')

    r.heading('10. 完整数据、复现入口与结果使用')
    r.p('CSV采用UTF-8 BOM，保留工作精度；温度℃、时间s、加热功率密度W/cm²、电流密度A/cm²、能量J。表格“—”表示未定义或缺失，不表示0。所有轨迹功率列描述结束于该行time_s的前一积分区间，独立能耗应采用25Σ_n,k q_(n,k)(t_n−t_(n−1))；默认梯形积分会在开关点引入半步误差。')
    r.p('首次事件、实际关热及后验段的时间标签分开。final_fields_*如果对应elapsed_s，则表示仿真最终场而非关热时刻场，应以time_s列为准。滤波速率、控制状态、风险和观测量在控制子步间保持，真实物理状态每个积分子步更新。')
    optional_table(r,root,'trajectory_data_dictionary.csv','全部轨迹字段字典')
    files=[]
    for path in sorted((root/'data').glob('*.csv')):
        try:df=pd.read_csv(path,encoding='utf-8-sig');rows=len(df);cols=len(df.columns)
        except Exception:rows='读取失败';cols='—'
        files.append({'文件':path.name,'数据行':rows,'列数':cols,'字节':path.stat().st_size})
    r.table('全部CSV工作文件索引',pd.DataFrame(files))
    r.formula('完整冻结参数复算：.\\run_all.ps1\n重新搜索与复算：.\\run_all.ps1 -Reoptimize\n仅绘图：python code/plot_results.py\n仅报告：python code/build_report.py')
    r.p('执行环境、输入快照和源文件哈希清单随目录保存。修改模型或参数后先重新计算，再做独立核验，最后生成图表与本报告。数值图片均由CSV绘制，提供300 dpi PNG与SVG矢量版本；figure_manifest.csv记录每图数据来源。当前成果是可复算的模型内结果，实际装置预测仍受前序物性、边界、相变与校准近似影响。')
    for path in sorted((root/'audit').glob('*.md')):r.link(path.stem,'audit/'+path.name)
    r.write(root);write_readme(root)
    print('Saved data-driven detailed Markdown / HTML report and README.')


def write_readme(root):
    n=len(list((root/'figures').glob('*.png')))
    text=f'''# 问题四修订求解结果

首选打开 **问题四_完整求解报告.html**；同名Markdown包含完整结果表。主表4采用 `guarded` 推荐动态与固定问题三功率按相同测量保持规则比较。名义 `dynamic`、重优化恒功率、理想首次口径和所有失败试验独立保留。

## 文件

- `code/`：完整可复算代码。
- `data/`：全部工作CSV、19点预冷扫描、搜索候选、轨迹、收敛、物理扰动、名义与推荐独立噪声验证。
- `figures/`：{n}张科研图，300 dpi PNG和SVG；图数据源见 `figure_manifest.csv`。
- `inputs/`：输入及来源快照；`audit/`：逻辑和独立验证记录。

## 复算

```powershell
python -m pip install --target .python_deps -r requirements.txt
./run_all.ps1
```

默认使用冻结控制参数重算；`./run_all.ps1 -Reoptimize`重新搜索。运行环境记录在 `data/run_environment.csv`。仅重画图与重建报告可分别运行 `python code/plot_results.py`、`python code/build_report.py`。

## 结果口径

真实首次达标仅作评价；测量温度裕度、电压和独立观测冰量连续满足2 s后实际关热，并锁存功率为0。主能耗统计至实际关热；`first_success_energy_J`为首次真实达标能耗。`constant_first`及19点扫描沿用理想首次口径。关热后60 s观察单独报告；并非所有启动成功方案都能持续暖态。

轨迹第n行功率属于结束于该时刻的区间，能耗按 `25*sum(q_n*(t_n-t_(n-1)))`求和。失败组能耗是已花费的电能，不纳入成功节能均值。有限搜索、有限随机种子与模型内验证均不构成全局最优或任意扰动安全证明。
'''
    (root/'README.md').write_text(text,encoding='utf-8-sig')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();build(args.root)

