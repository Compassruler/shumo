#!/usr/bin/env python3
"""Recreate publication figures directly from the exported question-1 CSV data.

Usage: python code/plot_results.py [--root RESULT_DIRECTORY]
All CSVs are read with utf-8-sig. Output: figures/*.pdf, figures/*.png,
and figures/figure_manifest.json. No fitting, smoothing, or data modification
is performed in this script. The five-layer baseline and bipolar-plate revision are distinguished explicitly.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
if (DEFAULT_ROOT / '.python_deps').is_dir():
    sys.path.insert(0, str(DEFAULT_ROOT / '.python_deps'))
os.environ.setdefault('MPLCONFIGDIR', str(DEFAULT_ROOT / '.mplconfig'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

COLORS = {'main': '#2369A1', 'bp': '#D55E00', 'exp': '#252A34',
          'pore': '#178A72', 'mem': '#AD568B', 'sat': '#B18320',
          'act': '#6E9FC1', 'ohm': '#E89A58', 'con': '#A890BF',
          'loss': '#CF655F', 'phase': '#198D8A', 'residual': '#555555'}
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
        'font.family': family, 'font.size': 9.5, 'axes.labelsize': 10,
        'axes.titlesize': 10, 'axes.titleweight': 'normal',
        'axes.titlelocation': 'left', 'axes.titlepad': 9,
        'axes.unicode_minus': False, 'axes.linewidth': .75,
        'axes.spines.top': False, 'axes.spines.right': False,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
        'legend.fontsize': 9, 'legend.frameon': False,
        'lines.linewidth': 1.7, 'savefig.dpi': 240,
        'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.grid': True, 'grid.color': '#DCE1E7', 'grid.alpha': .65,
        'grid.linewidth': .55, 'figure.facecolor': 'white',
        'axes.facecolor': 'white', 'mathtext.fontset': 'dejavusans',
    })


def read_csv(path: Path, required=None):
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


def panel(ax, label, ylabel=None, zero=False):
    ax.set_title(label)
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
    if labels is None:
        labels = [h.get_label() for h in handles]
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, 1.005),
               ncol=ncol, columnspacing=1.6, handlelength=2.6, borderaxespad=.1)


def finish(fig, output: Path, stem: str, caption: str, sources, manifest,
           top=.91, bottom=.09, wspace=.30, hspace=.40):
    fig.subplots_adjust(left=.09, right=.96, bottom=bottom, top=top,
                        wspace=wspace, hspace=hspace)
    for suffix in ['pdf', 'png']:
        fig.savefig(output / f'{stem}.{suffix}', bbox_inches='tight',
                    pad_inches=.09, metadata={'Creator': 'Question 1 plot_results.py'}
                    if suffix == 'pdf' else None)
    plt.close(fig)
    manifest.append({'id': stem, 'caption': caption,
                     'pdf': f'figures/{stem}.pdf', 'png': f'figures/{stem}.png',
                     'sources': [f'data/{p}' for p in sources]})


def plot_main_fit(all_data, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.0))
    for col, temp in enumerate(['20', '25']):
        d = all_data[f'main_minus{temp}']
        for row, (measure, ylabel) in enumerate([('V', '电压 / V'),
                                               ('T', '温度 / ℃')]):
            ax = axes[row, col]
            # Every experimental sample is shown; small open symbols preserve detail.
            exp = ax.plot(d['t_s'], d[f'{measure}_exp_' + ('V' if row == 0 else 'C')],
                          'o', color=COLORS['exp'], markersize=3.2,
                          markerfacecolor='white', markeredgewidth=.75,
                          label='实验采样值', zorder=3)[0]
            mod = ax.plot(d['t_s'], d[f'{measure}_model_' + ('V' if row == 0 else 'C')],
                          color=COLORS['main'], label='五层基线')[0]
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, mod], ncol=2)
    finish(fig, output, '01_main_experiment_comparison',
           '五层基线电压、温度与实验采样值的对比；模型结果与实验数据采用相同采样时刻。',
           ['main_minus20.csv', 'main_minus25.csv'], manifest)


def plot_bp_comparison(all_data, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.0))
    for col, temp in enumerate(['20', '25']):
        main = all_data[f'main_minus{temp}']
        bp = all_data[f'bp_minus{temp}']
        for row, (key, ylabel, expkey) in enumerate([
                ('V_model_V', '电压 / V', 'V_exp_V'),
                ('T_model_C', '温度 / ℃', 'T_exp_C')]):
            ax = axes[row, col]
            exp = ax.plot(main['t_s'], main[expkey], 'o', color=COLORS['exp'],
                          markersize=2.8, markerfacecolor='white',
                          markeredgewidth=.7, label='实验采样值', zorder=4)[0]
            p1 = ax.plot(main['t_s'], main[key], color=COLORS['main'],
                         label='五层基线')[0]
            p2 = ax.plot(bp['t_s'], bp[key], color=COLORS['bp'], linestyle='--',
                         label='含双极板修订')[0]
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, [exp, p1, p2], ncol=3)
    finish(fig, output, '02_bp_structural_comparison',
           '五层基线与含双极板修订模型的电压、温度响应。BP 曲线为纳入双极板热容量后的修订计算结果，与五层基线分开表示。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_errors(all_data, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.0))
    for col, temp in enumerate(['20', '25']):
        for row, (key, ylabel) in enumerate([
                ('V_rel_error_pct', '电压相对误差 / %'),
                ('T_rel_error_pct', '温度相对误差（℃ 绝对值分母）/ %')]):
            ax = axes[row, col]
            handles = []
            for model, label, ls in [('main', '五层基线', '-'),
                                     ('bp', '含双极板修订', '--')]:
                d = all_data[f'{model}_minus{temp}']
                handles.append(ax.plot(d['t_s'], d[key], color=COLORS[model],
                                       linestyle=ls, label=label)[0])
            ax.axhline(0, color='#8B929A', linewidth=.7, zorder=0)
            panel(ax, f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃', ylabel)
    shared_legend(fig, handles, ncol=2)
    finish(fig, output, '03_sample_relative_errors',
           '各采样时刻的电压与温度相对误差；温度按建模推导文件使用实验摄氏温度的绝对值作为分母；开尔文分母误差另存 CSV。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_ice(all_data, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.3))
    handles = []
    for idx, (key, model, temp) in enumerate(CASES):
        d, ax = all_data[key], axes.flat[idx]
        p1 = ax.plot(d['t_s'], d['ice_max_bulk'], color=COLORS['main'],
                     label='最大总冰体积分数')[0]
        p2 = ax.plot(d['t_s'], d['ice_pore_max_bulk'], color=COLORS['pore'],
                     linestyle='--', label='最大孔隙冰体积分数')[0]
        p3 = ax.plot(d['t_s'], d['ice_mem_max_bulk'], color=COLORS['mem'],
                     linestyle=':', linewidth=2, label='最大膜相冰体积分数')[0]
        ax2 = ax.twinx()
        p4 = ax2.plot(d['t_s'], d['s_ice_pore_max'], color=COLORS['sat'],
                      linestyle='-.', linewidth=1.5,
                      label='最大孔隙冰饱和度（右轴）')[0]
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
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.0))
    labels = ['模型电压', '活化损失', '欧姆损失', '浓差损失']
    palette = ['#DCE6EC', COLORS['act'], COLORS['ohm'], COLORS['con']]
    for idx, (key, model, temp) in enumerate(CASES):
        d, ax = all_data[key], axes.flat[idx]
        ax.stackplot(d['t_s'], d['V_model_V'], d['eta_act_V'], d['eta_ohm_V'],
                     d['eta_con_V'], colors=palette, alpha=.88, linewidth=0)
        ax.plot(d['t_s'], d['V_model_V'], color=COLORS['main'], linewidth=1.1)
        ax.plot(d['t_s'], d['E_rev_V'], '--', color='#252A34', linewidth=1.2)
        panel(ax, f'({chr(97 + idx)}) {model} · {temp}', '电压及损失 / V', zero=True)
    handles = [Patch(facecolor=c, label=l) for c, l in zip(palette, labels)]
    handles.append(Line2D([0], [0], linestyle='--', color='#252A34', label='可逆电压'))
    shared_legend(fig, handles, ncol=5)
    finish(fig, output, '05_voltage_loss_decomposition',
           '模型电压与活化、欧姆、浓差损失的堆叠分解；虚线表示可逆电压。',
           [f'{key}.csv' for key, _, _ in CASES], manifest)


def plot_balances(all_data, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    for col, temp in enumerate(['20', '25']):
        d = all_data[f'bp_minus{temp}']
        ax = axes[0, col]
        for key, label, color, ls in [
                ('water_produced_kg_m2', '累计产水', COLORS['main'], '-'),
                ('water_stored_kg_m2', '储水量变化', COLORS['pore'], '--'),
                ('water_out_kg_m2', '累计排水', COLORS['bp'], '-.')]:
            amount = d[key] - d['water_initial_kg_m2'] if key == 'water_stored_kg_m2' else d[key]
            ax.plot(d['t_s'], amount * 1e3, label=label, color=color, linestyle=ls)
        # Plot exported residual on a separate scale so conservation error remains visible.
        twin = ax.twinx()
        twin.plot(d['t_s'], d['water_balance_kg_m2'] * 1e3,
                  color='#7A7E86', linewidth=.9, linestyle=':', label='收支残差')
        twin.grid(False)
        twin.set_ylabel('水收支残差 / (g/m²)', color='#7A7E86', fontsize=8.5)
        twin.tick_params(axis='y', colors='#7A7E86', labelsize=8)
        twin.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
        twin.spines['right'].set_visible(True)
        panel(ax, f'({chr(97 + col)}) 含双极板修订 · −{temp} ℃', '水量 / (g/m²)')
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.18), ncol=3,
                  fontsize=8, columnspacing=.9, handlelength=1.8)
        ax = axes[1, col]
        for key, label, color, ls in [
                ('heat_gen_J_m2', '累计产热', COLORS['main'], '-'),
                ('heat_phase_J_m2', '累计相变放热', COLORS['phase'], '--'),
                ('heat_loss_J_m2', '累计散热', COLORS['loss'], '-.')]:
            ax.plot(d['t_s'], d[key] / 1e3, label=label, color=color, linestyle=ls)
        twin = ax.twinx()
        twin.plot(d['t_s'], d['energy_balance_J_m2'], color='#7A7E86',
                  linewidth=.9, linestyle=':', label='收支残差')
        twin.grid(False)
        twin.set_ylabel('能量收支残差 / (J/m²)', color='#7A7E86', fontsize=8.5)
        twin.tick_params(axis='y', colors='#7A7E86', labelsize=8)
        twin.ticklabel_format(axis='y', style='sci', scilimits=(-2, 3), useMathText=True)
        twin.spines['right'].set_visible(True)
        panel(ax, f'({chr(99 + col)}) 含双极板修订 · −{temp} ℃', '累计热量 / (kJ/m²)')
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.18), ncol=3,
                  fontsize=8, columnspacing=.9, handlelength=1.8)
    shared_legend(fig, [Line2D([0], [0], color='#7A7E86', linestyle=':',
                              label='灰色点线：收支残差（各面板右轴）')], ncol=1)
    finish(fig, output, '06_bp_water_energy_balances',
           '含双极板修订模型的累计水量、累计热量及守恒残差。储水变化扣除初始存水量；相变热正号表示放热。灰色点线残差采用各面板右轴单独刻度。',
           ['bp_minus20.csv', 'bp_minus25.csv'], manifest,
           top=.92, bottom=.13, wspace=.52, hspace=.72)


def field_grid(data, key):
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
    # Finite-volume cells are uniform within each layer, but their widths differ
    # greatly across a BP/MEA interface. Averaging adjacent centers would shift
    # that interface, so reconstruct each layer's physical cell boundaries.
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
    if len(values) < 2:
        raise ValueError('At least two time samples are required.')
    return np.r_[values[0] - (values[1] - values[0]) / 2,
                 (values[:-1] + values[1:]) / 2,
                 values[-1] + (values[-1] - values[-2]) / 2]


def layer_boundaries(ax, x_edges, layers):
    transitions = np.flatnonzero(layers[1:] != layers[:-1])
    for i in transitions:
        ax.axhline(x_edges[i + 1], color='white', alpha=.6,
                   linewidth=.65, linestyle='--')


def plot_fields(model, fields, output, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.25))
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
            ax.set_title(f'({chr(97 + row * 2 + col)}) 初始温度 −{temp} ℃')
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
        bar.set_label('局部温度 / ℃' if row == 0 else '局部总冰体积分数', labelpad=9)
        bar.outline.set_linewidth(.6)
        if row == 1 and i_max < .01:
            bar.formatter.set_powerlimits((-2, 2))
            bar.update_ticks()
    name = '五层基线' if model == 'main' else '含双极板修订模型'
    stem = '07_main_spacetime_fields' if model == 'main' else '08_bp_spacetime_fields'
    # Save directly: fixed colorbar axes should not be adjusted by finish().
    for ext in ['pdf', 'png']:
        fig.savefig(output / f'{stem}.{ext}', bbox_inches='tight', pad_inches=.09)
    plt.close(fig)
    manifest.append({'id': stem,
                     'caption': f'{name}局部温度与总冰体积分数时空分布。虚线表示计算层界面；同一行采用统一色标。' + ('双极板修订模型温度图显示整域，冰图显示 MEA 区域。' if model == 'bp' else ''),
                     'pdf': f'figures/{stem}.pdf', 'png': f'figures/{stem}.png',
                     'sources': [f'data/fields_{key}.csv' for key in key_list]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--validate-only', action='store_true',
                        help='Check CSV column schemas and rectangular fields without writing figures.')
    args = parser.parse_args()
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
    plot_main_fit(all_data, output, manifest)
    plot_bp_comparison(all_data, output, manifest)
    plot_errors(all_data, output, manifest)
    plot_ice(all_data, output, manifest)
    plot_voltage_terms(all_data, output, manifest)
    plot_balances(all_data, output, manifest)
    plot_fields('main', fields, output, manifest)
    plot_fields('bp', fields, output, manifest)
    (output / 'figure_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(manifest)} figures as vector PDF and PNG: {output}')


if __name__ == '__main__':
    main()
