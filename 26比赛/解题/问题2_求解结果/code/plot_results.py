"""Reproducible, CSV-only scientific figures for question 2.

Run with the bundled Python runtime.  No simulation is performed here.  Missing
optional datasets are skipped, and every exported figure is logged in a manifest.
"""
from pathlib import Path
import argparse
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.python_deps'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONT = Path('C:/Windows/Fonts/msyh.ttc')
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(FONT)).get_name()
else:
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams.update({
    'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 11,
    'legend.fontsize': 8.5, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'axes.unicode_minus': False, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.linewidth': .8, 'grid.alpha': .2,
    'grid.linewidth': .6, 'lines.linewidth': 1.6, 'svg.fonttype': 'none',
    'savefig.facecolor': 'white', 'figure.facecolor': 'white',
})

COLORS = ['#0072B2', '#D55E00', '#009E73', '#777777']
NAMES = {'constant': '恒流加载', 'ramp': '线性斜坡加载', 'step': '阶梯加载'}
STATUS = {'success': '启动成功', 'charge_exhausted': '电荷耗尽',
          'voltage_limit': '触及电压下限', 'physical_invalid': '物理约束失效',
          'time_limit': '达到时间上限'}
MANIFEST = []


def read_table(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def numeric(rows, key):
    return np.asarray([float(row.get(key, '') or 'nan') for row in rows])


def pick(rows, *keys):
    return next((key for key in keys if rows and key in rows[0]), None)


def field(row, *keys, default=''):
    return next((row[k] for k in keys if k in row and row[k] != ''), default)


def axis(ax, ylabel, xlabel='时间 / s'):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    ax.tick_params(direction='out', length=3)


def save(fig, name, title, sources, output, note=''):
    fig.suptitle(title, fontsize=13)
    fig.savefig(output / f'{name}.png', dpi=220, bbox_inches='tight')
    fig.savefig(output / f'{name}.svg', bbox_inches='tight')
    plt.close(fig)
    MANIFEST.append({'figure': name, 'title': title, 'data_sources': ';'.join(sources),
                     'png': f'{name}.png', 'svg': f'{name}.svg', 'note': note})


def strategy_plots(data, output):
    trajectories = {}
    for kind in NAMES:
        filename = f'trajectory_{kind}.csv'
        rows = read_table(data / filename)
        if rows:
            trajectories[kind] = (rows, filename)
    if not trajectories:
        return
    sources = [item[1] for item in trajectories.values()]
    summary = read_table(data / 'strategy_summary.csv')
    status_by_kind = {field(r, 'strategy', 'kind', 'loading_strategy'): field(r, 'status') for r in summary}
    n = len(trajectories)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout='constrained')
    for i, (kind, (rows, _)) in enumerate(trajectories.items()):
        t = numeric(rows, 'time_s')
        axes[0].plot(t, numeric(rows, 'j_A_cm2'), color=COLORS[i], label=NAMES[kind])
        axes[1].plot(t, numeric(rows, 'charge_C_cm2'), color=COLORS[i], label=NAMES[kind])
    axis(axes[0], '电流密度 / (A/cm²)')
    axis(axes[1], '累计电荷量 / (C/cm²)')
    axes[1].axhline(20, ls='--', color='#444444', lw=1, label='电荷预算 20 C/cm²')
    for ax in axes:
        ax.legend(loc='best', frameon=False)
        ax.set_xlim(left=0)
    save(fig, '01_加载策略与累计电荷', '最优加载策略与电荷消耗', sources, output)

    def panels():
        return plt.subplots(1, n, figsize=(4.35*n, 3.8), squeeze=False, layout='constrained')

    fig, axarr = panels()
    for ax, (kind, (rows, _)) in zip(axarr[0], trajectories.items()):
        t = numeric(rows, 'time_s')
        for i, (key, label) in enumerate([('T1_C', '端部单电池 1 = 5'), ('T2_C', '次端部单电池 2 = 4'),
                                         ('T3_C', '中心单电池 3'), ('TEP_C', '端板')]):
            if key in rows[0]:
                ax.plot(t, numeric(rows, key), color=COLORS[i], ls='--' if i == 3 else '-', label=label)
        ax.axhline(0, color='#444444', lw=.9, ls=':')
        axis(ax, '温度 / °C')
        ax.set_title(NAMES[kind])
        ax.legend(frameon=False, loc='best')
    save(fig, '02_各单电池与端板温度', '轴向温度非均匀性', sources, output,
         '镜像对称：单电池 1=5、2=4；端板不计入五片电池启动判据。')

    fig, axarr = panels()
    for ax, (kind, (rows, _)) in zip(axarr[0], trajectories.items()):
        t = numeric(rows, 'time_s')
        for i in (1, 2, 3):
            key = f'cell{i}_V'
            if key in rows[0]:
                ax.plot(t, numeric(rows, key), color=COLORS[i-1], label=['单电池 1 = 5', '单电池 2 = 4', '单电池 3'][i-1])
        ax.axhline(.3, color='#444444', lw=1, ls='--', label='安全下限 0.30 V')
        axis(ax, '单电池电压 / V')
        ax.set_title(NAMES[kind])
        ax.legend(frameon=False, loc='best')
    save(fig, '03_各单电池电压与安全约束', '全过程单电池电压', sources, output,
         '保留 CSV 内阶梯切换时刻左右极限；未在可视化阶段重新采样或平滑。')

    fig, axarr = panels()
    for ax, (kind, (rows, _)) in zip(axarr[0], trajectories.items()):
        t = numeric(rows, 'time_s')
        for i in (1, 2, 3):
            key = f'cell{i}_ice_bulk'
            if key in rows[0]:
                ax.plot(t, numeric(rows, key), color=COLORS[i-1], label=['单电池 1 = 5', '单电池 2 = 4', '单电池 3'][i-1])
        axis(ax, '冰体积分数（总体积基准）')
        ax.set_title(NAMES[kind])
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, loc='best')
    save(fig, '04_总体积基准冰体积分数', '总体积基准冰体积分数', sources, output,
         '总体积基准 ice_bulk 与孔隙冰饱和度分开呈现，禁止混作同一指标。')

    fig, axarr = panels()
    for ax, (kind, (rows, _)) in zip(axarr[0], trajectories.items()):
        t = numeric(rows, 'time_s')
        for i in (1, 2, 3):
            key = f'cell{i}_pore_ice_saturation'
            if key in rows[0]:
                ax.plot(t, numeric(rows, key), color=COLORS[i-1], label=['单电池 1 = 5', '单电池 2 = 4', '单电池 3'][i-1])
        axis(ax, '孔隙冰饱和度')
        ax.set_title(NAMES[kind])
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, loc='best')
    save(fig, '05_孔隙冰饱和度', '孔隙内冰占比与堵塞风险', sources, output,
         '孔隙冰饱和度不是题目要求汇总的总体积基准最大冰体积分数。')

    fig, axes = plt.subplots(2, n, figsize=(4.35*n, 6), squeeze=False, layout='constrained',
                              gridspec_kw={'height_ratios': [2.3, 1]})
    energy_fields = [('heat_gen_J_m2', '电化学产热', COLORS[0]),
                     ('heat_phase_J_m2', '净相变热', COLORS[1]),
                     ('heat_loss_J_m2', '向环境散热', COLORS[3]),
                     ('heat_sensible_J_m2', '总显热增量', COLORS[2])]
    for column, (kind, (rows, _)) in enumerate(trajectories.items()):
        t = numeric(rows, 'time_s')
        for key, label, color in energy_fields:
            if key in rows[0]:
                axes[0, column].plot(t, numeric(rows, key)/1000, label=label, color=color)
        axis(axes[0, column], '累计热量 / (kJ/m²)')
        axes[0, column].set_title(NAMES[kind])
        axes[0, column].legend(frameon=False, loc='best')
        key = 'energy_balance_J_m2'
        if key in rows[0]:
            axes[1, column].plot(t, numeric(rows, key), color='#555555')
            axes[1, column].ticklabel_format(axis='y', style='sci', scilimits=(-2, 3))
        axes[1, column].axhline(0, color='#888888', lw=.8)
        axis(axes[1, column], '守恒残差 / (J/m²)')
    save(fig, '06_全局热预算与能量守恒', '五片单电池与两块端板的全局热预算', sources, output,
         '单位为几何截面积归一化热量；Q显热−Q电化学−Q相变+Q散热=残差。')


