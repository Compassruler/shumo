"""Build Chinese results and algorithm reports from computed CSV, never typed values."""
from pathlib import Path
import csv,json,html,hashlib,sys

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=ROOT/'reports'
OUT.mkdir(exist_ok=True)
def read(name):
    with (DATA/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def num(row,key):return float(row[key])
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)

s=read('strategy_summary.csv');by={r['strategy']:r for r in s}
b=json.loads((DATA/'critical_temperature.json').read_text(encoding='utf-8'))
cv=read('convergence.csv');ss=read('sensitivity.csv');checks=read('independent_verification.csv')
export_checks=read('最终CSV独立核验.csv')
assert all(r['passed'].lower()=='true' for r in checks+export_checks), 'Verification failures must be resolved before delivery'
labels={'constant':'恒流','ramp':'线性升载（有限范围）','step':'三段阶梯（退化）'}
param={'constant':'j=0.5','ramp':'a=2.5，jp=0.5，tp=0.2 s','step':'j1=j2=j3=0.5；t1=8 s，t2=16 s'}
result_rows=[]
for r in s:
    k=r['strategy'];result_rows.append([labels[k],param[k],f"{num(r,'end_time_s'):.4f}",
        f"{num(r,'charge_C_cm2'):.5f}",f"{num(r,'max_current_A_cm2'):.3f}",
        f"{num(r,'min_voltage_V'):.6f}",f"{num(r,'max_ice_bulk'):.6f}",'成功' if r['status']=='success' else r['status']])
results=table(['加载策略','最优加载参数','启动时间 / s','累计电荷 / C·cm⁻²','最大电流 / A·cm⁻²','最低电压 / V','最大冰体积分数','结果'],result_rows)
warm=b['constant']['warm_feasible_C'];cold=b['constant']['cold_infeasible_C']
failure=b['below_critical'];critical=b['critical_failure']
traj=read('trajectory_below_critical.csv');last=traj[-1]
loss=table(['−14 ℃终止时位置','温度 / ℃','电压 / V','活化损失 / V','欧姆损失 / V','浓差损失 / V','最大冰体积分数'],[
    [label]+[f'{float(last[key]):.6f}' for key in [f'T{i}_C',f'cell{i}_V',f'cell{i}_eta_act',f'cell{i}_eta_ohm',f'cell{i}_eta_con',f'cell{i}_ice_bulk']]
    for i,label in [(1,'端部1和5'),(2,'次端部2和4'),(3,'中部3')]])
coarse=next(r for r in cv if r['strategy']=='constant' and int(r['grid_scale'])==8)
fine=next(r for r in cv if r['strategy']=='constant' and int(r['grid_scale'])==16)
dt_diff=abs(num(coarse,'end_time_s')-num(fine,'end_time_s'))
ice_rel=abs(num(coarse,'max_ice_bulk')-num(fine,'max_ice_bulk'))/num(fine,'max_ice_bulk')*100
count=sum(1 for _ in (DATA/'optimization_trace.csv').open(encoding='utf-8-sig'))-1

