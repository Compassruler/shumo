"""图11：六个相变通道的累计转化水量。"""
import numpy as np
import matplotlib.pyplot as plt
from common import CASES, COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 4.8)
PHASES = {'cond':'凝结','evap':'蒸发','dep':'凝华','sub':'升华','frz':'冻结','mlt':'融化'}


def build_figure():
    data = read_cases()
    fig, axes = plt.subplots(2, 3, figsize=FIGSIZE)
    handles = []
    for index, (phase, title) in enumerate(PHASES.items()):
        ax, peak = axes.flat[index], 0
        for tag, model, temp in CASES:
            d = data[tag]; amount = d[f'phase_{phase}_kg_m2']*1e3
            peak = max(peak, float(np.max(amount)))
            line = discrete_points(ax, d['t_s'], amount, COLORS[tag.split('_')[0]],
                                   f'{model} · {temp}')
            if index == 0: handles.append(line)
        panel(ax, f'({chr(97+index)}) {title}', '累计转化水量 / (g/m²)')
        if peak == 0:
            ax.set_ylim(-.05,1); ax.grid(False)
            ax.text(.5,.52,'本窗口内未激活',transform=ax.transAxes,ha='center',color='#666666')
        else:
            ax.set_ylim(0,peak*1.12)
            ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,3),useMathText=True)
    shared_legend(fig, handles, ncol=4)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '11_六个相变通道累计转化水量', args,
                    dict(left=.09, right=.96, bottom=.09, top=.87, wspace=.40, hspace=.47))
