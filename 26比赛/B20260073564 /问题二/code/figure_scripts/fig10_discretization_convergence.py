"""图10：恒流最优方案的时间与空间离散收敛性。"""
import matplotlib.pyplot as plt
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, numeric, pick, read_table

MARKER_SIZE=3.0


def build_figure():
    rows=[r for r in read_table('convergence.csv') if r.get('strategy')=='constant']
    xkey=pick(rows,'dt_s','dt','time_step_s','timestep_s')
    group_keys=[k for k in ['strategy','kind','scale','mesh_scale','mesh_factor','grid_scale'] if k in rows[0]]
    groups=list(dict.fromkeys(tuple(r[k] for k in group_keys) for r in rows))
    candidates=[(pick(rows,'end_time_s','startup_time_s'),'启动 / 终止时间 / s'),
                (pick(rows,'min_voltage_V'),'最低电压 / V'),
                (pick(rows,'max_ice_bulk'),'最大冰体积分数')]
    metrics=[item for item in candidates if item[0]]
    fig,axes=plt.subplots(1,len(metrics),figsize=(4.1*len(metrics),3.9),squeeze=False,layout='constrained')
    for index,group in enumerate(groups):
        subset=sorted([r for r in rows if tuple(r[k] for k in group_keys)==group],key=lambda r:float(r[xkey]))
        parts=[NAMES.get(v,v) if k in ['strategy','kind'] else f'空间倍率 {v}' for k,v in zip(group_keys,group)]
        label='，'.join(parts) if parts else '数值结果'
        for ax,(metric,ylabel) in zip(axes[0],metrics):
            discrete_points(ax,numeric(subset,xkey),numeric(subset,metric),COLORS[index%4],label,MARKER_SIZE)
            axis(ax,ylabel,'时间步长 / s'); ax.set_xscale('log')
            ax.ticklabel_format(axis='y',style='plain',useOffset=False)
    axes[0,0].legend(frameon=False)
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'10_时间空间离散收敛性',args)
