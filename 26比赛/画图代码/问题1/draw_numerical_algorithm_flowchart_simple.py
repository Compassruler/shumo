"""论文版数值求解流程图（简化版）：FVM + BE + 顺序分裂 + 热-电 Picard。

与 ``draw_numerical_algorithm_flowchart.py``（完整版）同源，但按"一个算法一个模块"
精简为更简洁的竖排结构：开始 → 输入初始化 → 四个算法模块 → 两级收敛判断 → 输出。
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Circle, Ellipse
from matplotlib.font_manager import FontProperties

# 输出目录：直接放到用户桌面
OUT = Path.home() / "Desktop"

INK = "#263640"
LINE = "#52636D"
ACCENT = "#426F8F"
LIGHT = "#F3F7F9"
MODULE = "#E9F1F5"
CHECK = "#F8F4EA"


def get_fonts():
    cn_paths = [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simsun.ttc")]
    cn_path = next((p for p in cn_paths if p.exists()), None)
    cn = FontProperties(fname=str(cn_path)) if cn_path else FontProperties(family="sans-serif")
    times = Path(r"C:\Windows\Fonts\times.ttf")
    en = FontProperties(fname=str(times)) if times.exists() else FontProperties(family="serif")
    return cn, en


CN, EN = get_fonts()


def text(ax, x, y, s, size=9.6, weight="normal", color=INK, ha="center", va="center",
         zorder=8, latin=False, rotation=0):
    fp = EN.copy() if latin else CN.copy()
    fp.set_size(size)
    fp.set_weight(weight)
    ax.text(x, y, s, ha=ha, va=va, color=color, fontproperties=fp, zorder=zorder,
            rotation=rotation, linespacing=1.3)


def rounded_box(ax, x, y, w, h, title, body=None, fill=LIGHT, lw=1.05, size=10.2):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.08", facecolor=fill,
        edgecolor=LINE, linewidth=lw, zorder=3))
    if body:
        text(ax, x, y + 0.15, title, size=size, weight="bold")
        text(ax, x, y - 0.21, body, size=8.4, color="#4C5C65")
    else:
        text(ax, x, y, title, size=size, weight="bold")


def module_box(ax, number, x, y, w, h, title, body):
    rounded_box(ax, x, y, w, h, title, body, fill=MODULE, lw=1.25)
    cx = x - w / 2 + 0.06
    ax.add_patch(Circle((cx, y), 0.24, facecolor=ACCENT, edgecolor="white", lw=1.3, zorder=6))
    text(ax, cx, y, str(number), size=10.6, weight="bold", color="white", latin=True, zorder=7)


def diamond(ax, x, y, w, h, label):
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=CHECK, edgecolor=LINE, lw=1.1, zorder=3))
    text(ax, x, y, label, size=9.0)


def arrow(ax, p1, p2, color=LINE, zorder=2):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=11,
        linewidth=1.05, color=color, zorder=zorder))


def down(ax, y1, y2, x=3.5):
    arrow(ax, (x, y1), (x, y2))


def draw():
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.unicode_minus": False, "svg.fonttype": "none",
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(5.7, 8.3))
    ax.set_xlim(0, 7)
    ax.set_ylim(0.0, 11.9)
    ax.axis("off")
    x = 3.5

    # 1. 开始
    ax.add_patch(Ellipse((x, 11.35), 1.15, 0.48, facecolor="white", edgecolor=LINE, lw=1.05, zorder=3))
    text(ax, x, 11.35, "开始", size=10, weight="bold")

    # 2. 输入与初始化
    rounded_box(ax, x, 10.45, 4.0, 0.66, "输入参数并初始化",
                "几何/物性 · 初始场 · 边界条件")
    down(ax, 11.11, 10.78)

    # 3~6. 四个算法模块
    module_box(ax, 1, x, 9.30, 4.45, 0.80, "有限体积空间离散",
               "分层控制体积分 · 构造离散方程组")
    down(ax, 10.12, 9.70)

    module_box(ax, 2, x, 8.05, 4.45, 0.80, "后向欧拉时间推进",
               "隐式离散 · 形成稳定代数方程组")
    down(ax, 8.90, 8.45)

    module_box(ax, 3, x, 6.80, 4.45, 0.80, "一阶顺序分裂",
               "依次更新组分输运 · 相变 · 物性与源项")
    down(ax, 7.65, 7.20)

    module_box(ax, 4, x, 5.55, 4.45, 0.80, "热-电 Picard 迭代",
               "由 T 求电压与产热 → 求解新温度场")
    down(ax, 6.40, 5.95)

    # 7. Picard 收敛判断
    diamond(ax, x, 4.30, 3.0, 0.88, "max|ΔT| < ε ？")
    down(ax, 5.15, 4.74)

    # 8. 终止条件判断
    diamond(ax, x, 2.90, 2.7, 0.80, "达到终止条件？")
    down(ax, 3.74, 3.30)

    # 9. 输出
    rounded_box(ax, x, 1.85, 2.2, 0.62, "输出计算结果", fill=LIGHT, size=10)
    down(ax, 2.50, 2.16)

    # --- Picard 循环（否 → 回到模块④）---
    text(ax, 5.45, 4.30, "否", size=8.6, color=LINE)
    arrow(ax, (5.00, 4.30), (6.10, 4.30))
    ax.plot([6.10, 6.10], [4.30, 5.55], color=LINE, lw=1.05, zorder=1)
    arrow(ax, (6.10, 5.55), (5.73, 5.55))
    text(ax, 6.22, 4.95, "m ← m+1", size=8.0, color=LINE, ha="left", latin=True)

    # --- 时间循环（否 → 回到模块②）---
    text(ax, 1.78, 2.90, "否", size=8.6, color=LINE)
    arrow(ax, (2.15, 2.90), (0.95, 2.90))
    ax.plot([0.95, 0.95], [2.90, 8.05], color=LINE, lw=1.05, zorder=1)
    arrow(ax, (0.95, 8.05), (1.27, 8.05))
    text(ax, 1.02, 5.45, "n ← n+1", size=8.0, color=LINE, rotation=90, latin=True)

    # 判断的"是"分支
    text(ax, 3.62, 3.72, "是", size=8.6, color=LINE, ha="left")
    text(ax, 4.90, 2.90, "是", size=8.6, color=LINE)

    out = OUT / "数值求解算法流程图_简化版"
    for ext, kw in [(".pdf", {}), (".png", {"dpi": 400})]:
        fig.savefig(str(out) + ext, bbox_inches="tight", pad_inches=0.06, **kw)
    plt.close(fig)
    print("saved:", str(out) + ".pdf")


if __name__ == "__main__":
    draw()
