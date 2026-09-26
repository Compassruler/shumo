"""图04：总冰、孔隙冰、膜相冰体积分数与孔隙冰饱和度。"""
import numpy as np
import matplotlib.pyplot as plt
from common import CASES, COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.1)
RIGHT_AXIS_COLOR = COLORS['saturation']


def build_figure():
    data = read_cases()
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for index, (key, model, temp) in enumerate(CASES):
        d, ax = data[key], axes.flat[index]
        h1 = discrete_points(ax, d['t_s'], d['ice_max_bulk'], COLORS['main'], '最大总冰体积分数')
        h2 = discrete_points(ax, d['t_s'], d['ice_pore_max_bulk'], COLORS['pore'], '最大孔隙冰体积分数')
        h3 = discrete_points(ax, d['t_s'], d['ice_mem_max_bulk'], COLORS['membrane'], '最大膜相冰体积分数')
        # 饱和度使用独立右轴，避免与体积分数共用量级。
        right = ax.twinx()
        h4 = discrete_points(right, d['t_s'], d['s_ice_pore_max'], RIGHT_AXIS_COLOR,
                             '最大孔隙冰饱和度（右轴）')
        right.grid(False); right.spines['right'].set_visible(True)
        right.set_ylabel('孔隙冰饱和度', color=RIGHT_AXIS_COLOR)
        right.tick_params(axis='y', colors=RIGHT_AXIS_COLOR)
        right.set_ylim(0, max(1.08*np.nanmax(d['s_ice_pore_max']), 1e-10))
        panel(ax, f'({chr(97+index)}) {model} · {temp}', '冰体积分数', zero=True)
    shared_legend(fig, [h1, h2, h3, h4], ncol=2)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '04_总冰孔隙冰膜相冰体积分数与孔隙冰饱和度', args,
                    dict(left=.09, right=.96, bottom=.09, top=.885, wspace=.42, hspace=.40))
