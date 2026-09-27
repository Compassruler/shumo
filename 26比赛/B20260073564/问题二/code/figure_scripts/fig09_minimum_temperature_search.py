"""图09：最低初始温度可行性搜索。"""
import numpy as np
import matplotlib.pyplot as plt
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, field, numeric, pick, read_table

FIGSIZE=(10.6,4.1)
MARKER_SIZE=3.0


def build_figure():
    rows=read_table('temperature_search.csv')
    tkey=pick(rows,'T0_C','ambient_C','temperature_C','initial_temperature_C','T_initial_C')
    group_key=pick(rows,'strategy','kind','loading_strategy')
    groups=list(dict.fromkeys(r[group_key] for r in rows)) if group_key else ['all']
    fig,axes=plt.subplots(1,2,figsize=FIGSIZE,layout='constrained')
    endkey=pick(rows,'min_end_temperature_C','end_temperature_C','Tend_C')
    for index,group in enumerate(groups):
        subset=[r for r in rows if not group_key or r[group_key]==group]
        success=np.array([field(r,'status','result')=='success' for r in subset])
        temperatures=numeric(subset,tkey); color=COLORS[index%len(COLORS)]
        name=NAMES.get(group,group if group!='all' else '计算工况')
        timekey=pick(subset,'end_time_s','startup_time_s','time_s')
        if timekey:
            times=numeric(subset,timekey)
            discrete_points(axes[0],temperatures[success],times[success],color,f'{name}：成功',MARKER_SIZE)
            if np.any(~success):
                discrete_points(axes[0],temperatures[~success],times[~success],COLORS[1],f'{name}：失败',MARKER_SIZE)
        if endkey:
            end=numeric(subset,endkey)
            discrete_points(axes[1],temperatures[success],end[success],color,f'{name}：成功',MARKER_SIZE)
            if np.any(~success):
                discrete_points(axes[1],temperatures[~success],end[~success],COLORS[1],f'{name}：失败',MARKER_SIZE)
    axis(axes[0],'启动 / 终止时间 / s','初始及环境温度 / °C')
    axis(axes[1],'终止时最低单电池温度 / °C','初始及环境温度 / °C')
    axes[1].axhline(0,color='#444444',ls='--',lw=1)
    axes[0].legend(frameon=False); axes[1].legend(frameon=False)
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'09_最低初温可行性搜索',args)
