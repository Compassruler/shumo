"""绘制论文版五片电堆热网络与七个计算节点示意图。

绘图源与解题代码分离；输出写入问题2结果 figures 目录。
当前热学口径：六处物理双极板；端板仅储热并通过 g_E 耦合；
环境对流 h 直接作用于端部电池 T1、T5。
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2] / "解题" / "问题2_求解结果"
sys.path.insert(0, str(ROOT / ".python_deps"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.font_manager import FontProperties


def fonts():
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    cn_path = next((p for p in candidates if p.exists()), None)
    cn = FontProperties(fname=str(cn_path)) if cn_path else FontProperties(family="sans-serif")
    latin_path = Path(r"C:\Windows\Fonts\times.ttf")
    latin = FontProperties(fname=str(latin_path)) if latin_path.exists() else FontProperties(family="serif")
    return cn, latin


CN, LATIN = fonts()
COL = {
    "ink": "#26343E",
    "muted": "#667681",
    "mea": "#E8A23A",
    "mea_edge": "#B87820",
    "bp_terminal": "#356F9F",
    "bp_shared": "#6EA6C4",
    "endplate": "#59636D",
    "conduct": "#C94A3B",
    "convect": "#2E846B",
    "guide": "#AEB7BD",
    "ambient_fill": "#EEF6F2",
}


def txt(ax, x, y, s, size=10, color=None, weight="normal", ha="center", va="center",
        rotation=0, latin=False, zorder=10):
    fp = LATIN.copy() if latin else CN.copy()
    fp.set_size(size)
    fp.set_weight(weight)
    ax.text(x, y, s, ha=ha, va=va, color=color or COL["ink"], rotation=rotation,
            fontproperties=fp, zorder=zorder)


def double_arrow(ax, x1, y1, x2, y2, color, lw=1.55, rad=0.0, zorder=4):
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="<->", mutation_scale=9,
        linewidth=lw, color=color, shrinkA=1, shrinkB=1,
        connectionstyle=f"arc3,rad={rad}", zorder=zorder,
    )
    ax.add_patch(arrow)


def node(ax, x, y, label):
    ax.add_patch(Circle((x, y), 0.255, facecolor="white", edgecolor=COL["ink"], lw=1.35, zorder=7))
    txt(ax, x, y + 0.01, label, size=11.5, weight="bold", latin=True, zorder=8)


def draw():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.unicode_minus": False, "svg.fonttype": "none",
        "pdf.fonttype": 42, "ps.fonttype": 42, "mathtext.fontset": "stix",
    })
    fig, ax = plt.subplots(figsize=(11.7, 4.25))
    ax.set_xlim(0, 12)
    ax.set_ylim(0.15, 3.65)
    ax.axis("off")

    # Geometry: five MEAs, four internal shared BPs, and two terminal BPs.
    centers = [3.0, 4.5, 6.0, 7.5, 9.0]
    mea_w, mea_y, mea_h = 1.18, 0.95, 1.12
    bp_w = 0.18
    ep_w = 0.40
    left_ep_x, right_ep_x = 1.72, 10.28
    left_bp_x = centers[0] - mea_w / 2 - bp_w
    right_bp_x = centers[-1] + mea_w / 2

    # Physical stack.
    for x in (left_ep_x, right_ep_x):
        ax.add_patch(Rectangle((x - ep_w / 2, mea_y - 0.08), ep_w, mea_h + 0.16,
                               facecolor=COL["endplate"], edgecolor=COL["ink"], lw=1.1, zorder=2))
        txt(ax, x, mea_y + mea_h / 2, "端板", size=9.2, color="white", rotation=90, zorder=3)

    for x in (left_bp_x, right_bp_x):
        ax.add_patch(Rectangle((x, mea_y), bp_w, mea_h,
                               facecolor=COL["bp_terminal"], edgecolor=COL["ink"], lw=0.9, zorder=2))

    for i, x in enumerate(centers, start=1):
        ax.add_patch(Rectangle((x - mea_w / 2, mea_y), mea_w, mea_h,
                               facecolor=COL["mea"], edgecolor=COL["mea_edge"], lw=1.0, zorder=2))
        txt(ax, x, mea_y + mea_h * 0.61, f"单电池 {i}", size=10.2, weight="bold")
        txt(ax, x, mea_y + mea_h * 0.34, "MEA", size=9.4, latin=True, color="#68471B")

    shared_x = []
    for a, b in zip(centers[:-1], centers[1:]):
        x = (a + b) / 2 - bp_w / 2
        shared_x.append(x)
        ax.add_patch(Rectangle((x, mea_y), bp_w, mea_h,
                               facecolor=COL["bp_shared"], edgecolor=COL["ink"], lw=0.9, zorder=3))

    # Seven thermal capacity nodes and alignment leaders.
    node_y = 3.15
    thermal_x = [left_ep_x] + centers + [right_ep_x]
    labels = [r"$\Theta_L$"] + [rf"$T_{i}$" for i in range(1, 6)] + [r"$\Theta_R$"]
    for x, label in zip(thermal_x, labels):
        node(ax, x, node_y, label)
        ax.plot([x, x], [node_y - 0.26, mea_y + mea_h + 0.09],
                color=COL["guide"], lw=0.85, ls=(0, (2.2, 2.2)), zorder=1)

    # Thermal conductance network.
    double_arrow(ax, left_ep_x + .27, node_y, centers[0] - .27, node_y, COL["conduct"])
    txt(ax, (left_ep_x + centers[0]) / 2, node_y + .22, r"$g_E$", size=10.5,
        color=COL["conduct"], weight="bold", latin=True)
    for a, b in zip(centers[:-1], centers[1:]):
        double_arrow(ax, a + .27, node_y, b - .27, node_y, COL["conduct"])
        txt(ax, (a + b) / 2, node_y + .22, r"$g_c$", size=10.5,
            color=COL["conduct"], weight="bold", latin=True)
    double_arrow(ax, centers[-1] + .27, node_y, right_ep_x - .27, node_y, COL["conduct"])
    txt(ax, (centers[-1] + right_ep_x) / 2, node_y + .22, r"$g_E$", size=10.5,
        color=COL["conduct"], weight="bold", latin=True)

    # Ambient convection acts on end cells, bypassing the end-plate capacity nodes.
    amb_l, amb_r = (0.50, 2.62), (11.50, 2.62)
    for x, y in (amb_l, amb_r):
        ax.add_patch(Rectangle((x - .38, y - .25), .76, .50, facecolor=COL["ambient_fill"],
                               edgecolor=COL["convect"], lw=1.15, zorder=5))
        txt(ax, x, y + .075, "环境", size=9.2, color=COL["convect"], weight="bold")
        txt(ax, x, y - .095, r"$T_{amb}$", size=9.4, color=COL["convect"], latin=True)
    double_arrow(ax, amb_l[0] + .38, amb_l[1] + .02, centers[0] - .20, node_y - .22,
                 COL["convect"], rad=-0.22)
    double_arrow(ax, centers[-1] + .20, node_y - .22, amb_r[0] - .38, amb_r[1] + .02,
                 COL["convect"], rad=0.22)
    txt(ax, 1.88, 2.55, r"$h$", size=10.5, color=COL["convect"], weight="bold", latin=True)
    txt(ax, 10.12, 2.55, r"$h$", size=10.5, color=COL["convect"], weight="bold", latin=True)

    # Minimal legend only: it explains visual encodings, not model prose.
    legend_y = .42
    items = [
        ("patch", COL["mea"], "单电池 MEA（5）"),
        ("patch", COL["bp_terminal"], "终端双极板（2）"),
        ("patch", COL["bp_shared"], "片间共享双极板（4）"),
        ("patch", COL["endplate"], "端板（2）"),
    ]
    starts = [2.10, 4.35, 6.55, 8.95]
    for start, (_, color, label) in zip(starts, items):
        ax.add_patch(Rectangle((start - .28, legend_y - .09), .30, .18,
                               facecolor=color, edgecolor=COL["ink"], lw=.7))
        txt(ax, start + .12, legend_y, label, size=8.6, ha="left")

    # A thin baseline visually joins the physical stack without adding text.
    ax.plot([left_ep_x - ep_w / 2, right_ep_x + ep_w / 2], [mea_y - .17, mea_y - .17],
            color=COL["ink"], lw=.8)

    out = ROOT / "figures"
    out.mkdir(parents=True, exist_ok=True)
    base = out / "00_电堆热网络与计算节点示意图_论文版"
    fig.savefig(base.with_suffix(".png"), dpi=420, bbox_inches="tight", pad_inches=.06)
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=.06)
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=.06)
    plt.close(fig)
    print(base)


if __name__ == "__main__":
    draw()
