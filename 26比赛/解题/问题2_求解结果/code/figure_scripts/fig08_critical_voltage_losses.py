"""图08：临界冷启动时端部与中心单电池电压损失分解。"""
import matplotlib.pyplot as plt
from common import COLORS, axis, cli, configure_style, discrete_points, export_and_show, numeric, read_table

FIGURE_HEIGHT=6.8
MARKER_SIZE=2.0


def build_figure():
    cases=[('临界成功侧',read_table('trajectory_critical_success.csv')),
           ('临界失败侧',read_table('trajectory_critical_failure.csv'))]
    fig,axes=plt.subplots(2,len(cases),figsize=(5*len(cases),FIGURE_HEIGHT),
                          squeeze=False,layout='constrained')
    losses=[('eta_act','活化损失',COLORS[0]),('eta_ohm','欧姆损失',COLORS[1]),
            ('eta_con','浓差损失',COLORS[2])]
    for col,(case,rows) in enumerate(cases):
        t=numeric(rows,'time_s')
        for row,cell in enumerate([1,3]):
            ax=axes[row,col]
            for field,label,color in losses:
                discrete_points(ax,t,numeric(rows,f'cell{cell}_{field}'),color,label,MARKER_SIZE)
            axis(ax,'电压损失 / V')
            ax.set_title(f'{case} · '+('端部单电池' if cell==1 else '中心单电池'))
            ax.legend(frameon=False)
    return fig


if __name__=='__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'08_临界启动电压损失分解',args)
