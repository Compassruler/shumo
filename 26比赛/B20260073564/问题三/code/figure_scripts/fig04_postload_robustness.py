"""图04：纯预热和附加稳健预热在关热加载后的温度回落与电压验证。"""
import numpy as np
import matplotlib.pyplot as plt
from common import (COLORS, NAMES, cells, cli, configure_style, decorate,
                    discrete_points, export_and_show, note, panel_title,
                    read_summary, read_traces, temperatures)

# ===== 常用调节区 =====
FIGSIZE = (11.3, 4.15)
MARKER_SIZE = 2.0
MINIMUM_MARKER_SIZE = 5.0


def build_figure():
    summary = read_summary()
    traces = read_traces("P_postload", "R")
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE)
    for key, trace_key in (("P", "P_postload"), ("R", "R")):
        trace = traces[trace_key]
        tau = trace["time_s"] - float(summary[key]["th_s"])
        keep = tau >= -1e-7
        minimum_temperature = np.min(temperatures(trace), axis=1)
        minimum_voltage = np.min(cells(trace, "V"), axis=1)
        discrete_points(axes[0], tau[keep], minimum_temperature[keep], COLORS[key],
                        NAMES[key], MARKER_SIZE)
        discrete_points(axes[1], tau[keep], minimum_voltage[keep], COLORS[key],
                        NAMES[key], MARKER_SIZE)

        # 单独强调最低温度点，但仍使用实心圆。
        index = np.flatnonzero(keep)[np.argmin(minimum_temperature[keep])]
        discrete_points(axes[0], [tau[index]], [minimum_temperature[index]], COLORS[key],
                        size=MINIMUM_MARKER_SIZE, zorder=5)
        axes[0].annotate(f"{minimum_temperature[index]:.2f} ℃",
                         (tau[index], minimum_temperature[index]),
                         xytext=(5, -15 if key == "P" else 7),
                         textcoords="offset points", color=COLORS[key], fontsize=9)

    axes[0].axhline(0, color=COLORS["danger"], linestyle="--", linewidth=1)
    axes[1].axhline(.30, color=COLORS["danger"], linestyle="--", linewidth=1)
    for ax, title, ylabel in zip(
            axes,
            ("(a) 关热后最低单片温度", "(b) 关热后最低单片电压"),
            ("全堆最低单片温度 / ℃", "全堆最低单片电压 / V")):
        panel_title(ax, title)
        decorate(ax, ylabel, r"关热后加载时间 $\tau=t-t_h$ / s")
        ax.set_xlim(left=0)
        ax.legend(frameon=False, loc="best")
    note(fig, r"$\tau=0$ 时关热并开始规定电流爬升；验证持续至累计电荷 20 C·cm$^{-2}$（$\tau=96.6667$ s）。" "\nP 的后续回落不改变首次成功记录；R 另加全过程不低于 0 ℃ 的稳健约束。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "04_关热后回落与稳健验证", args,
                    dict(left=.085, right=.98, bottom=.25, top=.90, wspace=.26))
