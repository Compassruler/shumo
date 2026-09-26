"""图09：冻结系数剖面与参数可辨识性。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common import COLORS, cli, configure_style, discrete_points, export_and_show, panel_title, read_csv, select, shared_legend

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.0)
MARKER_SIZE = 2.0  # 与图01模型计算点一致
REFERENCE_KF = 1.0


def build_figure():
    d = read_csv('冻结系数剖面.csv')
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    handles = []
    for row, (model, title) in enumerate([('main','五层基线'), ('bp','含双极板修订')]):
        for condition, color, label in [
                ('minus20', COLORS['main'], '−20 ℃：校准工况'),
                ('minus25', COLORS['bp'], '−25 ℃：留出工况')]:
            subset = select(d, model=model, condition=condition)
            order = np.argsort(subset['kf_s_inv'])
            for col, key in enumerate(['mean_squared_relative_objective', 'ice_at35_bulk']):
                x, y = subset['kf_s_inv'][order], subset[key][order]
                if col == 1: y = np.where(y > 0, y, np.nan)
                # k_f 是离散扫描取值，只画实心圆，不用线连接相邻扫描点。
                line = discrete_points(axes[row,col], x, y, color, label, MARKER_SIZE)
                axes[row,col].set_xscale('log')
                if col == 1: axes[row,col].set_yscale('log')
                axes[row,col].axvline(REFERENCE_KF, color='#888888', linewidth=.8, linestyle=':')
                axes[row,col].set_xlabel(r'冻结系数 $k_f$ / $\mathrm{s}^{-1}$')
            if row == 0: handles.append(line)
        axes[row,0].set_ylabel('平均平方相对误差目标')
        axes[row,1].set_ylabel('35 s 最大冰体积分数')
        for col in range(2): panel_title(axes[row,col], f'({chr(97+row*2+col)}) {title}')
    handles.append(Line2D([0],[0], color='#888888', linestyle=':', label=r'固定基准 $k_f=1$'))
    shared_legend(fig, handles, ncol=3)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '09_冻结系数剖面与参数可辨识性', args,
                    dict(left=.09, right=.96, bottom=.09, top=.91, wspace=.30, hspace=.45))
