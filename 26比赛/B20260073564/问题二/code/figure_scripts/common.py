"""问题二逐图脚本共用工具。只读取已有 CSV，不运行仿真。"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
# 优先使用当前 Python 环境中已验证可用的 NumPy/Matplotlib。
# 问题二目录中的 .python_deps 主要服务模型计算，可能与当前 Python 版本不匹配，
# 因此仅在系统环境确实缺包时作为后备路径。
try:
    import numpy as np
    import matplotlib.pyplot as plt
except ImportError:
    sys.path.append(str(ROOT / '.python_deps'))
    import numpy as np
    import matplotlib.pyplot as plt
from matplotlib import font_manager

DATA = ROOT / 'data'
OUTPUT = ROOT / 'figures'
COLORS = ['#0072B2', '#D55E00', '#009E73', '#777777']
NAMES = {'constant': '恒流加载', 'ramp': '线性斜坡加载', 'step': '阶梯加载'}
DISCRETE_MARKER_SIZE = 2.0  # 与问题一图01中的模型计算点一致


def configure_style():
    """采用与问题一一致的论文图字体和坐标轴风格。"""
    candidates = [Path('C:/Windows/Fonts/msyh.ttc'),
                  Path('/System/Library/Fonts/STHeiti Light.ttc'),
                  Path('/System/Library/Fonts/Supplemental/Songti.ttc')]
    font_path = next((p for p in candidates if p.exists()), None)
    if font_path:
        font_manager.fontManager.addfont(str(font_path))
        family = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        family = 'DejaVu Sans'
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [family, 'Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
        'font.size': 8.5, 'axes.labelsize': 9, 'axes.titlesize': 9,
        'legend.fontsize': 8, 'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
        'axes.titleweight': 'semibold', 'axes.unicode_minus': False,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .75, 'grid.alpha': .45, 'grid.linewidth': .5,
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'savefig.facecolor': 'white', 'figure.facecolor': 'white',
    })


def read_table(name):
    """读取 data/ 下的 UTF-8 CSV。"""
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f'找不到数据文件：{path}')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f'数据文件为空：{path}')
    return rows


def numeric(rows, key):
    """把 CSV 的指定字段转换为浮点数组。"""
    return np.asarray([float(row.get(key, '') or 'nan') for row in rows])


def pick(rows, *keys):
    """返回数据中第一个存在的候选字段名。"""
    return next((key for key in keys if rows and key in rows[0]), None)


def field(row, *keys, default=''):
    """从一行数据中读取第一个非空候选字段。"""
    return next((row[k] for k in keys if k in row and row[k] != ''), default)


def axis(ax, ylabel, xlabel='时间 / s'):
    """设置普通坐标轴的单位、网格和刻度方向。"""
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.grid(True); ax.tick_params(direction='out', length=3)
    ax.set_axisbelow(True)


def discrete_points(ax, x, y, color, label=None, size=DISCRETE_MARKER_SIZE,
                    zorder=3, face=True):
    """按问题一图01标准画离散数据：圆点、无连接线、细白边。"""
    facecolor = color if face else 'white'
    return ax.plot(x, y, marker='o', linestyle='None', color=color,
                   markersize=size, markerfacecolor=facecolor,
                   markeredgecolor='white' if face else color,
                   markeredgewidth=.25, alpha=.92,
                   label=label, zorder=zorder)[0]


def load_trajectories():
    """读取三种加载策略的轨迹表。"""
    result = {}
    for kind in NAMES:
        name = f'trajectory_{kind}.csv'
        path = DATA / name
        if path.exists():
            result[kind] = read_table(name)
    if not result:
        raise FileNotFoundError('未找到 trajectory_constant/ramp/step.csv')
    return result


def strategy_panels(trajectories, height=3.8):
    """按现有加载策略数量创建一排子图。"""
    return plt.subplots(1, len(trajectories), figsize=(4.35*len(trajectories), height),
                        squeeze=False, layout='constrained')


def cli(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--no-show', action='store_true', help='不打开交互窗口。')
    parser.add_argument('--no-save', action='store_true', help='只预览，不覆盖图片。')
    return parser.parse_args()


def export_and_show(fig, stem, args):
    """保存矢量 PDF/SVG 和 300 dpi PNG，并按需弹出交互窗口。"""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not args.no_save:
        for suffix in ['pdf', 'svg', 'png']:
            fig.savefig(OUTPUT / f'{stem}.{suffix}', bbox_inches='tight',
                        pad_inches=.09, dpi=300,
                        metadata={'Creator': f'Question 2 / {stem}'}
                        if suffix in {'pdf', 'svg'} else None)
        print(f'已保存：{OUTPUT / stem}.[pdf|svg|png]')
    if not args.no_show:
        print('已打开交互预览窗口；关闭窗口后程序结束。')
        plt.show()
    else:
        plt.close(fig)
