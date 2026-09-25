"""论文版数值求解流程图：FVM + BE + 顺序分裂 + 热-电 Picard。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2] / "解题" / "问题1_求解结果"
sys.path.insert(0, str(ROOT.parent / "问题2_求解结果" / ".python_deps"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Circle, Ellipse
from matplotlib.font_manager import FontProperties


def get_fonts():
    cn_paths = [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simsun.ttc")]
    cn_path = next((p for p in cn_paths if p.exists()), None)
    cn = FontProperties(fname=str(cn_path)) if cn_path else FontProperties(family="sans-serif")
    times = Path(r"C:\Windows\Fonts\times.ttf")
    en = FontProperties(fname=str(times)) if times.exists() else FontProperties(family="serif")
    return cn, en


CN, EN = get_fonts()
INK = "#263640"
LINE = "#52636D"
ACCENT = "#426F8F"
LIGHT = "#F3F7F9"
MODULE = "#E9F1F5"
CHECK = "#F8F4EA"


def text(ax, x, y, s, size=9.4, weight="normal", color=INK, ha="center", va="center",
         zorder=8, latin=False, rotation=0):
    fp = EN.copy() if latin else CN.copy()
    fp.set_size(size)
    fp.set_weight(weight)
    ax.text(x, y, s, ha=ha, va=va, color=color, fontproperties=fp, zorder=zorder,
            rotation=rotation,
            linespacing=1.35)


def rounded_box(ax, x, y, w, h, title, body=None, fill=LIGHT, lw=1.05):
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
        boxstyle="round,pad=0.035,rounding_size=0.08", facecolor=fill,
        edgecolor=LINE, linewidth=lw, zorder=3))
    if body:
        text(ax, x, y+0.16, title, size=9.7, weight="bold")
        text(ax, x, y-0.20, body, size=8.1, color="#4C5C65")
    else:
        text(ax, x, y, title, size=9.2)


def module_box(ax, number, x, y, w, h, title, body):
    rounded_box(ax, x, y, w, h, title, body, fill=MODULE, lw=1.25)
    cx = x-w/2+0.05
    ax.add_patch(Circle((cx, y), 0.235, facecolor=ACCENT, edgecolor="white", lw=1.3, zorder=6))
    text(ax, cx, y, str(number), size=10.4, weight="bold", color="white", latin=True, zorder=7)


def diamond(ax, x, y, w, h, label):
    pts = [(x, y+h/2), (x+w/2, y), (x, y-h/2), (x-w/2, y)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=CHECK, edgecolor=LINE, lw=1.1, zorder=3))
    text(ax, x, y, label, size=8.5)


def arrow(ax, p1, p2, color=LINE, rad=0, zorder=2):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=10,
        linewidth=1.05, color=color, connectionstyle=f"arc3,rad={rad}", zorder=zorder))


def down(ax, y1, y2, x=3.5):
    arrow(ax, (x, y1), (x, y2))


def draw():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.unicode_minus": False, "svg.fonttype": "none",
        "pdf.fonttype": 42, "ps.fonttype": 42, "mathtext.fontset": "stix",
    })
    fig, ax = plt.subplots(figsize=(6.25, 9.0))
    ax.set_xlim(0, 7)
    ax.set_ylim(0.15, 12.25)
    ax.axis("off")
    x = 3.5

    # Start and inputs.
    ax.add_patch(Ellipse((x, 11.72), 1.25, .50, facecolor="white", edgecolor=LINE, lw=1.05))
    text(ax, x, 11.72, "开始", size=9.5, weight="bold")
    rounded_box(ax, x, 10.93, 4.35, .72, "输入模型与数值参数",
                "几何/物性、初始场、边界条件、Δt 与收敛容差")
    down(ax, 11.47, 11.30)

    # Preprocessing module outside the time loop.
    module_box(ax, 1, x, 9.76, 4.70, .92, "有限体积空间离散",
               "分层控制体积分 · 面通量守恒 · 构造离散系数矩阵")
    down(ax, 10.57, 10.23)
    rounded_box(ax, x, 8.82, 3.75, .61, "初始化 t=0，给定 U(0)、T(0)", fill="white")
    down(ax, 9.30, 9.13)

    # Time-loop header.
    ax.add_patch(FancyBboxPatch((x-1.10, 7.94), 2.20, .48,
        boxstyle="round,pad=0.025,rounding_size=0.20", facecolor=ACCENT,
        edgecolor=ACCENT, lw=1.0, zorder=3))
    text(ax, x, 8.18, "时间步 n → n+1", size=9.0, weight="bold", color="white")
    down(ax, 8.52, 8.43)

    module_box(ax, 2, x, 7.20, 4.70, .92, "后向欧拉时间推进",
               "在 t(n+1) 隐式求值 · 形成稳定的代数方程组")
    down(ax, 7.94, 7.67)

    module_box(ax, 3, x, 5.85, 4.70, 1.05, "一阶顺序分裂",
               r"先更新组分输运与水-冰相变，再更新物性和源项")
    down(ax, 6.73, 6.38)

    module_box(ax, 4, x, 4.35, 4.70, 1.13, "热-电 Picard 迭代",
               "由 T(m) 计算 V(m) 与产热率；求解 T(m+1)")
    down(ax, 5.32, 4.92)

    diamond(ax, x, 2.96, 3.35, 1.05,
            "max |T(m+1)-T(m)| < eps_T ？")
    down(ax, 3.78, 3.49)

    # Picard loop: no branch returns to module 4.
    text(ax, 5.30, 3.08, "否", size=8.1, color=LINE)
    arrow(ax, (5.18, 2.96), (5.86, 2.96))
    ax.plot([5.86, 5.86, 5.86, 5.86], [2.96, 4.35, 4.92, 4.92], color=LINE, lw=1.05, zorder=1)
    arrow(ax, (5.86, 4.92), (5.77, 4.92))
    text(ax, 5.95, 4.04, "m ← m+1", size=8.0, color=LINE, ha="left", latin=True)

    text(ax, 3.76, 2.34, "是", size=8.1, color=LINE, ha="left")
    rounded_box(ax, x, 1.86, 4.40, .72, "接受本步解并执行数值检查",
                "更新状态 · 守恒残差 · 物理约束 · 启动事件", fill="white")
    down(ax, 2.44, 2.22)

    diamond(ax, x, .86, 2.40, .82, "达到终止条件？")
    down(ax, 1.50, 1.27)

    # No branch of the time loop returns to module 2.
    text(ax, 2.13, .86, "否", size=8.1, color=LINE)
    arrow(ax, (2.30, .86), (.62, .86))
    ax.plot([.62, .62, .62], [.86, 7.20, 7.20], color=LINE, lw=1.05, zorder=1)
    arrow(ax, (.62, 7.20), (1.12, 7.20))
    text(ax, .75, 4.15, "n ← n+1", size=8.0, color=LINE, rotation=90, latin=True)

    text(ax, 4.88, 1.04, "是", size=8.1, color=LINE)
    # Final output is placed to the right to preserve a compact bottom margin.
    rounded_box(ax, 5.95, .86, 1.70, .62, "输出计算结果", fill=LIGHT)
    arrow(ax, (4.70, .86), (5.10, .86))

    out = ROOT / "figures"
    out.mkdir(parents=True, exist_ok=True)
    base = out / "00_数值求解算法流程图_论文版"
    fig.savefig(base.with_suffix(".png"), dpi=420, bbox_inches="tight", pad_inches=.06)
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", pad_inches=.06)
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight", pad_inches=.06)
    plt.close(fig)
    print(base)


if __name__ == "__main__":
    draw()
