"""图05：各单电池孔隙冰饱和度。"""
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, load_trajectories, numeric, strategy_panels

FIGURE_HEIGHT=3.8
MARKER_SIZE=2.0


def build_figure():
    trajectories=load_trajectories(); fig,axarr=strategy_panels(trajectories,FIGURE_HEIGHT)
    labels=['单电池 1 = 5','单电池 2 = 4','单电池 3']
    for ax,(kind,rows) in zip(axarr[0],trajectories.items()):
        t=numeric(rows,'time_s')
        for index in range(3):
            discrete_points(ax,t,numeric(rows,f'cell{index+1}_pore_ice_saturation'),
                            COLORS[index],labels[index],MARKER_SIZE)
        axis(ax,'孔隙冰饱和度'); ax.set_title(NAMES[kind])
        ax.set_ylim(bottom=0); ax.legend(frameon=False)
    return fig


if __name__ == '__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'05_孔隙冰饱和度',args)
