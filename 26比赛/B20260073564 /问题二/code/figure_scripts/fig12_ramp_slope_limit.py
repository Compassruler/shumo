"""图12：线性升载时间趋零时的性能极限。"""
import matplotlib.pyplot as plt
from common import COLORS, axis, cli, configure_style, discrete_points, export_and_show, numeric, read_table

FIGSIZE=(10,3.8)
MARKER_SIZE=3.0


def build_figure():
    rows=sorted(read_table('ramp_slope_limit.csv'),key=lambda r:float(r['plateau_time_s']))
    fig,axes=plt.subplots(1,2,figsize=FIGSIZE,layout='constrained')
    t=numeric(rows,'plateau_time_s')
    for ax,key,label in zip(axes,['end_time_s','charge_C_cm2'],['启动时间 / s','累计电荷量 / (C/cm²)']):
        discrete_points(ax,t,numeric(rows,key),COLORS[0],label,MARKER_SIZE)
        ax.axvline(.2,color=COLORS[1],ls='--',lw=1,label='主表有限搜索下界 0.2 s')
        ax.set_xscale('log'); axis(ax,label,'达到 0.5 A/cm² 平台的时间 / s'); ax.legend(frameon=False)
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'12_线性升载斜率极限',args)