def critical_plots(data, output):
    cases = []
    for key, label in [('success', '临界成功侧'), ('failure', '临界失败侧')]:
        filename = f'trajectory_critical_{key}.csv'
        rows = read_table(data / filename)
        if rows:
            cases.append((label, rows, filename))
    if not cases:
        return
    n = len(cases)
    sources = [case[2] for case in cases]
    fig, axes = plt.subplots(2, n, figsize=(5*n, 6.8), squeeze=False, layout='constrained')
    for column, (label, rows, _) in enumerate(cases):
        t = numeric(rows, 'time_s')
        temp0 = numeric(rows, 'T1_C')[0]
        for i in (1, 2, 3):
            name = ['单电池 1 = 5', '单电池 2 = 4', '单电池 3'][i-1]
            axes[0, column].plot(t, numeric(rows, f'T{i}_C'), color=COLORS[i-1], label=name)
            axes[1, column].plot(t, numeric(rows, f'cell{i}_V'), color=COLORS[i-1], label=name)
        axes[0, column].axhline(0, color='#444444', lw=1, ls='--')
        axes[1, column].axhline(.3, color='#444444', lw=1, ls='--', label='安全下限 0.30 V')
        axes[0, column].set_title(f'{label}：初温 {temp0:.4f} °C')
        axis(axes[0, column], '温度 / °C')
        axis(axes[1, column], '单电池电压 / V')
        for row in (0, 1):
            axes[row, column].legend(frameon=False, loc='best')
    save(fig, '07_最低启动温度两侧轨迹', '临界初温两侧的温度与电压', sources, output,
         '成功或失败侧按对应输入文件命名，不在图表脚本内重新判定。')

    fig, axes = plt.subplots(2, n, figsize=(5*n, 6.8), squeeze=False, layout='constrained')
    for column, (label, rows, _) in enumerate(cases):
        t = numeric(rows, 'time_s')
        for row_index, cell in enumerate([1, 3]):
            ax = axes[row_index, column]
            for field_name, legend, color in [('eta_act', '活化损失', COLORS[0]),
                                              ('eta_ohm', '欧姆损失', COLORS[1]),
                                              ('eta_con', '浓差损失', COLORS[2])]:
                key = f'cell{cell}_{field_name}'
                if key in rows[0]:
                    ax.plot(t, numeric(rows, key), label=legend, color=color)
            axis(ax, '电压损失 / V')
            ax.set_title(f'{label} · ' + ('端部单电池' if cell == 1 else '中心单电池'))
            ax.legend(frameon=False, loc='best')
    save(fig, '08_临界启动电压损失分解', '临界冷启动的电压损失构成', sources, output)