report=f'''# 问题2 电堆自冷启动优化计算结果

本报告完成第二问的两项任务：在−10 ℃比较恒流、线性升载、三段阶梯；在相同20 C/cm²电荷预算和0.5 A/cm²电流上限下确定可自启动初温边界，并定位失败电池。结果来自用户MD框架与已有问题一含双极板标定模型的耦合求解，属于该模型及相变闭合假设下的条件预测。

## 1 表3 最优策略比较

{results}

加载参数的电流单位为A/cm²，斜率单位为A/(cm²·s)。最大冰体积分数取整个启动期间、五片电池所有MEA网格的最大值，**包含膜冰**，并非孔隙冰饱和度。恒流下仅多孔层最大冰体积分数为{num(by['constant'],'max_pore_ice_bulk'):.6f}，最大孔隙冰饱和度为{num(by['constant'],'max_pore_ice_saturation'):.6f}，两者另存于表3 CSV。

恒流搜索得到j=0.5；三段阶梯允许电流相等，故最优控制退化为同一条恒流曲线。t1=8 s和t2=16 s只是等价表示，三档相等时切换时刻不影响物理控制，不能把它们解释为可识别的唯一最优参数。

**线性升载的最优性需要限定。** 题目没有给斜率上限，MD中的t_min也未指定。有限参数搜索采用平台到达时间tp∈[0.2,120] s，平台电流jp≤0.5；所得边界解a=2.5、jp=0.5对应0.2 s升满载。`ramp_slope_limit.csv`继续计算tp=0.1、0.05、0.02、0.01 s，结果趋近恒流。因而2.5不是原题无限斜率范围的全局最优斜率；在本次搜索观察下，从零升载的启动时间下确界趋近{num(by['constant'],'end_time_s'):.4f} s。若要求三种曲线必须严格不同，需额外规定斜率上限或最小档差，原题没有这些约束。

本模型下−10 ℃满载最低电压仍为{num(by['constant'],'min_voltage_V'):.6f} V，电压裕度约{num(by['constant'],'min_voltage_V')-.3:.3f} V，冰占孔也很小。因此优化首要效果是尽早产热，降低端板吸热和环境散热的累计损失。原MD关于“先低后高严格优于恒流”的推断在当前参数下没有得到计算支持。

![加载与电荷](../figures/01_加载策略与累计电荷.png)
![各片温度](../figures/02_各单电池与端板温度.png)
![电压约束](../figures/03_各单电池电压与安全约束.png)

## 2 第二小问 最低初始温度

恒流及等价阶梯策略的临界初温位于 **({cold:.6f}, {warm:.6f}] ℃**，数值上约为 **−12.8 ℃**。这里冷端是预算耗尽前未达到启动条件的初温，暖端是已找到成功轨迹的初温；区间宽度为{warm-cold:.6f} ℃。

''' + table(['策略','失败侧初温 / ℃','成功侧初温 / ℃'],[
    [labels[k],f"{b[k]['cold_infeasible_C']:.6f}",f"{b[k]['warm_feasible_C']:.6f}"] for k in labels])+f'''

搜索先在−10、−11、−12、−12.5、−12.75、−13、−14、−16、−20 ℃逐点重新优化三类策略，再对已优化曲线二分，并在更细网格上复核分界两侧。所检查温度点的最优加载仍趋向满载恒流。该区间是给定模型与所搜索策略空间的可行边界，不构成对任意无限维电流控制的全局不可行性证明；实际模型误差和参数不确定性远大于0.005 ℃的二分分辨率，不宜把这些小数当成实物测温精度。

### 2.1 首要失效是端部能量不足

临界失败侧T0={critical['T0_C']:.6f} ℃，电荷达到{critical['charge_C_cm2']:.6f} C/cm²时，端部最低温度仍为{critical['min_end_temperature_C']:.6f} ℃，全程最低电压{critical['min_voltage_V']:.6f} V。

以更清楚的−14 ℃工况为例，0.5 A/cm²在40 s耗尽20 C/cm²电荷，端部1、5温度仍为{failure['min_end_temperature_C']:.4f} ℃，中部3已升到{failure['center_temperature_C']:.4f} ℃。全程最低电压{failure['min_voltage_V']:.6f} V，最大孔隙冰饱和度{failure['max_pore_ice_saturation']:.6f}，均未达到电压或孔隙堵塞失效。因此关键电池为**两端第1和第5片**，直接失败原因是**电荷预算耗尽时仍未越过0 ℃**。

端部必须向大热容端板供热，并承担对流散热；中间电池没有这两项边界负担。冰量增加和损失变化存在，但在临界点附近没有成为先触发的硬约束，不能将该失败写成“电压率先跌破0.30 V”。

{loss}

![临界两侧](../figures/07_最低启动温度两侧轨迹.png)
![损失分解](../figures/08_临界启动电压损失分解.png)

## 3 模型与算法

详见[算法模型与代码说明](算法模型与代码说明.md)。热网络有五个单片温度和两个端板温度；每片内部仍用一维有限体积求解膜水、液水、水蒸气、冰、氢气和氧气。温度反馈相变与电化学，再由实际电压与潜热更新热源，未重放实验温度、电压或固定单片热源。

空间输运与热网络采用后向欧拉，热源用Picard迭代收敛。利用镜像对称求解三个独立单片状态和四个独立温度，按[2,2,1]和两块端板权重计算整堆预算。电荷按策略解析积分；成功事件通过当前时间步重新积分并二分定位，不允许越过20 C/cm²后仍继续用电。

外层采用恒流网格加有界标量优化、升载与阶梯差分进化多种子搜索加Powell局部精修。已保存{count}条候选评估，成功/失败、参数、目标、硬约束指标均可追溯。失败轨迹记录终止时间而不标成启动时间。所有“最优”均为已定义搜索范围内发现的最优可行解，没有全局解析最优证书。

## 4 数值核验和精度

正式表3使用每片232个输运网格、时间步0.003125 s，轨迹CSV通常按0.05 s输出并保留初末、切换和极值行；路径最小电压、最大冰量仍在每个内部积分步统计。进一步使用464个网格、0.0015625 s核验，恒流启动时间变化{dt_diff:.6f} s，最大冰体积分数变化{ice_rel:.3f}%。冰量比启动时间更敏感，报告六位小数便于复核，不表示六位有效物理精度。

模型独立核验{len(checks)}项、最终CSV独立核验{len(export_checks)}项，共{len(checks)+len(export_checks)}项全部通过。加速内核与已有问题一的同温度输运、电化学和物性逐项对照误差在约10⁻¹³量级；完整七节点与对称降维热解一致。最终CSV核验另覆盖解析电荷、路径极值、成功条件、五片导出对称性及最细网格临界两侧状态。正式恒流累计热量残差{num(by['constant'],'energy_balance_J_m2'):.3e} J/m²，水量残差{num(by['constant'],'water_balance_kg_m2'):.3e} kg/m²。上述守恒是所采用离散模型的收支闭合，不等于证明经验闭合在实物上准确。

![收敛性](../figures/10_时间空间离散收敛性.png)

## 5 来源与局限

几何与物性来自附件1。j0继承已有含双极板问题一标定，只有j0被拟合；−25 ℃留出验证已有电压RMSE约0.06077 V、温度RMSE约0.23226 K。校准文件与当前参考源码经换行符规范化后哈希一致。这里的温度集中化是第二问MD的降阶假设，并未用附件2重新辨识热网络。

附件2的总电流与电流密度不能同时按25 cm²解释；本次沿用旧标定使用的电流密度列，完整差异见`附件2电流单位核验.csv`。相变参数原始单位是无量纲权重，转成时间率依赖参考时间1 s；冻结速率、膜不可冻结水和边界位置均做敏感性检查，详见`sensitivity.csv`，不能把计算边界视为不依赖这些假设的实验结论。

![参数敏感性](../figures/11_参数与边界假设敏感性.png)

完整MD修正见[推导核验](MD推导核验.md)。原题、原MD和附件保存在inputs；所有新代码、工作数据和图表位于本文件夹，不改动原始模型。
'''
(OUT/'问题2_结果报告.md').write_text(report,encoding='utf-8')

