"""Freeze supplied spreadsheet values and inherited model parameters as CSV."""
import bootstrap
from pathlib import Path
import csv,hashlib,shutil
import numpy as np
from openpyxl import load_workbook
import control_model as m

ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT.parent/'B题'/'氢燃料电池低温冷启动建模与控制策略研究  附件'
    out=ROOT/'inputs';out.mkdir(exist_ok=True)
    manifest=[]
    for name in ('附件1.xlsx','附件2.xlsx'):
        path=source/name
        wb=load_workbook(path,data_only=True,read_only=True)
        for sheet in wb:
            dest=out/f'{path.stem}_{sheet.title}.csv'
            with dest.open('w',newline='',encoding='utf-8-sig') as f:
                csv.writer(f).writerows(sheet.values)
        manifest.append([str(path),hashlib.sha256(path.read_bytes()).hexdigest(),'用户原始附件；只读取已存数值'])
    cfg=m.make_config(scale=2,j0=m.J0)
    st=m.initial_state(cfg,243.15);cap,res=m.properties(cfg,st)
    items=[('active_area',25,'cm2','题给'),('ambient_temperature',-30,'degC','题给'),
     ('initial_precooling_temperature',25,'degC','题给'),('N_cell',5,'1','题给'),
     ('q_max',1,'W/cm2','题给'),('h',40,'W/m2/K','题给'),('EP_capacity',39500,'J/m2/K','附件rho cp thickness'),
     ('BP_capacity',3033.36,'J/m2/K','1980*766*.002'),('BP_k',95,'W/m/K','附件1'),('EP_k',15,'W/m/K','附件1'),
     ('J0',m.J0,'A/m2','继承问题1/2/3标定值；本问未重新拟合'),('end_beta',10,'1','继承问题2/3端部浓差经验因子'),
     ('kf',1,'1/s','继承问题1/2/3相变参考情景'),('km',1,'1/s','继承问题1/2/3相变参考情景'),
     ('kcond',1,'1/s','继承问题1/2/3参考情景'),('kevap',1,'1/s','继承问题1/2/3参考情景'),
     ('kdep',1e-4,'1/s','继承问题1/2/3参考情景'),('ksub',1e-4,'1/s','继承问题1/2/3参考情景'),
     ('lambda_initial_nonfreezing',3,'1','继承膜初始含水量及非冻结水假设'),
     ('MEA_initial_capacity',cap,'J/m2/K','启动有效物性；含孔隙/气体/膜水'),
     ('MEA_initial_resistance',res,'m2 K/W','启动有效物性；含孔隙/气体/膜水'),
     ('G_cell_initial',1/(res+.002/95),'W/m2/K','由启动物性推得'),
     ('voltage_safe',.3,'V','题给式8'),('ice_critical',.99,'bulk fraction','题给式7'),
     ('load_ramp',.005,'A/cm2/s','题给'),('load_plateau',.3,'A/cm2','题给'),
     ('charge_budget',20,'C/cm2','按问题3建模继承解释'),('horizon',m.Q_TIME,'s','由电荷预算及加载积分推得'),
     ('hold',2,'s','问题4给出的保持逻辑；本次固定，不参与能耗优化'),
     ('dt',.025,'s','本次数值设置'),('control_period',.2,'s','本次采样周期'),
     ('mesh_scale',2,'1','每片58个质量控制体；7个热节点'),('post_stop_observation',60,'s','关热后后验观察，不计主表成本'),
     ('w_time',.005,'1','本次小权重；能耗主导'),('w_spread',.002,'1','本次小权重；能耗主导')]
    with (out/'parameter_inventory.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['parameter','value','unit','source_or_assumption']);w.writerows(items)
    with (out/'source_files.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['source','sha256','use']);w.writerows(manifest)
    with (out/'q3_constant_power.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['cell','q_W_cm2']);w.writerows(enumerate(m.CONSTANT,1))
    print('Frozen input CSV and parameter inventory')
if __name__=='__main__':main()
