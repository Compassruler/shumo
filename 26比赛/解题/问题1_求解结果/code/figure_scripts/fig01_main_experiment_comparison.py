"""图01：五层基线计算结果与实验采样值对比。"""
import matplotlib.pyplot as plt
from common import COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases, shared_legend

# ===== 常用调节区：修改后直接运行本文件即可预览 =====
FIGSIZE = (7.1, 5.0)          # 图宽和图高，单位：英寸
EXPERIMENT_COLOR = '#C44E52' # 实验采样点颜色
MARKER_SIZE = 2.5           # 实心圆大小
MODEL_COLOR = COLORS['main'] # 模型曲线颜色
MODEL_LINEWIDTH = 1.65       # 模型曲线线宽


def build_figure():
    """创建图对象；本函数只画图，不负责保存或弹窗。"""
    data = read_cases()
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    for col, temp in enumerate(['20', '25']):
        d = data[f'main_minus{temp}']
        for row, (symbol, unit, ylabel) in enumerate([
                ('V', 'V', '电压 / V'), ('T', 'C', '温度 / ℃')]):
            ax = axes[row, col]
            # 全部实验采样值：珊瑚红实心圆，白色细边避免密集点粘连。
            exp = discrete_points(ax, d['t_s'], d[f'{symbol}_exp_{unit}'],
                                  EXPERIMENT_COLOR, '实验采样值', MARKER_SIZE)
            # Python 模型计算曲线：改为点状标记表示五层基线。
            model = ax.plot(d['t_s'], d[f'{symbol}_model_{unit}'], 'o',
                            color=MODEL_COLOR, markersize=MARKER_SIZE*0.8,
                            markerfacecolor=MODEL_COLOR,
                            markeredgecolor='white', markeredgewidth=.2,
                            linestyle='none', alpha=.9,
                            label='五层基线', zorder=2)[0]
            panel(ax, f'({chr(97+row*2+col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, model], ncol=2)
    return fig


if __name__ == '__main__':
    args = cli(__doc__)
    configure_style()
    figure = build_figure()
    export_and_show(figure, '01_main_experiment_comparison', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91,
                         wspace=.30, hspace=.40))
