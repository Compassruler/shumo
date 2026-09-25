"""图12：近优冻结情景包络及 k_f=1 的同粗网格参考。"""
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from common import CASES, COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_csv, select, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.0)
BAND_COLOR = '#709DAF'
BAND_ALPHA = 0.32
REFERENCE_COLOR = COLORS['bp']


def build_figure():
    ranges = read_csv('近优冻结情景范围_非置信区间.csv')
    series = read_csv('冻结系数情景全时序.csv')
    fig, axes = plt.subplots(2,2,figsize=FIGSIZE)
    for index, (tag, model, temp) in enumerate(CASES):
        prefix, condition = tag.split('_',1)
        d = select(ranges, model=prefix, condition=condition)
        reference = select(series, model=prefix, condition=condition, kf_s_inv=1.)
        ax = axes.flat[index]
        ax.fill_between(d['t_s'], d['ice_max_bulk_min'], d['ice_max_bulk_max'],
                        color=BAND_COLOR, alpha=BAND_ALPHA, linewidth=0)
        discrete_points(ax, d['t_s'], d['ice_max_bulk_min'], '#4C7E92', '情景下界')
        discrete_points(ax, d['t_s'], d['ice_max_bulk_max'], '#4C7E92', '情景上界')
        discrete_points(ax, reference['t_s'], reference['ice_max_bulk'],
                        REFERENCE_COLOR, r'$k_f=1$ 同粗网格参考')
        count = int(d['n_scenarios'][0])
        panel(ax, f'({chr(97+index)}) {model} · {temp}（{count}个情景）', '最大冰体积分数', zero=True)
    shared_legend(fig, [Patch(facecolor=BAND_COLOR, alpha=BAND_ALPHA,
                              label='校准目标≤最小值×1.05的情景范围'),
                        Line2D([0],[0],color=REFERENCE_COLOR,marker='o',linestyle='None',
                               markersize=2.0,label=r'$k_f=1$ 同粗网格参考')],
                  ncol=2)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '12_近优冻结情景范围与kf1参考曲线', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91, wspace=.30, hspace=.45))
