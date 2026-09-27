"""图05：P、C、R 三种方案的累计能量预算与能量守恒残差。"""
import numpy as np
import matplotlib.pyplot as plt
from common import (COLORS, NAMES, cli, configure_style, decorate, discrete_points,
                    export_and_show, note, panel_title, read_traces)

# ===== 常用调节区 =====
FIGSIZE = (12.5, 4.3)
MARKER_SIZE = 6.0
ENERGY_COLORS = (COLORS["P"], COLORS["C"], COLORS["purple"], COLORS["gray"], COLORS["R"])


def build_figure():
    traces = read_traces("P", "C", "R")
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE)
    fields = ("E_aux_J", "E_gen_J", "E_phase_J", "E_loss_J", "E_sensible_J")
    labels = ("辅助热", "反应热", "相变净热", "−散热", "显热增量")
    x = np.arange(len(labels))
    for index, (ax, key) in enumerate(zip(axes, ("P", "C", "R"))):
        trace = traces[key]
        values = np.array([trace[name][-1] for name in fields], dtype=float)
        values[3] *= -1
        for position, value, color, label in zip(x, values, ENERGY_COLORS, labels):
            discrete_points(ax, [position], [value], color, label, MARKER_SIZE)
            ax.annotate(f"{value:.0f}", (position, value),
                        xytext=(0, 5 if value >= 0 else -13),
                        textcoords="offset points", ha="center", fontsize=8)
        ax.axhline(0, color="#626970", linewidth=.8)
        panel_title(ax, f"({chr(97 + index)}) {NAMES[key]}")
        decorate(ax, "累计能量 / J" if key == "P" else None, "")
        # 分类刻度必须在 decorate() 之后设置，避免被自动刻度定位器覆盖。
        ax.set_xticks(x, labels, rotation=25, ha="right")
        ax.grid(axis="x", visible=False)
        ax.margins(y=.22)
        residual = trace["energy_residual_J"][-1]
        ax.text(.03, .05, f"t = {trace['time_s'][-1]:.2f} s\n守恒残差 {residual:.1e} J",
                transform=ax.transAxes, va="bottom", fontsize=8)
    note(fig, "能量记账：辅助热 + 反应热 + 相变净热 − 环境散热 = 显热增量（含端板）。\nP/C 取主结果末端；R 取完整预热及加载验证末端，因此 R 不与 P 启动窗口直接比较。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "05_能量预算与守恒", args,
                    dict(left=.07, right=.99, bottom=.27, top=.91, wspace=.29))
