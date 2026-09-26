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
            self.md.append(f'数据源：[{source}](data/{source})；共 {len(df)} 行，CSV保留工作精度。\n')
            self.html.append(f'<p class="caption">数据源：<a href="data/{escape(source)}">{escape(source)}</a>；共 {len(df)} 行，CSV保留工作精度。</p>')
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


def build(root=ROOT):
    main=load('main_results.csv',root);initial=load('initial_temperature_cases.csv',root)
    params=load('optimized_parameters.csv',root);scan=load('constant_scan.csv',root)
    conv=load('startup_convergence.csv',root);sens=load('sensitivity.csv',root);noise=load('robustness.csv',root)
    guarded=load('guarded_results.csv',root,False)
    r=Report();r.heading('问题四：电堆动态辅助加热控制与预冷程度影响——完整数值求解',1)
    r.p('本报告依据提供的《问题4_建模推导源文件.md》及问题三已审计的水—热—电化学模型重算。数值、表格和图片均由本目录CSV生成；没有沿用原问题四结果数值。正文先给出结论，再给出方程修正、数值方法、控制律、优化过程、完整结果与验证。')
    r.heading('1. 主要数值结论')
    savings=[]
    for case in CASES:
        a=main[(main['case']==case)&(main.strategy=='dynamic')].iloc[0]
        b=main[(main['case']==case)&(main.strategy=='constant_hold')].iloc[0]
        saving=(b.E_aux_J-a.E_aux_J)/b.E_aux_J*100
        savings.append(dict(case=case,dynamic_E_J=a.E_aux_J,constant_E_J=b.E_aux_J,energy_saving_pct=saving,
                            dynamic_stop_s=a.stop_s,constant_stop_s=b.stop_s))
        direction='降低' if saving>=0 else '增加'
        r.p(f'{CASES[case]}：动态策略辅助能耗 {a.E_aux_J:.3f} J，首次达标 {a.first_success_s:.4f} s，完成保持并关热 {a.stop_s:.4f} s；相同2 s保持的恒功率策略能耗 {b.E_aux_J:.3f} J，动态能耗{direction} {abs(saving):.3f}%。动态最低单片电压 {a.min_voltage_V:.6f} V，最大冰体积分数 {a.max_ice_bulk:.6f}，最大同刻五片温差 {a.dTmax_K:.6f} K。')
    r.p('这组解以延长启动时间换取辅助电能下降：工况1/3在接近96.6667 s预算上限才关热，期间利用了更多电化学反应热；工况2零辅助加热也需要约86.72 s才能完成保持，恒功率仅需约7.61 s。动态组累计加载电荷明显更多，因而不能把“辅助电能节约”解释为氢耗或全系统总能耗同等下降。')
    nominal_noise=int(noise.feasible.astype(bool).sum())
    r.p(f'必须同时报告的限制：名义策略扰动试验仅{nominal_noise}/{len(noise)}次可行，工况1/3主要因截止前未完成连续2 s保持而失败；名义关热后60 s内工况1和3又降到0 ℃以下。故名义结果可作为能耗主导的数学优选解，不能直接称为可靠工程控制方案；未满足的保持、噪声和余热维持要求在第8—9节完整保留。')
    if guarded is not None:
        gnoise=load('guarded_robustness.csv',root)
        r.p(f'另给出留温度/时间裕度的备选：三工况名义辅助电能分别为'+ '、'.join(f'{x:.3f} J' for x in guarded.E_aux_J)+f'，在独立随机种子组的{len(gnoise)}次扰动试验中通过{int(gnoise.feasible.astype(bool).sum())}次。该方案改善了按时完成保持的试验表现，但工况1/3关热后仍回冷，不能声称已经满足持续暖态或任意扰动下的可靠运行；详见第9节备选完整表。')
    count=int(scan.feasible.astype(bool).sum())
    r.p(f'第(2)问固定问题三五片功率分配，对10、15、…、100 min共{len(scan)}个预冷点逐一仿真，可行点为{count}/{len(scan)}。10 min初场已整体高于0 ℃，按启动温度与状态判据在t=0即成功，辅助电能与冷启动时间均为0；这不等价于证明任意后续负载下都能长期稳定运行。')
    r.p('“最优”仅指本报告给定反馈结构、参数边界、加载曲线和搜索预算内找到的最优可行候选。非线性混合控制系统的有限次差分进化与局部搜索不能提供全局最优证明；动态策略在每一指标上是否改进，以表格的实际数值为准。')
    zero_cases=main[(main.strategy=='dynamic')&(main.E_aux_J==0)&main.feasible.astype(bool)]
    if len(zero_cases):
        r.p('其中'+ '、'.join(CASES[c] for c in zero_cases['case'])+'采用被动监测、风险时才启动安全后备的控制模式，名义功率为0且本次轨迹未触发补热。由于辅助电能非负，E_aux=0确实达到主目标的非负下界；该结论只针对主能耗目标和这些工况，不意味着加权目标J或其他工况也已获得全局最优。')
    NAMES.update({'dynamic_E_J':'动态能耗/J','constant_E_J':'恒功率保持能耗/J','energy_saving_pct':'节能率/%',
                  'dynamic_stop_s':'动态关热/s','constant_stop_s':'恒功率关热/s'})
    r.table('表1 统一保持条件下的能耗比较',pd.DataFrame(savings))

    r.heading('2. 输入、单位与必须修正的建模细节')
    r.p('预冷阶段：全场25 ℃，环境−30 ℃，端板真实外表面换热系数40 W/(m²·K)；几何为2块10 mm端板、6块2 mm双极板和5组五层MEA，总厚度33.6335 mm，电热丝面积每片25 cm²。两个端片各分摊1.5块双极板，中间三片各分摊1块；端板作为两个独立热节点，避免重复计入热容。')
    inventory=root/'inputs'/'parameter_inventory.csv'
    if inventory.exists():
        r.table('输入参数及来源清单',pd.read_csv(inventory,encoding='utf-8-sig'))
        r.link('原始参数来源CSV','inputs/parameter_inventory.csv')
    r.p('启动阶段继承问题三校准内核：j(t)=min(0.005t,0.3) A/cm²，各片电流相同；端电池电压传质项系数β=10，中间片β=1，交换电流参数j₀=0.10255839004732065（内核SI电流单位）。孔隙自由液水与冰初始为0，膜内保留λ=3的不可冻结结合水；“吹扫后无自由水”不能解释为膜质子电导所需水量也为0。')
    r.p('启动搜索时限96.6667 s由问题三累计电荷预算20 C/cm²的继承口径得到：前60 s累计9 C/cm²，随后以0.3 A/cm²补足11 C/cm²。它是本次与问题三一致比较采用的仿真边界；不将其宣称为问题四单独给定的新增硬条件。')
    fixes=pd.DataFrame([
      ['(4.3)外法向边界符号','左端 kTₓ=h(T−Tₐ)，右端 −kTₓ=h(T−Tₐ)','确保两端向低温环境散热'],
      ['边界半控制体热阻','g_b=(1/h+Δx/(2k))⁻¹','由控制体中心换算到真实表面对流'],
      ['(4.34)前馈重复累加','独立保存积分修正状态；q名义=q前馈+P+I+速率补偿','不在上次实际功率上每次再叠加完整前馈'],
      ['安全增强与渐缩顺序','先渐缩，最后q=max(q渐缩,q安全)','渐缩不能削弱最高优先级安全增强'],
      ['最大温差定义','ΔTmax=max_t(max_k T_k(t)−min_k T_k(t))','同一时刻五片之间的极差，不是跨时全局温度极差'],
      ['比较窗口','动态与constant_hold均到完成连续2 s保持并关热','constant_first单独作为问题三首次过零参考'],
      ['零时刻已成功','先检查初态，满足则t_s=0、E_aux=0','避免强制走一步造成虚假时间和电能'],
      ['长期预冷结论','分别核算全场、端板—中心、五片温差','20→40 min绝对梯度下降，不能预设一定更不均匀'],
      ['“安全保证/全局最优”','以实际检验的约束和有限候选搜索范围表述','规则本身不构成鲁棒不变集或全局极小证明']
    ],columns=['项目','实际采用','原因'])
    r.table('表2 推导与实现修正',fixes)
    r.p('预冷按文档的名义材料物性计算：MEA热容60.75966 J/(m²·K)、BP热容3033.36 J/(m²·K)，整堆97503.9583 J/(m²·K)。启动内核采用孔隙、气体、离聚物及膜含水量修正的有效物性，初态MEA热容约50.22752715 J/(m²·K)，整堆约97451.29764 J/(m²·K)。温度状态由预冷映射进入启动，未把两种物性近似混称为同一绝对焓表达；该继承近似应在论文中保留。预冷对流在端板外表面，主启动模型对流在端电池节点，沿用问题二/三约定。')

    r.heading('3. 预冷有限体积模型与完整初场结果')
    r.formula('C_i dT_i/dτ = g_(i−1/2)(T_(i−1)−T_i) + g_(i+1/2)(T_(i+1)−T_i)\nC_i=(ρc_p)_i Δx_i；g_(i+1/2)=[Δx_i/(2k_i)+Δx_(i+1)/(2k_(i+1))]⁻¹\n两端另加 g_b(T_amb−T_i)，T_amb=−30 ℃\nu=T−T_amb；(C/Δτ+L)u^(m+1)=(C/Δτ)u^m')
    r.p('将MEA五层显式展开，共33个材料区、146个基础控制体。正式预冷后向欧拉步长0.25 s；各要求时刻精确截断步长，不以更晚时间层代替。七节点初温采用对应区域的热容加权平均；完整BP按实际几何中面分开，每个控制体只归属一个节点。')
    r.table('表3 三工况七节点初场',initial,['case','cooling_min','TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C','mean_capacity_C','cell_range_K','field_range_K'],'initial_temperature_cases.csv')
    r.image('图03_三工况初始温度','图3 三工况初始节点温度；各子图纵轴独立，避免掩盖细小梯度')
    r.table('表4 三种平均温度与场的极值口径',initial,['case','mean_capacity_C','mean_length_C','mean_seven_nodes_C','field_min_C','field_max_C','center_minus_left_EP_K','surface_left_C','surface_right_C','relative_field_range','Bi_stack'],'initial_temperature_cases.csv')
    r.table('表5 10–100 min预冷的全部19点温度结果',load('precooling_nodes.csv',root),
            ['cooling_min','TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C','mean_capacity_C','field_range_K','cell_range_K'],'precooling_nodes.csv')
    r.image('图01_预冷温度场族','图1 完整预冷温度场族及空间梯度细节')
    r.image('图02_预冷均温与温差','图2 温度向−30 ℃渐近，同时10–100 min范围内绝对温差衰减')
    r.p('用y=C^(1/2)u将热算子转换为对称三对角矩阵，再求特征分解，得到同网格矩阵指数独立参考。整堆主慢时间常数约1233.25648 s（20.5543 min）；存在116.71122 s反对称模态，但均匀初态仅激发约4.14×10⁻⁵ K，不能单看特征时间判定其主导性。全半堆热阻包含一块EP、三块BP与2.5层MEA，Bi_stack=0.13963743。')
    r.table('表6 预冷主要特征模态',load('precooling_slow_modes.csv',root),source='precooling_slow_modes.csv')
    r.table('表7 守恒映射后的七节点热容',load('precooling_node_capacities.csv',root),source='precooling_node_capacities.csv')

    r.heading('4. 启动被控对象、成功条件与数值推进')
    r.p('每片MEA采用水蒸气/液水/冰、氢气/氧气库存的一维有限体积离散；以蒸发/凝结、冻结/融化、凝华/升华更新相态，气相扩散与反应消耗耦合。正式每片58个控制体（基础29×网格倍率2）。温度使用七节点热网络：五片平均温度和两个端板温度，节点热容与MEA热阻随水相状态改变。模型完整核函数保存在fast_cell.py；本题新增控制器不删除原电化学可行性诊断。')
    r.formula('C_k(X) dT_k/dt = Σ_l G_kl(T_l−T_k) − h_k(T_k−T_amb) + q_gen,k + q_phase,k + 10⁴q_k\nq_gen,k = 10⁴j(t)[1.48−V_k]；q_k单位W/cm²，j单位A/cm²\nV_k = E_rev − η_act − η_ohm − η_con\nη_act = RT/(0.5F) asinh[j_SI/(2j₀(T,ice))]\nη_ohm = j_SI R_mem；η_con = −βRT/(4F) ln(1−j/j_lim)')
    r.p('顺序推进质量/相变状态后，对后向欧拉热方程和温度依赖电压进行Picard迭代，最大迭代30次，温度迭代终止阈值10⁻⁹ K。时间积分正式Δt=0.025 s，控制周期Δt_c=0.2 s；每个积分步按累计电荷差求该步平均电流，对控制更新、加载拐点、成功跨越和保持终点对齐。首次温度跨越采用最后子步重新积分并二分22次定位，避免简单采样量化启动时间。')
    r.formula('主路径约束：0≤q_k≤1 W/cm²；min_(k,t)V_k≥0.30 V；max_(k,x,t)ε_ice<0.99\n附加物理诊断：j/j_lim<1；气相孔隙率≥0；质子电导>0；库存不出现超容差负值\n首次成功 t_s：五片均温均>10⁻⁷ ℃，当步状态可行，且此前路径约束均满足\n关热 t_stop：上述条件连续满足2 s；之后锁定q_k=0\nE_aux = 25 Σ_k Σ_n q_(k,n) Δt_n  [J]')
    r.p('10⁻⁷ ℃是严格T>0判据的数值阈值。主表冰指标是全MEA所有空间控制体中的局部最大体积分数ε_ice=m_ice/ρ_ice；它不同于孔隙冰饱和度，也不同于仅多孔层冰体积分数。CSV同时保留这些分量用于辨识，主表与0.99阈值比较不混用定义。')
    r.p('动态与constant_hold主表均统计[0,t_stop]；first_success_energy_J单独给出[0,t_s]积分。constant_first使用0 s保持，提供与问题三相同的首次达标窗口。主算例关热后继续按原加载曲线运行60 s，功率严格锁定为0，该段用于检查回落和持续状态，单独成表，不混入主表极值和辅助能耗。')

    r.heading('5. 可执行的反馈控制律与离线参数整定')
    r.p('每片只输出自己的电热丝功率，五路功率独立。控制器在温度/电压采样上叠加所设测量噪声后，以时间常数0.15 s低通滤波，再以0.20 s时间常数滤波差分速率。内部水相状态用于模型软测量；无冰参考电压与实测电压的非负残差提供有界冰量校正。本实现属于模型辅助状态估计，未将仿真的真实冰量宣称为直接传感器测量，也未声称完成实际硬件观测器辨识。')
    r.formula('β=exp(−Δt_c/0.15)，β_r=exp(−Δt_c/0.20)\nT_ref,k=T0,k+(T_target−T0,k)min(t/t_plan,1)\ne_k=T_ref,k−T_f,k；r_req=max(0,(T_target−T_f,k)/max(t_plan−t,1))\nD_r=max(0,(r_req−r_T)/(r_req+0.01))；D_T=max(0,−T_f/30)\nq_ff=ff_factor·[C_k·dT_ref/dt+网络净散热−电化学反应热]/10⁴\nK_P,eff=K_P[0.6+0.4clip(−T_f/30,0,1)]\nI_trial=I_old+K_I e_k Δt_c（饱和方向的积分增量被抑制，I限幅[−2,2]）\nq_nom=q_ff+K_P,eff e_k+I+rate_gain·min(D_r,2)min(D_T,1)')
    r.p('温度超过0 ℃、估计冰量低于0.5且电压下降率大于−0.05 V/s时启用渐缩：ψ=clip((T_target−T_f)/taper_K,0,1)。安全条件使用逻辑“或”：估计冰量超过ice_warn、滤波电压低于0.30+delta_V、r_V<−0.1 V/s且V_f<0.6 V、或综合风险超过risk_warn，都触发增强。先渐缩，再将功率与安全增强值取较大者，最后限幅[0,1]。')
    r.formula('ε_est=clip[ε_model+L_obs·max(0,V_noice−V_measured)/0.1,0,1]\nR=0.4 ε_est/0.99+0.4 max(0,(0.30+delta_V−V_f)/delta_V)+0.2 min(max(0,−r_V)/0.1,1)\nq_boost=q_boost_min+(1−q_boost_min)clip((R−risk_warn)/(1−risk_warn),0,1)\nq=clip(max(q_tapered,q_boost),0,1)  （仅安全预警触发时取max）')
    states=pd.DataFrame([[1,'冰堵/低压风险','任一安全预警成立','安全增强最高优先级'],[2,'温度偏低且温升不足','D_r>0.1，低温时补偿有效','前馈+PI+速率补偿'],[3,'正常跟踪','未触发其他状态','保持/调整名义功率'],[4,'接近目标且风险较低','温度>0、冰估计<0.5、电压下降缓和','渐缩功率'],[5,'已关热','全局成功连续保持2 s','关断锁存、功率恒为0']],columns=['状态码','识别状态','触发说明','动作'])
    r.table('表8 控制状态机',states)
    r.p('首先尝试零名义功率策略：令K_P、K_I、rate_gain、ff_factor均为0，保留滤波、状态识别、电压校正和最高优先级安全后备。若正式精度仿真可行且E_aux=0，则已达到主能耗的非负下界，可直接选择该模式。其他工况在六维参数域进行差分进化，随机种子20260926与73，每次18代、种群倍率6；先用Δt=0.1 s、网格倍率1筛选，再将可行候选中目标函数最低的12个以正式Δt=0.025 s、网格倍率2重新排序，最后进行Powell有界局部搜索（最多150次评估）。')
    r.p('本次计算对规划时间的边界进行了审计：工况1保留初始[5,90] s范围搜索，增加90、95、100、110、130、160、190 s规划值的边界候选后，以种子9026在扩展域[5,190] s继续差分进化；最终参数以表9为准。规划时间是参考轨迹参数，不是允许的启动时限，即使t_plan超过96.6667 s，实际关热仍必须在96.6667 s预算内完成。所有候选及阶段标签保存在optimization_search.csv；从头运行最终脚本会直接使用扩展域，已保存参数复算可精确重建交付轨迹。')
    r.formula('常规搜索域：T_target∈[0.2,4] ℃；t_plan∈[5,190] s；K_P∈[0.025,0.65]；\nK_I∈[0.0005,0.07]；taper_K∈[0.1,2] K；rate_gain∈[0,0.4]\n零能耗后备分支：K_P=K_I=rate_gain=ff_factor=0（独立于常规搜索域）\n可行域内 J=E_aux/E_const,hold + 0.005 t_stop/t_const,hold + 0.002 ΔTmax/ΔT_const,hold\n不可行候选使用显著更大的罚值，并不作为最终可行解\n通常固定：hold=2 s；q_boost_min=0.6；ice_warn=0.8；delta_V=0.1 V；\nrisk_warn=0.7；L_obs=0.02；ff_factor=1（零能耗分支除外）')
    r.p('上述权重以能耗为主，但不是严格字典序最小化；启动时间和一致性只占小权重。参考量按每工况同精度粗搜索恒功率保持策略计算。恒功率基准在所有工况使用同一问题三分配q=(1,1,0.6245115587719579,1,1) W/cm²，未给动态组更换电流加载曲线，也未把按工况重新优化后的恒功率与固定恒功率混为一谈。')
    r.table('表9 三工况全部控制参数',params,source='optimized_parameters.csv')
    search=load('optimization_search.csv',root,False)
    if search is not None:
        stats=[]
        for (case,stage),g in search.groupby(['case','stage'],sort=False):
            good=g[g.feasible.astype(bool)]
            stats.append({'工况':CASES.get(case,case),'搜索阶段':stage,'候选数':len(g),'可行候选数':len(good),'最低可行J':float(good.J.min()) if len(good) else np.nan})
        r.table('表10 搜索覆盖与最优可行目标值',pd.DataFrame(stats),source='optimization_search.csv')

    r.heading('6. 第(1)问：三工况完整比较结果')
    r.table('表11（题目表4扩展）全部策略的主结果',main,
      ['case','strategy','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk','max_power_W_cm2'],'main_results.csv')
    r.p('constant_first是辅助参考行，终止窗口较短，不能直接将其能耗差称为与2 s保持动态策略公平比较的节能率。表1及图7的节能比较仅使用dynamic与constant_hold；全部组别均保留，便于复核问题三衔接。')
    trade=[]
    for case in CASES:
        a=main[(main['case']==case)&(main.strategy=='dynamic')].iloc[0]
        b=main[(main['case']==case)&(main.strategy=='constant_hold')].iloc[0]
        trade.append({'工况':CASES[case],'关热时间增加/s':a.stop_s-b.stop_s,'关热时间倍率':a.stop_s/b.stop_s,
          '温差变化/K':a.dTmax_K-b.dTmax_K,'最低电压变化/V':a.min_voltage_V-b.min_voltage_V,
          '最大冰量变化':a.max_ice_bulk-b.max_ice_bulk,'截止前剩余/s':96.6666666667-a.stop_s})
    r.table('各项性能的实际取舍（动态−恒功率保持）',pd.DataFrame(trade))
    r.p('工况1/3的五片一致性明显改善，工况2动态温差则略大；三工况动态最低电压都更低、最大冰量都更大，但名义轨迹仍处于规定安全界限内。因此源推导中“电压更高、冰量更小、时间相近”等预期在本次能耗优先优化中并未普遍实现，不作为结论保留。')
    percell=load('per_cell_heater_energy.csv',root,False)
    if percell is not None:
        energy=percell.pivot(index=['case','strategy'],columns='cell',values='energy_J').reset_index()
        energy=energy.rename(columns={k:f'第{k}片能耗/J' for k in range(1,6)})
        r.table('各片辅助电能完整分配',energy,source='per_cell_heater_energy.csv')
        NAMES.update({'cell':'电池序号','average_power_W_cm2':'时窗平均功率/W·cm⁻²','peak_power_W_cm2':'峰值功率/W·cm⁻²','heating_duration_s':'非零加热时长/s'})
        r.table('各片功率与有效加热时长',percell,['case','strategy','cell','average_power_W_cm2','peak_power_W_cm2','heating_duration_s'],'per_cell_heater_energy.csv')
        r.p('名义节能主要通过空间重新分配实现：深冷两工况把大部分辅助电能用于端片，以抵消端板热汇；中间片较早退出辅助加热，主要依靠电化学产热和片间传热升温。逐片电能由原始功率区间积分独立汇总，五片之和应与主表E_aux一致。')
    r.image('图07_三工况主指标比较','图7 两种策略在相同2 s保持条件下的能耗、时间、一致性、电压与冰量')
    for i,case in enumerate(CASES,4):
        r.image(f'图{i:02d}_{case}_动态控制轨迹',f'图{i} {CASES[case]}温度、电压、冰量与五路功率；灰色背景为关热后验证段')
    r.table('表12 首次成功、关热状态与加载量',main,
      ['case','strategy','first_success_s','first_success_energy_J','charge_at_success_C_cm2','stop_s','final_min_T_C','final_max_T_C','final_left_EP_C','elapsed_s'],'main_results.csv')
    r.table('表13 各组物理可行性与非线性迭代诊断',main,
      ['case','strategy','min_gas_porosity','max_j_over_jlim','min_kappa_S_m','min_inventory','max_iteration_error_K','max_water_residual_kg'],'main_results.csv')
    r.table('表14 关热后60 s独立验证',main,
      ['case','strategy','post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J'],'main_results.csv')
    dynamic=main[main.strategy=='dynamic']
    postbad=dynamic[(dynamic.post_min_T_C<=0)|(dynamic.post_min_voltage_V<.3)|(dynamic.post_max_ice_bulk>=.99)]
    if len(postbad):
        r.p('关热后验证中，以下动态工况至少一项持续状态标准未满足：'+ '、'.join(CASES[c] for c in postbad['case'])+'。因此应区分“按题设完成首次成功及保持”与“关热后整个验证段持续高于0 ℃且安全”；该结果不应被隐藏或改写为长期稳定成功。')
    else:r.p('三个动态工况在关热后60 s验证段内，最低片温保持高于0 ℃，电压与冰量也满足对应阈值；结论限于该60 s加载验证窗。post_energy_J应为0，说明关热锁存期间没有隐含二次补热。')

    r.heading('7. 第(2)问：10–100 min恒功率冷启动扫描')
    r.p('每隔5 min求一次完整预冷场，将该场的七节点温度传入同一启动模型。使用问题三固定五路功率，保持时间设为0，按照首次满足条件终止；这是第(2)问与问题三恒功率策略一致的统计口径。对每个扫描点保存完整时间序列trajectory_scan_XXXmin.csv，包含实际功率、所有单片温度/电压/冰量、相态诊断、累计能量和残差。')
    r.table('表15 全部19点恒功率扫描主指标',scan,
      ['cooling_min','mean_capacity_C','feasible','E_aux_J','first_success_s','dTmax_K','min_voltage_V','max_ice_bulk','final_min_T_C','final_max_T_C'],'constant_scan.csv')
    r.table('表16 全部19点扫描的能量与物理诊断',scan,
      ['cooling_min','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg','min_gas_porosity','max_j_over_jlim','min_kappa_S_m','max_iteration_error_K'],'constant_scan.csv')
    r.image('图08_预冷时间扫描','图8 固定恒功率在全部19个预冷时长下的启动结果')
    if count==len(scan):
        r.p('本次19个网格点均可行，因此10–100 min离散扫描内没有发现恒功率失败点，也不能声称已识别到临界预冷时间。给定恒功率对完全冷却−30 ℃基准本来就是可行方案，较暖初场全部可行与该设定一致；源文档“必存在临界冷却时间”的定性文字不作为数值结论。')
    else:
        failed=scan[~scan.feasible.astype(bool)]
        r.p('不可行的预冷网格点为：'+ '、'.join(f'{x:g} min' for x in failed.cooling_min)+'。这是离散采样发现的失败点；没有对临界冷却时刻做专门二分定位，不输出虚假的连续精确临界值。')
    r.p('初始温差与启动过程温差不是同一量。预冷越久，整体初温越接近−30 ℃且初始绝对梯度趋小；启动中端板热汇、对流位置、局部产熱/融冰和功率分配仍能重新形成片间温差。因而应联合阅读表5初场与表15过程极值，不能只用初始温差解释启动一致性。')

    r.heading('8. 能量、水量、网格步长与程序检验')
    r.formula('预冷：ΔU_released = A Σ_i C_i[T_i(0)−T_i(τ)]\nQ_loss = A Σ_m Δτ_m g_b[u_L^(m+1)+u_R^(m+1)]\n预冷残差 = ΔU_released−Q_loss\n启动离散残差 = E_sensible−E_aux−E_gen−E_phase+E_loss\n水量残差 = A·(最终水库存−初始水库存−累计生成+累计边界流出)')
    r.p('预冷累计散热与后向欧拉使用同一时间层端点积分，避免用不一致的梯形公式制造守恒误差。启动E_phase为“净释放到显热方程的相变热”，冻结为正、融化为负。启动显热量逐步累加Σ C(X_new)ΔT；含水量变化使热容变化，它不等于简单的端点C(T)T之差。近机器精度残差证明该离散方程闭合，不能据此宣称实际全部热物理误差为0，特别是携水显焓等继承近似仍存在。')
    r.table('表17 三工况各策略完整能量收支',main,
      ['case','strategy','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg','max_water_residual_kg'],'main_results.csv')
    r.image('图09_能量收支与累积能耗','图9 主要能量收支与动态辅助加热累计积分')
    r.table('表18 全部19点预冷能量守恒',load('precooling_energy_balance.csv',root),source='precooling_energy_balance.csv')
    r.table('表19 预冷模型全部单项验证',load('precooling_validation.csv',root),source='precooling_validation.csv')
    r.table('表20 预冷网格与时间步收敛',load('precooling_convergence.csv',root),source='precooling_convergence.csv')
    r.p('时间收敛对同一预冷网格的矩阵指数参考作比较；空间收敛对8倍网格的七节点热容投影作比较，避免不同控制体中心直接错位比差。启动收敛固定已选控制参数，分别改变时间步、水相控制体数量及控制周期；不在每个加密设置重新优化，以免混淆离散误差与策略改变。')
    r.table('表21 三工况全部启动加密结果',conv,
      ['case','dt_s','scale','period_s','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk','energy_residual_J','max_water_residual_kg'],'startup_convergence.csv')
    for case in CASES:
        g=conv[(conv['case']==case)&(conv.dt_s==.025)&(conv.period_s==.2)].sort_values('scale')
        base=g[g.scale==2].iloc[0];fine=g.iloc[-1]
        denergy=(fine.E_aux_J-base.E_aux_J)/base.E_aux_J*100 if base.E_aux_J else 0.
        dice=(fine.max_ice_bulk-base.max_ice_bulk)/base.max_ice_bulk*100
        r.p(f'{CASES[case]}固定Δt=0.025 s，从58控制体加密到{int(fine.scale*29)}控制体：辅助能耗变化{denergy:.5f}%，局部冰峰值从{base.max_ice_bulk:.6f}变为{fine.max_ice_bulk:.6f}，相对变化{dice:.3f}%。')
    r.p('局部冰峰值具有明显网格依赖，新增细网格上仍未稳定，不能称为“全部物理量网格无关”。总体能耗和关热时间变化小，只支持这些积分量的数值稳定性。冰量对离散和相变分裂敏感，需结合联合减小时间步的结果判断；当前已测试设置中冰峰值仍远离0.99，仅能说这些设置内安全阈值判定未改变，不给出未证明的连续模型误差界。')
    joint=load('coupled_convergence.csv',root,False)
    if joint is not None:
        r.table('表21补充 空间网格与时间步联合加密',joint,
          ['case','scale','dt_s','period_s','feasible','E_aux_J','first_success_s','stop_s','min_voltage_V','max_ice_bulk','energy_residual_J'],'coupled_convergence.csv')
        for case in CASES:
            g=joint[joint['case']==case].sort_values('scale');last=g.iloc[-1]
            base=main[(main['case']==case)&(main.strategy=='dynamic')].iloc[0]
            de=100*(last.E_aux_J-base.E_aux_J)/base.E_aux_J if base.E_aux_J else 0.
            r.p(f'{CASES[case]}联合加密：局部冰峰值依次为'+ '、'.join(f'{x:.6f}' for x in g.max_ice_bulk)+f'；最细设置与主表的能耗差为{de:.4f}%，首次成功时间差{last.first_success_s-base.first_success_s:.5f} s。')
        r.p('联合加密的相邻冰峰值增量近似减半，呈现一阶收敛趋势；固定时间步下单独加密空间得到的较大峰值偏移包含顺序分裂和界面单控制体供体限幅的时间误差。主表保留58控制体、0.025 s的统一设置供公平优化比较，冰峰值仅作有限分辨率估计，不能按显示的小数位解释为实物预测精度。全MEA局部冰峰值可发生在膜内，不能直接称为气道孔隙堵塞；孔隙冰总体积分数、膜冰体积分数及孔隙冰饱和度已在各片轨迹分别保存。')
    r.image('图10_网格步长与控制周期检验','图10 预冷独立参考、固定时间步空间加密与空间时间联合加密对比')
    # Include every independently exported small check table without assuming its schema.
    included={'precooling_validation.csv','precooling_convergence.csv','precooling_energy_balance.csv','startup_convergence.csv'}
    for path in sorted((root/'data').glob('*.csv')):
        if path.name in included:continue
        if any(s in path.stem.lower() for s in ('validation','verification','audit','unit_test','check')):
            df=load(path.name,root)
            if len(df)<1000:r.table('补充检验：'+path.stem,df,source=path.name)

    r.heading('9. 物理/控制参数敏感性及测量扰动检验')
    r.p('预冷敏感性分别改变h与BP/MEA等效导热倍率，端板材料导热率不变；该倍率是参数化的有效热阻扰动，不是实测接触热阻。固定20 min或40 min比较不同h时，更大h既增强换热也使温度更快接近环境，因此绝对温差未必单调变大。用全场温差除以剩余热容均温，可区别绝对温差与归一化不均匀程度。')
    r.table('表22 全部预冷传热敏感性组合',load('precooling_sensitivity.csv',root),
      ['cooling_min','h_W_m2K','conductance_factor','G_eff_W_m2K','mean_capacity_C','field_range_K','cell_range_K','relative_field_range','Bi_stack'],'precooling_sensitivity.csv')
    r.p('启动敏感性以各工况最终参数为基准，分别对片间G、片—端板G_EP、h、目标温度、比例增益、积分增益、冰量预警阈值和电压预警带作±20%单因素扰动；其余参数保持不变，控制器不重新优化。它刻画指定扰动方向的局部数值响应，不代表模型参数已经由试验识别。')
    r.table('表23 全部启动敏感性试验',sens,
      ['case','parameter','factor','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk','final_min_T_C'],'sensitivity.csv')
    r.image('图11_物理参数与控制器敏感性','图11 预冷绝对/归一化梯度及工况1启动单因素敏感性；全部工况结果见表23')
    r.p('测量扰动试验：温度噪声为独立零均值高斯噪声，标准差0.2 K；电压噪声标准差0.005 V；每一初场平移−1、0、+1 K分别使用种子1000–1009共10次，三工况总计90次。初温扰动同时施加到五片和两端板，参考轨迹仍按该试验输入初温生成，增益与整定参数不变。')
    r.p('这里的噪声只进入control函数的温度/电压反馈通道；全局成功判定valid与关热计时仍使用被控模型真值，冰软测量的模型先验状态也理想已知。因此这是一项反馈通道扰动仿真，并非完整实机传感—观测—安全停机链的验证。若部署，需要另行验证带估计误差的成功判定、传感器偏置/故障以及冰状态观测误差。')
    r.table('表24 全部90次测量与初场扰动',noise,
      ['case','seed','noise_T_K','noise_V_V','initial_shift_K','feasible','E_aux_J','first_success_s','stop_s','final_min_T_C','dTmax_K','min_voltage_V','max_ice_bulk'],'robustness.csv')
    robust_stats=[]
    for case,g in noise.groupby('case',sort=False):
        robust_stats.append({'工况':CASES.get(case,case),'试验数':len(g),'可行数':int(g.feasible.astype(bool).sum()),
          '能耗均值/J':g.E_aux_J.mean(),'能耗标准差/J':g.E_aux_J.std(ddof=1),'能耗最小/J':g.E_aux_J.min(),
          '能耗最大/J':g.E_aux_J.max(),'最低电压/V':g.min_voltage_V.min(),'最大冰体积分数':g.max_ice_bulk.max()})
    r.table('表25 扰动统计（同组混合初场平移）',pd.DataFrame(robust_stats))
    r.image('图12_测量噪声与初场扰动','图12 固定整定参数的90次扰动试验；序号与CSV数据行一致')
    n_ok=int(noise.feasible.astype(bool).sum())
    r.p(f'本次扰动试验可行数为{n_ok}/{len(noise)}。若全部通过，只能称为这组有限种子和扰动幅值内通过；高斯噪声理论上无界，有限蒙特卡洛试验不能证明任意噪声下都安全。可行性判据统计到关热时刻，不能把它与无限时间的闭环鲁棒稳定性等同。')
    if n_ok<len(noise):
        failures=noise[~noise.feasible.astype(bool)]
        if (failures.min_voltage_V>=.3).all() and (failures.max_ice_bulk<.99).all():
            r.p('失败轨迹的电压与冰量都没有越过硬安全阈值，主要问题是时间预算与保持条件：有的温度在冰点附近波动导致保持计时重置，有的首次达标太晚，剩余不足2 s。表中stop_s=−1表示在规定时限内没有完成关热条件，不是负的物理关热时间。失败组E_aux_J是截至仿真终止的已消耗电能，不能作为“成功节能”样本混入结论。')
    if guarded is not None:
        r.heading('9.1 留时间与温度裕度的备选方案',3)
        r.p('在保留名义最小能耗结果的基础上，补做有限候选的裕度设计。工况1/3将名义规划时间乘0.98、0.95、0.90、0.85，同时把目标温度提高到不少于1、2、3 ℃；连同原参数，每工况13个候选。工况2保留零名义功率模式。每候选用初温偏差±1 K及种子2000、2001、2002共6种训练扰动筛选，在所有训练点可行的候选中选名义辅助电能最低者。训练Δt=0.05 s、网格倍率2；最终轨迹以Δt=0.025 s重新计算。')
        r.p('随后采用全新的种子3000–3009、初场偏差−1/0/+1 K，仍为温度噪声标准差0.2 K、电压噪声标准差5 mV，每工况30次，总90次独立验证。训练种子、名义策略原噪声检验种子与本次验证种子互不相同；比较可行比例是各自种子组的经验比例，不是严格配对试验，也不是置信保证。')
        r.table('备选方案全部控制参数',load('guarded_parameters.csv',root),source='guarded_parameters.csv')
        r.table('备选方案主结果与关热后验证',guarded,
            ['case','strategy','feasible','E_aux_J','first_success_s','stop_s','dTmax_K','min_voltage_V','max_ice_bulk',
             'max_power_W_cm2','final_min_T_C','post_min_T_C','post_min_voltage_V','post_max_ice_bulk','post_energy_J'],'guarded_results.csv')
        extra=[]
        for _,g in guarded.iterrows():
            a=main[(main['case']==g['case'])&(main.strategy=='dynamic')].iloc[0]
            b=main[(main['case']==g['case'])&(main.strategy=='constant_hold')].iloc[0]
            ng=gnoise[gnoise['case']==g['case']]
            extra.append({'工况':CASES[g['case']],'较名义增加电能/J':g.E_aux_J-a.E_aux_J,
              '较名义增加/%':100*(g.E_aux_J-a.E_aux_J)/a.E_aux_J if a.E_aux_J else 0,
              '较恒功率保持节能/%':100*(b.E_aux_J-g.E_aux_J)/b.E_aux_J,'名义截止前裕度/s':96.6666666667-g.stop_s,
              '验证通过数':int(ng.feasible.astype(bool).sum()),'验证总数':len(ng),'验证最大关热/s':ng.stop_s.max()})
        r.table('备选成本、时间裕度与验证汇总',pd.DataFrame(extra))
        r.table('备选全部候选及训练筛选',load('guarded_design_search.csv',root),
            ['case','candidate','T_target_C','t_plan_s','training_passed','training_count','all_training_passed','training_max_stop_s','E_aux_J','stop_s','min_voltage_V','max_ice_bulk'],'guarded_design_search.csv')
        r.table('备选完整90次独立验证',gnoise,
            ['case','seed','noise_T_K','noise_V_V','initial_shift_K','feasible','E_aux_J','first_success_s','stop_s','final_min_T_C','dTmax_K','min_voltage_V','max_ice_bulk'],'guarded_robustness.csv')
        r.table('备选离散能量与物理诊断',guarded,
            ['case','E_aux_J','E_gen_J','E_phase_J','E_loss_J','E_sensible_J','energy_residual_J','water_residual_kg',
             'min_gas_porosity','max_j_over_jlim','min_kappa_S_m','max_iteration_error_K'],'guarded_results.csv')
        r.image('图13_名义与留裕度备选','图13 以少量额外辅助电能获得时间裕度的备选；试验通过与持续暖态限制同时呈现')
        r.p('如果任务要求在本文有限温度/电压反馈扰动范围内更可靠地按时完成保持，优先采用留裕度备选；如果只优化名义模型的辅助电能，保留名义策略作为能耗边界。两者都没有解决工况1/3关热后再次跌破0 ℃的问题。若工程成功定义要求持续暖态，应把关热后最低温度或更长保持窗口显式加入优化约束并重算，不可将本报告现有结果改称持续运行成功。')

    r.heading('10. 可复现文件、数据字典与交付说明')
    r.p('CSV统一UTF-8 BOM编码，单位写入列名，工作文件保留计算精度；报告表格为排版展示做适量小数截断。温度T单位为℃、t为s、q为W/cm²、j为A/cm²、能量为J。报告中—表示未定义/缺失，不是0；失败方案的负时间哨兵值必须与feasible字段一起解释。')
    r.p('trajectory_*文件中，第n行功率描述“结束于该行time_s的积分区间”，因此独立辅助电能复算采用25Σ_{n≥1,k}q_(n,k)[t_n−t_(n−1)]；不能直接对该列做默认梯形积分，否则会引入开关时刻的半步误差。状态码、风险、滤波速率与冰量估计是最近一次控制更新值，积分子步之间保持。final_fields_*是关热后60 s仿真终态场，不是主表关热时刻的空间场；其time_s列明确给出对应时间。')
    dictionary=pd.DataFrame([
        ['time_s / j_A_cm2 / charge_C_cm2','实际时间、瞬时加载电流密度、累计电荷','s / A·cm⁻² / C·cm⁻²'],
        ['T1_C…T5_C / TEL_C / TER_C','五片平均温度、左/右端板温度','℃'],
        ['cellk_q_W_cm2','第k片在结束于本行的区间内加热功率密度','W·cm⁻²'],
        ['cellk_V_V','第k片当前电压','V'],
        ['cellk_ice_bulk','第k片全MEA空间最大冰体积分数','无量纲'],
        ['cellk_pore_ice_bulk / cellk_mem_ice_bulk','多孔层/膜内空间最大冰体积分数','无量纲'],
        ['cellk_pore_ice_saturation','多孔层局部冰体积/原始孔隙体积的最大值','无量纲，与0.99体积分数阈值不同'],
        ['cellk_lambda','第k片膜内平均含水量λ','无量纲'],
        ['cellk_j_over_jlim / cellk_gas_porosity','电流与极限电流之比、最小气相孔隙率','无量纲'],
        ['cellk_state / cellk_risk','最近控制更新的状态码和综合冰堵风险','状态码见表8；风险无量纲'],
        ['cellk_rT_K_s / cellk_rV_V_s','滤波温升速率/电压变化率','K·s⁻¹ / V·s⁻¹'],
        ['cellk_ice_est','模型加电压残差修正后的冰量估计','无量纲'],
        ['stopped','该行端点是否已进入不可逆关热状态','0/1；关热切换行的q仍记录此前区间'],
        ['E_aux_J…E_sensible_J','自t=0累计的五项离散热收支','J；后验期间反应等累计量继续更新'],
        ['energy_residual_J / water_residual_kg','逐行能量/水量平衡残差','J / kg'],
        ['water_inventory_kg / water_produced_kg / water_out_kg','水库存、累计生成、累计边界排出','kg']
    ],columns=['字段或字段族','含义','单位/注意'])
    r.table('工作数据字段说明',dictionary)
    exact_dict=load('trajectory_data_dictionary.csv',root,False)
    if exact_dict is not None:r.table('全部轨迹列的逐列数据字典',exact_dict,source='trajectory_data_dictionary.csv')
    files=[]
    for path in sorted((root/'data').glob('*.csv')):
        try:
            df=pd.read_csv(path,encoding='utf-8-sig');rows=len(df);columns=len(df.columns)
        except Exception:rows='读取失败';columns='—'
        files.append({'文件':path.name,'数据行':rows,'列数':columns,'字节':path.stat().st_size})
    r.table('表26 全部工作CSV索引',pd.DataFrame(files))
    r.formula('一键复算冻结控制参数与所有输出：.\\run_all.ps1\n重新优化并完整运行：.\\run_all.ps1 -Reoptimize\n单独重算主数值：python code/run_problem4.py --reuse-controls --skip-precool\n仅重画全部科研图：python code/plot_results.py\n仅重建完整报告：python code/build_report.py')
    r.p('运行顺序为数值计算→独立验证→图片生成→报告生成；若修改模型参数，应重新运行数值计算，不能只刷新图片。代码、输入快照与SHA-256清单提供源文件追溯。根目录README.md说明环境安装和关键文件；图像提供300 dpi PNG及SVG矢量版，两者读取同一CSV。')
    r.link('预冷模型审计与阶段衔接说明','audit/预冷模型审计.md')
    r.link('独立审计说明','audit/独立审计说明.md')
    r.write(root)
    write_readme(root)
    print('Saved detailed Markdown / HTML report and README.')


