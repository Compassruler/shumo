"""问题一单图脚本共用工具：读取数据、统一样式、导出和交互显示。"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.transforms import ScaledTranslation

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
OUTPUT = ROOT / 'figures'

# 全局颜色只提供默认值；每张图仍可在自己的文件开头覆盖。
COLORS = {
    'main': '#0072B2', 'bp': '#D55E00', 'experiment': '#C44E52',
    'pore': '#009E73', 'membrane': '#CC79A7', 'saturation': '#A66F00',
    'activation': '#56B4E9', 'ohmic': '#E69F00', 'concentration': '#8C6BB1',
    'phase': '#008B8B', 'loss': '#C44E52', 'residual': '#5F6368',
}
# 离散数据统一采用图01的样式：实心圆、无连接线、细白边。
# 连续模型结果仍按曲线或色块表达。
DISCRETE_MARKER_SIZE = 2.0  # 与图01中的模型计算点大小一致
CASES = [
    ('main_minus20', '五层基线', '−20 ℃'),
    ('main_minus25', '五层基线', '−25 ℃'),
    ('bp_minus20', '含双极板修订', '−20 ℃'),
    ('bp_minus25', '含双极板修订', '−25 ℃'),
]


def configure_style():
    """设置论文图的中文字体、字号、坐标轴和网格。"""
    font_path = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        family = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        installed = {f.name for f in font_manager.fontManager.ttflist}
        family = next((f for f in ['Noto Sans CJK SC', 'Source Han Sans SC',
                                    'Microsoft YaHei', 'SimHei'] if f in installed),
                      'DejaVu Sans')
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [family, 'Arial', 'DejaVu Sans'],
        'font.size': 8.5, 'axes.labelsize': 9, 'axes.titlesize': 9,
        'axes.titleweight': 'semibold', 'axes.titlelocation': 'left',
        'axes.titlepad': 8, 'axes.unicode_minus': False, 'axes.linewidth': .75,
        'axes.spines.top': False, 'axes.spines.right': False,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
        'legend.fontsize': 8, 'legend.frameon': False,
        'lines.linewidth': 1.65, 'savefig.dpi': 300,
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.grid': True, 'grid.color': '#D9DEE5', 'grid.alpha': .58,
        'grid.linewidth': .50, 'figure.facecolor': 'white',
        'axes.facecolor': 'white', 'mathtext.fontset': 'dejavusans',
    })


def read_csv(name, required=()):
    """读取 data/ 下的 CSV，并尽量把数值列转换为浮点数组。"""
    path = DATA / name
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        names, rows = reader.fieldnames or [], list(reader)
    missing = set(required).difference(names)
    if missing:
        raise ValueError(f'{name} 缺少字段：{sorted(missing)}')
    if not rows:
        raise ValueError(f'{name} 没有数据')
    result = {}
    for key in names:
        try:
            result[key] = np.array([float(r[key]) if r[key] else np.nan for r in rows])
        except ValueError:
            result[key] = np.array([r[key] for r in rows], dtype=object)
    return result


def read_cases():
    """读取四种主工况时序表。"""
    return {key: read_csv(f'{key}.csv') for key, _, _ in CASES}


def panel_title(ax, text):
    """绘制独立加粗的子图编号和普通标题。"""
    match = re.match(r'^\(([a-z])\)\s*(.*)$', text)
    if not match:
        raise ValueError(f'子图标题必须以 (a) 形式开头：{text}')
    letter, title = match.groups()
    ax.set_title(title)
    offset = ScaledTranslation(-13 / 72, 3 / 72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, letter, transform=ax.transAxes + offset,
            fontsize=9, fontweight='bold', ha='left', va='bottom')


def panel(ax, text, ylabel=None, zero=False):
    """设置常规 0–35 s 时序子图。"""
    panel_title(ax, text)
    ax.set_xlabel('时间 / s')
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.set_xlim(0, 35)
    ax.set_xticks(np.arange(0, 36, 5))
    ax.margins(y=.12)
    if zero:
        _, high = ax.get_ylim()
        ax.set_ylim(0, max(high, 1e-10))
    ax.set_axisbelow(True)


def shared_legend(fig, handles, ncol=3, labels=None):
    """在整图顶部放共享图例。"""
    if labels is None:
        labels = [h.get_label() for h in handles]
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, 1.005),
               ncol=ncol, columnspacing=1.6, handlelength=2.6, borderaxespad=.1)


def discrete_points(ax, x, y, color, label, size=DISCRETE_MARKER_SIZE, zorder=3):
    """按图01标准绘制离散数据：实心圆、无连接线、细白边。"""
    return ax.plot(x, y, marker='o', linestyle='None', color=color,
                   markersize=size, markerfacecolor=color,
                   markeredgecolor='white', markeredgewidth=.25,
                   alpha=.92, label=label, zorder=zorder)[0]


def export_and_show(fig, stem, args, layout=None):
    """按需导出并显示图片；显示窗口关闭后脚本才结束。"""
    if layout:
        fig.subplots_adjust(**layout)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not args.no_save:
        for suffix in ['pdf', 'svg', 'png']:
            fig.savefig(OUTPUT / f'{stem}.{suffix}', bbox_inches='tight',
                        pad_inches=.09, dpi=300,
                        metadata={'Creator': f'{Path(__file__).name} / {stem}'}
                        if suffix in {'pdf', 'svg'} else None)
        print(f'已保存：{OUTPUT / stem}.[pdf|svg|png]')
    if not args.no_show:
        print('已打开交互预览窗口；关闭窗口后程序结束。')
        plt.show()
    else:
        plt.close(fig)


def cli(description):
    """每张单图脚本共用的命令行参数。"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--no-show', action='store_true', help='不弹出交互窗口，用于自动运行。')
    parser.add_argument('--no-save', action='store_true', help='只预览，不覆盖 PDF/SVG/PNG。')
    return parser.parse_args()


def select(data, **filters):
    """按模型、工况或参数等条件筛选列式数据。"""
    mask = np.ones(len(next(iter(data.values()))), dtype=bool)
    for key, value in filters.items():
        mask &= np.isclose(data[key], value) if isinstance(value, (int, float)) else data[key] == value
    return {key: value[mask] for key, value in data.items()}


def field_grid(data, key):
    """把长表时空数据整理为“空间 × 时间”矩阵。"""
    times, locations = np.unique(data['t_s']), np.unique(data['x_um'])
    z = np.full((len(locations), len(times)), np.nan)
    ti, xi = np.searchsorted(times, data['t_s']), np.searchsorted(locations, data['x_um'])
    z[xi, ti] = data[key]
    if not np.isfinite(z).all():
        raise ValueError(f'{key} 时空网格不完整')
    layers = np.array([data['layer'][np.flatnonzero(data['x_um'] == x)[0]] for x in locations])
    return times, locations, z, layers


def sample_edges(values):
    """把采样中心转换为网格边界。"""
    return np.r_[values[0]-(values[1]-values[0])/2,
                 (values[:-1]+values[1:])/2,
                 values[-1]+(values[-1]-values[-2])/2]


def spatial_edges(x, layers):
    """逐材料层恢复有限体积单元的真实空间边界。"""
    edges = np.full(len(x)+1, np.nan)
    breaks = np.r_[0, np.flatnonzero(layers[1:] != layers[:-1])+1, len(x)]
    for start, stop in zip(breaks[:-1], breaks[1:]):
        positions = x[start:stop]
        step = float(np.median(np.diff(positions)))
        layer_edges = np.r_[positions[0]-step/2, positions+step/2]
        edges[start:stop+1] = layer_edges
    return edges
