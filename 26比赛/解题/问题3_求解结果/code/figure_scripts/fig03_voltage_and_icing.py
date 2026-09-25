"""图03：两种主策略的最低单片电压、冰体积分数和孔隙冰饱和度。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from common import (CELL_COLORS, COLORS, NAMES, cells, cli, configure_style, decorate,
                    discrete_points, export_and_show, note, panel_title, read_traces)

# ===== 常用调节区 =====
FIGSIZE = (11.3, 8.1)
MARKER_SIZE = 2.0
VOLTAGE_LIMIT = 0.30


def build_figure():
    traces = read_traces("P", "C")
    fig, axes = plt.subplots(3, 2, figsize=FIGSIZE, sharex="col")
    for col, key in enumerate(("P", "C")):
        trace = traces[key]
        time = trace["time_s"]
        voltage = cells(trace, "V")
        ice = cells(trace, "ice_bulk")
        saturation = cells(trace, "pore_ice_saturation")

        discrete_points(axes[0, col], time, np.min(voltage, axis=1), COLORS[key],
                        "全堆最低单片电压", MARKER_SIZE)
        axes[0, col].axhline(VOLTAGE_LIMIT, color=COLORS["danger"], linestyle="--",
                            linewidth=1, label="电压约束 0.30 V")
        axes[0, col].set_ylim(bottom=min(.27, np.min(voltage) - .02))

        discrete_points(axes[1, col], time, np.max(ice[:, [0, 4]], axis=1),
                        CELL_COLORS[0], "端部单片最大", MARKER_SIZE)
        discrete_points(axes[1, col], time, ice[:, 2], CELL_COLORS[2],
                        "中心单片", MARKER_SIZE)
        discrete_points(axes[1, col], time, np.max(ice, axis=1), COLORS["neutral"],
                        "全堆最大", MARKER_SIZE)

        discrete_points(axes[2, col], time, np.max(saturation[:, [0, 4]], axis=1),
                        COLORS[key], "端部孔隙冰饱和度", MARKER_SIZE)
        panel_title(axes[0, col], f"({chr(97 + col)}) {NAMES[key]}")
        for row in range(3):
            axes[row, col].legend(frameon=False, loc="best", fontsize=8)
        for row, ylabel in enumerate(("最低单片电压 / V", "MEA 体积平均冰体积分数", "端部孔隙冰饱和度")):
            decorate(axes[row, col], ylabel if col == 0 else None,
                     "时间 / s" if row == 2 else "")
            axes[row, col].set_xlim(0, time[-1])
            if row > 0:
                axes[row, col].set_ylim(bottom=0)
                source = ice if row == 1 else saturation
                if np.max(source) < 1e-10:
                    axes[row, col].set_ylim(0, 1e-4)
                formatter = ScalarFormatter(useMathText=True)
                formatter.set_powerlimits((-3, 3))
                axes[row, col].yaxis.set_major_formatter(formatter)
    note(fig, "统计窗口与图01相同，未包含 P 关热后续加载。ice_bulk 含膜内冰、以整个 MEA 体积平均；\n孔隙冰饱和度仅描述多孔层局部孔隙占据，二者分母不同。体积分数启动约束为 < 0.99。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "03_主策略电压与结冰", args,
                    dict(left=.09, right=.98, bottom=.13, top=.95, hspace=.24, wspace=.20))
