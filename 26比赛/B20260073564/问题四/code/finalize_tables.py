"""Present all table-4 columns, per-cell costs, state counts and data dictionary."""
import bootstrap
from pathlib import Path
import numpy as np
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def save(df,name):pd.DataFrame(df).to_csv(DATA/name,index=False,encoding='utf-8-sig',float_format='%.12g')
def main():
    main=pd.read_csv(DATA/'main_results.csv');rows=[];states=[]
    guard=pd.read_csv(DATA/'guarded_results.csv')
    comparison=pd.read_csv(DATA/'optimized_constant_results.csv')
    all_results=pd.concat([main,guard,comparison],ignore_index=True)
    case_names={'case1':'工况1 完全冷却','case2':'工况2 预冷20min','case3':'工况3 预冷40min'}
    for _,r in all_results.iterrows():
        h=pd.read_csv(DATA/f'trajectory_{r["case"]}_{r["strategy"]}.csv')
        h=h[h.time_s<=r.stop_s+1e-7];dt=h.time_s.diff().fillna(0.)
        # State at the row time governs the following interval; power instead
        # describes the interval ending at that time.
        state_dt=(h.time_s.shift(-1)-h.time_s).fillna(0.)
        for k in range(1,6):
            q=h[f'cell{k}_q_W_cm2']
            rows.append(dict(case=r['case'],strategy=r.strategy,cell=k,energy_J=25*np.dot(q,dt),
                 average_power_W_cm2=25*np.dot(q,dt)/(25*r.stop_s) if r.stop_s>0 else 0,
                 peak_power_W_cm2=q.max(),heating_duration_s=dt[q>1e-10].sum()))
            for state in range(0,6):
                states.append(dict(case=r['case'],strategy=r.strategy,cell=k,state=state,
                                   duration_s=state_dt[h[f'cell{k}_state']==state].sum()))
    save(rows,'per_cell_heater_energy.csv');save(states,'controller_state_duration.csv')
    tables=[]
    primary=pd.concat([main[main.strategy=='constant_hold'],guard],ignore_index=True).sort_values(['case','strategy'])
    for _,r in primary.iterrows():
        tables.append({'工况':case_names[r['case']],'控制策略':'推荐留裕度动态反馈' if r.strategy=='guarded' else '问题3固定恒功率（相同测量保持）',
          '功率控制策略_W每cm2':'独立观测器+逐片前馈PI及风险覆盖；完整参数和轨迹见CSV' if r.strategy=='guarded' else '[1,1,0.624511558772,1,1]',
          '首次启动成功时间_s':r.first_success_s,'首次成功能耗_J':r.first_success_energy_J,
          '保持后关热时间_s':r.stop_s,'辅助加热总能耗_J':r.E_aux_J,
          '电堆最大温差_K':r.dTmax_K,'最低单片电压_V':r.min_voltage_V,'最大局部冰体积分数':r.max_ice_bulk,
          '首次成功累计电荷_C每cm2':r.charge_at_success_C_cm2,'启动结果':'成功' if r.feasible else '失败'})
    save(tables,'表4_问题四完整结果.csv')
    groups={'q_W_cm2':('W/cm2','该行时刻结束的前一区间内恒定加热功率；初始行0'),
      'V_V':('V','单片电压'),'ice_bulk':('1','单片内局部冰总体积分数最大值，含孔隙及膜'),
      'pore_ice_bulk':('1','多孔层局部冰总体积分数最大值'),'mem_ice_bulk':('1','膜层局部冰体积分数最大值'),
      'pore_ice_saturation':('1','冰体积/干孔体积最大值；非题给严重冰堵阈值口径'),
      'lambda':('1','膜含水量厚度均值'),'j_over_jlim':('1','电流/极限电流'),
      'gas_porosity':('1','多孔域最小可用气相体积分数'),'state':('code','该时刻更新并作用于后一区间：1安全增强 2低温升温不足 3跟踪维持 4接近成功渐缩 5关断；constant策略0'),
      'risk':('1','综合冰堵风险指标'),'rT_K_s':('K/s','二级滤波温升速率'),
      'rV_V_s':('V/s','二级滤波电压变化率'),'ice_est':('1','独立观测器冰先验加预测电压与测量电压创新；非真实冰反馈'),
      'observer_voltage_V':('V','独立观测器预测电压'),
      'observer_ice_bulk':('1','独立观测器冰先验；未加电压创新的原始估计'),
      'filtered_temperature_C':('degC','最近控制采样更新的低通测温；用于停机检测'),
      'filtered_voltage_V':('V','最近控制采样更新的低通测压；用于停机检测'),
      'sensor_temperature_C':('degC','最近一次控制采样的测量温度'),
      'sensor_voltage_V':('V','最近一次控制采样的测量电压')}
    dictionary=[]
    for col in m.HISTORY:
        if col.startswith('cell'):
            key=col.split('_',1)[1];unit,meaning=groups[key]
        elif col.startswith('observer_'):unit,meaning='degC','积分区间末、传感器校正前的独立观测器热节点预测；端板无直接测量'
        elif col.startswith('T'):unit,meaning='degC','真实模型热节点平均温度，EL/ER为端板；仅供仿真评价'
        elif col.endswith('_J'):unit,meaning='J','累计离散热量/能量；相变为净释热，散热取正'
        elif col.endswith('_kg'):unit,meaning='kg','累计水量或收支残差；inventory为瞬时总库存'
        elif col=='stopped':unit,meaning='0/1','该时刻是否已锁定永久关断；stop行功率仍记刚结束区间'
        elif col=='time_s':unit,meaning='s','电流加载开始后的时间，含独立关热后观察段'
        elif col=='charge_C_cm2':unit,meaning='C/cm2','题给电流曲线精确积分；后验段独立于启动预算'
        else:unit,meaning='A/cm2','题给斜坡/平台电流密度'
        dictionary.append(dict(column=col,unit=unit,meaning=meaning))
    save(dictionary,'trajectory_data_dictionary.csv')
    inventory=[]
    for folder in ('data','inputs'):
        for path in sorted((ROOT/folder).glob('*.csv')):
            df=pd.read_csv(path,encoding='utf-8-sig',header=None if path.name.startswith('附件') else 0)
            inventory.append(dict(file=str(path.relative_to(ROOT)),rows=len(df),columns=len(df.columns),bytes=path.stat().st_size))
    save(inventory,'csv_inventory.csv')
    print('Table 4, per-cell energy, controller states, data dictionary saved')
if __name__=='__main__':main()