algorithm=r'''# 问题2 算法模型与代码说明

## 1 控制与状态

电流密度策略单位为A/cm²，物理内核电流密度为 j_SI=10⁴j A/m²。五片串联共享电流及单位面积电荷 q(t)=∫j dt，**不将电荷乘5**。五片反应热在整堆预算分别相加。

每片有水蒸气mv、液水及膜未冻结水ml、固态冰mi、氢气库存nh、氧气库存no的一维空间数组。各片平均温度由热网络决定；片内不另解重复的热方程。初始膜含水量λ=3，外部干气，孔隙初始液水与冰为0，所有温度与环境均为T0。

## 2 水冰气体电化学子模型

保留参考单片模型的有限体积后向欧拉格式：每界面的流出等于另一控制体流入。液水迁移使用Darcy毛细等效扩散；膜水扩散加上风电渗拖曳；两侧膜—CL交换成对转移。阴极CL产水面速率为

$$\dot m_{prod}=\frac{M_w10^4j}{2F}.$$

依次处理凝结、蒸发、凝华、升华、冻结和融化；实际转移量受供体库存限制，且同一转移同时用于水量和潜热。冻结率采用 k_f max[(273.15−T)/273.15,0]，膜仅冻结超过λ_nf=3的自由水。孔隙冰不迁移。

$$\varepsilon_g=\varepsilon_0-m_l/\rho_l-m_i/\rho_i,\quad
D_{O_2,eff}=D_{O_2,ref}(T/298.15)^{1.5}\varepsilon_g^{1.5}.$$

催化有效面积因子为阴极CL内(1−s_ice)^3.5的加权平均。氢氧输运源项分别为−j_SI/(2FL_aCL)与−j_SI/(4FL_cCL)，在各自CL分布；外边界浓度由给定压力、气体组成和该片温度决定。

$$V_k=E_{rev,k}-\eta_{act,k}-\eta_{ohm,k}-\eta_{con,k},$$
$$\eta_{con,k}=-\beta_k\frac{RT_k}{4F}\ln(1-j_{SI}/j_{lim,k}),\quad
\beta=(10,1,1,1,10).$$

Erev采用Nernst关系，活化采用原模型asinh形式，膜电导采用Springer关系并计入膜冰。j_lim由实际氧浓度和阴极有效扩散串联阻力确定。数值对数保护不能解除物理限制：若j/j_lim≥1、有效气孔率为负、膜电导非正或物种库存为负，则标为物理失效，不把截断后的电压作为可行证据。

实现位于`fast_cell.py`，参考源文件保存在`inputs/model_q1_reference.py`。加速仅替换数值执行和三对角求解实现，没有重新拟合相变参数。

## 3 七节点热网络

节点顺序为端板EL、单片1至5、端板ER。单片面热容为MEA片相分率加权积分与两块双极板面热容6066.72 J/(m²·K)之和，端板各39500 J/(m²·K)。各片相变后重算热容和MEA热阻。

$$R_{MEA,k}=\sum_i\Delta x_i/k_i,\quad
g_{k,k+1}=\left[\tfrac12R_{MEA,k}+0.004/95+\tfrac12R_{MEA,k+1}\right]^{-1},$$
$$g_{E,k}=\left[\tfrac12R_{MEA,k}+0.002/95+0.005/15\right]^{-1}.$$

初始gc≈350.56 W/(m²·K)、gE≈568.30 W/(m²·K)，与MD近似值350和568一致。干阴极混合气体导热系数沿用原模型0.02373 W/(m·K)，故与MD采用纯氮0.0235得到的末位值略异。

$$C_k\dot T_k=10^4j(1.48-V_k)+\dot q_{pc,k}
+\sum_lg_{kl}(T_l-T_k)-h_k(T_k-T_{amb}).$$

主边界h1=h5=40，其余hk=0；端板方程CE·dTE/dt=gE(Tend−TE)。片间热流成对抵消；端板不再次对流。相变热由实际质量转移和潜热得出，电化学热用经β修正的实际V，不重复添加欧姆或活化热。

温度隐式迭代为(C/Δt+G)T_new=C·T_old/Δt+b+qgen(T_new)。每步最大温度迭代差低于10⁻⁹ K停止，超过10⁻⁶ K视为求解异常。对称状态1=5、2=4、EL=ER降为四温度节点，中心节点对次端节点的导热为2gc(T2−T3)。预算权重显式保留两侧电池及端板，独立测试与完整七节点方程对照。

## 4 成功和失败

成功需要同时满足min(T1…T5)>0 ℃、max ε_ice<0.99、历史上每片电压均≥0.30 V，且0≤j≤0.5、q≤20。时间为这些条件第一次同时成立的时刻，数值定位温度目标10⁻⁷ ℃以表达严格不等号。初始载入、每步末、阶梯切换左右侧均检查电压。电荷解析积分，在预算耗尽的最后一步缩短时间步而不擅自改变控制曲线。

状态码success、charge_exhausted、voltage_limit、physical_invalid、time_limit分别表示成功、电荷耗尽、失压、物理失效和600 s搜索时间上限。失败的end_time_s是终止时间，不能当作启动时间。

## 5 控制向量参数化和搜索

恒流j=jc，jc∈[0,0.5]；线性升载j=min(at,jp)，用(jp,tp)搜索且a=jp/tp；N段阶梯有N档独立电流和N−1个正持续时长，切换时间为持续时长的累计值。各档不强制严格不同。基准N=3，并检查N=2和4。

主恒流采用26点网格及有界标量优化。升载和阶梯采用差分进化种子17、43，种群因子6、最多24代，再Powell精修；温度逐点搜索使用种子89、种群因子4、最多9代和热启动满载候选。完整历史保留，初次执行的非零搜索下界为0.02，最终代码已允许0，另有零档电流的角点核验。不存在靠反复调整闭合参数制造更好解的步骤。

可行目标是启动时间；失败评分为1000+100 max(−Tend,0)+10000 max(0.30−Vmin,0)，物理失效再加10000。该评分只帮助搜索，最终可行性仍由硬约束逐项判断。常流包含在阶梯类中，所以下界候选必须始终加入，防止优化器给出反而更差的阶梯解。

升载的主有限范围tp∈[0.2,120] s，tp下界属于数值约定，不是题给限制。以更短tp算极限序列，明确区分有限参数解与趋近恒流的边界。无全局最优证书。

## 6 温度搜索和核验

固定同一套标定参数，对多个初温分别搜索；在[−25,−5] ℃内以固定优化曲线作12次二分，分辨率20/4096≈0.004883 ℃。在分界两侧用464网格和0.0015625 s复算。最低温度仅在当前模型、闭合与所搜索控制空间内解释。

输出能量残差ΣC_newΔT−Qgen−Qphase+Qloss，水量残差Mstored−Minitial−Mproduced+Mout；全局均按电池镜像权重相加。纯对称性检查不能独立证明代码正确，所以另保留完整七节点热求解对照和旧单片逐过程对照。

正式结果网格每层[64,24,48,32,64]，合计232单元；更细核验每层翻倍。正式Δt=0.003125 s，更细Δt=0.0015625 s。报告必须同时说明数值误差与模型不确定性。
'''
(OUT/'算法模型与代码说明.md').write_text(algorithm,encoding='utf-8')