def temperature_plot(data, output):
    filename = 'temperature_search.csv'
    rows = read_table(data / filename)
    tk = pick(rows, 'T0_C', 'ambient_C', 'temperature_C', 'initial_temperature_C', 'T_initial_C')
    if not tk:
        return
    group_key = pick(rows, 'strategy', 'kind', 'loading_strategy')
    groups = list(dict.fromkeys(r[group_key] for r in rows)) if group_key else ['all']
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.1), layout='constrained')
    for index, group in enumerate(groups):
        subset = [r for r in rows if not group_key or r[group_key] == group]
        success = np.array([field(r, 'status', 'result') == 'success' for r in subset])
        temperatures = numeric(subset, tk)
        timekey = pick(subset, 'end_time_s', 'startup_time_s', 'time_s')
        endkey = pick(subset, 'min_end_temperature_C', 'end_temperature_C', 'Tend_C')
        name = NAMES.get(group, group if group != 'all' else '计算工况')
        color = COLORS[index % len(COLORS)]
        if timekey:
            times = numeric(subset, timekey)
            axes[0].scatter(temperatures[success], times[success], color=color, s=25, label=f'{name}：成功')
            if np.any(~success):
                axes[0].scatter(temperatures[~success], times[~success], color=color, marker='x', s=30, label=f'{name}：失败终止')
        if endkey:
            axes[1].scatter(temperatures[success], numeric(subset, endkey)[success], color=color, s=25)
            axes[1].scatter(temperatures[~success], numeric(subset, endkey)[~success], color=color, marker='x', s=30)
        else:
            axes[1].scatter(temperatures, success.astype(int), color=color, s=25, label=name)
    axis(axes[0], '启动 / 终止时间 / s', '初始及环境温度 / °C')
    axis(axes[1], '终止时最低单电池温度 / °C' if endkey else '启动可行性', '初始及环境温度 / °C')
    if endkey:
        axes[1].axhline(0, color='#444444', ls='--', lw=1)
    else:
        axes[1].set_yticks([0, 1], ['失败', '成功'])
        axes[1].set_ylim(-.15, 1.15)
    axes[0].legend(frameon=False, loc='best')
    save(fig, '09_最低初温可行性搜索', '最低启动初温的数值搜索', [filename], output,
         '成功用圆点，失败用叉号；失败工况横坐标对应初温，纵坐标为终止时间而非启动时间。')


