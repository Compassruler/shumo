"""图11：参数与边界假设敏感性离散圆点图。"""
import numpy as np
import matplotlib.pyplot as plt
from common import COLORS, axis, cli, configure_style, export_and_show, field, numeric, pick, read_table

POINT_SIZE=22


def build_figure():
    rows=read_table('sensitivity.csv')
    labelkey=pick(rows,'case','scenario','label','parameter','name','parameter_name')
    timekey=pick(rows,'end_time_s','startup_time_s')
    valuekey=pick(rows,'value','factor','multiplier','parameter_value')
    raw=[r[labelkey]+(f" = {r[valuekey]}" if valuekey and r[valuekey] else '') for r in rows]
    names={'baseline':'基准','intercell_conductance_0.8':'片间导度 ×0.8',
           'intercell_conductance_1.2':'片间导度 ×1.2','endplate_coupling_0.8':'端板耦合导度 ×0.8',
           'endplate_coupling_1.2':'端板耦合导度 ×1.2','endplate_capacity_0.8':'端板热容 ×0.8',
           'endplate_capacity_1.2':'端板热容 ×1.2','convection_on_endplate':'对流置于端板',
           'end_beta_1':'端部浓差系数 =1','fixed_dry_conductance':'固定初始干态导度',
           'freezing_rate_0.1':'冻结速率 ×0.1','freezing_rate_10.0':'冻结速率 ×10'}
    labels=[names.get(str(x),str(x).replace('_',' ')) for x in raw]
    colors=[COLORS[0] if field(r,'status',default='success')=='success' else COLORS[1] for r in rows]
    metrics=[(timekey,'启动 / 终止时间 / s')]
    if 'min_voltage_V' in rows[0]: metrics.append(('min_voltage_V','最低电压 / V'))
    fig,axes=plt.subplots(1,len(metrics),figsize=(6.2*len(metrics),max(3.8,.37*len(rows)+1)),
                          squeeze=False,layout='constrained',sharey=True)
    pos=np.arange(len(rows))
    for ax,(key,xlabel) in zip(axes[0],metrics):
        values=numeric(rows,key)
        # 每个敏感性工况是一个离散结果，统一用实心圆而不是条形。
        ax.scatter(values,pos,c=colors,s=POINT_SIZE,marker='o',edgecolors='white',linewidths=.25,zorder=3)
        ax.set_yticks(pos,labels); axis(ax,'',xlabel); ax.grid(axis='y',visible=False)
        if key=='min_voltage_V': ax.axvline(.3,color='#444444',ls='--',lw=1)
        for y,value in zip(pos,values):
            if np.isfinite(value): ax.annotate(f'{value:.3f}',(value,y),xytext=(4,0),textcoords='offset points',va='center',fontsize=8)
    axes[0,0].invert_yaxis()
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'11_参数与边界假设敏感性',args)