readme=f'''# 问题2求解交付

已完成第二问两小问。主结果：−10 ℃下0.5 A/cm²恒流约{num(by['constant'],'end_time_s'):.2f} s成功，电荷{num(by['constant'],'charge_C_cm2'):.4f} C/cm²；最低初温约−12.8 ℃，端部1和5在更冷时因电荷耗尽仍未过0 ℃而失败。

- [完整结果报告](reports/问题2_结果报告.md)
- [表3 CSV](data/表3_不同策略最优启动结果.csv)
- [第二小问初温区间 CSV](data/第二小问_最低初温区间.csv)
- [第二小问成功与失败工况 CSV](data/第二小问_临界与更冷工况.csv)
- [算法模型与代码说明](reports/算法模型与代码说明.md)
- [MD推导核验](reports/MD推导核验.md)
- [图表目录](figures)
- [工作数据字段说明](reports/数据字段说明.md)

线性升载主表a=2.5只是在tp≥0.2 s的有限范围内最优；原题未设斜率上限，其数值极限趋近恒流。阶梯最优三档相等，不能预先要求三种曲线一定不同。

## 复现

Python 3.12。首次安装后运行，建议在本结果文件夹中执行：

```powershell
python -m pip install -r code/requirements.txt
python code/run_question2.py
python code/finalize_results.py
python code/verify_model.py
python code/verify_exports.py
python code/plot_results.py
python code/build_report.py
```

`run_question2.py --reuse-search`仅跳过随机搜索，不能作为新增优化证据；完整复现请不加该选项。Numba首次运行需要编译，后续会复用本地缓存。`source_audit.py`和`inspect_sources.py`用于本机原始来源整理，常规复现无需重跑；输入原件已经保存于inputs。

正式数据为232空间单元/片、Δt=0.003125 s，另用464单元/片、Δt=0.0015625 s核验。CSV使用UTF-8 BOM，便于Excel打开。figures提供PNG和SVG，SVG为可缩放矢量图。优化历史与主数据可追溯；没有外部试验直接验证本题预测的冰量和临界温度。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')

fields='''# 工作数据字段说明

