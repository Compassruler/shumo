"""图02：五层基线、含双极板修订模型与实验值对比。"""
import matplotlib.pyplot as plt
from common import COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.0)
EXPERIMENT_MARKER_SIZE = 2.5  # 与图01实验点一致
MODEL_MARKER_SIZE = 2.0       # 与图01模型点一致
MAIN_COLOR, BP_COLOR = COLORS['main'], COLORS['bp']


def build_figure():
    data = read_cases()
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for col, temp in enumerate(['20', '25']):
        main, bp = data[f'main_minus{temp}'], data[f'bp_minus{temp}']
        for row, (key, exp_key, ylabel) in enumerate([
                ('V_model_V', 'V_exp_V', '电压 / V'),
                ('T_model_C', 'T_exp_C', '温度 / ℃')]):
            ax = axes[row, col]
            # 实验值是离散观测：统一使用实心圆，不绘制连接线。
            exp = discrete_points(ax, main['t_s'], main[exp_key],
                                  COLORS['experiment'], '实验采样值',
                                  EXPERIMENT_MARKER_SIZE, zorder=4)
            h_main = discrete_points(ax, main['t_s'], main[key], MAIN_COLOR,
                                     '五层基线', MODEL_MARKER_SIZE, zorder=2)
            h_bp = discrete_points(ax, bp['t_s'], bp[key], BP_COLOR,
                                   '含双极板修订', MODEL_MARKER_SIZE, zorder=2)
            panel(ax, f'({chr(97+row*2+col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, h_main, h_bp], ncol=3)

    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '02_bp_structural_comparison', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91, wspace=.30, hspace=.40))
