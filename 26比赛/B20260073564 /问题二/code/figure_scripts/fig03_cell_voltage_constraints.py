"""图03：各单电池电压及 0.30 V 安全约束。"""
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, load_trajectories, numeric, strategy_panels

FIGURE_HEIGHT = 3.8
MARKER_SIZE = 2.0
VOLTAGE_LIMIT = 0.30


def build_figure():
    trajectories=load_trajectories(); fig,axarr=strategy_panels(trajectories,FIGURE_HEIGHT)
    labels=['单电池 1 = 5','单电池 2 = 4','单电池 3']
    for ax,(kind,rows) in zip(axarr[0],trajectories.items()):
        t=numeric(rows,'time_s')
        for index in range(3):
            key=f'cell{index+1}_V'
            discrete_points(ax,t,numeric(rows,key),COLORS[index],labels[index],MARKER_SIZE)
        ax.axhline(VOLTAGE_LIMIT,color='#444444',lw=1,ls='--',label='安全下限 0.30 V')
        axis(ax,'单电池电压 / V'); ax.set_title(NAMES[kind]); ax.legend(frameon=False)
    return fig


if __name__ == '__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'03_各单电池电压与安全约束',args)