CSV编码均为UTF-8 BOM。所有时间单位s；温度列*_C为℃；电流密度j_A_cm2为A/cm²，内部jlim_A_m2为A/m²，比较时须换算；charge_C_cm2为单位面积串联电荷，不乘5。

## 数据文件

- `表3_不同策略最优启动结果.csv`：中文主结果表，包含题目全部要求列及两种冰量补充。
- `strategy_summary.csv`：正式高精度的英文机器可读汇总。所有极值统计覆盖每个内部积分步。
- `trajectory_*.csv`：每个方案的时间轨迹，通常输出间隔0.05 s，额外保留初末、切换与主要极值行。临界成功/失败及−14 ℃诊断也各有独立文件。
- `cells_*.csv`：五片显式长表，cell=1…5。对称电池共享物理结果，4与2、5与1完全镜像。
- `fields_terminal_*.csv`：各工况终止时，五片各层网格的水蒸气、液水、冰密度及冰体积分数。
- `optimization_trace.csv`：逐次参数评估记录，含成功/失败、评分、最大电流、全程最低电压及终温。objectives中的惩罚评分不是物理量。
- `temperature_search.csv`：温度逐点重优化，采用独立标注的较粗离散设置，不应与正式高精度主表末位混用。
- `temperature_bisection.csv`、`第二小问_最低初温区间.csv`：正式网格的二分轨迹及最终区间。
- `convergence.csv`：固定控制参数下时间和空间加密结果。
- `sensitivity.csv`：相同较细设置下物性、热边界及冻结率改变的条件预测，并非置信区间。
- `ramp_slope_limit.csv`：平台到达时间趋零的极限检验，标定值固定。
- `independent_verification.csv`：与原问题一内核及完整七节点热解的独立核验。
- `最终CSV独立核验.csv`：导出数据与解析电荷、汇总极值、路径约束和细网格临界状态的一致性核验。
- `source_hashes.json`与inputs：原件和代码来源校验；所有数值结果的主工作表均另有CSV，不依赖JSON才能读取。