def write_readme(root):
    text='''# 问题四完整数值求解

首选打开 **问题四_完整求解报告.html**。Markdown版同名保存，包含完整结果表。

## 目录

- `code/`：可复算Python源代码；`run_problem4.py`是主入口。
- `data/`：全部UTF-8 BOM工作CSV，包括9组主结果、19点扫描、优化候选、完整轨迹、守恒、加密、敏感性与90次扰动试验。
- `figures/`：12张科研图，均有300 dpi PNG与SVG；`figure_manifest.csv`记录数据来源。
- `inputs/`：本次使用的输入快照；`audit/`：方程与口径审计说明。

## 环境与复算

本机使用Python 3.12及固定版本NumPy、SciPy、Numba、pandas、Matplotlib。所附requirements.txt用于重建环境；本机局部依赖位于.python_deps。可直接运行run_all.ps1复算冻结参数与全部检验，添加-Reoptimize则重新搜索控制参数。跨机器运行前请用匹配Python版本安装依赖：

```powershell
python -m pip install --target .python_deps -r requirements.txt
./run_all.ps1
```

该入口默认用已保存控制参数复算全部数值、验证、表格、图和报告。需要重新进行参数搜索时，使用 `./run_all.ps1 -Reoptimize`。图表和报告可分别通过 `python code/plot_results.py`、`python code/build_report.py`重建。

本次执行环境由 `data/run_environment.csv`记录。`.python_deps/`为本次机器上的局部依赖目录（若存在）；Python脚本通过 `bootstrap.py`加载。若存在`requirements.txt`或环境锁文件，请优先按其固定版本安装。完整重优化耗时明显长于重画图；固定随机种子和环境用于复现搜索过程。

已有优化参数时，可执行：

```powershell
python code/run_problem4.py --reuse-controls --skip-precool
python code/plot_results.py
python code/build_report.py
```

## 统计口径

主比较是 `dynamic` 与 `constant_hold`：均在首次全片达标后连续保持2 s再关热；`constant_first`为问题三首次达标参考。第(2)问19点扫描沿用首次达标口径。关热后60 s验证单独列示。

轨迹功率列描述结束于该行时刻的前一积分区间，独立能耗必须用 `25*sum(q_n*(t_n-t_(n-1)))`复算，不用梯形积分。温度单位℃、时间s、单片加热功率密度W/cm²、电流密度A/cm²、能量J；最大温差为同一时刻五片极差的过程最大值。

本解是给定参数化反馈类与有限搜索预算内找到的可行优选解，不提供全局最优证明。两阶段物性与对流位置继承近似、有限扰动范围和关热后验证结论均在报告中明确说明。完整工作精度见CSV，报告显示精度不用于后续复算。
'''
    text=text.replace('12张科研图',f'{len(list((root/"figures").glob("*.png")))}张科研图')
    (root/'README.md').write_text(text,encoding='utf-8-sig')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();build(args.root)
