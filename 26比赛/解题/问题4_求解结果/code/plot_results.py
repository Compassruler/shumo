"""Render the Q4 CSV results into consistent PDF, editable SVG and 300 dpi PNG files.

This module reads the result tables only; no model evaluation is hidden in plots.
Use --precooling-only while startup calculations are still running.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
# The bundled local .python_deps was built on Windows. Do not shadow native packages.
if os.name == 'nt':
    sys.path.insert(0, str(ROOT / '.python_deps'))
else:
    try:
        import numpy, pandas, matplotlib
    except ImportError:
        native_deps = ROOT.parent / '问题1_求解结果' / '.python_deps'
        if native_deps.exists():
            sys.path.insert(0, str(native_deps))
import numpy as np
import pandas as pd
import matplotlib
# Batch calls retain the headless backend; --show enables interactive preview.
if '--show' not in sys.argv:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common_style import (COLORS, STRATEGY_COLORS, DANGER, configure_style, points,
                          log_points, failed_points, category_points, lighter, finish_style, align_regular_panels)
from audit_panel_alignment import require_matplotlib_panel_alignment
from matplotlib.colors import Normalize
from matplotlib.ticker import NullLocator

CASE_NAMES = {'case1': '工况1：完全冷却', 'case2': '工况2：预冷20 min',
              'case3': '工况3：预冷40 min'}
STRATEGY_NAMES = {'dynamic': '动态反馈', 'constant': '恒功率基准',
                  'D': '动态反馈', 'C': '恒功率基准',
                  'constant_hold': '恒功率＋2 s保持', 'constant_first':'恒功率首次过零'}
STRATEGY_NAMES.update({'dynamic':'名义能耗优选','guarded':'推荐留裕度动态',
                      'constant_optimized':'同工况重优化恒功率'})
MANIFEST = []
OPTIONS = {'figure': None, 'no_show': True, 'no_save': False}


def configure():
    configure_style()



def read(name, root=ROOT):
    path = root / 'data' / name
    return pd.read_csv(path, encoding='utf-8-sig') if path.exists() else None


def save(fig, name, title, sources, root=ROOT):
    number = name[1:3]
    if OPTIONS['figure'] is not None and number != OPTIONS['figure']:
        plt.close(fig)
        return
    note = finish_style(fig)
    align_regular_panels(fig)
    fig.canvas.draw()
    if not OPTIONS['no_save']:
        out = root / 'figures'
        out.mkdir(parents=True, exist_ok=True)
        require_matplotlib_panel_alignment(
            fig, json_out=root/'audit'/'figure_style'/f'{name}.alignment.json',
            strict=True, tolerance_pt=1.5, gutter_tolerance_pt=1.5)
        for suffix in ('pdf', 'svg', 'png'):
            kwargs = {'dpi': 300} if suffix == 'png' else {}
            fig.savefig(out / f'{name}.{suffix}', bbox_inches='tight', pad_inches=.13, **kwargs)
        MANIFEST.append({'figure': name, 'title': title, 'source_csv': ';'.join(sources),
                         'png_dpi': 300, 'png': name+'.png', 'svg': name+'.svg',
                         'pdf': name+'.pdf', 'plot_note': note})
        print('Saved', name, '[pdf|svg|png]')
    if not OPTIONS['no_show']:
        plt.show()
    plt.close(fig)



def spatial_line(ax, x, y, **kwargs):
    """空间连续场例外：保留有限体积场的连接曲线与时间色标。"""
    return ax.plot(x, y, **kwargs)


def label_panel(ax, text):
    ax.text(0, 1.04, text, transform=ax.transAxes, ha='left', fontweight='bold')


def precooling(root=ROOT):
    fields = read('precooling_fields.csv', root)
    nodes = read('precooling_nodes.csv', root)
    cases = read('initial_temperature_cases.csv', root)
    layers = read('precooling_layers.csv', root)
    if any(x is None for x in [fields, nodes, cases, layers]):
        raise FileNotFoundError('Run precooling.py first.')
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9), layout='constrained')
    times = sorted(fields.cooling_min.unique())
    cmap = plt.get_cmap('viridis_r'); norm = Normalize(10, 100)
    for t, group in fields.groupby('cooling_min', sort=True):
        spatial_line(axes[0], group.x_mm, group.temperature_C, color=cmap(norm(t)), lw=1.6)
        if t in (10, 20, 40, 100):
            spatial_line(axes[1], group.x_mm, group.temperature_C - group.temperature_C.min(),
                         color=cmap(norm(t)), label=f'{t:g} min')
    axes[0].set(xlabel='层叠方向 x / mm', ylabel='温度 / ℃', title='(a) 10–100 min 温度场族（间隔5 min）')
    axes[1].set(xlabel='层叠方向 x / mm', ylabel='相对当时最低温度 / K', title='(b) 空间温差细节')
    for ax in axes:
        ax.axvspan(0, 10, color='#9EB4BF', alpha=.12, zorder=0)
        ax.axvspan(float(layers.x_right_mm.max())-10, float(layers.x_right_mm.max()),
                   color='#9EB4BF', alpha=.12, zorder=0)
        ax.set_xlim(0, float(layers.x_right_mm.max()))
    axes[1].legend(title='预冷时间', loc='upper right')
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, pad=.025)
    cb.set_label('预冷时间 / min')
    fig._q4_note = '连续空间温度场保留曲线与时间色标；浅灰区域为两端端板。'
    save(fig,'图01_预冷温度场族','预冷温度场族与空间温差细节', ['precooling_fields.csv'],root)

    fig,axes=plt.subplots(1,2,figsize=(12.6,4.5),layout='constrained')
    for key,label,color in [('mean_capacity_C','热容加权均温',COLORS[0]),
            ('T3_C','中间电池均温',COLORS[1]),('surface_left_C','左外表面温度',COLORS[2])]:
        points(axes[0], nodes.cooling_min, nodes[key], label=label, color=color)
    axes[0].axhline(-30,color='#5C6267',ls='--',lw=1,label='环境 −30 ℃')
    axes[0].set(xlabel='预冷时间 / min',ylabel='温度 / ℃',title='(a) 整体降温与环境渐近')
    axes[0].legend()
    for key,label,color in [('field_range_K','全场极差（含真实表面）',COLORS[0]),
            ('center_minus_left_EP_K','中片—左端板均温差',COLORS[1]),
            ('cell_range_K','五片电池均温极差',COLORS[2])]:
        points(axes[1], nodes.cooling_min, nodes[key], label=label, color=color)
    axes[1].set(xlabel='预冷时间 / min',ylabel='同一时刻温差 / K',title='(b) 三种温差定义与预冷程度')
    axes[1].legend()
    save(fig,'图02_预冷均温与温差','预冷均温及不同口径温差',['precooling_nodes.csv'],root)

    fig,axes=plt.subplots(1,3,figsize=(13.0,4.2),layout='constrained')
    order=['TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C']
    ticklabels=['左端板','1','2','3','4','5','右端板']
    for ax,(_,row),color in zip(axes,cases.iterrows(),COLORS):
        values=row[order].to_numpy(dtype=float)
        points(ax,range(7),values,color=color,size=6.)
        ax.axhline(row.mean_capacity_C,color='#737A80',ls='--',lw=1,label='全场热容加权均温')
        ax.set_xticks(range(7),ticklabels,rotation=25)
        ax.set(title=CASE_NAMES.get(row['case'],row['case']),ylabel='节点均温 / ℃')
        pad=max(.07,np.ptp(values)*.3)
        ax.set_ylim(values.min()-pad,values.max()+pad)
        ax.text(.5,.07,f'五片均温差 = {row.cell_range_K:.4f} K',transform=ax.transAxes,ha='center',fontsize=10)
        ax.legend(loc='upper center',fontsize=8)
    save(fig,'图03_三工况初始温度','三种工况的七节点初始温度（各子图独立纵轴）', ['initial_temperature_cases.csv'],root)


def col(df, *names):
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f'Expected one of {names}; found {list(df.columns)}')


def feasible(df):
    return df['feasible'].astype(str).str.lower().isin(['true','1','1.0'])


def startup_figures(root=ROOT):
    original=read('main_results.csv',root)
    recommended=read('guarded_results.csv',root)
    if original is None or recommended is None:
        raise FileNotFoundError('main_results.csv missing; use --precooling-only for partial output')
    summary=pd.concat([recommended,original[original.strategy!='dynamic']],ignore_index=True)
    for number,case in enumerate(CASE_NAMES,4):
        hist=read(f'trajectory_{case}_guarded.csv',root)
        const=read(f'trajectory_{case}_constant_hold.csv',root)
        if hist is None:
            raise FileNotFoundError(f'Missing dynamic trajectory: {case}')
        record=summary[(summary['case']==case)&(summary.strategy=='guarded')].iloc[0]
        stop=float(record.stop_s)
        fig,axes=plt.subplots(2,2,figsize=(12.6,8.0),layout='constrained')
        for k,color in zip(range(1,6),COLORS):
            points(axes[0,0],hist.time_s,hist[f'cell{k}_q_W_cm2'],color=color,label=f'电池{k}')
            points(axes[0,1],hist.time_s,hist[f'T{k}_C'],color=color,label=f'电池{k}')
            points(axes[1,0],hist.time_s,hist[f'cell{k}_V_V'],color=color)
            points(axes[1,1],hist.time_s,hist[f'cell{k}_ice_bulk'],color=color)
        if const is not None:
            cut=const[const.time_s<=float(summary[(summary['case']==case)&(summary.strategy=='constant_hold')].iloc[0].stop_s)+1e-7]
            if len(cut):
                points(axes[0,1],cut.time_s,cut[[f'T{k}_C' for k in range(1,6)]].min(axis=1),color=STRATEGY_COLORS['constant_hold'],label='恒功率最低片温')
        axes[0,0].axhline(1,color='#72777C',ls='--',lw=1)
        axes[0,0].set(ylabel='单片功率密度 / (W/cm²)',ylim=(-.03,1.1),title='(a) 五路独立功率（区间保持）')
        axes[0,0].legend(ncol=3,loc='upper left')
        axes[0,1].axhline(0,color='#72777C',ls='--',lw=1)
        axes[0,1].set(ylabel='单片平均温度 / ℃',title='(b) 温升过程及恒功率参考')
        axes[0,1].legend(ncol=3,fontsize=8,loc='upper left')
        axes[1,0].axhline(.3,color='#A44848',ls='--',lw=1.2,label='安全下限 0.30 V')
        axes[1,0].set(ylabel='单片电压 / V',title='(c) 电压约束')
        axes[1,0].legend(loc='upper left')
        axes[1,1].axhline(.99,color='#A44848',ls='--',lw=1.2,label='严重冰堵阈值 0.99')
        axes[1,1].set(ylabel='MEA局部最大冰体积分数',title='(d) 冰量约束（全MEA局部最大值）',ylim=(-.035,1.06))
        axes[1,1].legend(loc='best')
        for ax in axes.flat:
            ax.set_xlabel('冷启动时间 / s')
            if stop>=0:ax.axvline(stop,color='#858B90',ls=':',lw=1.2)
            if stop>=0 and float(hist.time_s.max())>stop+.01:
                ax.axvspan(stop,float(hist.time_s.max()),color='#DDE6EB',alpha=.45,zorder=0)
        fig.suptitle(f'{CASE_NAMES[case]}｜推荐动态全过程；阴影为关热后验证',fontsize=14)
        fig._q4_note = '功率圆点对应前一积分区间的实际加热；所有时刻均保留，圆点之间不连线。'
        save(fig,f'图{number:02d}_{case}_动态控制轨迹',f'{CASE_NAMES[case]}动态控制轨迹',
             [f'trajectory_{case}_guarded.csv',f'trajectory_{case}_constant_hold.csv'],root)

    fig,axes=plt.subplots(2,3,figsize=(13.0,8.0),layout='constrained')
    metrics=[('E_aux_J','辅助加热总能耗 / J'),('stop_s','完成保持并关热 / s'),
             ('first_success_s','首次满足条件 / s'),('dTmax_K','过程最大五片温差 / K'),
             ('min_voltage_V','过程最低单片电压 / V'),('max_ice_bulk','过程最大冰体积分数')]
    x=np.arange(3);width=.35
    for ax,(key,label) in zip(axes.flat,metrics):
        for offset,strategy,color in [(-.5,'guarded',STRATEGY_COLORS['guarded']),(.5,'constant_hold',STRATEGY_COLORS['constant_hold'])]:
            vals=np.array([float(summary[(summary['case']==c)&(summary.strategy==strategy)].iloc[0][key]) for c in CASE_NAMES])
            labels=[f'{v:.1e}' if key=='max_ice_bulk' and 0<v<.001 else (f'{v:.3f}' if key=='max_ice_bulk' else f'{v:.2f}') for v in vals]
            category_points(ax,x+offset*width,vals,color,label=STRATEGY_NAMES[strategy],labels=labels)
        ax.set_xticks(x,['完全冷却','预冷20 min','预冷40 min'])
        ax.set_ylabel(label)
        ax.margins(y=.18)
    axes[0,0].legend(loc='upper right',fontsize=9)
    fig.suptitle('推荐动态与固定C：相同传感温度裕度与2 s连续测量保持，统计到实际关热',fontsize=14)
    save(fig,'图07_三工况主指标比较','推荐动态与固定C的共同测量停机比较',['guarded_results.csv','main_results.csv'],root)

    scan=read('constant_scan.csv',root)
    if scan is None:raise FileNotFoundError('constant_scan.csv missing')
    fig,axes=plt.subplots(2,3,figsize=(13.0,7.8),layout='constrained')
    scanmetrics=[('mean_capacity_C','预冷热容加权均温 / ℃'),('E_aux_J','辅助能耗 / J'),
                 ('first_success_s','首次满足条件 / s'),('dTmax_K','最大五片温差 / K'),
                 ('min_voltage_V','最低单片电压 / V'),('max_ice_bulk','最大冰体积分数')]
    for ax,(key,label),color in zip(axes.flat,scanmetrics,COLORS+[COLORS[0]]):
        points(ax, scan.cooling_min, scan[key], color=color)
        if 'feasible' in scan:
            bad=scan[~feasible(scan)]
            if len(bad):failed_points(ax,bad.cooling_min,bad[key],color=color,label='不可行（红圈）')
        ax.set(xlabel='预冷时间 / min',ylabel=label)
        ax.set_xticks([10,25,40,55,70,85,100])
        if key=='min_voltage_V':ax.axhline(.3,color='#A44848',ls='--',lw=1)
        if key=='max_ice_bulk':ax.axhline(.99,color='#A44848',ls='--',lw=1)
    fig.suptitle('固定问题三功率分配，10–100 min预冷共19点扫描',fontsize=14)
    save(fig,'图08_预冷时间扫描','固定恒功率策略随预冷时间的变化',['constant_scan.csv'],root)

    fig,axes=plt.subplots(1,2,figsize=(12.8,5.0),layout='constrained')
    keep=summary[summary.strategy.isin(['guarded','constant_hold'])].copy()
    labels=[CASE_NAMES[r['case']].split('：')[-1]+'\n'+('推荐动态' if r.strategy=='guarded' else '固定C') for _,r in keep.iterrows()]
    x=np.arange(len(keep))
    energy_items=[('E_aux_J','辅助输入',COLORS[0]),
                  ('E_gen_J','反应产热',COLORS[1]),
                  ('E_phase_J','相变净释热',COLORS[2]),
                  ('total_input','三项输入合计',COLORS[3]),
                  ('total_output','显热增量＋环境散热',COLORS[4])]
    for offset,(key,label,color) in zip(np.linspace(-.23,.23,5),energy_items):
        if key=='total_input':vals=keep.E_aux_J+keep.E_gen_J+keep.E_phase_J
        elif key=='total_output':vals=keep.E_sensible_J+keep.E_loss_J
        else:vals=keep[key]
        category_points(axes[0],x+offset,vals,color,label=label,size=5.)
    axes[0].set_xticks(x,labels,fontsize=8)
    axes[0].set(ylabel='离散能量收支 / J',title='(a) 分项输入及总量闭合')
    axes[0].legend(ncol=2,fontsize=9)
    for case,color in zip(CASE_NAMES,COLORS):
        hst=read(f'trajectory_{case}_guarded.csv',root)
        s=keep[(keep['case']==case)&(keep.strategy=='guarded')].iloc[0]
        hst=hst[hst.time_s<=s.stop_s+1e-7]
        points(axes[1],hst.time_s,hst.E_aux_J,color=color,label=CASE_NAMES[case])
    axes[1].set(xlabel='冷启动时间 / s',ylabel='累计辅助加热能耗 / J',title='(b) 动态策略电能积分')
    axes[1].legend()
    save(fig,'图09_能量收支与累积能耗','推荐策略离散能量闭合与累计电能',['guarded_results.csv','main_results.csv']+[f'trajectory_{c}_guarded.csv' for c in CASE_NAMES],root)

    convergence(root)
    sensitivity(root)
    robustness(root)
    if read('guarded_results.csv',root) is not None:
        guarded(root)
    constant_comparison(root)
    time_frontier(root)
    observer_diagnostics(root)


def convergence(root):
    pre=read('precooling_convergence.csv',root); start=read('guarded_convergence.csv',root)
    if start is None:raise FileNotFoundError('guarded_convergence.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(12.6,7.8),layout='constrained')
    for (study,t),g in pre.groupby(['study','cooling_min']):
        ax=axes[0,0] if study=='time' else axes[0,1]
        key='dt_s' if study=='time' else 'control_volumes'
        y='max_field_error_K' if study=='time' else 'max_node_error_K'
        group=g.sort_values(key)
        good=group[group[y]>1e-12]
        log_points(ax, good[key], good[y], label=f'{t:g} min', size=4.)
    axes[0,0].set(xlabel='预冷时间步长 / s',ylabel='最大场误差 / K',title='(a) 同网格矩阵指数时间参考')
    axes[0,1].set(xlabel='预冷控制体数量',ylabel='七节点投影最大误差 / K',title='(b) 8倍网格空间参考')
    for ax,key,study in [(axes[0,0],'dt_s','time'),(axes[0,1],'control_volumes','space')]:
        ticks=sorted(pre[(pre.study==study)&(pre.max_node_error_K>1e-12)][key].unique())
        ax.set_xticks(ticks,[f'{x:g}' for x in ticks])
        ax.xaxis.set_minor_locator(NullLocator())
    for ax in axes[0]:ax.legend()
    for case,color in zip(CASE_NAMES,COLORS):
        g=start[(start['case']==case)&(start.dt_s==.025)&(start.period_s==.2)].sort_values('scale').copy()
        if not len(g):continue
        reference=g[(g.dt_s==.025)&(g.scale==2)&(g.period_s==.2)].iloc[0]
        points(axes[1, 0], g.scale * 29, g.E_aux_J - reference.E_aux_J, color=color, label=CASE_NAMES[case], size=3.5)
        points(axes[1, 1], g.scale * 29, g.max_ice_bulk, color=color, label=CASE_NAMES[case], size=3.5)
        joint=read('coupled_convergence.csv',root)
        if joint is not None:
            j=joint[joint['case']==case].sort_values('scale')
            points(axes[1,0],j.scale*29,j.E_aux_J-reference.E_aux_J,color=lighter(color),size=5.)
            points(axes[1,1],j.scale*29,j.max_ice_bulk,color=lighter(color),size=5.)
        for ax in axes[1]:
            ax.set_xscale('log',base=2)
            ticks=sorted(set(g.scale*29) | (set(j.scale*29) if joint is not None else set()))
            ax.set_xticks(ticks,[f'{x:g}' for x in ticks],fontsize=9)
            ax.xaxis.set_minor_locator(NullLocator())
            ax.set_xlabel('每片MEA水相控制体数')
    axes[1,0].set(ylabel='相对正式58控制体的能耗差 / J',title='(c) 总体能耗对空间加密的响应')
    axes[1,1].set(ylabel='MEA局部最大冰体积分数',title='(d) 深色固定dt；浅色联合减半dt')
    axes[1,0].axhline(0,color='#737A80',ls='--',lw=.7)
    axes[1,0].legend(fontsize=9)
    method_handles=[points(axes[1,1],[],[],color=COLORS[4],size=3.5,label='固定dt（深色小圆）'),
                    points(axes[1,1],[],[],color=lighter(COLORS[4]),size=5.,label='联合减半dt（浅色大圆）')]
    axes[1,1].legend(handles=method_handles,loc='best',fontsize=9)
    save(fig,'图10_网格步长与控制周期检验','预冷与启动阶段的数值收敛检验',['precooling_convergence.csv','guarded_convergence.csv','coupled_convergence.csv'],root)


def sensitivity(root):
    pre=read('precooling_sensitivity.csv',root);start=read('sensitivity.csv',root)
    if start is None:raise FileNotFoundError('sensitivity.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(13.0,8.4),layout='constrained')
    for factor,g in pre[pre.cooling_min==20].groupby('conductance_factor'):
        g=g.sort_values('h_W_m2K')
        points(axes[0, 0], g.h_W_m2K, g.field_range_K, label=f'导热倍率 {factor:g}')
        points(axes[0, 1], g.h_W_m2K, g.relative_field_range, label=f'导热倍率 {factor:g}')
    axes[0,0].set(xlabel='端面换热 h / [W/(m²·K)]',ylabel='全场绝对温差 / K',title='(a) 预冷20 min：绝对不均匀程度')
    axes[0,1].set(xlabel='端面换热 h / [W/(m²·K)]',ylabel='全场温差 / (热容均温−环境温度)',title='(b) 预冷20 min：归一化不均匀程度')
    axes[0,0].legend(fontsize=8,ncol=2)
    case=next(iter(CASE_NAMES));g=start[start['case']==case].reset_index(drop=True)
    if not len(g):g=start.reset_index(drop=True)
    parameter_labels={'G':'g_c','G_EP':'g_E','h':'h','T_target':'T目标','K_P':'K_P','K_I':'K_I','ice_warn':'冰预警','delta_V':'ΔV'}
    labels=[f'{parameter_labels.get(r.parameter,r.parameter)}×{r.factor:g}' for _,r in g.iterrows()]
    for ax,key,label,color in [(axes[1,0],'E_aux_J','辅助能耗 / J',COLORS[0]),(axes[1,1],'dTmax_K','最大五片温差 / K',COLORS[1])]:
        category_points(ax,np.arange(len(g)),g[key],color)
        ax.set_xticks(range(len(g)),labels,rotation=80,ha='right',rotation_mode='anchor',fontsize=9)
        ax.set_ylabel(label)
        ax.set_title('工况1固定控制参数的单因素扰动')
        if 'feasible' in g:
            for i,r in g.iterrows():
                if str(r.feasible).lower() not in ('true','1','1.0'):ax.annotate('失败',(i,float(r[key])),xytext=(0,8),textcoords='offset points',color='#A44848',ha='center',va='bottom',fontsize=8)
    save(fig,'图11_物理参数与控制器敏感性','预冷传热参数与启动控制参数敏感性',['precooling_sensitivity.csv','sensitivity.csv'],root)


def robustness(root):
    df=read('robustness.csv',root)
    if df is None:raise FileNotFoundError('robustness.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(12.6,8.0),layout='constrained')
    df=df.reset_index(drop=True)
    # A failed run has no completion time. Show the actual first event if it
    # exists, otherwise its simulated endpoint, explicitly labelled below.
    df['first_or_end_s']=np.where(df.first_success_s>=0,df.first_success_s,df.elapsed_s)
    metrics=[('E_aux_J','辅助加热能耗 / J'),('first_or_end_s','首次真实达标 / s（未达标则仿真终点）'),
             ('min_voltage_V','最低单片电压 / V'),('max_ice_bulk','最大冰体积分数')]
    for case,color in zip(CASE_NAMES,COLORS):
        g=df[df['case']==case]
        for ax,(key,label) in zip(axes.flat,metrics):
            good=g[feasible(g)];bad=g[~feasible(g)]
            points(ax, good.index + 1, good[key], color=color, label=CASE_NAMES[case], size=3.5)
            failed_points(ax,bad.index+1,bad[key],color=color,label='失败（红圈）' if case=='case1' else None)
            ax.set(xlabel='扰动试验编号（CSV数据行）',ylabel=label)
    axes[0,0].legend(loc='best',fontsize=8)
    axes[0,1].axhline(96.6666666667,color='#A44848',ls='--',lw=1.1)
    axes[0,1].text(.03,.08,'虚线：首次达标期限；红圈为任一约束失败\n未找到首次事件的行显示实际仿真终点',transform=axes[0,1].transAxes,fontsize=8)
    axes[1,0].axhline(.3,color='#A44848',ls='--',lw=1,label='安全下限')
    axes[1,1].axhline(.99,color='#A44848',ls='--',lw=1,label='严重冰堵阈值')
    fig.suptitle('名义优选策略的测量/初场扰动：全部样本用圆点；红圈为任一约束失败',fontsize=13)
    save(fig,'图12_测量噪声与初场扰动','测量噪声和初场偏差下的能耗与安全约束',['robustness.csv'],root)


def guarded(root):
    nominal=read('main_results.csv',root);alt=read('guarded_results.csv',root)
    nnoise=read('robustness.csv',root);anoise=read('guarded_robustness.csv',root)
    fig,axes=plt.subplots(2,2,figsize=(12.4,8),layout='constrained')
    x=np.arange(3);width=.35
    for offset,df,ndf,color,label in [(-.5,nominal[nominal.strategy=='dynamic'],nnoise,COLORS[0],'名义能耗优选'),
                                      (.5,alt,anoise,STRATEGY_COLORS['guarded'],'推荐留裕度策略')]:
        data=df.set_index('case').reindex(list(CASE_NAMES))
        values=[data.E_aux_J.to_numpy(),data.stop_s.to_numpy(),
                np.array([100*feasible(ndf[ndf['case']==c]).mean() for c in CASE_NAMES]),
                data.post_min_T_C.to_numpy()]
        for ax,vals in zip(axes.flat,values):
            category_points(ax,x+offset*width,vals,color,label=label,labels=[f'{v:.2f}' for v in vals])
            ax.set_xticks(x,['完全冷却','预冷20 min','预冷40 min'])
            ax.margins(y=.18)
    for ax,label,title in zip(axes.flat,['辅助电能 / J','关热时刻 / s','扰动试验可行比例 / %','关热后60 s最低片温 / ℃'],
           ['(a) 实际辅助电能代价','(b) 采样确认并关热的时刻','(c) 各自独立种子组的经验比例','(d) 持续暖态需看关热后验证']):
        ax.set(ylabel=label,title=title)
    axes[0,0].legend(loc='upper right',fontsize=9)
    if 'startup_window_end_s' in alt:
        axes[0,1].axhline(alt.startup_window_end_s.max(),color='#A44848',ls='--',lw=1)
    axes[1,0].set_ylim(-5,120)
    axes[1,1].axhline(0,color='#737A80',ls='--',lw=1)
    fig.suptitle('名义能耗优选与推荐留裕度方案：独立试验通过率和关热后状态分别报告',fontsize=13)
    save(fig,'图13_名义与留裕度备选','名义策略与留裕度备选的能耗、时间、扰动可行比例及关热后温度',
         ['main_results.csv','guarded_results.csv','robustness.csv','guarded_robustness.csv'],root)


def constant_comparison(root):
    opt=read('optimized_constant_results.csv',root)
    if opt is None:return
    guard=read('guarded_results.csv',root);main=read('main_results.csv',root)
    fig,axes=plt.subplots(2,2,figsize=(13,8.0),layout='constrained')
    metrics=[('E_aux_J','实际关热前辅助电能 / J'),('first_success_s','首次真实达标 / s'),
             ('stop_s','完成测量保持并关热 / s'),('post_min_T_C','关热后60 s最低片温 / ℃')]
    x=np.arange(3);width=.24
    for offset,df,label,color in [(-1,main[main.strategy=='constant_hold'],'固定问题三C',STRATEGY_COLORS['constant_hold']),
                                  (0,opt,'同工况重优化恒功率',STRATEGY_COLORS['constant_optimized']),
                                  (1,guard,'推荐留裕度动态',STRATEGY_COLORS['guarded'])]:
        frame=df.set_index('case').reindex(list(CASE_NAMES))
        for ax,(metric,ylabel) in zip(axes.flat,metrics):
            vals=frame[metric].to_numpy(float)
            category_points(ax,x+offset*width,vals,color,label=label,
                labels=[f'{v:.2f}' if metric=='post_min_T_C' else f'{v:.1f}' for v in vals])
            for xx,yy,ok in zip(x+offset*width,vals,feasible(frame)):
                if not ok:
                    failed_points(ax,[xx],[yy],color=color,size=6.)
                    ax.annotate('失败',(xx,yy),xytext=(0,-16),textcoords='offset points',ha='center',color=DANGER,fontsize=8)
            ax.set_xticks(x,['完全冷却','预冷20 min','预冷40 min']);ax.set_ylabel(ylabel);ax.margins(y=.22)
    axes[0,0].legend(loc='best',fontsize=8)
    axes[1,1].axhline(0,color='#737A80',ls='--',lw=1)
    fig.suptitle('共同采样停机规则：固定功率、有限搜索重优化恒功率与推荐动态',fontsize=14)
    save(fig,'图14_重优化恒功率与推荐动态','同工况恒功率再优化与推荐动态的能耗和时间比较',
         ['optimized_constant_results.csv','guarded_results.csv','main_results.csv'],root)


def time_frontier(root):
    frontier=read('constant_time_frontier.csv',root)
    if frontier is None:return
    search=read('constant_optimization_search.csv',root)
    main=read('main_results.csv',root);guard=read('guarded_results.csv',root)
    baseline=read('constant_baselines.csv',root)
    fig,axes=plt.subplots(1,3,figsize=(15,5.0),layout='constrained')
    for ax,case in zip(axes,CASE_NAMES):
        if search is not None:
            g=search[(search['case']==case)&(search.mesh_scale==2)&(search.dt_s==.025)]
            ok=g[feasible(g)];bad=g[~feasible(g)]
            points(ax, ok.first_success_s, ok.E_aux_J, color='#C3CDD5', label='已评正式精度可行候选')
            if len(bad):failed_points(ax,np.where(bad.first_success_s>=0,bad.first_success_s,bad.elapsed_s),bad.E_aux_J,
                                      color=COLORS[4],label='失败（未达标时显示仿真终点）',size=2.)
        g=frontier[frontier['case']==case].sort_values('first_success_s')
        points(ax, g.first_success_s, g.E_aux_J, color=STRATEGY_COLORS['constant_optimized'], size=5, label='期限约束下最低已找到恒功率')
        for (first,energy),same in g.groupby(['first_success_s','E_aux_J'],sort=False):
            deadlines='/'.join(f'{x:.1f}' for x in same.deadline_s)
            caption=f'期限{deadlines}s' if len(same)<=2 else f'期限{same.deadline_s.min():g}–{same.deadline_s.max():.1f}s共{len(same)}点'
            ax.annotate(caption,(first,energy),xytext=(3,5),textcoords='offset points',fontsize=7.2)
        for df,strategy,label,color,marker in [(main,'constant_hold','固定C',STRATEGY_COLORS['constant_hold'],'o'),
                    (main,'dynamic','名义能耗优选',STRATEGY_COLORS['dynamic'],'o'),(guard,'guarded','推荐动态',STRATEGY_COLORS['guarded'],'o')]:
            q=df[(df['case']==case)&(df.strategy==strategy)]
            if len(q):
                a=q.iloc[0]
                if a.first_success_s>=0:points(ax,a.first_success_s,a.E_aux_J,size=7.,color=color,label=label,zorder=5)
        if baseline is not None:
            z=baseline[(baseline['case']==case)&(baseline.strategy=='zero_heater')]
            if len(z) and feasible(z).iloc[0]:points(ax,z.iloc[0].first_success_s,z.iloc[0].E_aux_J,size=6.,color=STRATEGY_COLORS['zero_heater'],label='零加热可行基线',zorder=6)
        ax.set(title=CASE_NAMES[case],xlabel='首次达标时间或未达标仿真终点 / s',ylabel='至实际关热的辅助电能 / J')
        ax.legend(loc='best',fontsize=7.2)
        ax.margins(x=.1,y=.18)
    fig.suptitle('有限搜索的能耗—时限边界；允许相同最优候选形成平段，不是全局最优证明',fontsize=13)
    save(fig,'图15_能耗时间候选前沿','共同规则下的有限候选能耗时间比较',
         ['constant_time_frontier.csv','constant_optimization_search.csv','main_results.csv','guarded_results.csv','constant_baselines.csv'],root)


def observer_diagnostics(root):
    example=(root/'data'/'observer_example_results.csv').exists()
    dataset='observer_example' if example else 'guarded'
    summary=read('observer_example_results.csv' if example else 'guarded_results.csv',root)
    histories={c:read(f'trajectory_{c}_{dataset}.csv',root) for c in CASE_NAMES}
    if any(h is None or 'observer_T1_C' not in h for h in histories.values()):return
    fig,axes=plt.subplots(3,3,figsize=(15.5,13.0),layout='constrained')
    for row,(case,color) in enumerate(zip(CASE_NAMES,COLORS)):
        record=summary[summary['case']==case].iloc[0];hist=histories[case]
        stop=float(record.stop_s);first=float(record.first_success_s)
        window=hist[hist.time_s<=(stop if stop>=0 else hist.time_s.max())+1e-8]
        cellerr=np.abs(window[[f'observer_T{k}_C' for k in range(1,6)]].to_numpy()-window[[f'T{k}_C' for k in range(1,6)]].to_numpy()).max(axis=1)
        eperr=np.abs(window[['observer_TEL_C','observer_TER_C']].to_numpy()-window[['TEL_C','TER_C']].to_numpy()).max(axis=1)
        points(axes[row,0],window.time_s,cellerr,color=color,label='五片最大温度估计误差')
        points(axes[row, 0], window.time_s, eperr, color='#737A80', label='端板最大温度估计误差')
        axes[row,0].set(ylabel='最大绝对温度误差 / K',xlabel='时间 / s',title=CASE_NAMES[case]+'：独立热状态')
        axes[row,0].legend(fontsize=9,loc='upper center',bbox_to_anchor=(.5,-.24),ncol=1)
        errors=window[[f'cell{k}_ice_est' for k in range(1,6)]].to_numpy()-window[[f'cell{k}_ice_bulk' for k in range(1,6)]].to_numpy()
        points(axes[row,1],window.time_s,np.max(np.abs(errors),axis=1),color=color,label='五片风险软测量最大误差')
        axes[row,1].axhline(0,color='#737A80',lw=.7)
        axes[row,1].set(xlabel='时间 / s',ylabel='冰体积分数绝对误差',title='校正冰量估计与真实局部峰值')
        axes[row,1].legend(fontsize=9,loc='upper center',bbox_to_anchor=(.5,-.24),ncol=1)
        start=max(0.,first-4.) if first>=0 else max(0.,float(hist.time_s.max())-8.)
        end=stop+1. if stop>=0 else hist.time_s.max()
        near=hist[(hist.time_s>=start)&(hist.time_s<=end)]
        points(axes[row,2],near.time_s,near[[f'T{k}_C' for k in range(1,6)]].min(axis=1),color=color,label='真实最低片温')
        points(axes[row, 2], near.time_s, near[[f'cell{k}_sensor_temperature_C' for k in range(1, 6)]].min(axis=1), color=COLORS[4], label='最近原始测温最小值')
        points(axes[row, 2], near.time_s, near[[f'cell{k}_filtered_temperature_C' for k in range(1, 6)]].min(axis=1), color='#9B8AAD', label='滤波测温最小值')
        margin=float(record.get('sensor_stop_margin_C',0.))
        axes[row,2].axhline(margin,color='#A44848',ls=':',lw=1,label=f'滤波测温阈值 {margin:g} ℃')
        axes[row,2].axhline(0,color='#777777',lw=.7)
        if first>=0:axes[row,2].axvline(first,color='#398476',ls='--',lw=1,label='真实首次达标')
        if stop>=0:axes[row,2].axvline(stop,color='#262626',ls='-.',lw=1,label='测量保持完成关热')
        axes[row,2].set(xlabel='时间 / s',ylabel='最低片温 / ℃',title='真实事件与采样停机（局部放大）')
        axes[row,2].legend(fontsize=9,ncol=2,loc='upper center',bbox_to_anchor=(.5,-.24))
    fig.suptitle('独立观测器：未参与训练的参数失配与测量噪声样例' if example else '推荐方案的独立观测与测量停机诊断',fontsize=13)
    save(fig,'图16_观测器误差与测量停机','独立观测器误差与真实首次成功、测量保持停机的区分',
         ['observer_example_results.csv' if example else 'guarded_results.csv']+[f'trajectory_{c}_{dataset}.csv' for c in CASE_NAMES],root)


def main(root=ROOT, precooling_only=False, figure=None, no_show=True, no_save=False):
    root = Path(root)
    if figure is not None:
        figure = f'{int(figure):02d}'
        if figure not in {f'{i:02d}' for i in range(1,17)}:
            raise ValueError('figure must be 01..16')
        if precooling_only and int(figure)>3:
            raise ValueError('--precooling-only only supports figures 01..03')
    OPTIONS.update(figure=figure, no_show=no_show, no_save=no_save)
    configure(); MANIFEST.clear(); precooling(root)
    if not precooling_only:
        startup_figures(root)
    if not no_save:
        manifest_path = root/'figures'/'figure_manifest.csv'
        updated = pd.DataFrame(MANIFEST)
        if manifest_path.exists():
            previous = pd.read_csv(manifest_path, encoding='utf-8-sig')
            # A selected render only replaces that figure's entry; preserve old columns.
            if len(updated):
                names = set(updated['figure'])
                preserved = previous[~previous['figure'].isin(names)]
                updated = pd.concat([preserved,updated],ignore_index=True,sort=False)
            else:
                updated = previous
        if len(updated):
            updated.sort_values('figure').to_csv(manifest_path,index=False,encoding='utf-8-sig')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--precooling-only',action='store_true')
    parser.add_argument('--figure',choices=[f'{i:02d}' for i in range(1,17)],help='只导出指定单图，不覆盖其他图或清单条目。')
    display=parser.add_mutually_exclusive_group()
    display.add_argument('--show',action='store_true',help='导出后打开交互预览。')
    display.add_argument('--no-show',action='store_true',help='只导出，不打开窗口（默认）。')
    parser.add_argument('--no-save',action='store_true',help='构建或预览图片，不覆盖文件。')
    args=parser.parse_args()
    main(args.root,args.precooling_only,args.figure,no_show=not args.show,no_save=args.no_save)
