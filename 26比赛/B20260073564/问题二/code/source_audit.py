"""Preserve supplied inputs and audit units/provenance without refitting."""
from pathlib import Path
import csv,json,hashlib,shutil
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
INPUTS=ROOT/'inputs';DATA=ROOT/'data';REPORTS=ROOT/'reports'
for p in (INPUTS,DATA,REPORTS):p.mkdir(exist_ok=True,parents=True)
source_md=BASE/'问题2_建模推导源文件.md'
sources=[source_md,BASE/'B题'/'氢燃料电池低温冷启动建模与控制策略研究.docx',
    BASE/'B题'/'氢燃料电池低温冷启动建模与控制策略研究  附件'/'附件1.xlsx',
    BASE/'B题'/'氢燃料电池低温冷启动建模与控制策略研究  附件'/'附件2.xlsx',
    BASE/'问题1_求解结果'/'data'/'calibration_bp.json',
    BASE/'问题1_求解结果'/'data'/'summary.json']
provenance=[]
for p in sources:
    dest=INPUTS/p.name
    if p == source_md or not dest.exists():shutil.copy2(p,dest)
    provenance.append({'file':p.name,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
old=BASE/'问题1_求解结果'/'code'/'model.py'
if not (INPUTS/'model_q1_reference.py').exists():shutil.copy2(old,INPUTS/'model_q1_reference.py')
raw=old.read_bytes();normalized=raw.replace(b'\r\n',b'\n')
cal=json.loads((INPUTS/'calibration_bp.json').read_text(encoding='utf-8'))
provenance.append({'file':'model_q1_reference.py','source':str(old),
    'sha256':hashlib.sha256(raw).hexdigest(),'LF_normalized_sha256':hashlib.sha256(normalized).hexdigest(),
    'calibration_code_matches_after_LF_normalization':hashlib.sha256(normalized).hexdigest()==cal['model_sha256']})
(DATA/'source_hashes.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')

def csvout(name,rows):
    with (DATA/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

wb=load_workbook(INPUTS/'附件2.xlsx',data_only=True,read_only=True)
audit=[]
for ws in wb:
    for rowno,row in enumerate(ws.values,1):
        if not isinstance(row[0],(int,float)) or len(row)<6:continue
        t,I,V,T,jc,jm=row[:6]
        audit.append({'sheet':ws.title,'excel_row':rowno,'time_s':t,'current_A':I,
            'provided_j_A_cm2':jc,'provided_j_A_m2':jm,'I_over_area25_A_cm2':I/25,
            'implied_area_cm2':I/jc if jc else '',
            'j_unit_conversion_error':jm-jc*1e4,'provided_I_minus_25j_A':I-25*jc,
            'used_in_inherited_calibration':bool(t<=35),
            'treatment':'沿用附件电流密度列与旧标定，不用总电流除以25替换密度'})
csvout('附件2电流单位核验.csv',audit)
params=[]
def par(name,value,unit,source,meaning):
    params.append({'parameter':name,'value':value,'unit':unit,'source':source,'treatment':meaning})
for name,value,unit,source,meaning in [
 ('A',25,'cm2','题面与附件1','串联电荷量只计一次；面积只用于总量换算'),
 ('j_max',.5,'A/cm2','问题2','全程硬约束'),('q_max',20,'C/cm2','问题2','未成功即预算耗尽为失败'),
 ('V_min',.30,'V','问题2与MD 2.7','全程每片路径约束'),('ice_max',.99,'1','问题2','总体积基准，不是孔隙冰饱和度'),
 ('j0_ref',cal['j0'],'A/m2','已有calibration_bp.json','继承含双极板版本，-20校准、-25留出'),
 ('k_freeze',1,'1/s','附件权重1与原问题1闭合','参考时间1s；孔隙冻结扩展为假设'),
 ('k_melt',1,'1/s','附件权重1与原问题1闭合','参考时间1s；孔隙融化扩展为假设'),
 ('k_cond/k_evap',1,'1/s','附件无量纲权重1','除以假定参考时间1s'),
 ('k_dep/k_sub',.0001,'1/s','附件权重1e-4与原问题1闭合','升华沿用反向对称闭合'),
 ('lambda_nf',3,'1','原问题1闭合','膜不可冻结水阈值，非独立测量'),
 ('L_BP',.002,'m','附件1','完整共享板与终端流场板均采用2 mm厚度'),
 ('plate_positions',6,'1','五MEA拓扑','四块内部共享BP+两块外侧终端流场板'),
 ('C_BP_single',3033.36,'J/m2/K','0.002*1980*766','一块完整板的面热容'),
 ('C_BP_end_node',4550.04,'J/m2/K','1.5*3033.36','端节点：一块终端板+半块内部共享板'),
 ('C_BP_middle_node',3033.36,'J/m2/K','2*0.5*3033.36','中间节点：左右各半块内部共享板'),
 ('C_BP_stack_total',18200.16,'J/m2/K','6*3033.36','总板热容守恒，不重复计数'),
 ('cell_pitch',.0023267,'m','L_MEA+L_BP','MEA中心间几何节距'),
 ('C_EP',39500,'J/m2/K','0.01*7900*500','每端单独温度节点'),
 ('h',40,'W/m2/K','题面与MD式2-17','主计算置于端部单片，外端板对流为敏感性'),
 ('beta_end',10,'1','附件1','只放大浓差项且回馈电化学产热'),
 ('beta_middle',1,'1','附件1','中间3片'),
 ('ramp_min_plateau_time',.2,'s','数值搜索约定，非题给硬件限制','另算0.1/0.05/0.02/0.01s考察无限斜率极限'),
 ('time_horizon',600,'s','数值搜索上限','超时只称搜索范围内未成功'),
 ('grid_scale',8,'1','数值选择','单片232水/气/冰网格；七温度节点'),
 ('time_step',.003125,'s','数值选择','加密复核至0.0015625s与464空间单元')]:par(name,value,unit,source,meaning)
csvout('参数来源与口径.csv',params)
print('Input audit complete; calibrated source code LF hash match:',provenance[-1]['calibration_code_matches_after_LF_normalization'])
