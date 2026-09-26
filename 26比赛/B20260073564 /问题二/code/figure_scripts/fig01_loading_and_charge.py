"""图01：三种最优加载策略及其累计电荷消耗。"""
import matplotlib.pyplot as plt
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, load_trajectories, numeric

# ===== 常用调节区 =====
FIGSIZE = (10, 3.8)
MARKER_SIZE = 2.0
CHARGE_BUDGET = 20.0


def build_figure():
    trajectories = load_trajectories()
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, layout='constrained')
    for index, (kind, rows) in enumerate(trajectories.items()):
        t, color = numeric(rows, 'time_s'), COLORS[index]
        discrete_points(axes[0], t, numeric(rows, 'j_A_cm2'), color,
                        NAMES[kind], MARKER_SIZE)
        discrete_points(axes[1], t, numeric(rows, 'charge_C_cm2'), color,
                        NAMES[kind], MARKER_SIZE)
    axis(axes[0], '电流密度 / (A/cm²)')
    axis(axes[1], '累计电荷量 / (C/cm²)')
    axes[1].axhline(CHARGE_BUDGET, ls='--', color='#444444', lw=1,
                    label='电荷预算 20 C/cm²')
    for ax in axes:
        ax.legend(loc='best', frameon=False); ax.set_xlim(left=0)
    return fig


if __name__ == '__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(), '01_加载策略与累计电荷', args)
