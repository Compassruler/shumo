#!/usr/bin/env python3
"""直接读取问题一的 Python 计算结果 CSV，生成论文插图。

常用命令：
  python code/plot_results.py [--root RESULT_DIRECTORY]
  python code/plot_results.py --figure 01
  python code/plot_results.py --figure 01_main_experiment_comparison

默认生成全部图片；使用 ``--figure`` 只重新生成一张图，适合逐图精细调整。
CSV 统一以 utf-8-sig 编码读取。输出包括 figures/*.pdf、*.svg、*.png
以及 figures/figure_manifest.json。本脚本只绘图，不重新拟合、不平滑数据，
也不修改 Python 算法的计算结果。五层基线和含双极板修订模型始终明确区分。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(DEFAULT_ROOT / '.mplconfig'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import ScaledTranslation

NATURE_FIGURE_SCRIPTS = Path.home() / '.codex' / 'skills' / 'nature-figure' / 'scripts'
if not NATURE_FIGURE_SCRIPTS.is_dir():
    raise RuntimeError('nature-figure QA scripts are required to export the figures.')
sys.path.insert(0, str(NATURE_FIGURE_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

# 全局配色：参考 Okabe-Ito 色盲友好方案，并配合不同线型保证黑白打印可区分。
# 若要统一修改所有图的颜色，优先修改此处；若只改一张图，可在对应函数内设局部颜色。
COLORS = {'main': '#0072B2', 'bp': '#D55E00', 'exp': '#202124',
          'pore': '#009E73', 'mem': '#CC79A7', 'sat': '#A66F00',
          'act': '#56B4E9', 'ohm': '#E69F00', 'con': '#8C6BB1',
          'loss': '#C44E52', 'phase': '#008B8B', 'residual': '#5F6368'}
CASES = [('main_minus20', '五层基线', '−20 ℃'),
         ('main_minus25', '五层基线', '−25 ℃'),
         ('bp_minus20', '含双极板修订', '−20 ℃'),
         ('bp_minus25', '含双极板修订', '−25 ℃')]
REQUIRED = ['t_s', 'V_exp_V', 'V_model_V', 'V_rel_error_pct', 'T_exp_C',
            'T_model_C', 'T_rel_error_pct', 'ice_max_bulk', 'ice_pore_max_bulk',
            'ice_mem_max_bulk', 's_ice_pore_max', 'E_rev_V', 'eta_act_V',
            'eta_ohm_V', 'eta_con_V', 'water_produced_kg_m2',
            'water_stored_kg_m2', 'water_initial_kg_m2', 'water_out_kg_m2', 'water_balance_kg_m2',
            'heat_gen_J_m2', 'heat_phase_J_m2', 'heat_loss_J_m2',
            'energy_balance_J_m2']


def configure_style():
    """设置中文字体、字号、线宽、网格和矢量文字等全局绘图样式。"""
    # macOS 优先使用系统黑体；其他系统依次尝试常见中文无衬线字体。
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
        'font.sans-serif': [family, 'Arial', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 8.5, 'axes.labelsize': 9,
        'axes.titlesize': 9, 'axes.titleweight': 'semibold',
        'axes.titlelocation': 'left', 'axes.titlepad': 8,
        'axes.unicode_minus': False, 'axes.linewidth': .75,
        'axes.spines.top': False, 'axes.spines.right': False,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.labelsize': 7.5, 'ytick.labelsize': 7.5,
        'legend.fontsize': 8, 'legend.frameon': False,
        'lines.linewidth': 1.65, 'savefig.dpi': 300,
        'svg.fonttype': 'none',
        'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.grid': True, 'grid.color': '#D9DEE5', 'grid.alpha': .58,
        'grid.linewidth': .50, 'figure.facecolor': 'white',
        'axes.facecolor': 'white', 'mathtext.fontset': 'dejavusans',
    })


def read_csv(path: Path, required=None):
    """读取一个 CSV，并检查绘图必需字段是否存在、数据是否为空。"""
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        names = reader.fieldnames or []
        rows = list(reader)
    missing = set(required or []).difference(names)
    if missing:
        raise ValueError(f'{path.name}: missing columns {sorted(missing)}')
    if not rows:
        raise ValueError(f'{path.name}: empty data')
    data = {}
    for name in names:
        if name == 'layer':
            data[name] = np.array([row[name] for row in rows], dtype=object)
        else:
            try:
                data[name] = np.array([float(row[name]) if row[name] else np.nan
                                       for row in rows], dtype=float)
            except ValueError:
                data[name] = np.array([row[name] for row in rows], dtype=object)
    return data


def panel_title(ax, label):
    """把加粗子图编号 (a) 与普通子图标题分开排版。"""
    match = re.match(r'^\(([a-z])\)\s*(.*)$', label)
    if not match:
        raise ValueError(f'Panel title must start with a lowercase label: {label}')
    letter, title = match.groups()
    ax.set_title(title)
    offset = ScaledTranslation(-13 / 72, 3 / 72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, letter, transform=ax.transAxes + offset,
            fontsize=9, fontweight='bold', ha='left', va='bottom')


def panel(ax, label, ylabel=None, zero=False):
    """设置普通时序子图的标题、单位、0–35 s 横轴和可选零起点纵轴。"""
    panel_title(ax, label)
    ax.set_xlabel('时间 / s')
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.set_xlim(0, 35)
    ax.set_xticks(np.arange(0, 36, 5))
    ax.margins(y=.12)
    if zero:
        low, high = ax.get_ylim()
        ax.set_ylim(0, max(high, 1e-6))
    ax.set_axisbelow(True)


def shared_legend(fig, handles, labels=None, ncol=3):
    """在整张图顶部建立共享图例，减少各子图内的重复和遮挡。"""
    if labels is None:
        labels = [h.get_label() for h in handles]
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, 1.005),
               ncol=ncol, columnspacing=1.6, handlelength=2.6, borderaxespad=.1)


def discrete_points(ax, x, y, color, label=None, size=2.0, zorder=3):
    """按图01标准绘制离散序列：实心圆、无连接线、细白边。"""
    return ax.plot(x, y, 'o', linestyle='None', color=color,
                   markersize=size, markerfacecolor=color,
                   markeredgecolor='white', markeredgewidth=.25,
                   alpha=.92, label=label, zorder=zorder)[0]


def finish(fig, output: Path, stem: str, caption: str, sources, manifest,
           top=.91, bottom=.09, wspace=.30, hspace=.40):
    """统一完成版式检查，并导出 PDF、SVG、300 dpi PNG。"""
    # 此处的 left/right/top/bottom/wspace/hspace 是调整子图间距的主要入口。
    fig.subplots_adjust(left=.09, right=.96, bottom=bottom, top=top,
                        wspace=wspace, hspace=hspace)
    qa_dir = output / 'qa'
    qa_dir.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(
        fig,
        json_out=qa_dir / f'{stem}.alignment.json',
        overlay_svg=qa_dir / f'{stem}.alignment.svg',
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
    )
    for suffix in ['pdf', 'svg', 'png']:
        fig.savefig(output / f'{stem}.{suffix}', bbox_inches='tight',
                    pad_inches=.09, dpi=300,
                    metadata={'Creator': 'Question 1 plot_results.py'}
                    if suffix in {'pdf', 'svg'} else None)
    plt.close(fig)
    manifest.append({'id': stem, 'caption': caption,
                     'pdf': f'figures/{stem}.pdf', 'svg': f'figures/{stem}.svg',
                     'png': f'figures/{stem}.png',
                     'alignment': f'figures/qa/{stem}.alignment.json',
                     'sources': [f'data/{p}' for p in sources]})


def plot_main_fit(all_data, output, manifest):
    """图01：五层基线的电压、温度计算值与全部实验采样点对比。"""
    # figsize=(宽, 高)，单位为英寸；修改后坐标轴会由 Matplotlib 自动重排。
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    # 图01实验点的局部配色；只改这里不会影响其他图片。
    experiment_color = '#C44E52'
    for col, temp in enumerate(['20', '25']):
        d = all_data[f'main_minus{temp}']
        for row, (measure, ylabel) in enumerate([('V', '电压 / V'),
                                               ('T', '温度 / ℃')]):
            ax = axes[row, col]
            # 显示全部实验采样点，不抽样；实心圆与蓝色模型曲线形成清晰区分。
            # markersize 控制圆点大小，markeredgewidth 控制白色细边宽度。
            exp = ax.plot(d['t_s'], d[f'{measure}_exp_' + ('V' if row == 0 else 'C')],
                          'o', color=experiment_color, markersize=3.0,
                          markerfacecolor=experiment_color,
                          markeredgecolor='white', markeredgewidth=.25,
                          alpha=.92, label='实验采样值', zorder=3)[0]
            mod = discrete_points(
                ax, d['t_s'], d[f'{measure}_model_' + ('V' if row == 0 else 'C')],
                COLORS['main'], '五层基线', size=2.0, zorder=2)
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, mod], ncol=2)
    finish(fig, output, '01_main_experiment_comparison',
           '五层基线电压、温度与实验采样值的对比；模型结果与实验数据采用相同采样时刻。',
           ['main_minus20.csv', 'main_minus25.csv'], manifest)


def plot_bp_comparison(all_data, output, manifest):
    """图02：实验值、五层基线与含双极板修订模型的结构对比。"""
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    for col, temp in enumerate(['20', '25']):
        main = all_data[f'main_minus{temp}']
        bp = all_data[f'bp_minus{temp}']
        for row, (key, ylabel, expkey) in enumerate([
                ('V_model_V', '电压 / V', 'V_exp_V'),
                ('T_model_C', '温度 / ℃', 'T_exp_C')]):
            ax = axes[row, col]
            exp = ax.plot(main['t_s'], main[expkey], 'o', linestyle='None',
                          color='#C44E52', markersize=3.0,
                          markerfacecolor='#C44E52', markeredgecolor='white',
                          markeredgewidth=.25, alpha=.92,
                          label='实验采样值', zorder=4)[0]
            p1 = discrete_points(ax, main['t_s'], main[key], COLORS['main'],
                                 '五层基线', size=2.0, zorder=2)
            p2 = discrete_points(ax, bp['t_s'], bp[key], COLORS['bp'],
                                 '含双极板修订', size=2.0, zorder=2)
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, p1, p2], ncol=3)
    finish(fig, output, '02_bp_structural_comparison',
           '五层基线与含双极板修订模型的电压、温度响应。BP 曲线为纳入双极板热容量后的修订计算结果，与五层基线分开表示。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_errors(all_data, output, manifest):
    """图03：两类模型在各实验采样时刻的电压和温度相对误差。"""
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    for col, temp in enumerate(['20', '25']):
        for row, (key, ylabel) in enumerate([
                ('V_rel_error_pct', '电压相对误差 / %'),
                ('T_rel_error_pct', '温度相对误差（摄氏口径）/ %')]):
            ax = axes[row, col]
            handles = []
            for model, label in [('main', '五层基线'),
                                 ('bp', '含双极板修订')]:
                d = all_data[f'{model}_minus{temp}']
                handles.append(ax.plot(d['t_s'], d[key], 'o', linestyle='None',
                                       color=COLORS[model], markersize=3.0,
                                       markerfacecolor=COLORS[model],
                                       markeredgecolor='white', markeredgewidth=.25,
                                       alpha=.92, label=label, zorder=3)[0])
            ax.axhline(0, color='#8B929A', linewidth=.7, zorder=0)
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, handles, ncol=2)
    finish(fig, output, '03_sample_relative_errors',
           '各采样时刻的电压与温度相对误差；温度按建模推导文件使用实验摄氏温度的绝对值作为分母；开尔文分母误差另存 CSV。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_ice(all_data, output, manifest):
    """图04：四种工况的总冰、孔隙冰、膜相冰和孔隙冰饱和度。"""
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.1))
    handles = []
    for idx, (key, model, temp) in enumerate(CASES):
        d, ax = all_data[key], axes.flat[idx]
        p1 = discrete_points(ax, d['t_s'], d['ice_max_bulk'], COLORS['main'],
                             '最大总冰体积分数')
        p2 = discrete_points(ax, d['t_s'], d['ice_pore_max_bulk'], COLORS['pore'],
                             '最大孔隙冰体积分数')
        p3 = discrete_points(ax, d['t_s'], d['ice_mem_max_bulk'], COLORS['mem'],
                             '最大膜相冰体积分数')
        # 右轴单独显示孔隙冰饱和度，避免与左轴三个体积分数量级混淆。
        ax2 = ax.twinx()
        p4 = discrete_points(ax2, d['t_s'], d['s_ice_pore_max'], COLORS['sat'],
                             '最大孔隙冰饱和度（右轴）')
        ax2.grid(False)
        ax2.spines['right'].set_visible(True)
        ax2.set_ylabel('孔隙冰饱和度', color=COLORS['sat'])
        ax2.tick_params(axis='y', colors=COLORS['sat'])
        ax2.set_ylim(0, max(1.08 * np.nanmax(d['s_ice_pore_max']), 1e-10))
        ax2.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
        panel(ax, f'({chr(97 + idx)}) {model} · {temp}', '冰体积分数', zero=True)
        handles = [p1, p2, p3, p4]
    shared_legend(fig, handles, ncol=2)
    finish(fig, output, '04_ice_fraction_saturation',
           '四组计算的最大总冰、孔隙冰、膜相冰体积分数及最大孔隙冰饱和度。各最大值可位于不同空间位置。',
           [f'{key}.csv' for key, _, _ in CASES], manifest,
           top=.885, wspace=.42)


def plot_voltage_terms(all_data, output, manifest):
    """图05：模型电压以及活化、欧姆、浓差损失的堆叠分解。"""
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    labels = ['模型电压', '活化损失', '欧姆损失', '浓差损失']
    palette = ['#DCE6EC', COLORS['act'], COLORS['ohm'], COLORS['con']]
    for idx, (key, model, temp) in enumerate(CASES):
        d, ax = all_data[key], axes.flat[idx]
        ax.stackplot(d['t_s'], d['V_model_V'], d['eta_act_V'], d['eta_ohm_V'],
                     d['eta_con_V'], colors=palette, alpha=.88, linewidth=0)
        discrete_points(ax, d['t_s'], d['V_model_V'], COLORS['main'], '模型电压')
        discrete_points(ax, d['t_s'], d['E_rev_V'], '#252A34', '可逆电压')
        panel(ax, f'({chr(97 + idx)}) {model} · {temp}', '电压及损失 / V', zero=True)
    handles = [Patch(facecolor=c, label=l) for c, l in zip(palette, labels)]
    handles.append(Line2D([0], [0], marker='o', linestyle='None', markersize=2,
                          color='#252A34', label='可逆电压'))
    shared_legend(fig, handles, ncol=5)
    finish(fig, output, '05_voltage_loss_decomposition',
           '模型电压与活化、欧姆、浓差损失的堆叠分解；虚线表示可逆电压。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_balances(all_data, output, manifest):
    """图06：含双极板修订模型的水量、热量累计值及守恒残差。"""
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.1))
    water_handles = []
    heat_handles = []
    for col, temp in enumerate(['20', '25']):
        d = all_data[f'bp_minus{temp}']
        ax = axes[0, col]
        for key, label, color in [
                ('water_produced_kg_m2', '累计产水', COLORS['main']),
                ('water_stored_kg_m2', '储水量变化', COLORS['pore']),
                ('water_out_kg_m2', '累计排水', COLORS['bp'])]:
            amount = d[key] - d['water_initial_kg_m2'] if key == 'water_stored_kg_m2' else d[key]
            line = discrete_points(ax, d['t_s'], amount * 1e3, color, label)
            if col == 0:
                water_handles.append(line)
        # 守恒残差数量级很小，因此使用右轴，避免被左轴累计量淹没。
        twin = ax.twinx()
        discrete_points(twin, d['t_s'], d['water_balance_kg_m2'] * 1e3,
                        '#7A7E86', '收支残差')
        twin.grid(False)
        twin.set_ylabel('水收支残差 / (g/m²)', color='#7A7E86', fontsize=8.5)
        twin.tick_params(axis='y', colors='#7A7E86', labelsize=8)
        twin.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
        twin.spines['right'].set_visible(True)
        panel(ax, f'({chr(97 + col)}) 含双极板修订 · −{temp} ℃', '水量 / (g/m²)')
        ax = axes[1, col]
        for key, label, color in [
                ('heat_gen_J_m2', '累计产热', COLORS['main']),
                ('heat_phase_J_m2', '累计相变放热', COLORS['phase']),
                ('heat_loss_J_m2', '累计散热', COLORS['loss'])]:
            line = discrete_points(ax, d['t_s'], d[key] / 1e3, color, label)
            if col == 0:
                heat_handles.append(line)
        twin = ax.twinx()
        discrete_points(twin, d['t_s'], d['energy_balance_J_m2'],
                        '#7A7E86', '收支残差')
        twin.grid(False)
        twin.set_ylabel('能量收支残差 / (J/m²)', color='#7A7E86', fontsize=8.5)
        twin.tick_params(axis='y', colors='#7A7E86', labelsize=8)
        twin.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
        twin.spines['right'].set_visible(True)
        panel(ax, f'({chr(99 + col)}) 含双极板修订 · −{temp} ℃', '累计热量 / (kJ/m²)')
    residual = Line2D([0], [0], color=COLORS['residual'], marker='o',
                      linestyle='None', markersize=2, label='收支残差（右轴）')
    legend_kw = dict(ncol=4, fontsize=7.5, frameon=False,
                     columnspacing=1.15, handlelength=1.7, borderaxespad=0)
    fig.legend(handles=water_handles + [residual], loc='upper center',
               bbox_to_anchor=(.5, .985), **legend_kw)
    fig.legend(handles=heat_handles + [residual], loc='center',
               bbox_to_anchor=(.5, .475), **legend_kw)
    finish(fig, output, '06_bp_water_energy_balances',
           '含双极板修订模型的累计水量、累计热量及守恒残差。储水变化扣除初始存水量；相变热正号表示放热。灰色点线残差采用各面板右轴单独刻度。',
           ['bp_minus20.csv', 'bp_minus25.csv'], manifest,
           top=.84, bottom=.10, wspace=.52, hspace=.75)


def field_grid(data, key):
    """把长表形式的时空数据整理成“空间位置 × 时间”的完整矩阵。"""
    times = np.unique(data['t_s'])
    locations = np.unique(data['x_um'])
    z = np.full((len(locations), len(times)), np.nan)
    ti = np.searchsorted(times, data['t_s'])
    xi = np.searchsorted(locations, data['x_um'])
    if len(np.unique(xi * len(times) + ti)) != len(data['t_s']):
        raise ValueError('Field data has duplicate time-position pairs.')
    z[xi, ti] = data[key]
    if not np.isfinite(z).all():
        raise ValueError(f'Field data is incomplete or nonfinite for {key}.')
    layers = np.empty(len(locations), dtype=object)
    for i, x in enumerate(locations):
        layers[i] = data['layer'][np.flatnonzero(data['x_um'] == x)[0]]
    return times, locations, z, layers


def spatial_edges(x, layers):
    """根据有限体积单元中心重建每层的真实物理边界。"""
    # 各材料层内部网格均匀，但 BP/MEA 界面两侧单元宽度差异很大；
    # 若直接平均相邻中心会移动界面，因此必须逐层恢复单元边界。
    edges = np.full(len(x) + 1, np.nan)
    breaks = np.r_[0, np.flatnonzero(layers[1:] != layers[:-1]) + 1, len(x)]
    for start, stop in zip(breaks[:-1], breaks[1:]):
        positions = x[start:stop]
        if len(positions) < 2:
            raise ValueError('At least two cell centers per layer are required to infer physical boundaries.')
        widths = np.diff(positions)
        step = float(np.median(widths))
        if not np.allclose(widths, step, rtol=1e-7, atol=1e-7):
            raise ValueError('Expected uniformly spaced finite-volume cell centers within each layer.')
        layer_edges = np.r_[positions[0] - step / 2, positions + step / 2]
        if start and not np.isclose(edges[start], layer_edges[0], rtol=1e-7, atol=1e-6):
            raise ValueError('Layer boundaries inferred from adjacent grids do not agree.')
        edges[start:stop + 1] = layer_edges
    return edges


def sample_edges(values):
    """由采样中心位置计算 pcolormesh 所需的单元边界。"""
    if len(values) < 2:
        raise ValueError('At least two time samples are required.')
    return np.r_[values[0] - (values[1] - values[0]) / 2,
                 (values[:-1] + values[1:]) / 2,
                 values[-1] + (values[-1] - values[-2]) / 2]


def layer_boundaries(ax, x_edges, layers):
    """在时空场中用白色虚线标出材料层界面。"""
    transitions = np.flatnonzero(layers[1:] != layers[:-1])
    for i in transitions:
        ax.axhline(x_edges[i + 1], color='white', alpha=.6,
                   linewidth=.65, linestyle='--')


def plot_fields(model, fields, output, manifest):
    """图07/08：指定模型的局部温度和总冰体积分数时空分布。"""
    # 两个温度面板共用温度范围，两个冰面板共用冰含量范围，便于横向比较。
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.1))
    key_list = [f'{model}_minus20', f'{model}_minus25']
    t_min = min(np.min(fields[k]['T_C']) for k in key_list)
    t_max = max(np.max(fields[k]['T_C']) for k in key_list)
    i_max = max(np.max(fields[k]['ice_bulk']) for k in key_list)
    if i_max <= 0:
        i_max = 1e-6
    norms = [colors.Normalize(t_min, t_max), colors.Normalize(0, i_max)]
    images = []
    for row, variable in enumerate(['T_C', 'ice_bulk']):
        for col, temp in enumerate(['20', '25']):
            ax = axes[row, col]
            times, x, z, layers = field_grid(fields[f'{model}_minus{temp}'], variable)
            # 双极板修订模型：温度图显示完整结构，冰图只显示 MEA 区域。
            if model == 'bp' and row == 1:
                mea = ~np.isin(layers, ['aBP', 'cBP'])
                x, z, layers = x[mea], z[mea, :], layers[mea]
                if not len(x):
                    raise ValueError('No MEA cells remain after excluding bipolar plates.')
            x_edges = spatial_edges(x, layers)
            im = ax.pcolormesh(sample_edges(times), x_edges, z, shading='flat',
                               cmap='coolwarm' if row == 0 else 'YlGnBu',
                               norm=norms[row], rasterized=False)
            layer_boundaries(ax, x_edges, layers)
            panel_title(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃')
            ax.set_xlabel('时间 / s')
            ax.set_ylabel('MEA 位置 / μm' if model == 'bp' and row == 1 else '厚度方向位置 / μm')
            ax.set_xlim(0, 35)
            ax.set_xticks(np.arange(0, 36, 5))
            ax.grid(False)
            if col == 0:
                images.append(im)
    fig.subplots_adjust(left=.10, right=.86, bottom=.09, top=.95,
                        wspace=.31, hspace=.42)
    for row, im in enumerate(images):
        pos = axes[row, 1].get_position()
        cax = fig.add_axes([.89, pos.y0, .019, pos.height])
        bar = fig.colorbar(im, cax=cax)
        bar.solids.set_rasterized(False)
        bar.set_label('局部温度 / ℃' if row == 0 else '局部总冰体积分数', labelpad=9)
        bar.outline.set_linewidth(.6)
        if row == 1 and i_max < .01:
            bar.formatter.set_powerlimits((-2, 2))
            bar.update_ticks()
    name = '五层基线' if model == 'main' else '含双极板修订模型'
    stem = '07_main_spacetime_fields' if model == 'main' else '08_bp_spacetime_fields'
    # 色条坐标轴的位置已经手动固定，因此这里直接导出，不再调用 finish() 调整布局。
    qa_dir = output / 'qa'
    qa_dir.mkdir(parents=True, exist_ok=True)
    require_matplotlib_panel_alignment(
        fig,
        axes=list(axes.flat),
        json_out=qa_dir / f'{stem}.alignment.json',
        overlay_svg=qa_dir / f'{stem}.alignment.svg',
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=True,
        strict=True,
    )
    for ext in ['pdf', 'svg', 'png']:
        fig.savefig(output / f'{stem}.{ext}', bbox_inches='tight', pad_inches=.09,
                    dpi=300, metadata={'Creator': 'Question 1 plot_results.py'}
                    if ext in {'pdf', 'svg'} else None)
    plt.close(fig)
    manifest.append({'id': stem,
                     'caption': f'{name}局部温度与总冰体积分数时空分布。虚线表示计算层界面；同一行采用统一色标。' + ('双极板修订模型温度图显示整域，冰图显示 MEA 区域。' if model == 'bp' else ''),
                     'pdf': f'figures/{stem}.pdf', 'svg': f'figures/{stem}.svg',
                     'png': f'figures/{stem}.png',
                     'alignment': f'figures/qa/{stem}.alignment.json',
                     'sources': [f'data/fields_{key}.csv' for key in key_list]})



PHASE_LABELS = {'kf': '冻结', 'km': '融化', 'kcond': '凝结',
                'kevap': '蒸发', 'kdep': '凝华', 'ksub': '升华'}
PHASE_CHANNELS = {'cond': '凝结', 'evap': '蒸发', 'dep': '凝华',
                  'sub': '升华', 'frz': '冻结', 'mlt': '融化'}


def select(data, **filters):
    """按字符串或数值条件筛选已经读入的列式数据。"""
    mask = np.ones(len(next(iter(data.values()))), dtype=bool)
    for key, value in filters.items():
        mask &= np.isclose(data[key], value) if isinstance(value, (float, int)) else data[key] == value
    return {k: v[mask] for k, v in data.items()}


def plot_profile(root, output, manifest):
    """图09：冻结系数剖面，用于展示参数可辨识性而非置信区间。"""
    data = read_csv(root / 'data/冻结系数剖面.csv',
                    ['model', 'condition', 'kf_s_inv', 'mean_squared_relative_objective', 'ice_at35_bulk'])
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    handles = []
    for row, (model, title) in enumerate([('main', '五层基线'), ('bp', '含双极板修订')]):
        for condition, color, label in [('minus20', COLORS['main'], '−20 ℃：校准工况'),
                                        ('minus25', COLORS['bp'], '−25 ℃：留出工况')]:
            d = select(data, model=model, condition=condition)
            order = np.argsort(d['kf_s_inv'])
            for col, key in enumerate(['mean_squared_relative_objective', 'ice_at35_bulk']):
                x, y = d['kf_s_inv'][order], d[key][order]
                if not np.isfinite(x).all() or np.any(x <= 0):
                    raise ValueError('Freezing coefficients must be finite and strictly positive for the log axis.')
                if col == 1:
                    y = np.where(y > 0, y, np.nan)
                h = axes[row, col].plot(x, y, 'o', linestyle='None', color=color,
                                        markersize=3.0, markerfacecolor=color,
                                        markeredgecolor='white', markeredgewidth=.25,
                                        alpha=.92, label=label, zorder=3)[0]
                axes[row, col].set_xscale('log')
                if col == 1:
                    axes[row, col].set_yscale('log')
                axes[row, col].axvline(1, color='#888888', linewidth=.8, linestyle=':')
                axes[row, col].set_xlabel(r'冻结系数 $k_f$ / $\mathrm{s}^{-1}$')
            if row == 0:
                handles.append(h)
        axes[row, 0].set_ylabel('平均平方相对误差目标')
        axes[row, 1].set_ylabel('35 s 最大冰体积分数')
        for col in range(2):
            panel_title(axes[row, col], f'({chr(97 + row * 2 + col)}) {title}')
    handles.append(Line2D([0], [0], color='#888888', linestyle=':', label='固定基准 $k_f=1$'))
    shared_legend(fig, handles, ncol=3)
    finish(fig, output, '09_freezing_identifiability',
           '冻结系数剖面：每个固定 kf 仅用−20℃重新拟合 j0，再预测−25℃。所有曲线采用粗网格和0.05 s步长，不能与正式细网格末位混比；竖线表示固定基准kf=1。剖面用于判断参数非唯一性，不是置信区间。',
           ['冻结系数剖面.csv'], manifest, top=.91, hspace=.45)


def plot_phase_sensitivity(root, output, manifest):
    """图10：六个相变系数的一次一因子敏感性矩阵。"""
    data = read_csv(root / 'data/参数与闭合敏感性.csv')
    parameters = list(PHASE_LABELS)
    metrics = [('max_delta_V_V', 1e3, 'max |ΔV|\n/mV'),
               ('max_delta_T_C', 1, 'max |ΔT|\n/℃'),
               ('delta_ice_at35', 100, '|Δ冰35s|\n/百分点')]
    matrices = []
    for tag, _, _ in CASES:
        model, condition = tag.split('_', 1)
        d = select(data, model=model, condition=condition, kind='phase_one_at_a_time')
        a = np.array([[np.max(np.abs(select(d, parameter=p)[k])) * scale
                       for k, scale, _ in metrics] for p in parameters])
        matrices.append(a)
    # 每个指标在四个面板中使用同一个颜色归一化上限，保证颜色可以直接比较。
    scale = np.maximum(np.max(np.stack(matrices), axis=(0, 1)), 1e-15)
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.2))
    for idx, ((_, model, temp), a) in enumerate(zip(CASES, matrices)):
        ax = axes.flat[idx]
        z = a / scale
        ax.pcolormesh(np.arange(4), np.arange(7), z, cmap='Blues',
                      vmin=0, vmax=1, shading='flat', rasterized=False)
        ax.set_xlim(0, 3)
        ax.set_ylim(6, 0)
        ax.set_xticks(np.arange(3) + .5, [m[2] for m in metrics], fontsize=9)
        ax.set_yticks(np.arange(6) + .5,
                      [PHASE_LABELS[p] + ' · ' + p for p in parameters])
        for i in range(6):
            for j in range(3):
                val = a[i, j]
                label = '0' if val == 0 else (f'{val:.3g}' if val >= .001 else f'{val:.1e}')
                ax.text(j + .5, i + .5, label, ha='center', va='center', fontsize=9,
                        color='white' if z[i, j] > .65 else '#20252B')
        panel_title(ax, f'({chr(97 + idx)}) {model} · {temp}')
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.text(.5, .02, '每项均取单独调整至0.1倍、10倍的较大影响；颜色按各指标在四面板的共同最大值归一化，数值为实际变化。',
             ha='center', fontsize=8.3)
    finish(fig, output, '10_phase_coefficient_sensitivity',
           '六相变系数按完全相同的0.1倍/10倍扰动规则逐一检验，j0保持正式校准值。数字为两种扰动的最大绝对影响；V、T取全时段最大差，冰取35 s最大冰体积分数差并换算为百分点。所有敏感性轨迹及各自基准采用同网格、0.025 s步长。零影响仅表明本工况/窗口内没有激活或影响低于数值输出精度，不证明参数普遍不重要。',
           ['参数与闭合敏感性.csv'], manifest, top=.94, bottom=.12, wspace=.35, hspace=.55)


def plot_phase_amounts(all_data, output, manifest):
    """图11：六个相变通道的累计转化水量。"""
    fig, axes = plt.subplots(2, 3, figsize=(7.1, 4.8))
    handles = []
    for idx, (phase, label) in enumerate(PHASE_CHANNELS.items()):
        ax = axes.flat[idx]
        peak = 0
        for tag, model, temp in CASES:
            d = all_data[tag]
            amount = d[f'phase_{phase}_kg_m2'] * 1e3
            peak = max(peak, float(np.max(amount)))
            color = COLORS[tag.split('_')[0]]
            ls = '-' if tag.endswith('20') else '--'
            h = discrete_points(ax, d['t_s'], amount, color, f'{model} · {temp}')
            if idx == 0:
                handles.append(h)
        panel(ax, f'({chr(97 + idx)}) {label}', '累计转化水量 / (g/m²)')
        # 全零通道不人为放大，而是明确标注本时间窗口内未激活。
        if peak == 0:
            ax.set_ylim(-.05, 1)
            ax.grid(False)
            ax.text(.5, .52, '本窗口内未激活', transform=ax.transAxes, ha='center', color='#666666')
        else:
            ax.set_ylim(0, peak * 1.12)
            ax.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
    shared_legend(fig, handles, ncol=4)
    finish(fig, output, '11_phase_cumulative_amounts',
           '冻结、融化、凝结、蒸发、凝华、升华六通道的累计转化水量，均为模型输出。各面板纵轴独立；全零通道明确标注未激活。累计相变量允许同一份水反复转化，不能相加当作互斥水库存，也不能直接除以产水解释为冻结概率。',
           [f'{key}.csv' for key, _, _ in CASES], manifest, top=.87, wspace=.40, hspace=.47)


def plot_near_optimal(root, output, manifest):
    """图12：近优冻结情景包络及 k_f=1 的同粗网格参考曲线。"""
    ranges = read_csv(root / 'data/近优冻结情景范围_非置信区间.csv')
    series = read_csv(root / 'data/冻结系数情景全时序.csv')
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 5.0))
    for idx, (tag, model, temp) in enumerate(CASES):
        prefix, condition = tag.split('_', 1)
        d = select(ranges, model=prefix, condition=condition)
        reference = select(series, model=prefix, condition=condition, kf_s_inv=1.)
        ax = axes.flat[idx]
        ax.fill_between(d['t_s'], d['ice_max_bulk_min'], d['ice_max_bulk_max'],
                        color='#709DAF', alpha=.32, linewidth=0)
        discrete_points(ax, d['t_s'], d['ice_max_bulk_min'], '#4C7E92', '情景下界')
        discrete_points(ax, d['t_s'], d['ice_max_bulk_max'], '#4C7E92', '情景上界')
        discrete_points(ax, reference['t_s'], reference['ice_max_bulk'],
                        COLORS['bp'], '$k_f=1$ 同粗网格参考')
        n_scenarios = int(d['n_scenarios'][0])
        panel(ax, f'({chr(97 + idx)}) {model} · {temp}（{n_scenarios}个情景）',
              '最大冰体积分数', zero=True)
    shared_legend(fig, [Patch(facecolor='#709DAF', alpha=.32, label='校准目标≤最小值×1.05的情景范围'),
                       Line2D([0], [0], color=COLORS['bp'], marker='o', linestyle='None',
                              markersize=2, label='$k_f=1$ 同粗网格参考')], ncol=2)
    finish(fig, output, '12_near_optimal_ice_scenarios',
           '仅由−20℃校准目标挑选不超过扫描最小值1.05倍的离散冻结情景，原样应用于−25℃，阴影为逐采样时刻最小/最大值。5%是工程误差容差而非统计显著性，范围不是置信区间，亦不是全部物理不确定性；1%/10%阈值另存CSV。橙色参考与阴影同采用粗网格0.05 s，正式主解另见图04。',
           ['近优冻结情景范围_非置信区间.csv', '冻结系数情景全时序.csv', '近优阈值敏感性.csv'],
           manifest, top=.91, hspace=.45)

def main():
    """解析命令行参数，校验数据，并按选择生成单图或全部图片。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--figure', default='all', metavar='ID',
                        help='Generate one figure by number (for example 01) or full stem; default: all.')
    parser.add_argument('--list-figures', action='store_true',
                        help='List valid figure IDs and exit without reading data or writing files.')
    parser.add_argument('--validate-only', action='store_true',
                        help='Check CSV column schemas and rectangular fields without writing figures.')
    args = parser.parse_args()

    figure_stems = [
        '01_main_experiment_comparison',
        '02_bp_structural_comparison',
        '03_sample_relative_errors',
        '04_ice_fraction_saturation',
        '05_voltage_loss_decomposition',
        '06_bp_water_energy_balances',
        '07_main_spacetime_fields',
        '08_bp_spacetime_fields',
        '09_freezing_identifiability',
        '10_phase_coefficient_sensitivity',
        '11_phase_cumulative_amounts',
        '12_near_optimal_ice_scenarios',
    ]
    if args.list_figures:
        print('\n'.join(figure_stems))
        return

    requested = args.figure.strip()
    selected_stem = None
    if requested.lower() != 'all':
        # 支持 1、01 或完整图片名；编号匹配限制为两位前缀，避免歧义。
        if requested.isdigit():
            requested = requested.zfill(2)
        matches = [stem for stem in figure_stems
                   if stem == requested or stem.startswith(requested + '_')]
        if len(matches) != 1:
            parser.error(f'unknown or ambiguous --figure {args.figure!r}; use --list-figures')
        selected_stem = matches[0]

    root = args.root.resolve()
    all_data = {key: read_csv(root / 'data' / f'{key}.csv', REQUIRED)
                for key, _, _ in CASES}
    fields = {key: read_csv(root / 'data' / f'fields_{key}.csv',
                            ['t_s', 'x_um', 'layer', 'T_C', 'ice_bulk'])
              for key, _, _ in CASES}
    for key, d in all_data.items():
        if not np.all(np.diff(d['t_s']) > 0):
            raise ValueError(f'{key}: sample times must be strictly increasing.')
        if d['t_s'][0] != 0 or not np.isclose(d['t_s'][-1], 35):
            raise ValueError(f'{key}: expected samples spanning 0–35 s.')
        for col in REQUIRED:
            if not np.isfinite(d[col]).all():
                raise ValueError(f'{key}: nonfinite values in {col}.')
        for variable in ['T_C', 'ice_bulk']:
            field_grid(fields[key], variable)
    if args.validate_only:
        print('Validated four working-data tables and four complete field grids.')
        return
    output = root / 'figures'
    output.mkdir(parents=True, exist_ok=True)
    configure_style()
    manifest = []
    jobs = {
        figure_stems[0]: lambda: plot_main_fit(all_data, output, manifest),
        figure_stems[1]: lambda: plot_bp_comparison(all_data, output, manifest),
        figure_stems[2]: lambda: plot_errors(all_data, output, manifest),
        figure_stems[3]: lambda: plot_ice(all_data, output, manifest),
        figure_stems[4]: lambda: plot_voltage_terms(all_data, output, manifest),
        figure_stems[5]: lambda: plot_balances(all_data, output, manifest),
        figure_stems[6]: lambda: plot_fields('main', fields, output, manifest),
        figure_stems[7]: lambda: plot_fields('bp', fields, output, manifest),
        figure_stems[8]: lambda: plot_profile(root, output, manifest),
        figure_stems[9]: lambda: plot_phase_sensitivity(root, output, manifest),
        figure_stems[10]: lambda: plot_phase_amounts(all_data, output, manifest),
        figure_stems[11]: lambda: plot_near_optimal(root, output, manifest),
    }
    stems_to_run = figure_stems if selected_stem is None else [selected_stem]
    for stem in stems_to_run:
        jobs[stem]()

    manifest_path = output / 'figure_manifest.json'
    if selected_stem is None or not manifest_path.exists():
        merged_manifest = manifest
    else:
        # 单图模式只替换该图的清单项，其余图片的清单信息保持不变。
        existing = json.loads(manifest_path.read_text(encoding='utf-8'))
        replacements = {item['id']: item for item in manifest}
        merged_manifest = [replacements.pop(item['id'], item) for item in existing]
        merged_manifest.extend(replacements.values())
        merged_manifest.sort(key=lambda item: item['id'])
    manifest_path.write_text(
        json.dumps(merged_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved as vector PDF/SVG and 300 dpi PNG: ' + ', '.join(stems_to_run))


if __name__ == '__main__':
    main()
