"""图01：纯预热与协同加热两种主策略的单电池及端板温度历程。"""
import numpy as np
import matplotlib.pyplot as plt
from common import (CELL_COLORS, COLORS, NAMES, cli, configure_style, decorate,
                    discrete_points, export_and_show, note, panel_title, read_summary,
                    read_traces)

# ===== 常用调节区 =====
FIGSIZE = (11.3, 4.0)
MARKER_SIZE = 2.0
ZERO_LINE_COLOR = "#30373D"


def draw_temperatures(ax, trace):
    """绘制镜像对称温度；若不对称则补画对应单片。"""
    time = trace["time_s"]
    handles = []
    for cell, color, label in zip((1, 2, 3), CELL_COLORS,
                                  ("单电池 1 / 5", "单电池 2 / 4", "单电池 3")):
        handles.append(discrete_points(ax, time, trace[f"T{cell}_C"], color, label, MARKER_SIZE))
    for cell, mirror, color in ((5, 1, CELL_COLORS[0]), (4, 2, CELL_COLORS[1])):
        if np.max(np.abs(trace[f"T{cell}_C"] - trace[f"T{mirror}_C"])) > 1e-5:
            handles.append(discrete_points(ax, time, trace[f"T{cell}_C"], color,
                                           f"单电池 {cell}（非对称）", MARKER_SIZE))
    handles.append(discrete_points(ax, time, trace["TEL_C"], COLORS["neutral"],
                                   "左 / 右端板", MARKER_SIZE))
    if np.max(np.abs(trace["TEL_C"] - trace["TER_C"])) > 1e-5:
        handles.append(discrete_points(ax, time, trace["TER_C"], COLORS["neutral"],
                                       "右端板（非对称）", MARKER_SIZE))
    return handles


def build_figure():
    summary = read_summary()
    traces = read_traces("P", "C")
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE, sharey=True)
    for index, (ax, key) in enumerate(zip(axes, ("P", "C"))):
        trace = traces[key]
        draw_temperatures(ax, trace)
        ax.axhline(0, color=ZERO_LINE_COLOR, linewidth=.85)
        heating_end = float(summary[key]["th_s"])
        if heating_end < trace["time_s"][-1] - .1:
            ax.axvline(heating_end, color="#858C92", linestyle=":", linewidth=1)
            ax.text(heating_end, .98, "关热", transform=ax.get_xaxis_transform(),
                    va="top", ha="right", fontsize=8)
        panel_title(ax, f"({chr(97 + index)}) {NAMES[key]}")
        decorate(ax, "温度 / ℃" if index == 0 else None)
        ax.set_xlim(0, trace["time_s"][-1])
        ax.text(.03, .97, f"统计至 {trace['time_s'][-1]:.2f} s",
                transform=ax.transAxes, va="top", fontsize=9)
    axes[1].legend(loc="lower right", frameon=False)
    note(fig, "P：预热至关热 / 加载开始；C：从通电至首次启动成功。端板温度不计入全部单电池超过 0 ℃ 的判据。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "01_主策略温度历程", args,
                    dict(left=.08, right=.98, bottom=.20, top=.90, wspace=.15))
