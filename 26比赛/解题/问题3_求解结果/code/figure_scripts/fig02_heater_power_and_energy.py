"""图02：三种方案的分片恒定加热功率与单片辅助加热能耗。"""
import numpy as np
import matplotlib.pyplot as plt
from common import (COLORS, NAMES, cli, configure_style, decorate, discrete_points,
                    export_and_show, note, panel_title, read_summary)

# ===== 常用调节区 =====
FIGSIZE = (11.3, 4.0)
MARKER_SIZE = 5.0
STRATEGY_OFFSETS = {"P": -.16, "C": 0.0, "R": .16}


def build_figure():
    summary = read_summary()
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE)
    cells = np.arange(1, 6)
    for key in ("P", "C", "R"):
        x = cells + STRATEGY_OFFSETS[key]
        power = [summary[key][f"q{k}_W_cm2"] for k in cells]
        energy = [summary[key][f"E{k}_J"] for k in cells]
        discrete_points(axes[0], x, power, COLORS[key], NAMES[key], MARKER_SIZE)
        discrete_points(axes[1], x, energy, COLORS[key], NAMES[key], MARKER_SIZE)
    for ax, ylabel, title in zip(
            axes,
            (r"加热功率密度 / (W·cm$^{-2}$)", "单片辅助加热能耗 / J"),
            ("(a) 各片恒定加热功率", "(b) 各片累计辅助能耗")):
        decorate(ax, ylabel, "单电池编号")
        ax.set_xticks(cells)
        ax.set_xlim(.5, 5.5)
        ax.grid(axis="x", visible=False)
        panel_title(ax, title)
    axes[0].axhline(1, color="#525A62", linestyle=":", linewidth=1)
    axes[0].set_ylim(0, 1.13)
    axes[0].legend(frameon=False, loc="center left", bbox_to_anchor=(.02, .38))
    energies = "；".join(f"{key}: {summary[key]['E_aux_J']:.1f} J" for key in ("P", "C", "R"))
    note(fig, f"单片面积 25 cm²；能耗 $E_k=25q_kt_h$。R 为增加加载后不回落要求的附加设计。\n总辅助能耗：{energies}。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "02_分片加热功率与能耗", args,
                    dict(left=.08, right=.98, bottom=.24, top=.90, wspace=.30))