def convergence_plot(data, output):
    filename = 'convergence.csv'
    rows = read_table(data / filename)
    rows = [row for row in rows if row.get('strategy') == 'constant']
    xkey = pick(rows, 'dt_s', 'dt', 'time_step_s', 'timestep_s')
    if not xkey:
        return
    group_keys = [k for k in ['strategy', 'kind', 'scale', 'mesh_scale', 'mesh_factor', 'grid_scale'] if k in rows[0]]
    groups = list(dict.fromkeys(tuple(r[k] for k in group_keys) for r in rows))
    ykeys = [pick(rows, 'end_time_s', 'startup_time_s'), pick(rows, 'min_voltage_V'), pick(rows, 'max_ice_bulk')]
    metrics = [(k, label) for k, label in zip(ykeys, ['启动 / 终止时间 / s', '最低电压 / V', '最大冰体积分数']) if k]
    if not metrics:
        return
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.1*len(metrics), 3.9), squeeze=False, layout='constrained')
    for index, group in enumerate(groups):
        subset = [r for r in rows if tuple(r[k] for k in group_keys) == group]
        subset = sorted(subset, key=lambda r: float(r[xkey]))
        parts = []
        for key, val in zip(group_keys, group):
            parts.append(NAMES.get(val, val) if key in ['strategy', 'kind'] else f'空间倍率 {val}')
        label = '，'.join(parts) if parts else '数值结果'
        for ax, (metric, ylabel) in zip(axes[0], metrics):
            ax.plot(numeric(subset, xkey), numeric(subset, metric), marker='o', ms=4,
                    color=COLORS[index % 4], ls=['-', '--', ':', '-.'][index // 4 % 4], label=label)
            axis(ax, ylabel, '时间步长 / s')
            ax.set_xscale('log')
            ax.ticklabel_format(axis='y', style='plain', useOffset=False)
    axes[0, 0].legend(frameon=False, loc='best')
    save(fig, '10_时间空间离散收敛性', '恒流最优方案的时间与空间离散收敛性', [filename], output,
         '仅对横坐标步长排序连接；未改变任何数值。')


def sensitivity_plot(data, output):
    filename = 'sensitivity.csv'
    rows = read_table(data / filename)
    if not rows:
        return
    labelkey = pick(rows, 'case', 'scenario', 'label', 'parameter', 'name', 'parameter_name')
    timekey = pick(rows, 'end_time_s', 'startup_time_s')
    if not labelkey or not timekey:
        return
    valuekey = pick(rows, 'value', 'factor', 'multiplier', 'parameter_value')
    labels = [r[labelkey] + (f" = {r[valuekey]}" if valuekey and r[valuekey] else '') for r in rows]
    names={'baseline':'基准', 'intercell_conductance_0.8':'片间导度 ×0.8',
           'intercell_conductance_1.2':'片间导度 ×1.2','endplate_coupling_0.8':'端板耦合导度 ×0.8',
           'endplate_coupling_1.2':'端板耦合导度 ×1.2','endplate_capacity_0.8':'端板热容 ×0.8',
           'endplate_capacity_1.2':'端板热容 ×1.2','convection_on_endplate':'对流置于端板',
           'end_beta_1':'端部浓差系数 =1','fixed_dry_conductance':'固定初始干态导度',
           'freezing_rate_0.1':'冻结速率 ×0.1','freezing_rate_10.0':'冻结速率 ×10'}
    labels = [names.get(str(label),str(label).replace('_',' ')) for label in labels]
    colors = [COLORS[0] if field(r, 'status', default='success') == 'success' else COLORS[1] for r in rows]
    metrics = [(timekey, '启动 / 终止时间 / s')]
    if 'min_voltage_V' in rows[0]:
        metrics.append(('min_voltage_V', '最低电压 / V'))
    fig, axes = plt.subplots(1, len(metrics), figsize=(6.2*len(metrics), max(3.8, .37*len(rows)+1.0)), squeeze=False, layout='constrained', sharey=True)
    pos = np.arange(len(rows))
    for ax, (key, label) in zip(axes[0], metrics):
        vals = numeric(rows, key)
        ax.barh(pos, vals, color=colors, height=.65, alpha=.88)
        ax.set_yticks(pos, labels)
        axis(ax, '', label)
        ax.grid(axis='y', visible=False)
        if key == 'min_voltage_V':
            ax.axvline(.3, color='#444444', ls='--', lw=1)
        ax.margins(x=.14)
        for y, value in zip(pos, vals):
            if np.isfinite(value):
                ax.annotate(f'{value:.3f}', (value, y), xytext=(4, 0), textcoords='offset points', va='center', fontsize=8)
    axes[0, 0].invert_yaxis()
    save(fig, '11_参数与边界假设敏感性', '参数与边界假设敏感性（蓝：成功；橙：失败）', [filename], output,
         '保留输入 CSV 工况顺序；失败工况显示终止时间。')


def ramp_limit_plot(data, output):
    filename='ramp_slope_limit.csv'
    rows=read_table(data/filename)
    if not rows:return
    rows=sorted(rows,key=lambda r:float(r['plateau_time_s']))
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
    t=numeric(rows,'plateau_time_s')
    for ax,key,label in zip(axes,['end_time_s','charge_C_cm2'],['启动时间 / s','累计电荷量 / (C/cm²)']):
        ax.plot(t,numeric(rows,key),color=COLORS[0],marker='o',ms=4)
        ax.axvline(.2,color=COLORS[1],ls='--',lw=1,label='主表有限搜索下界 0.2 s')
        ax.set_xscale('log');axis(ax,label,'达到 0.5 A/cm² 平台的时间 / s')
        ax.legend(frameon=False)
    save(fig,'12_线性升载斜率极限','升载时间趋零时的性能极限',[filename],output,
         '同一离散设置下比较不同升载时间；0.2s为数值搜索约定，不是题给斜率限制。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--output', type=Path, default=ROOT / 'figures')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    strategy_plots(args.data, args.output)
    critical_plots(args.data, args.output)
    temperature_plot(args.data, args.output)
    convergence_plot(args.data, args.output)
    sensitivity_plot(args.data, args.output)
    ramp_limit_plot(args.data, args.output)
    with (args.output / 'figure_manifest.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['figure', 'title', 'data_sources', 'png', 'svg', 'note'])
        writer.writeheader()
        writer.writerows(MANIFEST)
    print(json.dumps({'figures_created': len(MANIFEST), 'directory': str(args.output),
                      'names': [m['figure'] for m in MANIFEST]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
