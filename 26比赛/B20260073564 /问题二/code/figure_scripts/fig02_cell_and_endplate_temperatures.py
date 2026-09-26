"""图02：三种策略下各单电池与端板温度。"""
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, load_trajectories, numeric, strategy_panels

# ===== 常用调节区 =====
FIGURE_HEIGHT = 3.8
MARKER_SIZE = 2.0


def build_figure():
    trajectories = load_trajectories()
    fig, axarr = strategy_panels(trajectories, FIGURE_HEIGHT)
    fields = [('T1_C','端部单电池 1 = 5'), ('T2_C','次端部单电池 2 = 4'),
              ('T3_C','中心单电池 3'), ('TEP_C','端板')]
    for ax, (kind, rows) in zip(axarr[0], trajectories.items()):
        t = numeric(rows, 'time_s')
        for index, (key, label) in enumerate(fields):
            if key in rows[0]:
                discrete_points(ax, t, numeric(rows,key), COLORS[index], label, MARKER_SIZE)
        ax.axhline(0, color='#444444', lw=.9, ls=':')
        axis(ax, '温度 / °C'); ax.set_title(NAMES[kind]); ax.legend(frameon=False)
    return fig


if __name__ == '__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(), '02_各单电池与端板温度', args)
