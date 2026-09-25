"""图10：六个相变系数的一次一因子敏感性矩阵。"""
import numpy as np
import matplotlib.pyplot as plt
from common import CASES, cli, configure_style, export_and_show, panel_title, read_csv, select

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.2)
COLORMAP = 'Blues'
TEXT_SIZE = 9
PHASE_LABELS = {'kf':'冻结','km':'融化','kcond':'凝结','kevap':'蒸发','kdep':'凝华','ksub':'升华'}


def build_figure():
    d = read_csv('参数与闭合敏感性.csv')
    parameters = list(PHASE_LABELS)
    metrics = [('max_delta_V_V',1e3,'max |ΔV|\n/mV'),
               ('max_delta_T_C',1,'max |ΔT|\n/℃'),
               ('delta_ice_at35',100,'|Δ冰35s|\n/百分点')]
    matrices = []
    for tag, _, _ in CASES:
        model, condition = tag.split('_', 1)
        subset = select(d, model=model, condition=condition, kind='phase_one_at_a_time')
        matrix = np.array([[np.max(np.abs(select(subset, parameter=p)[key]))*factor
                            for key, factor, _ in metrics] for p in parameters])
        matrices.append(matrix)
    # 同一指标在四个面板共用颜色上限，数字仍显示实际变化量。
    scale = np.maximum(np.max(np.stack(matrices), axis=(0,1)), 1e-15)
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for index, ((_, model, temp), matrix) in enumerate(zip(CASES, matrices)):
        ax = axes.flat[index]; normalized = matrix/scale
        ax.pcolormesh(np.arange(4), np.arange(7), normalized, cmap=COLORMAP,
                      vmin=0, vmax=1, shading='flat', rasterized=False)
        ax.set_xlim(0,3); ax.set_ylim(6,0)
        ax.set_xticks(np.arange(3)+.5, [m[2] for m in metrics], fontsize=9)
        ax.set_yticks(np.arange(6)+.5, [PHASE_LABELS[p]+' · '+p for p in parameters])
        for i in range(6):
            for j in range(3):
                value = matrix[i,j]
                text = '0' if value == 0 else (f'{value:.3g}' if value >= .001 else f'{value:.1e}')
                ax.text(j+.5, i+.5, text, ha='center', va='center', fontsize=TEXT_SIZE,
                        color='white' if normalized[i,j]>.65 else '#20252B')
        panel_title(ax, f'({chr(97+index)}) {model} · {temp}')
        ax.grid(False)
        for spine in ax.spines.values(): spine.set_visible(False)
    fig.text(.5,.02,'每项均取单独调整至0.1倍、10倍的较大影响；颜色按各指标共同最大值归一化。',
             ha='center',fontsize=8.3)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '10_phase_coefficient_sensitivity', args,
                    dict(left=.09, right=.96, bottom=.12, top=.94, wspace=.35, hspace=.55))
