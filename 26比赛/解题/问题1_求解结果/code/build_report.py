"""Generate current reports and independent checks from completed exported data."""
from pathlib import Path
import csv,json
import numpy as np
from io_utils import ROOT, write_csv
from model import LC, LF
DAT=ROOT/'data'; REP=ROOT/'reports'
TAGS=['main_minus20','main_minus25','bp_minus20','bp_minus25']
LABEL={'main':'五层基线','bp':'含双极板修订'}
PHASE={'cond':'凝结','evap':'蒸发','dep':'凝华','sub':'升华','frz':'冻结','mlt':'融化'}
PARAM={'kf':'冻结','km':'融化','kcond':'凝结','kevap':'蒸发','kdep':'凝华','ksub':'升华'}
def read(name):
    with (DAT/name).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def mdtable(headers, rows):
    esc=lambda value:str(value).replace('|',r'\|')
    return '\n'.join(['| '+' | '.join(map(esc,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(esc,row))+' |' for row in rows])
def f(x,n=6):return f'{float(x):.{n}g}'
def arr(rows,key):return np.array([float(r[key]) for r in rows])
def subset(rows,**kwargs):return [r for r in rows if all(r[k]==v for k,v in kwargs.items())]
def title(tag):
    model,condition=tag.split('_',1)
    return LABEL[model]+' / '+('−20℃' if condition=='minus20' else '−25℃')
def maximum(rows,key):return float(np.max(np.abs(arr(rows,key))))

def dictionary():
    main=read('bp_minus20.csv')[0]; groups={
    't_s':'原始采样时刻，s','j_A_m2':'正式求解输入电流密度，A/m²，附件2 F列','I_exp_A':'附件记录电流，A；与25cm²面积不一致，不用于驱动方程','I_consistent_25cm2_A':'j×0.0025重算电流，A，非原始实测电流',
    'V_exp_V':'实测电压，V','V_model_V':'模型单电池电压，V','V_rel_error_pct':'|模型−实验|/|实验V|×100，百分数','T_exp_C':'实测平均温度，℃','T_model_C':'相应完整热域的厚度加权空间平均温度，℃','T_MEA_C':'仅五层膜电极厚度加权平均，℃','T_min_C':'全热域最低局部温度，℃','T_max_C':'全热域最高局部温度，℃','T_rel_error_pct':'摄氏值分母的相对误差，百分数','T_rel_error_K_pct':'开尔文值分母的相对误差，百分数',
    'ice_max_bulk':'max(mi/920)，包含孔隙冰和膜冰，控制体体积基准，无量纲','ice_pore_max_bulk':'只在GDL/CL统计的最大孔隙冰体积分数','ice_mem_max_bulk':'只在PEM统计的最大膜冰体积分数','s_ice_pore_max':'max(mi/(920 ε0))，孔隙冰饱和度，不能当bulk冰分数','s_liquid_pore_max':'孔液最大饱和度，排除PEM束缚水','gas_porosity_min':'多孔层最小剩余气孔率，排除无气孔PEM','ice_max_x_um':'最大冰所在节点的MEA坐标，μm','ice_max_layer':'最大冰所在层；初始全为0时位置无物理意义',
    'lambda_mean':'PEM未冻膜含水量的厚度加权平均','lambda_min':'PEM最小未冻膜含水量','kappa_min_S_m':'PEM最小质子电导率，S/m','cO2_cCL_mol_m3':'cCL氧气孔内摩尔浓度平均，mol/m³','active_area_factor':'cCL厚度平均(1−si)^3.5','j_lim_A_m2':'含冰修正极限电流密度，A/m²','j_over_jlim':'加载与极限电流之比，未把真实比值截到0.99','E_rev_V':'可逆电压，V','eta_act_V':'活化损失，V','eta_ohm_V':'膜串联电阻和接触电阻损失，V','eta_con_V':'浓差损失，V',
    'water_produced_kg_m2':'累计法拉第产水，kg/m²','water_stored_kg_m2':'现存全部水，含初始膜水，kg/m²','water_initial_kg_m2':'初始膜水1.3932e-3 kg/m²','water_vapor_kg_m2':'当前孔隙水蒸气库存，kg/m²','water_liquid_pore_kg_m2':'当前孔液库存，不含膜水，kg/m²','water_unfrozen_mem_kg_m2':'当前未冻膜水库存，kg/m²','water_ice_kg_m2':'当前全部冰库存，kg/m²','water_out_kg_m2':'累计干气边界净排出水，kg/m²','water_balance_kg_m2':'现存−初始−生成＋排出，kg/m²',
    'heat_gen_J_m2':'累计j(Eth−V模型)反应热，J/m²','heat_phase_J_m2':'累计实际相变及等效吸附热，正为放热，J/m²','heat_loss_J_m2':'两外侧累计对流散热，正向环境，J/m²','heat_sensible_integral_J_m2':'∑步∑格 Ceff(new)ΔTΔx的路径积分，J/m²；非完整焓状态差','energy_balance_J_m2':'离散显热路径−生成−相变＋散热，J/m²','H2_balance_mol_m2':'氢气现存−初始＋边界净流出＋反应消耗，mol/m²','O2_balance_mol_m2':'氧气同口径守恒残差，mol/m²',
    'model_valid':'该采样状态物理约束均有效时为1','ever_invalid':'截至该时刻是否曾有内部时间步越界，0表示没有','thermal_iterations_max':'截至该时刻最大热Picard迭代次数','min_gas_porosity_all_steps':'所有内部步的最小剩余孔隙率','min_kappa_all_steps':'所有内部步最小电导率，S/m','max_j_over_jlim_all_steps':'所有内部步最大j/jlim'}

    phase_labels={'cond':'凝结','evap':'蒸发','dep':'凝华','sub':'升华','frz':'冻结','mlt':'融化','frz_pore':'孔液冻结','frz_mem':'膜水冻结','mlt_pore':'孔冰融化','mlt_mem':'膜冰融化'}
    for name,label in phase_labels.items():
        groups[f'phase_{name}_kg_m2']=f'截至当前采样时刻累计{label}质量/电池面积，kg/m²；非当前库存'
        groups[f'rate_{name}_kg_m2_s']=f'前一采样时刻至当前时刻的平均{label}速率，kg/(m²·s)；t=0定义为0，非瞬时导数'
    groups.update(heat_adsorption_J_m2='膜/孔水交换采用等效潜热的累计量，J/m²；正为放热，与六相变分开列出',phase_heat_balance_J_m2='累计相变热减去六通道潜热与等效吸附热的重建值，J/m²',ice_balance_kg_m2='冰库存−累计冻结−累计凝华＋累计融化＋累计升华，kg/m²；初始无冰',ice_to_produced_water_ratio='当前冰库存/累计法拉第产水，无量纲；t=0定义0，非冻结率/概率，初始膜水也可能成冰')
    assert not set(main)-set(groups), f'Undocumented: {set(main)-set(groups)}'
    text=['# 数据字段说明','', '主CSV均以一个工况、一个采样时刻为一行，0–35 s共176行。中文合并CSV352行，以“工况初温_摄氏度”区分；详细英文CSV包含更多诊断量。以下为详细时序字段：','',mdtable(['字段','含义与单位'],[[k,groups[k]] for k in main]),'',
    '## 空间场CSV','', '每行表示一个采样时刻的一个有限体积单元。正式五层58格，含板74格；176个时刻分别为10208行、13024行。`x_um`原点是aGDL外表面，含板坐标从约−2000 μm延伸到2326.7 μm；`dx_um`为实际单元宽度。`layer`为aBP/aGDL/aCL/PEM/cCL/cGDL/cBP。', '',
    '`T_C`是局部摄氏温度；`mv_kg_m3`为孔隙水蒸气，`mi_kg_m3`为当地冰质量/控制体总体积；`ml_kg_m3`在多孔层为孔液，在PEM为未冻束缚水，不能把两者都解释成孔液。`ice_bulk=mi/920`；`gas_porosity`只在多孔层有气孔含义，PEM/BP输出0；`lambda_unfrozen`只在PEM有效，其他层输出0。双极板没有水状态，水字段均0。', '',
    '## 相变与情景数据','', '六相变累计量是单向通量累计，非互斥库存，同一份水可以重复转化。冻结/融化总量分别等于孔相与膜相分量之和。采样段平均速率=相邻累计值差/实际采样间隔，0秒记0。','', '`参数与闭合敏感性.csv`单参数统一扰动0.1、1、10倍，j0固定，使用倍数2网格及0.025 s；差值参照各自同网格基准。all_phase_rates检验共同时间尺度，结构闭合另列。冻结剖面使用倍数1网格及0.05 s，各kf仅在−20℃重估j0。近优范围以校准目标≤扫描最小值×1.05选情景，同一集合应用于−25℃；1%/10%阈值另存CSV。这些min/max均非统计置信区间。','', '## 精度、误差与缺测','', 'CSV保留浮点计算精度，末位不表示测量精度或参数可信区间。无冰的实验观测列，因为附件没有冰测量；不得将模型冰与实验温度/电压拟合精度混为一谈。数值积分中对小于机器精度的负值只用于容差判断；没有修改输出观测数据。敏感性与剖面数据是条件情景，非统计置信区间。']
    (REP/'数据字段说明.md').write_text('\n'.join(text),encoding='utf-8')

def independent_checks(data):
    checks=[]
    for tag,rows in data.items():
        fields=read(f'fields_{tag}.csv');a=lambda col:arr(rows,col)
        assert len(rows)==176 and np.allclose(a('t_s'),np.arange(176)*.2,atol=1e-8)
        assert all(int(r['model_valid'])==1 and int(r['ever_invalid'])==0 for r in rows)
        for key in rows[0]:
            if key!='ice_max_layer':assert np.isfinite(a(key)).all(),(tag,key)
        assert np.allclose(a('V_rel_error_pct'),abs(a('V_model_V')-a('V_exp_V'))/abs(a('V_exp_V'))*100)
        assert np.allclose(a('T_rel_error_pct'),abs(a('T_model_C')-a('T_exp_C'))/abs(a('T_exp_C'))*100)
        assert np.allclose(a('V_model_V'),a('E_rev_V')-a('eta_act_V')-a('eta_ohm_V')-a('eta_con_V'),atol=1e-12)
        indexed={}
        for r in fields:indexed.setdefault(round(float(r['t_s']),7),[]).append(r)
        mean_errors=[];ice_errors=[];mass_errors=[]
        for row in rows:
            ff=indexed[round(float(row['t_s']),7)]
            dx=arr(ff,'dx_um')*1e-6;T=arr(ff,'T_C');ice=arr(ff,'ice_bulk')
            mass=arr(ff,'mv_kg_m3')+arr(ff,'ml_kg_m3')+arr(ff,'mi_kg_m3')
            mean_errors.append(abs(dx@T/dx.sum()-float(row['T_model_C'])))
            ice_errors.append(abs(ice.max()-float(row['ice_max_bulk'])))
            mass_errors.append(abs(dx@mass-float(row['water_stored_kg_m2'])))
        assert max(mean_errors)<1e-10 and max(ice_errors)<1e-12 and max(mass_errors)<1e-12
        rate_error=0.
        for name in list(PHASE)+['frz_pore','frz_mem','mlt_pore','mlt_mem']:
            cumulative=a(f'phase_{name}_kg_m2');rate=a(f'rate_{name}_kg_m2_s')
            expected=np.r_[0.,np.diff(cumulative)/np.diff(a('t_s'))]
            rate_error=max(rate_error,float(np.max(abs(rate-expected))))
            assert cumulative.min()>=-1e-15 and np.diff(cumulative).min()>=-1e-15
            assert np.allclose(rate,expected,rtol=1e-10,atol=1e-14)
        for name in ['frz','mlt']:
            assert np.allclose(a(f'phase_{name}_kg_m2'),a(f'phase_{name}_pore_kg_m2')+a(f'phase_{name}_mem_kg_m2'),atol=1e-13)
        ice_res=a('water_ice_kg_m2')-a('phase_frz_kg_m2')-a('phase_dep_kg_m2')+a('phase_mlt_kg_m2')+a('phase_sub_kg_m2')
        heat=LC*(a('phase_cond_kg_m2')-a('phase_evap_kg_m2'))+(LC+LF)*(a('phase_dep_kg_m2')-a('phase_sub_kg_m2'))+LF*(a('phase_frz_kg_m2')-a('phase_mlt_kg_m2'))+a('heat_adsorption_J_m2')
        heat_error=float(np.max(abs(a('heat_phase_J_m2')-heat)))
        assert np.max(abs(ice_res))<1e-12 and heat_error<1e-7
        assert np.allclose(a('ice_balance_kg_m2'),ice_res,atol=1e-13)
        assert np.allclose(a('ice_to_produced_water_ratio')[1:],a('water_ice_kg_m2')[1:]/a('water_produced_kg_m2')[1:])
        checks.append(dict(dataset=tag,samples=len(rows),first_s=0,last_s=35,interval_s=.2,all_internal_steps_valid=True,
            field_average_max_difference_K=max(mean_errors),field_ice_max_difference=max(ice_errors),field_water_max_difference_kg_m2=max(mass_errors),
            phase_rate_max_difference_kg_m2_s=rate_error,ice_budget_max_residual_kg_m2=float(np.max(abs(ice_res))),phase_heat_reconstruction_max_error_J_m2=heat_error,passed=True))
    write_csv(DAT/'最终交付独立核验.csv',checks)
    return checks

def main():
    summary=json.loads((DAT/'summary.json').read_text())
    cal={m:json.loads((DAT/f'calibration_{m}.json').read_text()) for m in LABEL}
    assert all(p['fitted_parameters']==['j0'] and p['kf_is_fitted'] is False for p in cal.values())
    data={tag:read(f'{tag}.csv') for tag in TAGS}
    checks=independent_checks(data)
    sensitivity=read('参数与闭合敏感性.csv');profile=read('冻结系数剖面.csv')
    thresholds=read('近优阈值敏感性.csv');convergence=read('网格与时间步收敛.csv');tests=read('退化与守恒测试.csv')
    assert len(profile)==36 and all(r['passed']=='True' for r in tests)
    figures=json.loads((ROOT/'figures/figure_manifest.json').read_text())
    assert len(figures)==12
    lines=['# 问题一计算结果与验证报告','',
        '**本次采用统一简化相变模型：六个相变系数全部固定为明确说明来源的参考值，只用−20℃数据校准交换电流密度j₀，再用−25℃留出验证。冻结系数不再由电压、温度自由拟合，也不为冻结单独增加成核或JMAK模型。**','',
        '主解冰量明显增加，但增加本身不是模型已被证实的证据。附件没有冰量观测，正式冰量仍是给定相变时间尺度、膜水阈值及接口闭合下的条件预测。六系数统一敏感性与冻结剖面用于量化这一限制。','',
        '## 1. 工作数据与比较口径','',
        '- [含双极板主工作数据：两工况352行](../data/含双极板修订_两工况352行工作数据.csv)：各176行，0、0.2、…、35 s。',
        '- [五层结构对照：两工况352行](../data/五层基线_两工况352行工作数据.csv)：与主解使用相同相变处理，分别校准j₀。',
        '- [算法模型与实现说明](算法模型与实现说明.md)、[参数与新增假设清单](非题给参数与新增假设清单.md)、[完整数据字典](数据字段说明.md)。','',
        '模型温度是相应完整热域的厚度加权平均：五层326.7 μm，含双极板4326.7 μm；含板结果另存仅MEA平均温度T_MEA_C。实验温度与哪一种平均严格对应缺少独立测温定义，因此保留两种输出。最大冰体积分数为max(mi/ρi)，按控制体总体积计；孔隙饱和度则除以原始孔隙率，不能混用。','',
        '电压误差为|V模型−V实验|/|V实验|；温度主相对误差采用摄氏温度绝对值分母，并同时给出开尔文口径、绝对误差和RMSE。相变速率输出是前一采样时刻至当前时刻的区间平均，不是采样点瞬时导数。','',
        '## 2. 数据来源与结构诊断','',
        '附件2每工况184行、0–36.6 s，本次截取0–35 s各176行。加载采用F列A/m²，因其与E列A/cm²一致；附件电流与25 cm²面积不一致，详细CSV保留原电流及按25 cm²重算电流，不混用于方程。实验V、T仅用于校准目标和事后比较，不替代物理状态。','',
        mdtable(['工况','实测热量推算面热容 J/(m²·K)','附件双板面热容 J/(m²·K)','电流/电流密度隐含面积中位数 cm²'],[[r['condition'],f(r['apparent_heat_capacity_J_m2_K']),f(r['bipolar_plate_heat_capacity_J_m2_K']),f(r['implied_area_median_cm2'])] for r in read('热容与面积诊断.csv')]),'',
        '上述表观热容忽略相变热与温差分布，仅为独立结构诊断，不将实测V或T输入正式热计算。五层基线的严重温度失配说明其热域不足；含板改进与相变处理的影响应分开评价。','',
        '## 3. 相变系数如何统一处理','',
        mdtable(['系数','过程','固定参考值 s⁻¹','原始附件行','来源/闭合限定'],[[r['parameter'],r['process'],f(r['effective_rate_s_inv']),r['attachment_row'],r['qualification']] for r in read('相变参数来源与处理.csv')]),'',
        '附件的相变参数单位为“−”，不是直接给定的s⁻¹物性。本次对所有相变统一采用1 s参考时间：有效系数=附件权重/参考时间；kf/km从膜水—冰项扩展至孔液冻结/孔冰融化，ksub由凝华权重对称扩展，均明确列为闭合假设。该处理提供一致、可复现的基准，不能声称已从实验确定绝对相变时间尺度。','',
        '保留简化有限速率源项；液/汽交换使用液水面饱和蒸气压，冰/汽交换使用冰面饱和蒸气压；补齐升华的质量转移与吸热。所有转移受供体库存约束，接收相增加的质量与供体扣除相等。膜内仍采用固定不可冻水阈值λnf=3，与孔隙水共享简化冻结系数，这是待验证假设。','',
        '## 4. 校准、求解与精度','',
        '一维非均匀有限体积，隐式输运、有限量相变、热—电压Picard迭代；正式MEA58格，含板74格，最大步长0.0125 s。仅辨识j₀：先在log10(j₀)∈[−5,3]粗扫描，再有界一维搜索，最后用正式网格细化。目标是176个时刻的电压与摄氏温度相对残差平方和的平均，没有冻结参数正则项。','',
        mdtable(['模型','j₀ / (A/m²)','固定kf / s⁻¹','校准目标','评估次数'],[[LABEL[m],f(p['j0'],10),f(p['kf']),f(p['objective']),p['n_model_evaluations']] for m,p in cal.items()]),'',
        '两个模型分别只用−20℃工况校准；−25℃未用于调参、选择情景或阈值。留出验证仅在固定结构、初始条件和闭合下成立，不能称为整个建模流程的盲验。五层模型的j₀补偿热结构失配，不宜视作可靠电化学物性。','',
        mdtable(['模型/工况','用途','V RMSE / V','V平均相对误差 / %','V最大相对误差 / %','T RMSE / ℃','T平均相对误差 / %','T最大相对误差 / %'],[[title(k),'校准' if k.endswith('20') else '留出验证',f(v['V_RMSE']),f(v['V_MAPE_pct']),f(v['V_max_relative_error_pct']),f(v['T_RMSE']),f(v['T_MAPE_pct']),f(v['T_max_relative_error_pct'])] for k,v in summary.items()]),'',
        '含板模型改善了温度预测，但电压谷与后期回升仍有系统偏差；本次不通过增设经验电压补偿来掩盖偏差。固定相变基准主要解决参数处理不一致和冻结系数被误差目标压至下界的问题，并不保证更低的V/T误差。','',
        '## 5. 第一问每5秒结果表','',
        '完整工作数据保留0.2 s全部采样；下表实验值来自附件2原始精度，误差不基于提前四舍五入的温度。','']
    for key in ['minus20','minus25']:
        rows=[r for r in data['bp_'+key] if np.isclose(float(r['t_s'])/5,round(float(r['t_s'])/5))]
        lines += [f'### 含双极板 / {"−20℃" if key=="minus20" else "−25℃"}','',mdtable(['t / s','实验V / V','模型V / V','V误差 / %','实验T / ℃','模型T / ℃','T误差 / %','最大冰体积分数'],[[f(r['t_s'],4),f(r['V_exp_V']),f(r['V_model_V']),f(r['V_rel_error_pct']),f(r['T_exp_C']),f(r['T_model_C']),f(r['T_rel_error_pct']),f(r['ice_max_bulk'])] for r in rows]),'']
    lines += ['## 6. 冰量、相变贡献与未激活通道','',
        mdtable(['模型/工况','35s最大冰体积分数','孔隙最大冰体积分数','膜最大冰体积分数','最大冰所在层','冰库存 g/m²','冰库存/累计产水'],[[title(tag),f(rows[-1]['ice_max_bulk']),f(rows[-1]['ice_pore_max_bulk']),f(rows[-1]['ice_mem_max_bulk']),rows[-1]['ice_max_layer'],f(float(rows[-1]['water_ice_kg_m2'])*1000),f(rows[-1]['ice_to_produced_water_ratio'])] for tag,rows in data.items()]),'',
        '最后一列是冰库存与累计产水的质量比，既不是冻结概率，也不是产水的冻结转化率：冰还可能来自初始膜水，同一份水也可能多次相变。全域最大冰、孔隙最大冰、膜最大冰可位于不同位置，不可将它们相加。','',
        mdtable(['模型/工况']+[f'累计{label} g/m²' for label in PHASE.values()],[[title(tag)]+[f(float(rows[-1][f'phase_{name}_kg_m2'])*1000) for name in PHASE] for tag,rows in data.items()]),'',
        '本次模型规定反应产水先进入cCL孔液并使用干气边界；水蒸气是否达到液/冰面饱和状态由求解决定。因此凝结或凝华累计量为零是该窗口/闭合的结果，不能据此删去方程或认定相应系数不重要。含板两工况局部温度在0–35 s均低于0℃，融化未激活；五层−20℃局部可越过0℃，微量融化也被保留，不能把两种结构一概称为无融化。','',
        '## 7. 六系数公平敏感性与共同时间尺度','',
        '每个系数均独立改成基准的0.1、1、10倍，j₀不重新拟合；四组模型/工况使用同一规则。下表取0.1/10倍中较大的影响，V和T为全时段最大绝对变化，冰为35 s最大冰体积分数的绝对变化。敏感性及其基准均为网格倍数2、0.025 s；不与正式0.0125 s结果末位直接比较。','']
    for model in LABEL:
        sr=subset(sensitivity,model=model,kind='phase_one_at_a_time')
        lines += [f'### {LABEL[model]}','',mdtable(['系数','工况','max |ΔV| / V','max |ΔT| / ℃','|Δ最大冰35s|'],[[param+'（'+label+'）',condition, f(max(float(r['max_delta_V_V']) for r in subset(sr,parameter=param,condition=condition))),f(max(float(r['max_delta_T_C']) for r in subset(sr,parameter=param,condition=condition))),f(max(abs(float(r['delta_ice_at35'])) for r in subset(sr,parameter=param,condition=condition)))] for param,label in PARAM.items() for condition in ['minus20','minus25']]),'']
    common=subset(sensitivity,kind='common_phase_timescale')
    lines += ['所有相变同时乘0.1/10倍，等价于改变共同参考时间，检验“附件无量纲权重→秒尺度”这一共同假设。它与单独扰动kf不是同一种检验。','',mdtable(['模型','工况','共同倍率','V RMSE / V','T RMSE / ℃','35s最大冰体积分数'],[[LABEL[r['model']],r['condition'],r['multiplier'],f(r['V_RMSE']),f(r['T_RMSE']),f(r['ice_at35_bulk'])] for r in common if float(r['multiplier'])!=1]),'',
        '固定λnf与膜/CL交换系数的结构敏感性也保存在同一CSV。单参数试验不覆盖全部参数交互作用；无效状态通过valid_samples和ever_invalid明确记录，不将无效结果当作可靠预测。','',
        '## 8. 冻结剖面与近优情景范围','',
        '另行扫描kf=10⁻⁴、10⁻³、0.01、0.03、0.1、0.3、1、3、10 s⁻¹；对每个kf只用−20℃重新估计j₀，再预测−25℃。这不是主解的参数选取程序，而是检验V/T是否足以识别冰量。所有剖面采用较粗网格及0.05 s步长。','',
        mdtable(['模型','工况','工程目标容差','纳入离散情景数','kf最小 / s⁻¹','kf最大 / s⁻¹','35s冰分数最小','35s冰分数最大'],[[LABEL[r['model']],r['condition'],f(float(r['allowed_relative_objective_increase'])*100)+'%',r['n_scenarios'],f(r['selected_kf_min']),f(r['selected_kf_max']),f(r['ice_at35_min']),f(r['ice_at35_max'])] for r in thresholds]),'',
        '5%近优集合定义为J−20(kf)≤1.05×扫描中的最小J−20，同一集合原样用于−25℃。1%和10%阈值同时展示，避免选择单一阈值制造确定性。阴影是有限离散情景的逐时刻最小/最大值，**不是统计置信区间、不是概率区间，也不是所有物理可行情景的边界**。本次仍保留固定附件基准主解；若基准不在某个近优集合中，也应如实展示。','',
        '含板模型的固定kf=1基准未进入本次5%近优集合；这表明附件参考时间假设与仅按V/T最小化的偏好存在差异。主解保留的是统一参数基准，并非剖面中的拟合最优点；不能把基准冰量解释成由实验唯一反演的结果。','',
        '## 9. 独立一致性、守恒与离散误差','',
        mdtable(['模型/工况','水残差 kg/m²','冰预算残差 kg/m²','离散能量残差 J/m²','相变热重建误差 J/m²','有效采样'],[[title(k),f(summary[k]['max_abs_water_balance_kg_m2']),f(maximum(rows,'ice_balance_kg_m2')),f(summary[k]['max_abs_energy_balance_J_m2']),f(maximum(rows,'phase_heat_balance_J_m2')),str(summary[k]['valid_samples'])+'/176'] for k,rows in data.items()]),'',
        f'六个通道分别检查质量配对、非负库存、正确激活与潜热符号；连同零载、关闭成冰及全部相变关闭测试，共{len(tests)}项全部通过。另从导出的局部场独立重算平均温度、最大冰和总水量；从累计相变重算区间平均速率、冰库存预算和相变热。详细检查见最终交付独立核验CSV。','',
        'verify_phase_exports.py另从全部CSV独立核验正式四轨迹、两个中文352行表、108条敏感性轨迹和36条冻结剖面轨迹，检查区间速率积分、法拉第产水、冰库存及潜热收支；结果见相变输出独立核验CSV。','',
        '水残差为现存−初始−累计产水＋累计排水；冰残差为冰库存−冻结−凝华＋融化＋升华。相变热重建为Lc(凝结−蒸发)+(Lc+Lf)(凝华−升华)+Lf(冻结−融化)+等效吸附热。离散能量预算使用ΣCeff(new)ΔTΔx路径，不包含完整开放系统焓输运，不能写成严格全热力学能量守恒。','',
        mdtable(['模型/工况','细化检查','max ΔV / V','max ΔT / ℃','max Δ最大冰分数','冰差/基准峰'],[[LABEL[r['model']]+'/'+r['condition'],r['check'],f(r['max_difference_V_model_V']),f(r['max_difference_T_model_C']),f(r['max_difference_ice_max_bulk']),f(r['relative_difference_to_peak_ice_max_bulk'])] for r in convergence]),'',
        '网格/步长检查只反映数值离散误差，不能替代物理参数验证；所有正式轨迹内部步均监测水/气非负、剩余孔隙率、正电导率及j<jlim，未把超限电流剪裁后冒充可行。','',
        '## 10. 图表与直接数据来源','']
    for item in figures:
        lines += [f'### {item["id"]}','',item['caption'],'',f'![{item["id"]}](../{item["png"]})','',f'[矢量PDF](../{item["pdf"]})；数据：'+'、'.join(f'[{Path(x).name}](../{x})' for x in item['sources'])+'。','']
    lines += ['## 11. 文件索引与可复现性','', '运行方式见[README](../README.md)。生成顺序为求解、绘图、报告与独立核验；所有数字从本轮CSV生成，没有沿用旧报告的校准数值或“kf触底”主解结论。','',mdtable(['CSV文件','用途'],[[f'[{p.name}](../data/{p.name})',purpose(p.name)] for p in sorted(DAT.glob('*.csv'))]),'',
        '环境、校准参数及追溯文件：'+'；'.join(f'[{p.name}](../data/{p.name})' for p in sorted(DAT.glob('*.json')))+'。','',
        '主要限制：共同1 s参考时间、共享冻结系数、固定膜不可冻水阈值、CL膜水交换及温度测量算子的对应均待独立证据约束。改进后可以审查相变预算与参数敏感性，但没有将模型冰量变成实测量。']
    (REP/'RESULTS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    dictionary()
    write_readme(summary)
    print(f'Report and dictionary regenerated; {len(checks)} full datasets independently verified; {len(figures)} figures indexed.')

def purpose(name):
    if name.startswith('fields_'):return '所有采样时刻各空间单元的局部状态'
    if '每5秒' in name:return '第一问每5秒结果表'
    if '352' in name:return '两工况合并中文工作数据'
    if '全部采样' in name:return '单工况中文全部176采样数据'
    if name.startswith(('bp_','main_')):return '完整英文时序，含相变质量/速率/热/冰预算'
    if 'trace' in name:return 'j₀校准每次模型评估日志'
    return {'原始数据与单位审计.csv':'电流密度输入及面积冲突审计','热容与面积诊断.csv':'实测值驱动的独立结构诊断','附件1参数原值.csv':'附件参数原值及行号','相变参数来源与处理.csv':'六系数来源、参考时间及新增闭合','网格与时间步收敛.csv':'四工况独立网格、步长及同时细化','参数与闭合敏感性.csv':'六系数统一扰动、共同时间尺度与结构闭合敏感性','相变敏感性全时序.csv':'所有敏感性情景的逐采样状态','冻结系数剖面.csv':'固定kf、仅−20℃重估j₀及−25℃验证','冻结系数情景全时序.csv':'各冻结剖面情景的全部采样与收支','近优冻结情景范围_非置信区间.csv':'5%工程容差筛选后的逐时刻范围，非置信区间','近优阈值敏感性.csv':'1%、5%、10%工程容差比较，非置信区间','退化与守恒测试.csv':'六通道单独激活与质量/潜热/退化测试','最终交付独立核验.csv':'全采样、相变速率、场均值及预算的独立重算','相变输出独立核验.csv':'全部正式/敏感性/剖面轨迹、速率积分、产水和冰热收支独立核验'}.get(name,'计算结果')

def write_readme(summary):
    v=summary['bp_minus25']
    (ROOT/'README.md').write_text(f'''# 问题1求解结果

0–35 s、每0.2 s输出：两工况各176行；含双极板与五层对照均已计算。所有文件沿用原目录覆盖，无新增备份目录。

**先阅读：[计算结果与验证报告](reports/RESULTS_REPORT.md)。**

- [含双极板主工作数据：352行](data/含双极板修订_两工况352行工作数据.csv)
- [五层结构对照：352行](data/五层基线_两工况352行工作数据.csv)
- [算法模型与实现说明](reports/算法模型与实现说明.md)
- [相变与新增假设清单](reports/非题给参数与新增假设清单.md)
- [完整数据字段说明](reports/数据字段说明.md)
- [12组PNG与矢量PDF图表](figures)

本次六相变系数统一固定为附件权重/假定1 s参考时间，只拟合j₀；补齐升华并分开液水面/冰面饱和蒸气压。−25℃留出验证：电压平均相对误差{v['V_MAPE_pct']:.3f}%，温度平均相对误差{v['T_MAPE_pct']:.3f}%（摄氏口径）。冰量是依赖闭合假设的条件预测，不能因冰量变大就认定更准确。

六系数均做0.1/10倍敏感性，另检验共同时间尺度；冻结剖面只作非唯一性诊断。近优阴影采用校准目标增加不超过5%的离散情景，明确不是置信区间。

## 复现

建议Python 3.12；基本依赖见code/requirements.txt。inputs保留附件及当前源MD副本，环境和来源哈希见data/运行记录与来源哈希.json。在本目录执行：

```sh
python -m pip install -r code/requirements.txt
python code/run_question1.py
python code/plot_results.py
python code/build_report.py
python code/verify_phase_exports.py
python code/build_parameter_inventory.py
python code/build_parameter_source_pdf.py
```

参数清单PDF另外需要reportlab和中文字体，本机环境已具备。`run_question1.py --reuse`只在模型哈希与当前校准相同时复用j₀；改变模型后请重新校准。不要使用`--no-verify`生成最终交付，因为它不更新敏感性、剖面和数值检查。全套计算耗时取决于机器。

正式结果采用网格倍数2、0.0125 s；敏感性采用倍数2、0.025 s；剖面采用倍数1、0.05 s。图内比较使用各自同网格基准，不能把粗细网格数值的末位差误认为参数影响。

`data`：完整CSV、时空场、相变累计量/区间平均速率、参数来源、敏感性、剖面及检查；`figures`：12组图；`reports`：说明。CSV采用UTF-8 BOM，便于Excel直接打开。
''',encoding='utf-8')

if __name__=='__main__':main()
