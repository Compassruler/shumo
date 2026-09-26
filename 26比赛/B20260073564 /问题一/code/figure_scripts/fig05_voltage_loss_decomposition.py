"""图05：模型电压与三类电压损失的堆叠分解。"""
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from common import CASES, COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.0)
AREA_ALPHA = 0.88
AREA_COLORS = ['#DCE6EC', COLORS['activation'], COLORS['ohmic'], COLORS['concentration']]


def build_figure():
    data = read_cases()
    labels = ['模型电压', '活化损失', '欧姆损失', '浓差损失']
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for index, (key, model, temp) in enumerate(CASES):
        d, ax = data[key], axes.flat[index]
        ax.stackplot(d['t_s'], d['V_model_V'], d['eta_act_V'], d['eta_ohm_V'],
                     d['eta_con_V'], colors=AREA_COLORS, alpha=AREA_ALPHA, linewidth=0)
        # 堆叠区域保持连续色块；其上叠加的离散数值使用图01式圆点。
        ax_model = discrete_points(ax, d['t_s'], d['V_model_V'], COLORS['main'], '模型电压')
        rev = discrete_points(ax, d['t_s'], d['E_rev_V'], '#252A34', '可逆电压')
        panel(ax, f'({chr(97+index)}) {model} · {temp}', '电压及损失 / V', zero=True)
    handles = [Patch(facecolor=c, label=t) for c, t in zip(AREA_COLORS, labels)]
    handles.append(Line2D([0], [0], marker='o', linestyle='None', markersize=2.0,
                          color='#252A34', label='可逆电压'))
    shared_legend(fig, handles, ncol=5)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '05_模型电压与活化欧姆浓差损失分解', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91, wspace=.30, hspace=.40))