## 主要字段

`end_time_s`：成功时为启动时间，失败时仅为终止时间。`status`：success成功，charge_exhausted电荷耗尽，voltage_limit失压，physical_invalid物理域失效，time_limit达到600 s上限。

`failure_cell`：直接触发失压或物理失效时的代表电池编号；0表示未以该类单片硬约束终止，并不表示没有热启动瓶颈。电荷耗尽工况应结合终温判断，当前临界失败的热瓶颈是第1、5片。

`T1_C,T2_C,T3_C,TEP_C`：端片1=5、次端片2=4、中片3和端板温度。`cellk_V`为单片电压；`eta_act/eta_ohm/eta_con`为三类损失，浓差已包含端部乘数10。`j_over_jlim`是无量纲比值，不能被对数保护截断伪造成可行。

`ice_bulk`：MEA全部网格最大mi/920，包含膜冰；`pore_ice_bulk`：只对多孔层取最大mi/920；`mem_ice_bulk`：膜区最大值；`pore_ice_saturation`：多孔层最大mi/(920 ε0)；它们不是同一指标。`gas_porosity_min`为多孔层剩余气相孔隙率的最小值。

`heat_gen/phase/loss/sensible_J_m2`：五片及两端板总预算，除以共同截面积，非单片平均。乘0.0025 m²可得整堆焦耳数。`heat_sensible`是逐步ΣC_newΔT而非终末CT之差。`energy_balance`=显热−电化学热−相变热+散热。`water_balance`=存储−初始−产水+排出。流出边界只有水蒸气，液水按原模型封闭边界处理。

`grid_scale`：基础29个输运单元的倍率，与七个温度节点数量无关。`dt_s`为内部最大积分步，事件附近更小。
'''
(OUT/'数据字段说明.md').write_text(fields,encoding='utf-8')

# Simple offline preview: readable results, links and native PNG charts.
headers=['策略','参数','启动 / s','电荷 / C·cm⁻²','峰值电流','最低电压 / V','最大冰分数','结果']
htmltable='<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'
for row in result_rows:htmltable+='<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>'
htmltable+='</tbody></table>'
figs=sorted((ROOT/'figures').glob('*.png'))
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>问题2计算结果</title>
<style>body{font-family:'Microsoft YaHei',sans-serif;max-width:1200px;margin:40px auto;padding:0 24px;color:#182536;line-height:1.7}h1,h2{font-weight:600}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #ddd;padding:10px;text-align:left}th{background:#edf2f7}img{max-width:100%;margin:20px 0}a{color:#176499}p{max-width:1000px}</style>
<h1>问题2 电堆自冷启动优化结果</h1>'''+f'<p>最低初温约−12.8 ℃；数值分界({cold:.6f}, {warm:.6f}] ℃。端部第1、5片为瓶颈。</p>'+htmltable+'''<p>线性升载行仅对应tp≥0.2 s的有限搜索范围，题目没有斜率上限；继续提高斜率时趋近恒流。三档相等时阶梯退化为恒流。冰体积分数包含膜冰。</p>
<p><a href="问题2_结果报告.md">详细结果报告</a> · <a href="算法模型与代码说明.md">算法模型</a> · <a href="../data/表3_不同策略最优启动结果.csv">表3 CSV</a></p>'''
for fig in figs:page+=f'<h2>{html.escape(fig.stem)}</h2><img src="../figures/{html.escape(fig.name)}" alt="{html.escape(fig.stem)}">'
(OUT/'问题2_结果预览.html').write_text(page+'</html>',encoding='utf-8')
manifest=[]
for folder in ['code','data','figures','inputs','reports']:
    for p in sorted((ROOT/folder).glob('*')):
        if p.is_file():manifest.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'交付文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Reports built; manifest entries:',len(manifest))
