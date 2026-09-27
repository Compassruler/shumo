"""问题三逐图脚本共用的读取、样式、圆点和导出工具。"""
from pathlib import Path
import argparse
import csv
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUTPUT = ROOT / "figures"

# Matplotlib 需要可写缓存；放在问题三图片目录中，避免依赖个人主目录。
OUTPUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT / ".matplotlib"))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator

COLORS = {
    "P": "#316D9C", "C": "#C77835", "R": "#398476",
    "neutral": "#737A80", "danger": "#A44848", "grid": "#D9DEE3",
    "cell1": "#316D9C", "cell2": "#C77835", "cell3": "#398476",
    "purple": "#9B8AAD", "gray": "#B8BDC1",
}
NAMES = {"P": "P 纯预热", "C": "C 协同加热", "R": "R 稳健预热（附加）"}
CELL_COLORS = [COLORS["cell1"], COLORS["cell2"], COLORS["cell3"]]

# 与问题一图01一致：实心圆、无连接线、细白边。
DISCRETE_MARKER_SIZE = 2.0


def configure_style():
    """设置中文字体和论文图通用样式。"""
    # macOS 自带华文黑体时直接从字体文件加载，保证 PDF/SVG 中文稳定。
    font_path = Path("/System/Library/Fonts/STHeiti Light.ttc")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        font = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        candidates = ["Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", "SimHei"]
        available = {item.name for item in font_manager.fontManager.ttflist}
        font = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [font, "DejaVu Sans"],
        "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 11,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "axes.unicode_minus": False, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#555B61",
        "axes.linewidth": .7, "axes.grid": True, "grid.alpha": .35,
        "grid.color": COLORS["grid"], "grid.linewidth": .55,
        "savefig.facecolor": "white", "figure.facecolor": "white",
        "pdf.fonttype": 42, "svg.fonttype": "none",
        "mathtext.fontset": "dejavusans",
    })


def read_csv(name):
    """读取数值 CSV；不能转为数值的字段保留为字符串。"""
    path = DATA / name
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"{path.name} 没有数据。")
    result = {}
    for key in rows[0]:
        values = [row[key] for row in rows]
        try:
            result[key] = np.asarray(values, dtype=float)
        except (TypeError, ValueError):
            result[key] = np.asarray(values, dtype=object)
    return result


def read_summary():
    """按 P、C、R 三种策略读取汇总结果。"""
    table = read_csv("summary_results.csv")
    result = {}
    for index, key in enumerate(table["strategy"]):
        key = str(key).strip()
        if key in NAMES:
            result[key] = {name: values[index] for name, values in table.items()}
    if set(result) != {"P", "C", "R"}:
        raise ValueError("summary_results.csv 必须包含 P、C、R 三种策略。")
    return result


def read_traces(*names):
    """读取指定轨迹，例如 P、C、P_postload、R。"""
    traces = {name: read_csv(f"trajectory_{name}.csv") for name in names}
    for name, trace in traces.items():
        time = trace["time_s"]
        if len(time) < 2 or np.any(np.diff(time) < 0):
            raise ValueError(f"trajectory_{name}.csv 的时间序列无效。")
    return traces


def cells(trace, field):
    """将五片单电池的同名字段组成 n×5 数组。"""
    return np.column_stack([trace[f"cell{k}_{field}"] for k in range(1, 6)])


def temperatures(trace):
    """将五片单电池温度组成 n×5 数组。"""
    return np.column_stack([trace[f"T{k}_C"] for k in range(1, 6)])


def discrete_points(ax, x, y, color, label=None, size=DISCRETE_MARKER_SIZE,
                    alpha=.92, zorder=3):
    """按问题一图01样式绘制离散实心圆点，不添加连接线。"""
    return ax.plot(x, y, linestyle="None", marker="o", markersize=size,
                   markerfacecolor=color, markeredgecolor="white",
                   markeredgewidth=.25, color=color, alpha=alpha,
                   label=label, zorder=zorder)[0]


def decorate(ax, ylabel=None, xlabel="时间 / s"):
    """统一坐标轴、网格和刻度。"""
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(MaxNLocator(6))
    ax.yaxis.set_major_locator(MaxNLocator(6))
    ax.tick_params(direction="out", length=3)
    ax.set_axisbelow(True)


def panel_title(ax, text):
    ax.set_title(text, loc="left", pad=8, fontweight="medium")


def note(fig, text):
    fig.text(.08, .015, text, va="bottom", ha="left", fontsize=8.5, color="#545B62")


def num(value, digits=3):
    value = float(value)
    if abs(value) < 1e-12:
        return "0"
    if abs(value) < 1e-3:
        return f"{value:.2e}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def cli(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--no-show", action="store_true", help="只导出，不打开交互窗口。")
    parser.add_argument("--no-save", action="store_true", help="只预览，不覆盖图片。")
    return parser.parse_args()


def export_and_show(fig, stem, args, adjust=None):
    """导出矢量 PDF/SVG 和 300 dpi PNG，并按需显示交互窗口。"""
    if adjust:
        fig.subplots_adjust(**adjust)
    if not args.no_save:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUTPUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=.13)
        fig.savefig(OUTPUT / f"{stem}.svg", bbox_inches="tight", pad_inches=.13)
        fig.savefig(OUTPUT / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=.13)
        print(f"已保存：{OUTPUT / stem}.[pdf|svg|png]")
    if not args.no_show:
        plt.show()
    plt.close(fig)
