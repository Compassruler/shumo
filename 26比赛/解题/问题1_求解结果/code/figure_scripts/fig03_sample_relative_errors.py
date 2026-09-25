"""图03：各采样时刻的电压与温度相对误差。"""
import matplotlib.pyplot as plt
from common import COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.0)
ZERO_LINE_COLOR = '#8B929A'


def build_figure():
    data = read_cases()
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for col, temp in enumerate(['20', '25']):
        for row, (key, ylabel) in enumerate([
                ('V_rel_error_pct', '电压相对误差 / %'),
                ('T_rel_error_pct', '温度相对误差（摄氏口径）/ %')]):
            ax = axes[row, col]
            handles = []
            # 相对误差仅定义在实验采样时刻，因此画成离散实心圆，不连接。
            for model, label in [('main', '五层基线'), ('bp', '含双极板修订')]:
                d = data[f'{model}_minus{temp}']
                handles.append(discrete_points(ax, d['t_s'], d[key],
                                               COLORS[model], label))
            ax.axhline(0, color=ZERO_LINE_COLOR, linewidth=.7, zorder=0)
            panel(ax, f'({chr(97+row*2+col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, handles, ncol=2)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '03_sample_relative_errors', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91, wspace=.30, hspace=.40))
