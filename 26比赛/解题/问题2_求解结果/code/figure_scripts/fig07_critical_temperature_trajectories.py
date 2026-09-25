"""图07：最低启动温度临界成功侧与失败侧轨迹。"""
import matplotlib.pyplot as plt
from common import COLORS, axis, cli, configure_style, discrete_points, export_and_show, numeric, read_table

FIGURE_HEIGHT=6.8
MARKER_SIZE=2.0


def build_figure():
    cases=[('临界成功侧',read_table('trajectory_critical_success.csv')),
           ('临界失败侧',read_table('trajectory_critical_failure.csv'))]
    fig,axes=plt.subplots(2,len(cases),figsize=(5*len(cases),FIGURE_HEIGHT),
                          squeeze=False,layout='constrained')
    labels=['单电池 1 = 5','单电池 2 = 4','单电池 3']
    for col,(case,rows) in enumerate(cases):
        t=numeric(rows,'time_s'); temp0=numeric(rows,'T1_C')[0]
        for index in range(3):
            discrete_points(axes[0,col],t,numeric(rows,f'T{index+1}_C'),COLORS[index],labels[index],MARKER_SIZE)
            discrete_points(axes[1,col],t,numeric(rows,f'cell{index+1}_V'),COLORS[index],labels[index],MARKER_SIZE)
        axes[0,col].axhline(0,color='#444444',lw=1,ls='--')
        axes[1,col].axhline(.3,color='#444444',lw=1,ls='--',label='安全下限 0.30 V')
        axes[0,col].set_title(f'{case}：初温 {temp0:.4f} °C')
        axis(axes[0,col],'温度 / °C'); axis(axes[1,col],'单电池电压 / V')
        axes[0,col].legend(frameon=False); axes[1,col].legend(frameon=False)
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'07_最低启动温度两侧轨迹',args)
