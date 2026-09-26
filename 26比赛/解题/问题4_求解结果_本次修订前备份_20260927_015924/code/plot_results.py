"""Render the Q4 CSV results into publication-ready PNG and vector SVG files.

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
sys.path.insert(0, str(ROOT / '.python_deps'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import Normalize
from matplotlib.ticker import NullLocator

COLORS = ['#155B8E', '#D57524', '#259989', '#A25386', '#697683']
CASE_NAMES = {'case1': '工况1：完全冷却', 'case2': '工况2：预冷20 min',
              'case3': '工况3：预冷40 min'}
STRATEGY_NAMES = {'dynamic': '动态反馈', 'constant': '恒功率基准',
                  'D': '动态反馈', 'C': '恒功率基准',
                  'constant_hold': '恒功率＋2 s保持', 'constant_first':'恒功率首次过零'}
MANIFEST = []


def configure():
    candidates = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'SimSun']
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((s for s in candidates if s in available), 'DejaVu Sans')
    plt.rcParams.update({'font.family': [chosen,'DejaVu Sans'], 'font.size': 11,
        'axes.titlesize': 12, 'axes.labelsize': 11, 'legend.fontsize': 9,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.unicode_minus': False, 'svg.fonttype': 'path',
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'grid.alpha': .22, 'grid.linewidth': .65, 'axes.grid': True,
        'lines.linewidth': 1.8, 'savefig.facecolor': 'white'})


def read(name, root=ROOT):
    path = root / 'data' / name
    return pd.read_csv(path, encoding='utf-8-sig') if path.exists() else None


def save(fig, name, title, sources, root=ROOT):
    out = root / 'figures'
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / (name+'.png'), dpi=300, bbox_inches='tight', pad_inches=.15)
    fig.savefig(out / (name+'.svg'), bbox_inches='tight', pad_inches=.15)
    plt.close(fig)
    MANIFEST.append({'figure': name, 'title': title, 'source_csv': ';'.join(sources),
                     'png_dpi': 300, 'png': name+'.png', 'svg': name+'.svg'})
    print('Saved', name)


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
        axes[0].plot(group.x_mm, group.temperature_C, color=cmap(norm(t)), lw=1.6)
        if t in (10, 20, 40, 100):
            axes[1].plot(group.x_mm, group.temperature_C - group.temperature_C.min(),
                         color=cmap(norm(t)), label=f'{t:g} min')
    axes[0].set(xlabel='层叠方向 x / mm', ylabel='温度 / ℃', title='(a) 10–100 min 温度场族（间隔5 min）')
    axes[1].set(xlabel='层叠方向 x / mm', ylabel='相对当时最低温度 / K', title='(b) 空间温差细节')
    for ax in axes:
        ax.axvspan(0, 10, color='#9EB4BF', alpha=.12, zorder=0)
        ax.axvspan(float(layers.x_right_mm.max())-10, float(layers.x_right_mm.max()),
                   color='#9EB4BF', alpha=.12, zorder=0)
        ax.set_xlim(0, float(layers.x_right_mm.max()))
    axes[1].legend(title='预冷时间', loc='upper right')
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes[0], pad=.025)
    cb.set_label('预冷时间 / min')
    save(fig,'图01_预冷温度场族','预冷温度场族与空间温差细节', ['precooling_fields.csv'],root)

    fig,axes=plt.subplots(1,2,figsize=(12.6,4.5),layout='constrained')
    for key,label,color in [('mean_capacity_C','热容加权均温',COLORS[0]),
            ('T3_C','中间电池均温',COLORS[1]),('surface_left_C','左外表面温度',COLORS[2])]:
        axes[0].plot(nodes.cooling_min,nodes[key],'-o',ms=3,label=label,color=color)
    axes[0].axhline(-30,color='#5C6267',ls='--',lw=1,label='环境 −30 ℃')
    axes[0].set(xlabel='预冷时间 / min',ylabel='温度 / ℃',title='(a) 整体降温与环境渐近')
    axes[0].legend()
    for key,label,color in [('field_range_K','全场极差（含真实表面）',COLORS[0]),
            ('center_minus_left_EP_K','中片—左端板均温差',COLORS[1]),
            ('cell_range_K','五片电池均温极差',COLORS[2])]:
        axes[1].plot(nodes.cooling_min,nodes[key],'-o',ms=3,label=label,color=color)
    axes[1].set(xlabel='预冷时间 / min',ylabel='同一时刻温差 / K',title='(b) 三种温差定义与预冷程度')
    axes[1].legend()
    save(fig,'图02_预冷均温与温差','预冷均温及不同口径温差',['precooling_nodes.csv'],root)

    fig,axes=plt.subplots(1,3,figsize=(13.0,4.2),layout='constrained')
    order=['TEL_C','T1_C','T2_C','T3_C','T4_C','T5_C','TER_C']
    ticklabels=['左端板','1','2','3','4','5','右端板']
    for ax,(_,row),color in zip(axes,cases.iterrows(),COLORS):
        values=row[order].to_numpy(dtype=float)
        ax.plot(range(7),values,'o-',color=color,ms=5)
        ax.axhline(row.mean_capacity_C,color='#666666',ls='--',lw=1,label='全场热容加权均温')
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


def startup_figures(root=ROOT):
    summary=read('main_results.csv',root)
    if summary is None:
        raise FileNotFoundError('main_results.csv missing; use --precooling-only for partial output')
    for number,case in enumerate(CASE_NAMES,4):
        hist=read(f'trajectory_{case}_dynamic.csv',root)
        const=read(f'trajectory_{case}_constant_hold.csv',root)
        if hist is None:
            raise FileNotFoundError(f'Missing dynamic trajectory: {case}')
        record=summary[(summary['case']==case)&(summary.strategy=='dynamic')].iloc[0]
        stop=float(record.stop_s)
        fig,axes=plt.subplots(2,2,figsize=(12.6,8.0),layout='constrained')
        styles=['-','-','-','--',':']
        for k,color,style in zip(range(1,6),COLORS,styles):
            axes[0,0].step(hist.time_s,hist[f'cell{k}_q_W_cm2'],where='pre',color=color,ls=style,label=f'电池{k}')
            axes[0,1].plot(hist.time_s,hist[f'T{k}_C'],color=color,ls=style,label=f'电池{k}')
            axes[1,0].plot(hist.time_s,hist[f'cell{k}_V_V'],color=color,ls=style)
            axes[1,1].plot(hist.time_s,hist[f'cell{k}_ice_bulk'],color=color,ls=style)
        if const is not None:
            cut=const[const.time_s<=float(summary[(summary['case']==case)&(summary.strategy=='constant_hold')].iloc[0].stop_s)+1e-7]
            if len(cut):
                axes[0,1].plot(cut.time_s,cut[[f'T{k}_C' for k in range(1,6)]].min(axis=1),color='#3C3C3C',ls='-.',lw=1.6,label='恒功率最低片温')
        axes[0,0].axhline(1,color='#72777C',ls='--',lw=1)
        axes[0,0].set(ylabel='单片功率密度 / (W/cm²)',ylim=(-.03,1.1),title='(a) 五路独立功率（区间保持）')
        axes[0,0].legend(ncol=3,loc='upper left')
        axes[0,1].axhline(0,color='#72777C',ls='--',lw=1)
        axes[0,1].set(ylabel='单片平均温度 / ℃',title='(b) 温升过程及恒功率参考')
        axes[0,1].legend(ncol=3,fontsize=8)
        axes[1,0].axhline(.3,color='#B84440',ls='--',lw=1.2,label='安全下限 0.30 V')
        axes[1,0].set(ylabel='单片电压 / V',title='(c) 电压约束')
        axes[1,0].legend(loc='best')
        axes[1,1].axhline(.99,color='#B84440',ls='--',lw=1.2,label='严重冰堵阈值 0.99')
        axes[1,1].set(ylabel='MEA局部最大冰体积分数',title='(d) 冰量约束（全MEA局部最大值）',ylim=(-.035,1.06))
        axes[1,1].legend(loc='best')
        for ax in axes.flat:
            ax.set_xlabel('冷启动时间 / s')
            ax.axvline(stop,color='#858B90',ls=':',lw=1.2)
            if float(hist.time_s.max())>stop+.01:
                ax.axvspan(stop,float(hist.time_s.max()),color='#DDE6EB',alpha=.45,zorder=0)
        fig.suptitle(f'{CASE_NAMES[case]}｜动态控制全过程；虚线右侧为关热后验证',fontsize=14)
        save(fig,f'图{number:02d}_{case}_动态控制轨迹',f'{CASE_NAMES[case]}动态控制轨迹',
             [f'trajectory_{case}_dynamic.csv',f'trajectory_{case}_constant_hold.csv'],root)

    fig,axes=plt.subplots(2,3,figsize=(13.0,8.0),layout='constrained')
    metrics=[('E_aux_J','辅助加热总能耗 / J'),('stop_s','完成保持并关热 / s'),
             ('first_success_s','首次满足条件 / s'),('dTmax_K','过程最大五片温差 / K'),
             ('min_voltage_V','过程最低单片电压 / V'),('max_ice_bulk','过程最大冰体积分数')]
    x=np.arange(3);width=.35
    for ax,(key,label) in zip(axes.flat,metrics):
        for offset,strategy,color in [(-.5,'dynamic',COLORS[0]),(.5,'constant_hold',COLORS[1])]:
            vals=np.array([float(summary[(summary['case']==c)&(summary.strategy==strategy)].iloc[0][key]) for c in CASE_NAMES])
            bars=ax.bar(x+offset*width,vals,width,label=STRATEGY_NAMES[strategy],color=color)
            labels=[f'{v:.1e}' if key=='max_ice_bulk' and 0<v<.001 else (f'{v:.3f}' if key=='max_ice_bulk' else f'{v:.2f}') for v in vals]
            ax.bar_label(bars,labels=labels,fontsize=8,padding=3)
        ax.set_xticks(x,['完全冷却','预冷20 min','预冷40 min'])
        ax.set_ylabel(label)
        ax.margins(y=.18)
    axes[0,0].legend(loc='upper right',fontsize=9)
    fig.suptitle('同一终止口径比较：首次全片达标后连续保持2 s，均统计到实际关热',fontsize=14)
    save(fig,'图07_三工况主指标比较','动态与恒功率在统一保持窗口下的比较',['main_results.csv'],root)

    scan=read('constant_scan.csv',root)
    if scan is None:raise FileNotFoundError('constant_scan.csv missing')
    fig,axes=plt.subplots(2,3,figsize=(13.0,7.8),layout='constrained')
    scanmetrics=[('mean_capacity_C','预冷热容加权均温 / ℃'),('E_aux_J','辅助能耗 / J'),
                 ('first_success_s','首次满足条件 / s'),('dTmax_K','最大五片温差 / K'),
                 ('min_voltage_V','最低单片电压 / V'),('max_ice_bulk','最大冰体积分数')]
    for ax,(key,label),color in zip(axes.flat,scanmetrics,COLORS+[COLORS[0]]):
        ax.plot(scan.cooling_min,scan[key],'-o',ms=3.5,color=color)
        if 'feasible' in scan:
            bad=scan[~scan.feasible.astype(bool)]
            if len(bad):ax.scatter(bad.cooling_min,bad[key],color='#C54746',marker='x',s=60,label='不可行')
        ax.set(xlabel='预冷时间 / min',ylabel=label)
        ax.set_xticks([10,25,40,55,70,85,100])
        if key=='min_voltage_V':ax.axhline(.3,color='#B84440',ls='--',lw=1)
        if key=='max_ice_bulk':ax.axhline(.99,color='#B84440',ls='--',lw=1)
    fig.suptitle('固定问题三功率分配，10–100 min预冷共19点扫描',fontsize=14)
    save(fig,'图08_预冷时间扫描','固定恒功率策略随预冷时间的变化',['constant_scan.csv'],root)

    fig,axes=plt.subplots(1,2,figsize=(12.8,5.0),layout='constrained')
    keep=summary[summary.strategy.isin(['dynamic','constant_hold'])].copy()
    labels=[CASE_NAMES[r['case']].split('：')[-1]+'\n'+('动态' if r.strategy=='dynamic' else '恒功率') for _,r in keep.iterrows()]
    x=np.arange(len(keep));bottom=np.zeros(len(keep))
    for key,label,color in [('E_aux_J','辅助输入',COLORS[0]),('E_gen_J','反应产热',COLORS[1]),('E_phase_J','相变净释热',COLORS[2])]:
        vals=keep[key].to_numpy(float);axes[0].bar(x,vals,bottom=bottom,label=label,color=color,width=.7);bottom+=vals
    axes[0].plot(x,keep.E_sensible_J+keep.E_loss_J,'k_',markersize=18,label='显热增量＋环境散热')
    axes[0].set_xticks(x,labels,fontsize=8)
    axes[0].set(ylabel='离散能量收支 / J',title='(a) 输入与去向的总量闭合')
    axes[0].legend(ncol=2,fontsize=9)
    for case,color in zip(CASE_NAMES,COLORS):
        hst=read(f'trajectory_{case}_dynamic.csv',root)
        s=keep[(keep['case']==case)&(keep.strategy=='dynamic')].iloc[0]
        hst=hst[hst.time_s<=s.stop_s+1e-7]
        axes[1].plot(hst.time_s,hst.E_aux_J,color=color,label=CASE_NAMES[case])
    axes[1].set(xlabel='冷启动时间 / s',ylabel='累计辅助加热能耗 / J',title='(b) 动态策略电能积分')
    axes[1].legend()
    save(fig,'图09_能量收支与累积能耗','离散能量闭合与动态累计电能',['main_results.csv']+[f'trajectory_{c}_dynamic.csv' for c in CASE_NAMES],root)

    convergence(root)
    sensitivity(root)
    robustness(root)
    if read('guarded_results.csv',root) is not None:
        guarded(root)


def convergence(root):
    pre=read('precooling_convergence.csv',root); start=read('startup_convergence.csv',root)
    if start is None:raise FileNotFoundError('startup_convergence.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(12.6,7.8),layout='constrained')
    for (study,t),g in pre.groupby(['study','cooling_min']):
        ax=axes[0,0] if study=='time' else axes[0,1]
        key='dt_s' if study=='time' else 'control_volumes'
        y='max_field_error_K' if study=='time' else 'max_node_error_K'
        group=g.sort_values(key)
        good=group[group[y]>1e-12]
        ax.loglog(good[key],good[y],'-o',ms=4,label=f'{t:g} min')
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
        axes[1,0].plot(g.scale*29,g.E_aux_J-reference.E_aux_J,'o-',color=color,label=CASE_NAMES[case])
        axes[1,1].plot(g.scale*29,g.max_ice_bulk,'o-',color=color,label=CASE_NAMES[case])
        joint=read('coupled_convergence.csv',root)
        if joint is not None:
            j=joint[joint['case']==case].sort_values('scale')
            axes[1,0].plot(j.scale*29,j.E_aux_J-reference.E_aux_J,'s--',color=color,ms=4)
            axes[1,1].plot(j.scale*29,j.max_ice_bulk,'s--',color=color,ms=4)
        for ax in axes[1]:
            ax.set_xscale('log',base=2)
            ax.set_xticks(g.scale*29,[f'{x:g}' for x in g.scale*29],fontsize=9)
            ax.xaxis.set_minor_locator(NullLocator())
            ax.set_xlabel('每片MEA水相控制体数')
    axes[1,0].set(ylabel='相对正式58控制体的能耗差 / J',title='(c) 总体能耗对空间加密的响应')
    axes[1,1].set(ylabel='MEA局部最大冰体积分数',title='(d) 实线固定dt；虚线联合减半dt')
    axes[1,0].axhline(0,color='#666666',ls='--',lw=.7)
    axes[1,0].legend(fontsize=8)
    save(fig,'图10_网格步长与控制周期检验','预冷与启动阶段的数值收敛检验',['precooling_convergence.csv','startup_convergence.csv','coupled_convergence.csv'],root)


def sensitivity(root):
    pre=read('precooling_sensitivity.csv',root);start=read('sensitivity.csv',root)
    if start is None:raise FileNotFoundError('sensitivity.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(13.0,8.4),layout='constrained')
    for factor,g in pre[pre.cooling_min==20].groupby('conductance_factor'):
        g=g.sort_values('h_W_m2K')
        axes[0,0].plot(g.h_W_m2K,g.field_range_K,'-o',ms=4,label=f'导热倍率 {factor:g}')
        axes[0,1].plot(g.h_W_m2K,g.relative_field_range,'-o',ms=4,label=f'导热倍率 {factor:g}')
    axes[0,0].set(xlabel='端面换热 h / [W/(m²·K)]',ylabel='全场绝对温差 / K',title='(a) 预冷20 min：绝对不均匀程度')
    axes[0,1].set(xlabel='端面换热 h / [W/(m²·K)]',ylabel='全场温差 / (热容均温−环境温度)',title='(b) 预冷20 min：归一化不均匀程度')
    axes[0,0].legend(fontsize=8,ncol=2)
    case=next(iter(CASE_NAMES));g=start[start['case']==case].reset_index(drop=True)
    if not len(g):g=start.reset_index(drop=True)
    labels=[f'{r.parameter}\n×{r.factor:g}' for _,r in g.iterrows()]
    for ax,key,label,color in [(axes[1,0],'E_aux_J','辅助能耗 / J',COLORS[0]),(axes[1,1],'dTmax_K','最大五片温差 / K',COLORS[1])]:
        ax.bar(range(len(g)),g[key],color=color,width=.75)
        ax.set_xticks(range(len(g)),labels,rotation=55,ha='right',fontsize=7.5)
        ax.set_ylabel(label)
        ax.set_title('工况1固定控制参数的单因素扰动')
        if 'feasible' in g:
            for i,r in g.iterrows():
                if not bool(r.feasible):ax.text(i,float(r[key]),'失败',color='#C54746',ha='center',va='bottom',fontsize=8)
    save(fig,'图11_物理参数与控制器敏感性','预冷传热参数与启动控制参数敏感性',['precooling_sensitivity.csv','sensitivity.csv'],root)


def robustness(root):
    df=read('robustness.csv',root)
    if df is None:raise FileNotFoundError('robustness.csv missing')
    fig,axes=plt.subplots(2,2,figsize=(12.6,8.0),layout='constrained')
    df=df.reset_index(drop=True)
    df['completion_display_s']=np.where(df.feasible,df.stop_s,96.6666666667)
    metrics=[('E_aux_J','辅助加热能耗 / J'),('completion_display_s','完成2 s保持并关热 / s'),
             ('min_voltage_V','最低单片电压 / V'),('max_ice_bulk','最大冰体积分数')]
    for case,color in zip(CASE_NAMES,COLORS):
        g=df[df['case']==case]
        for ax,(key,label) in zip(axes.flat,metrics):
            good=g[g.feasible];bad=g[~g.feasible]
            ax.scatter(good.index+1,good[key],color=color,s=26,label=CASE_NAMES[case],alpha=.85)
            ax.scatter(bad.index+1,bad[key],color=color,s=32,marker='x',linewidths=1.3)
            ax.set(xlabel='扰动试验编号（CSV数据行）',ylabel=label)
    axes[0,0].legend(loc='best',fontsize=8)
    axes[0,1].axhline(96.6666666667,color='#B84440',ls='--',lw=1.1)
    axes[0,1].text(.03,.08,'× 未在截止前完成保持；时间置于截止线示意',transform=axes[0,1].transAxes,fontsize=9)
    axes[1,0].axhline(.3,color='#B84440',ls='--',lw=1,label='安全下限')
    axes[1,1].axhline(.99,color='#B84440',ls='--',lw=1,label='严重冰堵阈值')
    fig.suptitle('固定参数的测量/初场扰动：圆点为可行，叉号为未完成规定保持',fontsize=13)
    save(fig,'图12_测量噪声与初场扰动','测量噪声和初场偏差下的能耗与安全约束',['robustness.csv'],root)


def guarded(root):
    nominal=read('main_results.csv',root);alt=read('guarded_results.csv',root)
    nnoise=read('robustness.csv',root);anoise=read('guarded_robustness.csv',root)
    fig,axes=plt.subplots(2,2,figsize=(12.4,8),layout='constrained')
    x=np.arange(3);width=.35
    for offset,df,ndf,color,label in [(-.5,nominal[nominal.strategy=='dynamic'],nnoise,COLORS[0],'名义能耗优选'),
                                      (.5,alt,anoise,COLORS[1],'留裕度备选')]:
        data=df.set_index('case').reindex(list(CASE_NAMES))
        values=[data.E_aux_J.to_numpy(),data.stop_s.to_numpy(),
                np.array([100*ndf[ndf['case']==c].feasible.mean() for c in CASE_NAMES]),
                data.post_min_T_C.to_numpy()]
        for ax,vals in zip(axes.flat,values):
            bars=ax.bar(x+offset*width,vals,width,color=color,label=label)
            ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=9)
            ax.set_xticks(x,['完全冷却','预冷20 min','预冷40 min'])
            ax.margins(y=.18)
    for ax,label,title in zip(axes.flat,['辅助电能 / J','关热时刻 / s','扰动试验可行比例 / %','关热后60 s最低片温 / ℃'],
           ['(a) 以少量额外电能预留裕度','(b) 提前完成连续2 s保持','(c) 独立试验种子组，均为30次/工况','(d) 两者均未保证深冷工况持续暖态']):
        ax.set(ylabel=label,title=title)
    axes[0,0].legend(loc='upper right',fontsize=9)
    axes[0,1].axhline(96.6666667,color='#B84440',ls='--',lw=1)
    axes[1,0].set_ylim(0,120)
    axes[1,1].axhline(0,color='#666666',ls='--',lw=1)
    fig.suptitle('名义辅助能耗优选与有限扰动测试通过的备选：结果及限制同时呈现',fontsize=13)
    save(fig,'图13_名义与留裕度备选','名义策略与留裕度备选的能耗、时间、扰动可行比例及关热后温度',
         ['main_results.csv','guarded_results.csv','robustness.csv','guarded_robustness.csv'],root)


def main(root=ROOT, precooling_only=False):
    configure(); MANIFEST.clear(); precooling(root)
    if not precooling_only:
        startup_figures(root)
    pd.DataFrame(MANIFEST).to_csv(root/'figures'/'figure_manifest.csv', index=False,encoding='utf-8-sig')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--precooling-only',action='store_true')
    args=parser.parse_args()
    main(args.root,args.precooling_only)
