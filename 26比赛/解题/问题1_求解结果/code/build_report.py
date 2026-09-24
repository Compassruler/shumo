"""Generate traceable result report, data dictionary, acceptance checks, and profile plot."""
from pathlib import Path
import csv,json,shutil,hashlib
import numpy as np
from io_utils import ROOT, SOURCE, write_csv, json_write
DAT=ROOT/'data'; REP=ROOT/'reports'; REP.mkdir(exist_ok=True)
def read(name):
    with (DAT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def mdtable(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def f(x,n=6):return f'{float(x):.{n}g}'

def main():
    summary=json.loads((DAT/'summary.json').read_text())
    cal={m:json.loads((DAT/f'calibration_{m}.json').read_text()) for m in ['main','bp']}
    # Build self-contained source folder without changing user's source files.
    inp=ROOT/'inputs';inp.mkdir(exist_ok=True)
    for name in ['附件1.xlsx','附件2.xlsx']:
        src=SOURCE/name
        if src.resolve()!=(inp/name).resolve():shutil.copy2(src,inp/name)
    src=ROOT.parent/'问题1_建模推导源文件.md'
    if src.exists():shutil.copy2(src,inp/src.name)
    checks=[]
    for tag in ['main_minus20','main_minus25','bp_minus20','bp_minus25']:
        rows=read(f'{tag}.csv');fields=read(f'fields_{tag}.csv')
        a=lambda col:np.array([float(r[col]) for r in rows])
        assert len(rows)==176 and np.allclose(a('t_s'),np.arange(176)*.2,atol=1e-8)
        assert all(int(r['model_valid'])==1 and int(r['ever_invalid'])==0 for r in rows)
        assert np.allclose(a('V_rel_error_pct'),abs(a('V_model_V')-a('V_exp_V'))/abs(a('V_exp_V'))*100)
        assert np.allclose(a('T_rel_error_pct'),abs(a('T_model_C')-a('T_exp_C'))/abs(a('T_exp_C'))*100)
        assert np.allclose(a('V_model_V'),a('E_rev_V')-a('eta_act_V')-a('eta_ohm_V')-a('eta_con_V'),atol=1e-12)
        mean_errors=[];ice_errors=[];mass_errors=[]
        for row in rows:
            ff=[r for r in fields if abs(float(r['t_s'])-float(row['t_s']))<1e-8]
            dx=np.array([float(r['dx_um'])*1e-6 for r in ff]);T=np.array([float(r['T_C']) for r in ff])
            ice=np.array([float(r['ice_bulk']) for r in ff]);mass=np.array([float(r['mv_kg_m3'])+float(r['ml_kg_m3'])+float(r['mi_kg_m3']) for r in ff])
            mean_errors.append(abs(dx@T/dx.sum()-float(row['T_model_C'])))
            ice_errors.append(abs(ice.max()-float(row['ice_max_bulk'])))
            mass_errors.append(abs(dx@mass-float(row['water_stored_kg_m2'])))
        assert max(mean_errors)<1e-10 and max(ice_errors)<1e-12 and max(mass_errors)<1e-12
        checks.append(dict(dataset=tag,samples=176,first_s=0,last_s=35,interval_s=.2,all_internal_steps_valid=True,
            field_average_max_difference_K=max(mean_errors),field_ice_max_difference=max(ice_errors),field_water_max_difference_kg_m2=max(mass_errors),passed=True))
    write_csv(DAT/'最终交付独立核验.csv',checks)
    # Original parameter list retained as table for provenance.
    import openpyxl
    sheet=openpyxl.load_workbook(inp/'附件1.xlsx',data_only=True).active
    write_csv(DAT/'附件1参数原值.csv',[dict(原始行号=i,类别=r[0],名称=r[1],原值=r[2],原单位=r[3],说明=r[4]) for i,r in enumerate(list(sheet.values)[1:],2)])
    # Identifiability figure, actual profile evaluations only.
    from plot_results import configure_style
    import matplotlib.pyplot as plt
    configure_style()
    prof=read('冻结系数剖面.csv');xx=np.array([float(r['kf_s_inv']) for r in prof]); yy=np.array([float(r['mean_squared_relative_objective']) for r in prof]);ice=np.array([float(r['ice_at35_bulk']) for r in prof])
    fig,axes=plt.subplots(1,2,figsize=(9.5,3.5),layout='constrained')
    axes[0].semilogx(xx,yy,'o-',color='#2369A1');axes[0].set(xlabel='冻结速率常数 $k_f$ / (1/s)',ylabel='平均平方相对误差目标')
    axes[1].loglog(xx,ice,'o-',color='#AD568B');axes[1].set(xlabel='冻结速率常数 $k_f$ / (1/s)',ylabel='35 s 最大冰体积分数')
    for suffix in ['png','pdf']:fig.savefig(ROOT/'figures'/f'09_freezing_identifiability.{suffix}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    figures=json.loads((ROOT/'figures/figure_manifest.json').read_text())
    figures=[x for x in figures if x['id']!='09_freezing_identifiability']
    figures.append(dict(id='09_freezing_identifiability',caption='冻结系数剖面：每个固定冻结系数都重新优化交换电流密度，均仅使用−20℃数据。误差目标在小冻结系数区间变化很小，而冰量跨多个数量级；这不是置信区间。',pdf='figures/09_freezing_identifiability.pdf',png='figures/09_freezing_identifiability.png',sources=['data/冻结系数剖面.csv']))
    json_write(ROOT/'figures/figure_manifest.json',figures)
    lines=['# 问题一计算结果与验证报告','',
        '本报告对应所给《问题1_建模推导源文件.md》，覆盖第一问的三相水/冰占孔模型、温度/电压/冰时序、参数校准、独立验证、相对误差以及每5秒结果表。代码只从实验取得加载电流密度和指定初温；实验电压、温度仅用于参数目标与事后误差，不直接代替模型输出。', '',
        '**结论：五层原热域不能同时解释温度与电压。纳入附件给定双极板后，温度预测明显改善，但电压谷深度与后期回升仍有系统偏差。冻结系数贴近搜索下界，冰体积分数只能作为条件预测，不能声称已被实验验证。**','',
        '## 1. 结果入口与口径','',
        '- [推荐工作数据：两工况352行](../data/含双极板修订_两工况352行工作数据.csv)：−20℃与−25℃各176行，0、0.2、…、35.0 s，无插补实验输出。','- [五层基线：两工况352行](../data/五层基线_两工况352行工作数据.csv)：保留MD五层热域的结构失配证据。','- [算法、方程与新增闭合说明](算法模型与实现说明.md)；[数据字典](数据字段说明.md)。', '',
        '“模型温度”是相应计算热域的厚度加权空间平均：五层为326.7 μm，含双极板为4326.7 μm；后者额外给出 `T_MEA_C`，避免把两种平均定义混淆。两种模型分别仅用−20℃工况校准，不使用−25℃数据挑选或调整参数。结构与接口等闭合具有假设性，因此这里的独立验证是**在固定模型结构和闭合假设下的参数留出验证**，不是对完整模型结构的盲验。', '',
        '温度主相对误差按MD：|T模型−T实验|/|T实验(℃)|×100%。另存开尔文分母误差，并汇总温度绝对误差和RMSE。模型最大冰体积分数按控制体总体积计，区分孔隙冰、膜冰和孔隙冰饱和度；三个最大值不必位于同一点。','',
        '## 2. 原始数据与结构核对','',
        '附件2的两张表各有184行、0–36.6 s；本次严格取0–35 s各176行。电流密度两列彼此一致，但与“电流/25 cm²”不一致：−25℃隐含303 cm²，−20℃约310 cm²。因此采用F列 A/m²，保留原始电流以及按25 cm²重算电流，绝不混用。', '',
        mdtable(['工况','由实测热量估算的面热容 J/(m²·K)','附件双板面热容 J/(m²·K)'],[[r['condition'],f(r['apparent_heat_capacity_J_m2_K']),f(r['bipolar_plate_heat_capacity_J_m2_K'])] for r in read('热容与面积诊断.csv')]),'',
        '上述表是结构诊断：C表观=[∫j(1.48−V实验)dt−∫80(T实验−T0)dt]/[T实验(35)−T0]。它忽略相变热与温差分布，仅用于说明双极板热容的重要性，**不将实测V或T送入正式热求解**。两块2 mm双极板的6066.72 J/(m²·K)远超过薄膜电极，解释了MD五层热结构的缺口。', '',
        '## 3. 求解与标定','',
        '方法为一维非均匀有限体积、守恒界面通量、后向欧拉输运、有限量相变更新与热—电压Picard迭代。水/热/气过程分裂为一阶算法，正式输出最大步长0.0125 s；MEA 58格，含板74格。每个原始采样时刻都严格落点，电流在相邻实测时刻之间线性插值。', '',
        '在较粗网格上用三个初猜进行有界信赖域非线性最小二乘，目标包含176个电压相对残差、176个摄氏温度相对残差，以及权重10⁻⁶的对数参数正则项。仅辨识j₀与k_f；k_m=1、k_vl=1、k_vi=10⁻⁴作为有量纲的假设基准，另做敏感性。相变权重从无量纲解释成速率是模型假设，不是附件给出了这些s⁻¹物性。', '',
        mdtable(['模型','j₀/(A/m²)','k_f/(1/s)','目标函数','求解次数'],[[tag,f(p['j0'],10),f(p['kf'],10),f(p['objective']),p['n_model_evaluations']] for tag,p in cal.items()]),'',
        '五层模型将j₀推到极大值以降低反应热，仍无法拟合实验，属于热结构不充分的诊断结果，不建议将这一参数当作有效电化学物性。两个模型的k_f均贴近10⁻⁴搜索下界；这不是冻结速率已经测准。','',
        '## 4. 拟合与独立验证精度','',
        mdtable(['模型/工况','用途','电压RMSE/V','电压平均相对误差/%','电压最大相对误差/%','温度RMSE/℃','温度平均相对误差/%','温度最大相对误差/%'],
         [[key,'标定' if key.endswith('20') else '独立验证',f(v['V_RMSE']),f(v['V_MAPE_pct']),f(v['V_max_relative_error_pct']),f(v['T_RMSE']),f(v['T_MAPE_pct']),f(v['T_max_relative_error_pct'])] for key,v in summary.items()]),'',
        '含板模型的电压谷偏浅、后期电压恢复不足，因此不能写成“高精度再现全部电压动态”；温度拟合改善与电压动态不足应分别陈述。电压短板可能与膜/CL水交换、低温电化学关联和未显式建模的CL束缚水动态有关，本次没有加入按时间拟合的经验电压补偿。', '',
        '## 5. 第一问表1、表2：含双极板修订模型','',
        '以下实验值直接来自附件2未先四舍五入；因此与MD中仅保留两位小数的实验温度相比，误差末位会不同。完整CSV保留计算精度；冰量的显示精度不代表物理确定性。','']
    for key in ['minus20','minus25']:
        rows=read(f'bp_{key}.csv');selected=[r for r in rows if np.isclose(float(r['t_s'])/5,round(float(r['t_s'])/5))]
        lines.extend([f'### {"−20℃（校准）" if key=="minus20" else "−25℃（独立验证）"}','',mdtable(['t/s','实验V/V','模型V/V','V误差/%','实验T/℃','模型T/℃','T误差/%','最大冰体积分数'],[[f(r['t_s'],4),f(r['V_exp_V']),f(r['V_model_V']),f(r['V_rel_error_pct']),f(r['T_exp_C']),f(r['T_model_C']),f(r['T_rel_error_pct']),f(r['ice_max_bulk'])] for r in selected]),''])
    lines.extend(['## 6. 时间变化与冰量解释','',
        mdtable(['工况','35s模型T/℃','35s模型V/V','35s孔隙最大冰体积分数','35s膜最大冰体积分数','最大冰位置'],[[key,f(summary['bp_'+key]['final']['T_model_C']),f(summary['bp_'+key]['final']['V_model_V']),f(summary['bp_'+key]['final']['ice_pore_max_bulk']),f(summary['bp_'+key]['final']['ice_mem_max_bulk']),summary['bp_'+key]['final']['ice_max_layer']] for key in ['minus20','minus25']]),'',
        '模型随加载升温，局部冰仍在累积；含板模型与实测在0–35 s均未升至0℃。不能根据电压回升宣称已经融冰或冷启动成功，也不能把短窗口内“尚未达到启动条件”写成最终启动失败。电压变化由负载、温度、膜水合与各极化共同决定。', '',
        '冻结系数剖面显示：从10⁻⁴增至约0.133 s⁻¹，优化目标只从'+f(yy[0],7)+'变为'+f(yy[5],7)+'，但35 s最大冰体积分数由'+f(ice[0],7)+'变为'+f(ice[5],7)+'。这说明冰量弱可辨识；这些剖面值属于情景比较，不能当作统计置信区间。冻结/融化及接口假设敏感性详见[参数与闭合敏感性](../data/参数与闭合敏感性.csv)、[冻结系数剖面](../data/冻结系数剖面.csv)。', '',
        '## 7. 数值一致性与守恒检验','',
        mdtable(['模型/工况','最大水量残差 kg/m²','最大离散能量残差 J/m²','有效采样数'],[[k,f(v['max_abs_water_balance_kg_m2']),f(v['max_abs_energy_balance_J_m2']),str(v['valid_samples'])+'/176'] for k,v in summary.items()]),'',
        '所有正式轨迹的内部步均通过非负水量/气体、孔隙容量、正电导率与j<j_lim检查。没有把超限电流剪成0.99 j_lim后当作可行；数值保护仅在公式计算中防无穷，并同时保留原始比值及失效标记。水质量残差为“现存水−初水−累计产水＋累计排水”。能量残差为已离散Ceff·ΔT方程的路径预算；没有完整建模迁移水携带的显热和全部可变热容焓项，因此不宣称严格全热力学能量守恒。', '',
        mdtable(['工况（含板）','网格×2且步长÷2：max ΔV/V','max ΔT/℃','max Δ最大冰体积分数'],[[r['condition'],f(r['max_difference_V_model_V']),f(r['max_difference_T_model_C']),f(r['max_difference_ice_max_bulk'])] for r in read('网格与时间步收敛.csv') if r['model']=='bp' and r['check']=='grid_double_time_half']),'',
        '温度与电压的数值差远小于实验拟合误差；局部膜冰峰仍存在约几个百分点的离散敏感性，不宣称完全网格无关。更大的不确定性来自冻结系数和接口闭合。参数/剖面扫描用较粗网格进行趋势诊断，不应与正式细网格结果末位混比。零电流/关闭相变的等温退化、关闭成冰后的零冰检查通过；独立从时空场重算平均温度、最大冰和总水量，与时序输出一致。', '',
        '## 8. 可视化图表与对应数据',''])
    for item in figures:
        lines.extend([f'### {item["id"]}','',item['caption'],'',f'![{item["id"]}](../{item["png"]})','',f'[矢量PDF](../{item["pdf"]})；数据：'+ '、'.join(f'[{Path(x).name}](../{x})' for x in item['sources'])+'。',''])
    lines.extend(['## 9. 文件索引、运行与来源','',
        'Python入口：[run_question1.py](../code/run_question1.py)；模型：[model.py](../code/model.py)；绘图：[plot_results.py](../code/plot_results.py)；本报告生成及独立核验：[build_report.py](../code/build_report.py)。完整运行方法见根目录README。','',
        'CSV索引（均UTF-8 BOM，便于Excel打开）：',''])
    lines.append(mdtable(['文件','用途'],[[f'[{p.name}](../data/{p.name})',purpose(p.name)] for p in sorted(DAT.glob('*.csv'))]))
    lines.extend(['','参数、环境和追溯文件：'+ '；'.join(f'[{p.name}](../data/{p.name})' for p in sorted(DAT.glob('*.json')))+'。','',
        '算法与结果均依据原始附件、当前代码和运行数据整理，不沿用工作区旧报告数值。原始文件未覆盖；inputs保留源文件副本。参考文献用于解释物理机制，不作为本次新增闭合常数已被实验确定的证据。'])
    (REP/'RESULTS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    dictionary()
    (ROOT/'README.md').write_text('''# 问题1求解结果

已完成0–35 s、0.2 s间隔的两组工况计算（每组176行），并提供代码、算法说明、校准/验证、敏感性与9组图表。

**首先阅读：[计算结果与验证报告](reports/RESULTS_REPORT.md)。**

- [主要工作数据：含双极板修订、两工况352行](data/含双极板修订_两工况352行工作数据.csv)
- [五层原热域对照、两工况352行](data/五层基线_两工况352行工作数据.csv)
- [算法模型与实现说明](reports/算法模型与实现说明.md)
- [数据字段说明](reports/数据字段说明.md)
- [图表目录](figures)

修订模型在−25℃独立验证中的电压平均相对误差约8.09%，温度约0.47%。电压谷仍有系统偏差，冻结系数触及搜索下界，冰量属于尚未被实验验证的条件预测。请同时保留这些结论边界。

## 复现

建议Python 3.12；依赖见code/requirements.txt，运行环境实测版本在data/运行记录与来源哈希.json。inputs包含原始附件副本。可在本文件所在目录执行：

```sh
python -m pip install -r code/requirements.txt
python code/run_question1.py
python code/plot_results.py
python code/build_report.py
```

`python code/run_question1.py --reuse` 复用已保存标定并重算结果与验证；修改物理模型后应去掉`--reuse`重新校准。完整运行约数分钟，取决于机器。当前工作目录已有`.python_deps`供本机运行，其内容不放入交付压缩包。

`data`保留正式全采样CSV、空间场、每5秒表、原始数据审计、标定日志、网格/步长检查、敏感性及来源哈希；`figures`为PNG预览和矢量PDF；`reports`为完整说明。CSV使用UTF-8 BOM，数值是数字而非带单位字符串。
''',encoding='utf-8')
    (ROOT/'code/requirements.txt').write_text('numpy>=2.0\nscipy>=1.12\nopenpyxl>=3.1\nmatplotlib>=3.8\n',encoding='utf-8')
    files=[]
    for folder in ['code','data','figures','reports','inputs']:
        for p in sorted((ROOT/folder).glob('*')):
            if p.is_file():files.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    json_write(ROOT/'交付文件清单.json',files)
    print('Report, dictionary, profile plot and independent acceptance checks complete.')

def purpose(name):
    if 'fields_' in name:return '每采样时刻各空间单元的局部温度、水相与冰分布'
    if '每5秒' in name:return '第一问表1/表2对应时刻'
    if '352' in name:return '两工况合并的中文主工作数据'
    if '全部采样' in name:return '单工况中文全采样工作数据'
    if name.startswith(('bp_','main_')):return '机器可读详细时序，含水/热/气体守恒与极化项'
    if 'trace' in name:return '每次标定评估的参数、目标与有效性'
    return {'原始数据与单位审计.csv':'未改动观测及电流/面积换算冲突','热容与面积诊断.csv':'基于实测值的独立结构诊断','附件1参数原值.csv':'题给参数原值及来源行号','网格与时间步收敛.csv':'网格/时间步细化的结果差','参数与闭合敏感性.csv':'冻结、融化、相变、束缚水与交换接口敏感性','冻结系数剖面.csv':'固定kf重新拟合j0，评价弱可辨识性','退化与守恒测试.csv':'零载等温和无成冰退化测试','最终交付独立核验.csv':'时间覆盖、误差定义、空间场重算与内部步有效性'}.get(name,'计算结果')

def dictionary():
    main=read('bp_minus20.csv')[0]; groups={
    't_s':'原始采样时刻，s','j_A_m2':'正式求解输入电流密度，A/m²，附件2 F列','I_exp_A':'附件记录电流，A；与25cm²面积不一致，不用于驱动方程','I_consistent_25cm2_A':'j×0.0025重算电流，A，非原始实测电流',
    'V_exp_V':'实测电压，V','V_model_V':'模型单电池电压，V','V_rel_error_pct':'|模型−实验|/|实验V|×100，百分数','T_exp_C':'实测平均温度，℃','T_model_C':'相应完整热域的厚度加权空间平均温度，℃','T_MEA_C':'仅五层膜电极厚度加权平均，℃','T_min_C':'全热域最低局部温度，℃','T_max_C':'全热域最高局部温度，℃','T_rel_error_pct':'摄氏值分母的相对误差，百分数','T_rel_error_K_pct':'开尔文值分母的相对误差，百分数',
    'ice_max_bulk':'max(mi/920)，包含孔隙冰和膜冰，控制体体积基准，无量纲','ice_pore_max_bulk':'只在GDL/CL统计的最大孔隙冰体积分数','ice_mem_max_bulk':'只在PEM统计的最大膜冰体积分数','s_ice_pore_max':'max(mi/(920 ε0))，孔隙冰饱和度，不能当bulk冰分数','s_liquid_pore_max':'孔液最大饱和度，排除PEM束缚水','gas_porosity_min':'多孔层最小剩余气孔率，排除无气孔PEM','ice_max_x_um':'最大冰所在节点的MEA坐标，μm','ice_max_layer':'最大冰所在层；初始全为0时位置无物理意义',
    'lambda_mean':'PEM未冻膜含水量的厚度加权平均','lambda_min':'PEM最小未冻膜含水量','kappa_min_S_m':'PEM最小质子电导率，S/m','cO2_cCL_mol_m3':'cCL氧气孔内摩尔浓度平均，mol/m³','active_area_factor':'cCL厚度平均(1−si)^3.5','j_lim_A_m2':'含冰修正极限电流密度，A/m²','j_over_jlim':'加载与极限电流之比，未把真实比值截到0.99','E_rev_V':'可逆电压，V','eta_act_V':'活化损失，V','eta_ohm_V':'膜串联电阻和接触电阻损失，V','eta_con_V':'浓差损失，V',
    'water_produced_kg_m2':'累计法拉第产水，kg/m²','water_stored_kg_m2':'现存全部水，含初始膜水，kg/m²','water_initial_kg_m2':'初始膜水1.3932e-3 kg/m²','water_vapor_kg_m2':'当前孔隙水蒸气库存，kg/m²','water_liquid_pore_kg_m2':'当前孔液库存，不含膜水，kg/m²','water_unfrozen_mem_kg_m2':'当前未冻膜水库存，kg/m²','water_ice_kg_m2':'当前全部冰库存，kg/m²','water_out_kg_m2':'累计干气边界净排出水，kg/m²','water_balance_kg_m2':'现存−初始−生成＋排出，kg/m²',
    'heat_gen_J_m2':'累计j(Eth−V模型)反应热，J/m²','heat_phase_J_m2':'累计实际相变及等效吸附热，正为放热，J/m²','heat_loss_J_m2':'两外侧累计对流散热，正向环境，J/m²','heat_sensible_integral_J_m2':'∑步∑格 Ceff(new)ΔTΔx的路径积分，J/m²；非完整焓状态差','energy_balance_J_m2':'离散显热路径−生成−相变＋散热，J/m²','H2_balance_mol_m2':'氢气现存−初始＋边界净流出＋反应消耗，mol/m²','O2_balance_mol_m2':'氧气同口径守恒残差，mol/m²',
    'model_valid':'该采样状态物理约束均有效时为1','ever_invalid':'截至该时刻是否曾有内部时间步越界，0表示没有','thermal_iterations_max':'截至该时刻最大热Picard迭代次数','min_gas_porosity_all_steps':'所有内部步的最小剩余孔隙率','min_kappa_all_steps':'所有内部步最小电导率，S/m','max_j_over_jlim_all_steps':'所有内部步最大j/jlim'}
    text=['# 数据字段说明','', '主CSV均以一个工况、一个采样时刻为一行，0–35 s共176行。中文合并CSV352行，以“工况初温_摄氏度”区分；详细英文CSV包含更多诊断量。以下为详细时序字段：','',mdtable(['字段','含义与单位'],[[k,groups.get(k,'见模型代码')] for k in main]),'',
    '## 空间场CSV','', '每行表示一个采样时刻的一个有限体积单元。正式五层58格，含板74格；176个时刻分别为10208行、13024行。`x_um`原点是aGDL外表面，含板坐标从约−2000 μm延伸到2326.7 μm；`dx_um`为实际单元宽度。`layer`为aBP/aGDL/aCL/PEM/cCL/cGDL/cBP。', '',
    '`T_C`是局部摄氏温度；`mv_kg_m3`为孔隙水蒸气，`mi_kg_m3`为当地冰质量/控制体总体积；`ml_kg_m3`在多孔层为孔液，在PEM为未冻束缚水，不能把两者都解释成孔液。`ice_bulk=mi/920`；`gas_porosity`只在多孔层有气孔含义，PEM/BP输出0；`lambda_unfrozen`只在PEM有效，其他层输出0。双极板没有水状态，水字段均0。', '',
    '## 精度、误差与缺测','', 'CSV保留浮点计算精度，末位不表示测量精度或参数可信区间。无冰的实验观测列，因为附件没有冰测量；不得将模型冰与实验温度/电压拟合精度混为一谈。数值积分中对小于机器精度的负值只用于容差判断；没有修改输出观测数据。敏感性与剖面数据是条件情景，非统计置信区间。']
    (REP/'数据字段说明.md').write_text('\n'.join(text),encoding='utf-8')
if __name__=='__main__':main()
